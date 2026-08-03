from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, session, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import CourseStaff, User, Course, Student, FeeCollection, Expense, AuditLog, ApprovalRequest, ClassSession, Attendance, Donation
from helpers import calculate_attendance

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    if current_user.role in ['Teacher', 'CR', 'TA']:
        return redirect(url_for('staff.portal'))
    
    # Session Persistence
    if 'filter_applied' in request.args:
        selected_course_id = request.args.get('course_id', '')
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')
        session['dash_course_id'] = selected_course_id
        session['dash_start_date'] = start_date_str
        session['dash_end_date'] = end_date_str
    else:
        selected_course_id = session.get('dash_course_id', '')
        start_date_str = session.get('dash_start_date', '')
        end_date_str = session.get('dash_end_date', '')

    start_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except:
            pass
            
    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except:
            pass

    current_year = date.today().year
    current_month = date.today().month
    today_date = date.today()
    
    # Common variables
    total_active_students = 0
    hand_cash = 0.0
    in_account = 0.0
    total_fees = 0.0
    total_expenses = 0.0
    net_balance = 0.0
    students_paid_count = 0
    
    latest_fees = []
    latest_expenses = []

    # Prepare base queries based on role

    course_overview = None
    if selected_course_id and selected_course_id.isdigit():
        c_id = int(selected_course_id)
        sel_course = Course.query.get(c_id)
        
        if sel_course:
            session_query = ClassSession.query.filter_by(course_id=c_id, status='Submitted')
            if start_date:
                session_query = session_query.filter(ClassSession.date >= start_date)
            if end_date:
                session_query = session_query.filter(ClassSession.date <= end_date)
            total_sessions = session_query.count()
            active_staff = CourseStaff.query.filter_by(course_id=c_id).join(User, CourseStaff.user_id == User.id).filter(User.status == 'Active').all()
            
            crs = [s for s in active_staff if s.role_in_course == 'CR']
            tas = [s for s in active_staff if s.role_in_course == 'TA']
            teachers = [s for s in active_staff if s.role_in_course == 'Teacher']
            
            teacher_stats = []
            for t in teachers:
                subjects = [s.strip() for s in t.subjects_taught.split(',')] if t.subjects_taught else []
                sub_counts = {}
                for sub in subjects:
                    if sub:
                        sub_q = ClassSession.query.filter_by(course_id=c_id, subject_name=sub)
                        if start_date:
                            sub_q = sub_q.filter(ClassSession.date >= start_date)
                        if end_date:
                            sub_q = sub_q.filter(ClassSession.date <= end_date)
                        count = sub_q.count()
                        sub_counts[sub] = count
                        
                teacher_stats.append({
                    'name': t.user.full_name,
                    'subjects': sub_counts
                })
                
            from sqlalchemy import func
            sb_q = db.session.query(ClassSession.subject_name, func.count(ClassSession.id)).filter(ClassSession.course_id == c_id)
            if start_date:
                sb_q = sb_q.filter(ClassSession.date >= start_date)
            if end_date:
                sb_q = sb_q.filter(ClassSession.date <= end_date)
            subject_breakdown_query = sb_q.group_by(ClassSession.subject_name).all()
            
            subject_breakdown = {sub: count for sub, count in subject_breakdown_query if sub}

            course_overview = {
                'course': sel_course,
                'duration': sel_course.duration,
                'total_sessions': total_sessions,
                'subject_breakdown': subject_breakdown,
                'crs': crs,
                'teachers': teacher_stats,
                'tas': tas
            }

    if current_user.role == 'Coordinator':
        assigned_courses = Course.query.filter_by(coordinator_id=current_user.id).all()
        assigned_course_ids = [c.id for c in assigned_courses]
        courses_list = assigned_courses
        
        if not assigned_course_ids:
            return render_template('dashboard.html', 
                                   total_active_students=0, hand_cash=0.0, in_account=0.0,
                                   total_fees=0.0, total_expenses=0.0, total_donations=0.0, donations=[], latest_donations=[], net_balance=0.0, students_paid_count=0, current_cycle_month_name='',
                                   latest_fees=[], latest_expenses=[], courses=[],
                                   today_collections=0.0, monthly_collections=0.0,
                                   expenses_added=0.0, pending_requests_count=0,
                                   selected_course_id='', start_date_str='', end_date_str='',
                                   active_course_staff=[], active_course_students=[])
            
        base_fee_q = FeeCollection.query.join(Student).filter(Student.course_id.in_(assigned_course_ids), FeeCollection.is_deleted==False)
        base_exp_q = Expense.query.filter(Expense.course_id.in_(assigned_course_ids), Expense.is_deleted==False)
        base_don_q = Donation.query.filter(Donation.deleted_at.is_(None)) # Donations are not course-specific usually, but let's keep them global or filter if needed. Let's make them global for now.
        base_stu_q = Student.query.filter(Student.course_id.in_(assigned_course_ids), Student.status=='Active')
        
    else: # Admin
        courses_list = Course.query.filter_by(status='Active').all()
        base_fee_q = FeeCollection.query.join(Student).filter(FeeCollection.is_deleted==False)
        base_exp_q = Expense.query.filter(Expense.is_deleted==False)
        base_don_q = Donation.query.filter(Donation.deleted_at.is_(None))
        base_stu_q = Student.query.filter(Student.status=='Active')
    if not selected_course_id and courses_list:
        selected_course_id = str(courses_list[0].id)

    # Apply Course Filter
    if selected_course_id and selected_course_id.isdigit():
        c_id = int(selected_course_id)
        if current_user.role == 'Admin' or c_id in assigned_course_ids:
            base_fee_q = base_fee_q.filter(Student.course_id == c_id)
            base_exp_q = base_exp_q.filter(Expense.course_id == c_id)
            base_stu_q = base_stu_q.filter(Student.course_id == c_id)

    total_active_students = base_stu_q.count()

    # Apply Date Filters (for financial metrics)
    if start_date:
        base_fee_q = base_fee_q.filter(FeeCollection.date_collected >= start_date)
        base_exp_q = base_exp_q.filter(Expense.expense_date >= start_date)
        base_don_q = base_don_q.filter(Donation.date >= start_date)
    if end_date:
        base_fee_q = base_fee_q.filter(FeeCollection.date_collected <= end_date)
        base_exp_q = base_exp_q.filter(Expense.expense_date <= end_date)
        base_don_q = base_don_q.filter(Donation.date <= end_date)

    # Calculate Metrics
    fees = base_fee_q.all()
    hand_cash = sum(f.amount_paid for f in fees if f.payment_method == 'Cash')
    in_account = sum(f.amount_paid for f in fees if f.payment_method == 'Online')
    total_fees = hand_cash + in_account
    expenses = base_exp_q.all()
    total_expenses = sum(e.amount for e in expenses)
    donations = base_don_q.order_by(Donation.date.desc()).all()
    total_donations = sum(d.amount for d in donations)
    
    # Calculate students paid count dynamically based on the course start_date
    students_paid_count = 0
    if selected_course_id and selected_course_id.isdigit():
        c_id_for_fee = int(selected_course_id)
        course_obj = Course.query.get(c_id_for_fee)
        if course_obj and course_obj.start_date:
            from dateutil.relativedelta import relativedelta
            
            start_d = course_obj.start_date
            today_d = date.today()
            
            # If the course starts in the future, count starts from start_date
            if today_d < start_d:
                current_cycle_start = start_d
            else:
                # Find the month boundary where start_d + X months <= today_d < start_d + (X+1) months
                current_cycle_start = start_d
                while current_cycle_start + relativedelta(months=1) <= today_d:
                    current_cycle_start += relativedelta(months=1)
                    
            current_cycle_end = current_cycle_start + relativedelta(months=1) - timedelta(days=1)
            
            # Filter fees to this specific current cycle using the new fee_month logic
            current_cycle_str = current_cycle_start.strftime('%Y-%m')
            cycle_fees = [f for f in fees if f.fee_month == current_cycle_str]
            students_paid_count = len(set(f.student_id for f in cycle_fees))
            current_cycle_month_name = current_cycle_start.strftime('%B')
            cycle_collections = sum(f.amount_paid for f in cycle_fees)
            monthly_collections_override = cycle_collections
            
            # Expenses remain time-bound
            cycle_expenses = sum(e.amount for e in expenses if e.expense_date and current_cycle_start <= e.expense_date.date() <= current_cycle_end)
            monthly_expenses_override = cycle_expenses
            
            # Donations remain time-bound
            cycle_donations = sum(d.amount for d in donations if d.date and current_cycle_start <= d.date <= current_cycle_end)
            monthly_donations_override = cycle_donations
            
            # Calculate Next Cycle Advance Payments
            next_cycle_start = current_cycle_start + relativedelta(months=1)
            next_cycle_str = next_cycle_start.strftime('%Y-%m')
            next_cycle_fees = [f for f in fees if f.fee_month == next_cycle_str]
            next_cycle_students_paid_count = len(set(f.student_id for f in next_cycle_fees))
            next_cycle_month_name = next_cycle_start.strftime('%B')
        else:
            students_paid_count = len(set(f.student_id for f in fees))
    else:
        students_paid_count = len(set(f.student_id for f in fees))

    net_balance = total_fees + total_donations - total_expenses
    
    latest_fees = base_fee_q.order_by(FeeCollection.date_collected.desc()).limit(5).all()
    latest_expenses = base_exp_q.order_by(Expense.expense_date.desc()).limit(5).all()
    latest_donations = base_don_q.order_by(Donation.date.desc()).limit(5).all()

    # Role specific logic

    course_overview = None
    if selected_course_id and selected_course_id.isdigit():
        c_id = int(selected_course_id)
        sel_course = Course.query.get(c_id)
        
        if sel_course:
            session_query = ClassSession.query.filter_by(course_id=c_id, status='Submitted')
            if start_date:
                session_query = session_query.filter(ClassSession.date >= start_date)
            if end_date:
                session_query = session_query.filter(ClassSession.date <= end_date)
            total_sessions = session_query.count()
            active_staff = CourseStaff.query.filter_by(course_id=c_id).join(User, CourseStaff.user_id == User.id).filter(User.status == 'Active').all()
            
            crs = [s for s in active_staff if s.role_in_course == 'CR']
            tas = [s for s in active_staff if s.role_in_course == 'TA']
            teachers = [s for s in active_staff if s.role_in_course == 'Teacher']
            
            teacher_stats = []
            for t in teachers:
                subjects = [s.strip() for s in t.subjects_taught.split(',')] if t.subjects_taught else []
                sub_counts = {}
                for sub in subjects:
                    if sub:
                        sub_q = ClassSession.query.filter_by(course_id=c_id, subject_name=sub)
                        if start_date:
                            sub_q = sub_q.filter(ClassSession.date >= start_date)
                        if end_date:
                            sub_q = sub_q.filter(ClassSession.date <= end_date)
                        count = sub_q.count()
                        sub_counts[sub] = count
                        
                teacher_stats.append({
                    'name': t.user.full_name,
                    'subjects': sub_counts
                })
                
            from sqlalchemy import func
            sb_q = db.session.query(ClassSession.subject_name, func.count(ClassSession.id)).filter(ClassSession.course_id == c_id)
            if start_date:
                sb_q = sb_q.filter(ClassSession.date >= start_date)
            if end_date:
                sb_q = sb_q.filter(ClassSession.date <= end_date)
            subject_breakdown_query = sb_q.group_by(ClassSession.subject_name).all()
            
            subject_breakdown = {sub: count for sub, count in subject_breakdown_query if sub}

            course_overview = {
                'course': sel_course,
                'duration': sel_course.duration,
                'total_sessions': total_sessions,
                'subject_breakdown': subject_breakdown,
                'crs': crs,
                'teachers': teacher_stats,
                'tas': tas
            }

    if current_user.role == 'Coordinator':
        # Unfiltered by date for today/month summary metrics, but filtered by course
        coord_fee_q = FeeCollection.query.join(Student).filter(FeeCollection.is_deleted==False)
        if selected_course_id and selected_course_id.isdigit() and int(selected_course_id) in assigned_course_ids:
            coord_fee_q = coord_fee_q.filter(Student.course_id == int(selected_course_id))
        else:
            coord_fee_q = coord_fee_q.filter(Student.course_id.in_(assigned_course_ids))
            
        all_coord_fees = coord_fee_q.all()
        today_collections = sum([f.amount_paid for f in all_coord_fees if f.date_collected.date() == today_date])
        monthly_collections = sum([f.amount_paid for f in all_coord_fees if f.date_collected.year == current_year and f.date_collected.month == current_month])
        if 'monthly_collections_override' in locals():
            monthly_collections = monthly_collections_override
        
        pending_requests_count = ApprovalRequest.query.filter_by(requested_by_id=current_user.id, status='Pending').count()
        
        active_students_list = base_stu_q.all()
        
        def get_daily_absentees(target_date):
            absentees = []
            sessions = ClassSession.query.filter(
                ClassSession.course_id.in_(assigned_course_ids), 
                ClassSession.date == target_date,
                ClassSession.status == 'Submitted'
            ).all()
            if not sessions:
                return []
                
            course_sessions = {}
            for s in sessions:
                course_sessions.setdefault(s.course_id, []).append(s)
                
            session_ids = [s.id for s in sessions]
            all_attendance = Attendance.query.filter(Attendance.session_id.in_(session_ids)).all()
            att_dict = {}
            for a in all_attendance:
                att_dict.setdefault(a.student_id, {})[a.session_id] = a.status
                
            for student in active_students_list:
                s_sessions = course_sessions.get(student.course_id, [])
                total_sessions = len(s_sessions)
                if total_sessions == 0:
                    continue
                    
                present_count = 0
                missed_subjects = []
                for s in s_sessions:
                    status = att_dict.get(student.id, {}).get(s.id)
                    if status == 'Present':
                        present_count += 1
                    else:
                        missed_subjects.append(s.subject_name)
                        
                if present_count == 0:
                    absentees.append({
                        'student': student,
                        'absent_type': 'Full',
                        'missed_subjects': ['All']
                    })
                elif present_count < total_sessions:
                    absentees.append({
                        'student': student,
                        'absent_type': 'Partial',
                        'missed_subjects': missed_subjects
                    })
            return absentees

        today_absentees = get_daily_absentees(today_date)
        yesterday_date = today_date - timedelta(days=1)
        yesterdays_absentees = get_daily_absentees(yesterday_date)
                    
        last_2_dates_by_course = {}
        for c_id in assigned_course_ids:
            dates = db.session.query(ClassSession.date).filter(
                ClassSession.course_id == c_id
            ).distinct().order_by(ClassSession.date.desc()).limit(2).all()
            if len(dates) == 2:
                last_2_dates_by_course[c_id] = [d[0] for d in dates]

        target_session_ids = []
        for c_id, dates in last_2_dates_by_course.items():
            s_ids = db.session.query(ClassSession.id).filter(
                ClassSession.course_id == c_id,
                ClassSession.date.in_(dates)
            ).all()
            target_session_ids.extend([s[0] for s in s_ids])

        student_date_status = {}
        if target_session_ids:
            consec_att = Attendance.query.join(ClassSession).filter(
                Attendance.session_id.in_(target_session_ids)
            ).all()
            for att in consec_att:
                student_date_status.setdefault(att.student_id, {}).setdefault(att.session.date, []).append(att.status)

        consecutive_absences = []
        low_attendance = []
        
        for student in active_students_list:
            calc = calculate_attendance(student.id, student.course_id)
            if calc['total'] > 0 and calc['percentage'] < 70:
                low_attendance.append({'student': student, 'percentage': calc['percentage'], 'formatted': calc['formatted']})
                
            dates = last_2_dates_by_course.get(student.course_id)
            if dates and len(dates) == 2:
                d1_statuses = student_date_status.get(student.id, {}).get(dates[0], [])
                d2_statuses = student_date_status.get(student.id, {}).get(dates[1], [])
                
                # Student must have attendance records on both dates, and ZERO "Present" statuses on both dates
                if d1_statuses and d2_statuses:
                    if 'Present' not in d1_statuses and 'Present' not in d2_statuses:
                        consecutive_absences.append(student)
                
        
        active_course_staff = []
        active_course_students = []
        if selected_course_id:
            active_course_staff = CourseStaff.query.filter_by(course_id=selected_course_id).all()
            active_course_students = Student.query.filter_by(course_id=selected_course_id, status='Active').all()
            
        return render_template('dashboard.html', 
                                   total_active_students=total_active_students,
                                   hand_cash=hand_cash,
                                   in_account=in_account,
                                   total_fees=total_fees,
                                   total_expenses=total_expenses,
                                   total_donations=total_donations,
                                   total_collections_combined=total_fees + total_donations,
                                   net_balance=net_balance,
                                   students_paid_count=students_paid_count,
                                   next_cycle_students_paid_count=locals().get('next_cycle_students_paid_count', 0),
                                   current_cycle_month_name=locals().get('current_cycle_month_name', ''),
                                   next_cycle_month_name=locals().get('next_cycle_month_name', ''),
                                   latest_fees=latest_fees,
                                   latest_expenses=latest_expenses,
                                   courses=courses_list,
                                   selected_course_id=selected_course_id,
                                   today_collections=today_collections,
                                   monthly_collections=monthly_collections,
                                   monthly_donations=locals().get('monthly_donations_override', 0.0),
                                   monthly_expenses=locals().get('monthly_expenses_override', 0.0),
                                   expenses_added=total_expenses,
                                   pending_requests_count=pending_requests_count,
                                   start_date_str=start_date_str, end_date_str=end_date_str,
                                   yesterdays_absentees=yesterdays_absentees,
                                   today_absentees=today_absentees,
                                   consecutive_absences=consecutive_absences,
                                   low_attendance=low_attendance,
                                   active_course_staff=active_course_staff, active_course_students=active_course_students, course_overview=course_overview)
                                   
    else: # Admin
        pending_edit_requests = ApprovalRequest.query.filter_by(request_type='Edit', status='Pending').count()
        pending_delete_requests = ApprovalRequest.query.filter_by(request_type='Delete', status='Pending').count()
        recent_activities = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_collections_chart = [0.0] * 12
        monthly_expenses_chart = [0.0] * 12
        
        # Admin Chart Data (Always for current year, not affected by date filter but affected by course filter)
        admin_chart_fee_q = FeeCollection.query.filter_by(is_deleted=False)
        admin_chart_exp_q = Expense.query.filter_by(is_deleted=False)
        
        if selected_course_id and selected_course_id.isdigit():
            c_id = int(selected_course_id)
            admin_chart_fee_q = admin_chart_fee_q.join(Student).filter(Student.course_id == c_id)
            admin_chart_exp_q = admin_chart_exp_q.filter(Expense.course_id == c_id)
            
        for f in admin_chart_fee_q.all():
            if f.date_collected and f.date_collected.year == current_year:
                monthly_collections_chart[f.date_collected.month - 1] += f.amount_paid
                
        for e in admin_chart_exp_q.all():
            if e.expense_date and e.expense_date.year == current_year:
                monthly_expenses_chart[e.expense_date.month - 1] += e.amount
                
        admin_chart_session_q = ClassSession.query
        if selected_course_id and selected_course_id.isdigit():
            c_id = int(selected_course_id)
            admin_chart_session_q = admin_chart_session_q.filter(ClassSession.course_id == c_id)
            
        if start_date:
            admin_chart_session_q = admin_chart_session_q.filter(ClassSession.date >= start_date.date())
        if end_date:
            admin_chart_session_q = admin_chart_session_q.filter(ClassSession.date <= end_date.date())
            
        # Session-wise Attendance Trend (Last 15 Sessions or filtered)
        if not start_date and not end_date:
            recent_sessions = admin_chart_session_q.order_by(ClassSession.date.desc(), ClassSession.id.desc()).limit(15).all()
        else:
            recent_sessions = admin_chart_session_q.order_by(ClassSession.date.desc(), ClassSession.id.desc()).all()
            
        # Reverse to chronological order for the chart (left to right)
        recent_sessions.reverse()
        
        daily_chart_dates = []
        daily_chart_percentages = []
        
        for s in recent_sessions:
            subject_short = s.subject_name[:12] + '...' if len(s.subject_name) > 12 else s.subject_name
            label = f"{s.date.strftime('%b %d')} ({subject_short})"
            daily_chart_dates.append(label)
            
            total_records = Attendance.query.filter_by(session_id=s.id).count()
            present_records = Attendance.query.filter_by(session_id=s.id, status='Present').count()
            
            perc = (present_records / total_records * 100) if total_records > 0 else 0
            daily_chart_percentages.append(round(perc, 1))
                
        


    active_course_students = Student.query.filter_by(course_id=selected_course_id, status='Active').all() if selected_course_id else []

    return render_template('dashboard.html', 
                               total_active_students=total_active_students,
                               hand_cash=hand_cash,
                               in_account=in_account,
                               total_fees=total_fees,
                               total_expenses=total_expenses,
                               total_donations=total_donations,
                               total_collections_combined=total_fees + total_donations,
                               net_balance=net_balance,
                               students_paid_count=students_paid_count,
                               next_cycle_students_paid_count=locals().get('next_cycle_students_paid_count', 0),
                               current_cycle_month_name=locals().get('current_cycle_month_name', ''),
                               next_cycle_month_name=locals().get('next_cycle_month_name', ''),
                               latest_fees=latest_fees,
                               cycle_collections=locals().get('monthly_collections_override', 0.0),
                               monthly_donations=locals().get('monthly_donations_override', 0.0),
                               cycle_expenses=locals().get('monthly_expenses_override', 0.0),
                               latest_expenses=latest_expenses,
                               courses=courses_list,
                               selected_course_id=selected_course_id,
                               pending_edit_requests=pending_edit_requests,
                               pending_delete_requests=pending_delete_requests,
                               recent_activities=recent_activities,
                               months_list=months_list,
                               monthly_collections=monthly_collections_chart,
                               monthly_expenses=monthly_expenses_chart,
                               start_date_str=start_date_str, end_date_str=end_date_str,
                               daily_chart_dates=daily_chart_dates,
                               daily_chart_percentages=daily_chart_percentages,
                               active_course_students=active_course_students,
                               course_overview=course_overview)
