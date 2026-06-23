from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, session
from flask_login import login_required, current_user
from extensions import db
from models import User, Course, Student, FeeCollection, Expense, AuditLog, ApprovalRequest, ClassSession, Attendance
from helpers import calculate_attendance

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
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
    if current_user.role == 'Coordinator':
        assigned_courses = Course.query.filter_by(coordinator_id=current_user.id).all()
        assigned_course_ids = [c.id for c in assigned_courses]
        courses_list = assigned_courses
        
        if not assigned_course_ids:
            return render_template('dashboard.html', 
                                   total_active_students=0, hand_cash=0.0, in_account=0.0,
                                   total_fees=0.0, total_expenses=0.0, net_balance=0.0, students_paid_count=0,
                                   latest_fees=[], latest_expenses=[], courses=[],
                                   today_collections=0.0, monthly_collections=0.0,
                                   expenses_added=0.0, pending_requests_count=0,
                                   start_date_str=start_date_str, end_date_str=end_date_str)
                                   
        base_fee_q = FeeCollection.query.join(Student).filter(Student.course_id.in_(assigned_course_ids), FeeCollection.is_deleted==False)
        base_exp_q = Expense.query.filter(Expense.course_id.in_(assigned_course_ids), Expense.is_deleted==False)
        base_stu_q = Student.query.filter(Student.course_id.in_(assigned_course_ids), Student.status=='Active')
        
    else: # Admin
        courses_list = Course.query.filter_by(status='Active').all()
        base_fee_q = FeeCollection.query.join(Student).filter(FeeCollection.is_deleted==False)
        base_exp_q = Expense.query.filter(Expense.is_deleted==False)
        base_stu_q = Student.query.filter(Student.status=='Active')

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
    if end_date:
        base_fee_q = base_fee_q.filter(FeeCollection.date_collected <= end_date)
        base_exp_q = base_exp_q.filter(Expense.expense_date <= end_date)

    # Calculate Metrics
    fees = base_fee_q.all()
    hand_cash = sum(f.amount_paid for f in fees if f.payment_method == 'Cash')
    in_account = sum(f.amount_paid for f in fees if f.payment_method == 'Online')
    total_fees = hand_cash + in_account
    
    # Calculate students paid count (unique students in the date range)
    students_paid_count = len(set(f.student_id for f in fees))

    expenses = base_exp_q.all()
    total_expenses = sum(e.amount for e in expenses)
    
    net_balance = total_fees - total_expenses
    
    latest_fees = base_fee_q.order_by(FeeCollection.date_collected.desc()).limit(5).all()
    latest_expenses = base_exp_q.order_by(Expense.expense_date.desc()).limit(5).all()

    # Role specific logic
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
        
        pending_requests_count = ApprovalRequest.query.filter_by(requested_by_id=current_user.id, status='Pending').count()
        
        today_absentees = []
        today_sessions = ClassSession.query.filter(
            ClassSession.course_id.in_(assigned_course_ids), 
            ClassSession.date == today_date
        ).all()
        session_ids = [s.id for s in today_sessions]
        if session_ids:
            absent_records = Attendance.query.filter(
                Attendance.session_id.in_(session_ids),
                Attendance.status.in_(['Absent', 'Leave'])
            ).all()
            seen_students = set()
            for rec in absent_records:
                if rec.student_id not in seen_students:
                    today_absentees.append(rec)
                    seen_students.add(rec.student_id)
                    
        yesterday_date = today_date - timedelta(days=1)
        yesterdays_absentees = []
        yesterday_sessions = ClassSession.query.filter(
            ClassSession.course_id.in_(assigned_course_ids), 
            ClassSession.date == yesterday_date
        ).all()
        y_session_ids = [s.id for s in yesterday_sessions]
        if y_session_ids:
            y_absent_records = Attendance.query.filter(
                Attendance.session_id.in_(y_session_ids),
                Attendance.status.in_(['Absent', 'Leave'])
            ).all()
            seen_y_students = set()
            for rec in y_absent_records:
                if rec.student_id not in seen_y_students:
                    yesterdays_absentees.append(rec)
                    seen_y_students.add(rec.student_id)
                    
        active_students_list = base_stu_q.all()
        consecutive_absences = []
        low_attendance = []
        
        for student in active_students_list:
            calc = calculate_attendance(student.id, student.course_id)
            if calc['total'] > 0 and calc['percentage'] < 70:
                low_attendance.append({'student': student, 'percentage': calc['percentage'], 'formatted': calc['formatted']})
                
            recent_att = Attendance.query.join(ClassSession).filter(
                Attendance.student_id == student.id
            ).order_by(ClassSession.date.desc()).limit(2).all()
            
            if len(recent_att) == 2 and all(a.status == 'Absent' for a in recent_att):
                consecutive_absences.append(student)
                
        return render_template('dashboard.html', 
                               total_active_students=total_active_students,
                               hand_cash=hand_cash,
                               in_account=in_account,
                               total_fees=total_fees,
                               total_expenses=total_expenses,
                               net_balance=net_balance,
                               students_paid_count=students_paid_count,
                               latest_fees=latest_fees,
                               latest_expenses=latest_expenses,
                               courses=courses_list,
                               selected_course_id=selected_course_id,
                               today_collections=today_collections,
                               monthly_collections=monthly_collections,
                               expenses_added=total_expenses,
                               pending_requests_count=pending_requests_count,
                               start_date_str=start_date_str, end_date_str=end_date_str,
                               yesterdays_absentees=yesterdays_absentees,
                               today_absentees=today_absentees,
                               consecutive_absences=consecutive_absences,
                               low_attendance=low_attendance)
                               
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
            
        recent_sessions = admin_chart_session_q.order_by(ClassSession.date.desc()).all()
        unique_dates = []
        seen_dates = set()
        for s in recent_sessions:
            if s.date not in seen_dates:
                unique_dates.append(s.date)
                seen_dates.add(s.date)
            # Only limit to 14 if no date filters are applied
            if not start_date and not end_date and len(unique_dates) == 14:
                break
                
        unique_dates.reverse()
        daily_chart_dates = []
        daily_chart_percentages = []
        
        for d in unique_dates:
            daily_chart_dates.append(d.strftime('%b %d'))
            day_sessions = admin_chart_session_q.filter(ClassSession.date == d).all()
            day_session_ids = [s.id for s in day_sessions]
            
            if day_session_ids:
                total_records = Attendance.query.filter(Attendance.session_id.in_(day_session_ids)).count()
                present_records = Attendance.query.filter(
                    Attendance.session_id.in_(day_session_ids), 
                    Attendance.status == 'Present'
                ).count()
                perc = (present_records / total_records * 100) if total_records > 0 else 0
                daily_chart_percentages.append(round(perc, 1))
            else:
                daily_chart_percentages.append(0)
                
        return render_template('dashboard.html', 
                               total_active_students=total_active_students,
                               hand_cash=hand_cash,
                               in_account=in_account,
                               total_fees=total_fees,
                               total_expenses=total_expenses,
                               net_balance=net_balance,
                               students_paid_count=students_paid_count,
                               latest_fees=latest_fees,
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
                               daily_chart_percentages=daily_chart_percentages)
