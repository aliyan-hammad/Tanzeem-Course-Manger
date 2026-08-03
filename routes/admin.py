import json
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db
from models import User, Course, Student, FeeCollection, Expense, Attendance, AuditLog, ApprovalRequest, ClassSession, CourseStaff
from helpers import log_audit, calculate_attendance
from sync_listeners import trigger_sync_fee_month, trigger_sync_expense_month

admin_bp = Blueprint('admin', __name__)

# --- Staff Admin Actions ---
@admin_bp.route('/staff', methods=['GET', 'POST'])
@login_required
def staff():
    if current_user.role != 'Admin':
        flash('Access denied! Admin permissions required.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        full_name = request.form.get('full_name')
        contact = request.form.get('contact')
        cnic = request.form.get('cnic')
        email = request.form.get('email')
        date_of_joining_str = request.form.get('date_of_joining')
        date_of_joining = datetime.strptime(date_of_joining_str, '%Y-%m-%d').date() if date_of_joining_str else None

        if form_type in ['coordinator', 'teacher', 'ta']:
            username = request.form.get('username')
            password = request.form.get('password')
            role_map = {'coordinator': 'Coordinator', 'teacher': 'Teacher', 'ta': 'TA'}
            role = role_map.get(form_type)
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists!', 'danger')
                return redirect(url_for('admin.staff'))
                
            salary_type = request.form.get('salary_type', 'Fixed Monthly')
            salary_amount = float(request.form.get('salary_amount', 0.0))
            bank_details = request.form.get('bank_details')
            
            hashed_pw = generate_password_hash(password)
            new_user = User(
                username=username, 
                password_hash=hashed_pw, 
                role=role,
                full_name=full_name,
                contact=contact,
                cnic=cnic,
                email=email,
                date_of_joining=date_of_joining,
                salary_type=salary_type,
                salary_amount=salary_amount,
                bank_details=bank_details,
                status='Active'
            )
            db.session.add(new_user)
            db.session.commit()
            
            # Handle Course assignment for Teacher/TA
            if role in ['Teacher', 'TA']:
                course_id = request.form.get('course_id')
                if course_id:
                    subjects_taught = request.form.get('subjects_taught') if role == 'Teacher' else None
                    assigned_teacher_id = request.form.get('assigned_teacher_id') if role == 'TA' else None
                    
                    new_staff = CourseStaff(
                        course_id=int(course_id),
                        user_id=new_user.id,
                        role_in_course=role,
                        assigned_teacher_id=int(assigned_teacher_id) if assigned_teacher_id else None,
                        subjects_taught=subjects_taught
                    )
                    db.session.add(new_staff)
                    db.session.commit()
            
            log_audit('Create', 'User', record_id=new_user.id, remarks=f'Admin registered {role}: {full_name}')
            flash(f'{role} registered successfully!', 'success')
            
        elif form_type == 'general_staff':
            role = request.form.get('role')
            if role == 'Other':
                role = request.form.get('custom_role')
            
            salary = float(request.form.get('salary', 0.0))
            payment_method = request.form.get('payment_method', 'Cash')
            address = request.form.get('address')
            
            from models import GeneralStaff
            new_gs = GeneralStaff(
                name=full_name,
                contact=contact,
                address=address,
                cnic=cnic,
                role=role,
                salary=salary,
                payment_method=payment_method,
                date_of_joining=date_of_joining
            )
            db.session.add(new_gs)
            db.session.commit()
            log_audit('Create', 'GeneralStaff', record_id=new_gs.id, remarks=f'Admin registered General Staff: {full_name}')
            flash(f'General Staff registered successfully!', 'success')
            
        return redirect(url_for('admin.staff'))
        
    coordinators = User.query.filter_by(role='Coordinator').all()
    teachers_tas = User.query.filter(User.role.in_(['Teacher', 'TA'])).all()
    from models import GeneralStaff
    general_staff = GeneralStaff.query.all()
    crs = User.query.filter_by(role='CR').all()
    active_courses = Course.query.filter_by(status='Active').all()
    active_teachers = User.query.filter_by(role='Teacher', status='Active').all()
    
    return render_template('staff.html', 
                           coordinators=coordinators, 
                           teachers_tas=teachers_tas, 
                           general_staff=general_staff, 
                           crs=crs,
                           active_courses=active_courses,
                           active_teachers=active_teachers)

@admin_bp.route('/staff/edit/<int:id>', methods=['POST'])
@login_required
def edit_staff(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    staff_member = User.query.filter_by(id=id).first_or_404()
    old_status = staff_member.status
    staff_member.full_name = request.form.get('full_name')
    staff_member.contact = request.form.get('contact')
    staff_member.status = request.form.get('status')
    staff_member.cnic = request.form.get('cnic')
    staff_member.email = request.form.get('email')
    
    date_of_joining_str = request.form.get('date_of_joining')
    if date_of_joining_str:
        from datetime import datetime
        staff_member.date_of_joining = datetime.strptime(date_of_joining_str, '%Y-%m-%d').date()
        
    staff_member.salary_amount = float(request.form.get('salary_amount', 0.0))
    if request.form.get('salary_type'):
        staff_member.salary_type = request.form.get('salary_type')
    if request.form.get('bank_details') is not None:
        staff_member.bank_details = request.form.get('bank_details')
        
    if request.form.get('role'):
        staff_member.role = request.form.get('role')
        
    if staff_member.role != 'General Staff':
        password = request.form.get('password')
        if password:
            staff_member.password_hash = generate_password_hash(password)
            
    # Handle CourseStaff updates for Teacher/TA
    if staff_member.role in ['Teacher', 'TA']:
        course_id = request.form.get('course_id')
        if course_id:
            course_staff = CourseStaff.query.filter_by(user_id=staff_member.id).first()
            if not course_staff:
                course_staff = CourseStaff(user_id=staff_member.id)
                db.session.add(course_staff)
                
            course_staff.course_id = int(course_id)
            course_staff.role_in_course = staff_member.role
            
            if staff_member.role == 'Teacher':
                course_staff.subjects_taught = request.form.get('subjects_taught')
                course_staff.assigned_teacher_id = None
            elif staff_member.role == 'TA':
                assigned_tid = request.form.get('assigned_teacher_id')
                course_staff.assigned_teacher_id = int(assigned_tid) if assigned_tid else None
                course_staff.subjects_taught = None
        
    db.session.commit()
    log_audit('Update', 'User', record_id=staff_member.id, remarks=f'Admin modified staff: {staff_member.username}')
    flash(f'Staff details updated successfully!', 'success')
    return redirect(url_for('admin.staff'))


@admin_bp.route('/gs/edit/<int:id>', methods=['POST'])
@login_required
def edit_gs(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    from models import GeneralStaff
    gs = GeneralStaff.query.get_or_404(id)
    
    gs.name = request.form.get('full_name')
    gs.contact = request.form.get('contact')
    gs.cnic = request.form.get('cnic')
    
    role = request.form.get('role')
    if role == 'Other':
        role = request.form.get('custom_role')
    gs.role = role
    
    gs.salary = float(request.form.get('salary', 0.0))
    gs.payment_method = request.form.get('payment_method', 'Cash')
    
    date_of_joining_str = request.form.get('date_of_joining')
    if date_of_joining_str:
        from datetime import datetime
        gs.date_of_joining = datetime.strptime(date_of_joining_str, '%Y-%m-%d').date()
        
    db.session.commit()
    log_audit('Update', 'GeneralStaff', record_id=gs.id, remarks=f'Admin modified GS: {gs.name}')
    flash(f'General Staff updated successfully!', 'success')
    return redirect(url_for('admin.staff'))

@admin_bp.route('/gs/delete/<int:id>', methods=['POST'])
@login_required
def delete_gs(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    from models import GeneralStaff
    gs = GeneralStaff.query.get_or_404(id)
    name = gs.name
    db.session.delete(gs)
    db.session.commit()
    log_audit('Delete', 'GeneralStaff', record_id=id, remarks=f'Admin deleted GS: {name}')
    flash('General Staff member deleted successfully!', 'success')
    return redirect(url_for('admin.staff'))

@admin_bp.route('/staff/delete/<int:id>', methods=['POST'])
@login_required
def delete_staff(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    staff_member = User.query.filter_by(id=id).first_or_404()
    
    if len(staff_member.managed_courses) > 0:
        course_names = ", ".join([c.name for c in staff_member.managed_courses])
        flash(f'Cannot delete staff because they are currently managing courses: {course_names}. Please assign a different coordinator to these courses first.', 'danger')
    else:
        username = staff_member.username
        db.session.delete(staff_member)
        db.session.commit()
        log_audit('Delete', 'User', record_id=id, remarks=f'Admin permanently deleted staff: {username}')
        flash('Staff member deleted successfully!', 'success')
    return redirect(url_for('admin.staff'))

# --- Courses Admin Actions ---
@admin_bp.route('/courses', methods=['GET', 'POST'])
@login_required
def courses():
    if current_user.role != 'Admin':
        flash('Access denied! Admin permissions required.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        batch = request.form.get('batch')
        status = request.form.get('status', 'Active')
        duration = request.form.get('duration')
        if duration == 'Other':
            duration = request.form.get('custom_duration')
            
        coordinator_id_str = request.form.get('coordinator_id')
        coordinator_id = int(coordinator_id_str) if (coordinator_id_str and coordinator_id_str.isdigit()) else None
        
        base_fee = float(request.form.get('base_fee', 0.0))
        
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        subjects_list = request.form.getlist('subjects')
        subjects_json = json.dumps([s for s in subjects_list if s.strip()])
        
        existing = Course.query.filter_by(name=name).first()
        if existing:
            flash('Course title already exists!', 'danger')
        else:
            new_course = Course(
                name=name,
                batch=batch,
                status=status,
                duration=duration,
                coordinator_id=coordinator_id,
                base_fee=base_fee,
                start_date=start_date,
                end_date=end_date,
                subjects=subjects_json
            )
            db.session.add(new_course)
            db.session.commit()
            log_audit('Create', 'Course', record_id=new_course.id, remarks=f'Admin created course: {name}')
            flash('Course registered successfully!', 'success')
        return redirect(url_for('admin.courses'))
        
    all_courses = Course.query.all()
    coordinators_list = User.query.filter_by(role='Coordinator', status='Active').all()
    return render_template('courses.html', courses=all_courses, coordinators=coordinators_list, json=json)

@admin_bp.route('/courses/edit/<int:id>', methods=['POST'])
@login_required
def edit_course(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    course = Course.query.get_or_404(id)
    old_name = course.name
    course.name = request.form.get('name')
    course.batch = request.form.get('batch')
    course.status = request.form.get('status', 'Active')
    
    duration = request.form.get('duration')
    if duration == 'Other':
        course.duration = request.form.get('custom_duration')
    else:
        course.duration = duration
        
    coordinator_id_str = request.form.get('coordinator_id')
    course.coordinator_id = int(coordinator_id_str) if (coordinator_id_str and coordinator_id_str.isdigit()) else None
    
    course.base_fee = float(request.form.get('base_fee', 0.0))
    
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    course.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    course.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    
    subjects_list = request.form.getlist('subjects')
    course.subjects = json.dumps([s for s in subjects_list if s.strip()])
    course.status = request.form.get('status')
    
    db.session.commit()
    log_audit('Update', 'Course', record_id=course.id, remarks=f'Admin updated course: {old_name} -> {course.name}')
    flash('Course details updated successfully!', 'success')
    return redirect(url_for('admin.courses'))

@admin_bp.route('/courses/delete/<int:id>', methods=['POST'])
@login_required
def delete_course(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    course = Course.query.get_or_404(id)
    if len(course.students) > 0:
        flash('Cannot delete course because students are enrolled in it.', 'danger')
    else:
        name = course.name
        db.session.delete(course)
        db.session.commit()
        log_audit('Delete', 'Course', record_id=id, remarks=f'Admin permanently deleted course: {name}')
        flash('Course deleted successfully!', 'success')
    return redirect(url_for('admin.courses'))

# --- Reports Route ---
@admin_bp.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    from flask import session
    if current_user.role != 'Admin':
        flash('Access denied! Admins permissions required.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    today = date.today()
    default_month = today.strftime('%Y-%m')
    
    # Session Persistence
    if request.method == 'POST' or 'filter_applied' in request.args:
        report_month = request.form.get('report_month') or request.args.get('report_month') or default_month
        course_id_str = request.form.get('course_id') or request.args.get('course_id')
        subject = request.form.get('subject') or request.args.get('subject')
        
        session['report_month'] = report_month
        session['report_course_id'] = course_id_str
        session['report_subject'] = subject
    else:
        report_month = session.get('report_month', default_month)
        course_id_str = session.get('report_course_id')
        subject = session.get('report_subject')
        
    courses_list = Course.query.filter_by(status='Active').all()
    
    if not course_id_str and courses_list:
        course_id_str = str(courses_list[0].id)
        
    course_id = int(course_id_str) if (course_id_str and course_id_str.isdigit()) else None
    
    import calendar
    from dateutil.relativedelta import relativedelta
    from datetime import timedelta
    year, month = map(int, report_month.split('-'))
    
    course_day = 1
    if course_id:
        c_obj = Course.query.get(course_id)
        if c_obj and c_obj.start_date:
            course_day = c_obj.start_date.day
            
    try:
        start_date = datetime(year, month, course_day)
    except ValueError:
        # Snap to end of month if course day is 31 and month only has 30 days
        start_date = datetime(year, month, calendar.monthrange(year, month)[1])
        
    end_date = start_date + relativedelta(months=1) - timedelta(seconds=1)
    
    # Generate last 24 months for dropdown
    months_list = []
    for i in range(24):
        d = today - relativedelta(months=i)
        months_list.append(d.strftime('%Y-%m'))
    
    # 1. Student Registry (No date filter, but course filter applies)
    student_query = Student.query
    if course_id:
        student_query = student_query.filter_by(course_id=course_id)
    students_list = student_query.order_by(Student.registration_id.desc()).all()
    
    # 2. Fee Collection Report (Fee Month filter, course filter applies)
    fee_query = FeeCollection.query.filter(
        FeeCollection.fee_month == report_month,
        FeeCollection.is_deleted == False
    )
    if course_id:
        fee_query = fee_query.join(Student).filter(Student.course_id == course_id)
    fees_list = fee_query.order_by(FeeCollection.date_collected.desc()).all()
    total_fees = sum([f.amount_paid for f in fees_list])
    
    # 3. Expenses Report (Date range filter, course filter applies)
    expense_query = Expense.query.filter(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date,
        Expense.is_deleted == False
    )
    if course_id:
        expense_query = expense_query.filter_by(course_id=course_id)
    expenses_list = expense_query.order_by(Expense.expense_date.desc()).all()
    total_expenses = sum([e.amount for e in expenses_list])
    
    # Calculate Cumulative Net Balance up to the end_date of the selected month
    cum_fee_q = FeeCollection.query.filter(FeeCollection.date_collected <= end_date, FeeCollection.is_deleted == False)
    if course_id:
        cum_fee_q = cum_fee_q.join(Student).filter(Student.course_id == course_id)
    
    cum_exp_q = Expense.query.filter(Expense.expense_date <= end_date, Expense.is_deleted == False)
    if course_id:
        cum_exp_q = cum_exp_q.filter_by(course_id=course_id)
        
    cumulative_net_balance = sum([f.amount_paid for f in cum_fee_q.all()]) - sum([e.amount for e in cum_exp_q.all()])
    
    prev_end_date = start_date - timedelta(seconds=1)
    prev_fee_q = FeeCollection.query.filter(FeeCollection.date_collected <= prev_end_date, FeeCollection.is_deleted == False)
    if course_id:
        prev_fee_q = prev_fee_q.join(Student).filter(Student.course_id == course_id)
        
    prev_exp_q = Expense.query.filter(Expense.expense_date <= prev_end_date, Expense.is_deleted == False)
    if course_id:
        prev_exp_q = prev_exp_q.filter_by(course_id=course_id)
        
    prev_cumulative_net_balance = sum([f.amount_paid for f in prev_fee_q.all()]) - sum([e.amount for e in prev_exp_q.all()])
    current_net_profit = total_fees - total_expenses
    
    prev_month_dt = start_date - relativedelta(months=1)
    prev_month_str = prev_month_dt.strftime('%Y-%m')
    
    # 4. Attendance Summary (Date range filter, course filter applies)
    students_query = Student.query.filter_by(status='Active')
    if course_id:
        students_query = students_query.filter_by(course_id=course_id)
    students_list = students_query.all()
    
    attendance_stats = {}
    for s in students_list:
        calc = calculate_attendance(s.id, s.course_id, subject_name=subject, start_date=start_date.date(), end_date=end_date.date())
        
        leave_query = Attendance.query.join(ClassSession).filter(
            Attendance.student_id == s.id,
            Attendance.status == 'Leave',
            ClassSession.course_id == s.course_id,
            ClassSession.status == 'Submitted'
        )
        if subject:
            leave_query = leave_query.filter(ClassSession.subject_name == subject)
        if start_date:
            leave_query = leave_query.filter(ClassSession.date >= start_date.date())
        if end_date:
            leave_query = leave_query.filter(ClassSession.date <= end_date.date())
            
        leave_count = leave_query.count()
        present_count = calc['attended']
        total_sessions = calc['total']
        absent_count = max(0, total_sessions - present_count - leave_count)
        
        attendance_stats[s.id] = {
            'present': present_count,
            'absent': absent_count,
            'leave': leave_count,
            'student': s,
            'calc': calc
        }
            
    return render_template('reports.html',
                           total_fees=total_fees,
                           total_expenses=total_expenses,
                           cumulative_net_balance=cumulative_net_balance,
                           prev_cumulative_net_balance=prev_cumulative_net_balance,
                           current_net_profit=current_net_profit,
                           prev_month_str=prev_month_str,
                           report_month=report_month,
                           months_list=months_list,
                           selected_course_id=course_id_str,
                           selected_subject=subject,
                           courses=courses_list,
                           students=students_list,
                           fees=fees_list,
                           expenses=expenses_list,
                           attendance_stats=attendance_stats.values())

# --- Approvals Actions ---
@admin_bp.route('/requests')
@login_required
def view_requests():
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    pending_requests = ApprovalRequest.query.filter_by(status='Pending').order_by(ApprovalRequest.created_at.desc()).all()
    history_requests = ApprovalRequest.query.filter(ApprovalRequest.status != 'Pending').order_by(ApprovalRequest.created_at.desc()).all()
    
    fee_records = {f.id: f for f in FeeCollection.query.all()}
    expense_records = {e.id: e for e in Expense.query.all()}
    
    return render_template('approval_requests.html', 
                           pending_requests=pending_requests, 
                           history_requests=history_requests,
                           fee_records=fee_records,
                           expense_records=expense_records,
                           json=json)

@admin_bp.route('/requests/<int:id>/action', methods=['POST'])
@login_required
def action_request(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    req = ApprovalRequest.query.get_or_404(id)
    if req.status != 'Pending':
        flash('Request already processed!', 'warning')
        return redirect(url_for('admin.view_requests'))
        
    action = request.form.get('action')
    admin_notes = request.form.get('admin_notes', '')
    
    req.status = 'Approved' if action == 'Approve' else 'Rejected'
    req.actioned_by_id = current_user.id
    req.actioned_at = datetime.utcnow()
    req.admin_notes = admin_notes
    
    if action == 'Approve':
        if req.request_type == 'Edit':
            payload = json.loads(req.temporary_edit_payload)
            if req.module == 'Fee':
                record = FeeCollection.query.filter_by(id=req.record_id, is_deleted=False).first()
                if record:
                    old_vals = {
                        'amount_paid': record.amount_paid,
                        'payment_method': record.payment_method,
                        'date_collected': record.date_collected.strftime('%Y-%m-%d') if record.date_collected else None
                    }
                    record.amount_paid = payload['amount_paid']
                    record.payment_method = payload['payment_method']
                    if payload['date_collected']:
                        record.date_collected = datetime.strptime(payload['date_collected'], '%Y-%m-%d')
                    db.session.commit()
                    log_audit('Update', 'Fee', record_id=record.id, old_values=old_vals, new_values=payload, remarks=f'Edit request approved: {admin_notes}')
                    
                    if old_vals['date_collected']:
                        old_month = datetime.strptime(old_vals['date_collected'], '%Y-%m-%d').strftime('%B %Y')
                        trigger_sync_fee_month(current_app._get_current_object(), old_month)
                    if record.date_collected:
                        new_month = record.date_collected.strftime('%B %Y')
                        if new_month != old_month:
                            trigger_sync_fee_month(current_app._get_current_object(), new_month)
            elif req.module == 'Expense':
                record = Expense.query.filter_by(id=req.record_id, is_deleted=False).first()
                if record:
                    old_vals = {
                        'title': record.title,
                        'amount': record.amount,
                        'payment_method': record.payment_method,
                        'course_id': record.course_id,
                        'expense_date': record.expense_date.strftime('%Y-%m-%d') if record.expense_date else None
                    }
                    record.title = payload['title']
                    record.amount = payload['amount']
                    record.payment_method = payload['payment_method']
                    record.course_id = payload['course_id']
                    if payload['expense_date']:
                        record.expense_date = datetime.strptime(payload['expense_date'], '%Y-%m-%d')
                    db.session.commit()
                    log_audit('Update', 'Expense', record_id=record.id, old_values=old_vals, new_values=payload, remarks=f'Edit request approved: {admin_notes}')
                    
                    if old_vals['expense_date']:
                        old_month = datetime.strptime(old_vals['expense_date'], '%Y-%m-%d').strftime('%B %Y')
                        trigger_sync_expense_month(current_app._get_current_object(), old_month)
                    if record.expense_date:
                        new_month = record.expense_date.strftime('%B %Y')
                        if new_month != old_month:
                            trigger_sync_expense_month(current_app._get_current_object(), new_month)
            elif req.module == 'Donation':
                record = Donation.query.filter_by(id=req.record_id).filter(Donation.deleted_at.is_(None)).first()
                if record:
                    old_vals = {
                        'donor_name': record.donor_name,
                        'amount': record.amount,
                        'cause': record.cause,
                        'method': record.method,
                        'date': record.date.strftime('%Y-%m-%d') if record.date else None
                    }
                    record.donor_name = payload['donor_name']
                    record.amount = payload['amount']
                    record.cause = payload['cause']
                    record.method = payload['method']
                    if payload['date']:
                        record.date = datetime.strptime(payload['date'], '%Y-%m-%d')
                    db.session.commit()
                    log_audit('Update', 'Donation', record_id=record.id, old_values=old_vals, new_values=payload, remarks=f'Edit request approved: {admin_notes}')
        elif req.request_type == 'Delete':
            if req.module == 'Fee':
                record = FeeCollection.query.filter_by(id=req.record_id, is_deleted=False).first()
                if record:
                    record.is_deleted = True
                    record.deleted_by_id = current_user.id
                    record.deleted_at = datetime.utcnow()
                    record.delete_reason = req.reason
                    db.session.commit()
                    log_audit('Soft Delete', 'Fee', record_id=record.id, remarks=f'Delete request approved: {req.reason}')
                    
                    if record.date_collected:
                        trigger_sync_fee_month(current_app._get_current_object(), record.date_collected.strftime('%B %Y'))
            elif req.module == 'Expense':
                record = Expense.query.filter_by(id=req.record_id, is_deleted=False).first()
                if record:
                    record.is_deleted = True
                    record.deleted_by_id = current_user.id
                    record.deleted_at = datetime.utcnow()
                    record.delete_reason = req.reason
                    db.session.commit()
                    log_audit('Soft Delete', 'Expense', record_id=record.id, remarks=f'Delete request approved: {req.reason}')
                    
                    if record.expense_date:
                        trigger_sync_expense_month(current_app._get_current_object(), record.expense_date.strftime('%B %Y'))
            elif req.module == 'Donation':
                record = Donation.query.filter_by(id=req.record_id).filter(Donation.deleted_at.is_(None)).first()
                if record:
                    record.deleted_at = datetime.utcnow()
                    db.session.commit()
                    log_audit('Soft Delete', 'Donation', record_id=record.id, remarks=f'Delete request approved: {req.reason}')
                    
        flash(f'Request successfully {req.status.lower()}d!', 'success')
    else:
        log_audit(f'Reject {req.request_type}', req.module, record_id=req.record_id, remarks=f'Request rejected. Admin notes: {admin_notes}')
        flash('Request successfully rejected!', 'info')
        
    db.session.commit()
    return redirect(url_for('admin.view_requests'))

# --- Audit Logs Route ---
@admin_bp.route('/audit_logs')
@login_required
def view_audit_logs():
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    action_filter = request.args.get('action_type', '')
    module_filter = request.args.get('module', '')
    
    query = AuditLog.query
    if action_filter:
        query = query.filter_by(action_type=action_filter)
    if module_filter:
        query = query.filter_by(module=module_filter)
        
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('audit_logs.html', logs=logs, action_filter=action_filter, module_filter=module_filter)
