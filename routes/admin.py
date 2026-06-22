import json
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db
from models import User, Course, Student, FeeCollection, Expense, Attendance, AuditLog, ApprovalRequest, ClassSession
from helpers import log_audit, calculate_attendance
from helpers import log_audit

admin_bp = Blueprint('admin', __name__)

# --- Coordinators Admin Actions ---
@admin_bp.route('/coordinators', methods=['GET', 'POST'])
@login_required
def coordinators():
    if current_user.role != 'Admin':
        flash('Access denied! Admin permissions required.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        contact = request.form.get('contact')
        
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Username already exists!', 'danger')
        else:
            hashed_pw = generate_password_hash(password)
            new_coord = User(
                username=username, 
                password_hash=hashed_pw, 
                role='Coordinator',
                full_name=full_name,
                contact=contact,
                status='Active'
            )
            db.session.add(new_coord)
            db.session.commit()
            log_audit('Create', 'User', record_id=new_coord.id, remarks=f'Admin registered coordinator: {full_name} ({username})')
            flash(f'Coordinator "{full_name}" registered successfully!', 'success')
        return redirect(url_for('admin.coordinators'))
        
    all_coords = User.query.filter_by(role='Coordinator').all()
    return render_template('coordinators.html', coordinators=all_coords)

@admin_bp.route('/coordinators/edit/<int:id>', methods=['POST'])
@login_required
def edit_coordinator(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    coord = User.query.filter_by(id=id, role='Coordinator').first_or_404()
    old_status = coord.status
    coord.full_name = request.form.get('full_name')
    coord.contact = request.form.get('contact')
    coord.status = request.form.get('status')
    
    password = request.form.get('password')
    if password:
        coord.password_hash = generate_password_hash(password)
        
    db.session.commit()
    log_audit('Update', 'User', record_id=coord.id, remarks=f'Admin modified coordinator: {coord.username}. Status: {old_status} -> {coord.status}')
    flash(f'Coordinator "{coord.full_name}" credentials updated successfully!', 'success')
    return redirect(url_for('admin.coordinators'))

@admin_bp.route('/coordinators/delete/<int:id>', methods=['POST'])
@login_required
def delete_coordinator(id):
    if current_user.role != 'Admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    coord = User.query.filter_by(id=id, role='Coordinator').first_or_404()
    
    if len(coord.managed_courses) > 0:
        course_names = ", ".join([c.name for c in coord.managed_courses])
        flash(f'Cannot delete coordinator because they are currently managing courses: {course_names}. Please assign a different coordinator to these courses first.', 'danger')
    else:
        username = coord.username
        db.session.delete(coord)
        db.session.commit()
        log_audit('Delete', 'User', record_id=id, remarks=f'Admin permanently deleted coordinator: {username}')
        flash('Coordinator deleted successfully!', 'success')
    return redirect(url_for('admin.coordinators'))

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
    if current_user.role != 'Admin':
        flash('Access denied! Admins permissions required.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    today = date.today()
    default_start = date(today.year, today.month, 1).strftime('%Y-%m-%d')
    default_end = today.strftime('%Y-%m-%d')
    
    start_date_str = request.form.get('start_date') or default_start
    end_date_str = request.form.get('end_date') or default_end
    course_id_str = request.form.get('course_id')
    subject = request.form.get('subject')
    
    course_id = int(course_id_str) if (course_id_str and course_id_str.isdigit()) else None
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    
    # 1. Student Registry (No date filter, but course filter applies)
    student_query = Student.query
    if course_id:
        student_query = student_query.filter_by(course_id=course_id)
    students_list = student_query.order_by(Student.registration_id.desc()).all()
    
    # 2. Fee Collection Report (Date range filter, course filter applies)
    fee_query = FeeCollection.query.filter(
        FeeCollection.date_collected >= start_date,
        FeeCollection.date_collected <= end_date,
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
    
    # 4. Attendance Summary (Date range filter, course filter applies)
    attendance_query = Attendance.query.join(ClassSession).filter(
        ClassSession.date >= start_date.date(),
        ClassSession.date <= end_date.date()
    )
    if course_id:
        attendance_query = attendance_query.join(Student).filter(Student.course_id == course_id)
    if subject:
        attendance_query = attendance_query.filter(ClassSession.subject_name == subject)
    attendances_list = attendance_query.all()
    
    # Group attendance by student
    attendance_stats = {}
    for att in attendances_list:
        if att.student_id not in attendance_stats:
            calc = calculate_attendance(att.student_id, att.student.course_id)
            attendance_stats[att.student_id] = {'present': 0, 'absent': 0, 'leave': 0, 'student': att.student, 'calc': calc}
        if att.status == 'Present':
            attendance_stats[att.student_id]['present'] += 1
        elif att.status == 'Absent':
            attendance_stats[att.student_id]['absent'] += 1
        elif att.status == 'Leave':
            attendance_stats[att.student_id]['leave'] += 1
            
    courses_list = Course.query.filter_by(status='Active').all()
    
    return render_template('reports.html',
                           total_fees=total_fees,
                           total_expenses=total_expenses,
                           start_date=start_date_str,
                           end_date=end_date_str,
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
            elif req.module == 'Expense':
                record = Expense.query.filter_by(id=req.record_id, is_deleted=False).first()
                if record:
                    record.is_deleted = True
                    record.deleted_by_id = current_user.id
                    record.deleted_at = datetime.utcnow()
                    record.delete_reason = req.reason
                    db.session.commit()
                    log_audit('Soft Delete', 'Expense', record_id=record.id, remarks=f'Delete request approved: {req.reason}')
                    
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
