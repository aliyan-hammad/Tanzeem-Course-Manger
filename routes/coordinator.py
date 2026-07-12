import json
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Course, Student, FeeCollection, Expense, Attendance, ApprovalRequest, ClassSession, CourseStaff, User
from helpers import log_audit
from sqlalchemy.exc import IntegrityError

coordinator_bp = Blueprint('coordinator', __name__)

# --- Student Registry ---
@coordinator_bp.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        father_name = request.form.get('father_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        qualification = request.form.get('qualification')
        profession = request.form.get('profession')
        cnic = request.form.get('cnic')
        
        course_id_str = request.form.get('course_id')
        course_id = int(course_id_str) if (course_id_str and course_id_str.isdigit()) else None
        
        if current_user.role == 'Coordinator':
            managed_course = Course.query.filter_by(id=course_id, coordinator_id=current_user.id).first()
            if not managed_course:
                flash('Access denied! You cannot enroll students in this course.', 'danger')
                return redirect(url_for('coordinator.students'))
        
        enrollment_date_str = request.form.get('enrollment_date')
        if enrollment_date_str:
            enrollment_date = datetime.strptime(enrollment_date_str, '%Y-%m-%d')
        else:
            enrollment_date = datetime.utcnow()

        last_student = Student.query.order_by(Student.id.desc()).first()
        if last_student and last_student.registration_id.isdigit():
            new_reg_id = str(int(last_student.registration_id) + 1)
        else:
            new_reg_id = "1001"
        
        new_student = Student(
            registration_id=new_reg_id,
            full_name=full_name,
            father_name=father_name,
            phone=phone,
            address=address,
            qualification=qualification,
            profession=profession,
            cnic=cnic,
            course_id=course_id,
            enrollment_date=enrollment_date
        )
        db.session.add(new_student)
        db.session.commit()
        log_audit('Create', 'Student', record_id=new_student.id, remarks=f'Registered student: {full_name} (Reg ID: {new_reg_id})')
        flash(f'Student added successfully! Reg ID: {new_reg_id}', 'success')
        return redirect(url_for('coordinator.students'))
        
    selected_course_id = request.args.get('course_id')
    
    if current_user.role == 'Coordinator':
        assigned_courses = Course.query.filter_by(coordinator_id=current_user.id).all()
        courses_list = assigned_courses
    else:
        courses_list = Course.query.filter_by(status='Active').all()

    if not courses_list:
        return render_template('students.html', students=[], courses=[], selected_course_id=None, pagination=None)

    # Force a valid course selection
    valid_course_ids = [str(c.id) for c in courses_list]
    if not selected_course_id or selected_course_id not in valid_course_ids:
        selected_course_id = valid_course_ids[0]

    c_filter = int(selected_course_id)
    all_students = Student.query.filter_by(course_id=c_filter).order_by(Student.registration_id.desc()).all()
        
    return render_template('students.html', students=all_students, courses=courses_list, selected_course_id=selected_course_id, pagination=None)

@coordinator_bp.route('/students/edit/<int:id>', methods=['POST'])
@login_required
def edit_student(id):
    student = Student.query.get_or_404(id)
    
    if current_user.role == 'Coordinator':
        if student.course_id:
            assigned = Course.query.filter_by(id=student.course_id, coordinator_id=current_user.id).first()
            if not assigned:
                flash('Access denied!', 'danger')
                return redirect(url_for('coordinator.students'))
        else:
            flash('Access denied!', 'danger')
            return redirect(url_for('coordinator.students'))
            
    old_name = student.full_name
    student.full_name = request.form.get('full_name')
    student.father_name = request.form.get('father_name')
    student.phone = request.form.get('phone')
    student.address = request.form.get('address')
    student.qualification = request.form.get('qualification')
    student.profession = request.form.get('profession')
    student.cnic = request.form.get('cnic')
    
    course_id_str = request.form.get('course_id')
    course_id = int(course_id_str) if (course_id_str and course_id_str.isdigit()) else None
    
    if current_user.role == 'Coordinator' and course_id:
        assigned = Course.query.filter_by(id=course_id, coordinator_id=current_user.id).first()
        if not assigned:
            flash('Access denied! Selected course is not managed by you.', 'danger')
            return redirect(url_for('coordinator.students'))
            
    student.course_id = course_id
    student.status = request.form.get('status')
    
    enrollment_date_str = request.form.get('enrollment_date')
    if enrollment_date_str:
        student.enrollment_date = datetime.strptime(enrollment_date_str, '%Y-%m-%d')
        
    db.session.commit()
    log_audit('Update', 'Student', record_id=student.id, remarks=f'Updated student details: {old_name} -> {student.full_name}')
    flash('Student records updated successfully!', 'success')
    return redirect(url_for('coordinator.students'))

@coordinator_bp.route('/students/delete/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    if current_user.role == 'Coordinator':
        if not student.course_id or not Course.query.filter_by(id=student.course_id, coordinator_id=current_user.id).first():
            flash('Access denied!', 'danger')
            return redirect(url_for('coordinator.students'))
            
    full_name = student.full_name
    try:
        db.session.delete(student)
        db.session.commit()
        log_audit('Delete', 'Student', record_id=id, remarks=f'Permanently deleted student: {full_name}')
        flash('Student deleted successfully!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash("Cannot delete this student because he has associated attendance or fee records.", "danger")
        
    return redirect(url_for('coordinator.students'))

# --- Fees Handling ---
@coordinator_bp.route('/fees', methods=['GET', 'POST'])
@login_required
def fees():
    if request.method == 'POST':
        if current_user.role != 'Coordinator':
            flash('Access denied! Only coordinators can collect fees.', 'danger')
            return redirect(url_for('coordinator.fees'))
            
        registration_id = request.form.get('registration_id')
        amount_paid = float(request.form.get('amount_paid'))
        payment_method = request.form.get('payment_method', 'Cash')
        fee_month = request.form.get('fee_month')
        if not fee_month:
            fee_month = datetime.utcnow().strftime('%Y-%m')
        
        date_collected_str = request.form.get('date_collected')
        if date_collected_str:
            date_collected = datetime.strptime(date_collected_str, '%Y-%m-%d')
        else:
            date_collected = datetime.utcnow()
            
        student = Student.query.filter_by(registration_id=registration_id, status='Active').first()
        if not student:
            flash('Active student with this Registration ID not found!', 'danger')
            return redirect(url_for('coordinator.fees'))
            
        if not student.course_id or not Course.query.filter_by(id=student.course_id, coordinator_id=current_user.id).first():
            flash('Access denied! You do not manage this student.', 'danger')
            return redirect(url_for('coordinator.fees'))
            
        existing_fee = FeeCollection.query.filter_by(
            student_id=student.id, 
            fee_month=fee_month, 
            is_deleted=False
        ).first()
        if existing_fee:
            flash(f'Fee for {student.full_name} for the month {fee_month} has already been collected!', 'danger')
            return redirect(url_for('coordinator.fees'))
                
        new_fee = FeeCollection(
            student_id=student.id, 
            amount_paid=amount_paid, 
            payment_method=payment_method,
            fee_month=fee_month,
            date_collected=date_collected,
            collected_by_id=current_user.id
        )
        db.session.add(new_fee)
        db.session.commit()
        
        log_audit('Create', 'Fee', record_id=new_fee.id, 
                  new_values={'student_id': student.id, 'amount_paid': amount_paid, 'payment_method': payment_method, 'date_collected': date_collected.strftime('%Y-%m-%d')},
                  remarks=f'Coordinator created Fee Voucher #{new_fee.id} of Rs. {amount_paid:.2f} for student {student.full_name}')
                  
        flash(f'Fee of Rs. {amount_paid:.2f} ({payment_method}) collected from {student.full_name}!', 'success')
        return redirect(url_for('coordinator.fees'))
        
    selected_course_id = request.args.get('course_id')
    selected_month = request.args.get('fee_month', datetime.now().strftime('%Y-%m'))

    if current_user.role == 'Coordinator':
        assigned_courses = Course.query.filter_by(coordinator_id=current_user.id).all()
        courses_list = assigned_courses
    else:
        courses_list = Course.query.filter_by(status='Active').all()

    if not courses_list:
        return render_template('fees.html', fees=[], active_students=[], courses=[], selected_course_id=None, selected_month=selected_month, pagination=None)

    valid_course_ids = [str(c.id) for c in courses_list]
    if not selected_course_id or selected_course_id not in valid_course_ids:
        selected_course_id = valid_course_ids[0]

    c_filter = int(selected_course_id)
    
    all_fees = FeeCollection.query.join(Student).filter(
        Student.course_id == c_filter, 
        FeeCollection.is_deleted == False,
        FeeCollection.fee_month == selected_month
    ).order_by(FeeCollection.date_collected.desc()).all()
    
    active_students = Student.query.filter_by(course_id=c_filter, status='Active').all()
        
    return render_template('fees.html', fees=all_fees, active_students=active_students, courses=courses_list, selected_course_id=selected_course_id, selected_month=selected_month, pagination=None)

@coordinator_bp.route('/attendance', methods=['GET'])
@login_required
def attendance():
    if current_user.role == 'Coordinator':
        courses = Course.query.filter_by(coordinator_id=current_user.id, status='Active').all()
    else:
        courses = Course.query.filter_by(status='Active').all()

    if not courses:
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        return render_template('attendance.html', courses=[], today=today)

    selected_course_id = request.args.get('course_id')
    filter_date_str = request.args.get('filter_date', '')
    if not selected_course_id and courses:
        selected_course_id = courses[0].id
        
    course = next((c for c in courses if str(c.id) == str(selected_course_id)), courses[0] if courses else None)
    
    from datetime import date, timedelta, datetime
    today = date.today()
    todays_sessions = []
    pending_past_sessions = []
    past_sessions = []
    active_course_staff = []
    
    if course:
        todays_sessions = ClassSession.query.filter_by(course_id=course.id, date=today).order_by(ClassSession.id.desc()).all()
        
        if filter_date_str:
            try:
                filter_date = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
                past_sessions = ClassSession.query.filter(ClassSession.course_id==course.id, ClassSession.date == filter_date, ClassSession.status == 'Submitted').order_by(ClassSession.date.desc()).all()
            except ValueError:
                pass
        else:
            three_days_ago = today - timedelta(days=3)
            past_sessions = ClassSession.query.filter(ClassSession.course_id==course.id, ClassSession.date >= three_days_ago, ClassSession.date < today, ClassSession.status == 'Submitted').order_by(ClassSession.date.desc()).all()
            
        pending_past_sessions = ClassSession.query.filter(ClassSession.course_id==course.id, ClassSession.date < today, ClassSession.status == 'Pending').order_by(ClassSession.date.desc()).all()
            
        active_course_staff = CourseStaff.query.filter_by(course_id=course.id).all()
        
    import json
    subjects_list = []
    if course and course.subjects:
        try:
            subjects_list = json.loads(course.subjects)
        except Exception:
            pass
            
    return render_template('attendance.html', courses=courses, active_course=course, todays_sessions=todays_sessions, pending_past_sessions=pending_past_sessions, past_sessions=past_sessions, active_course_staff=active_course_staff, today=today.strftime('%Y-%m-%d'), filter_date_str=filter_date_str, subjects=subjects_list)

@coordinator_bp.route('/create_session', methods=['POST'])
@login_required
def create_session():
    course_id = request.form.get('course_id')
    subject_name = request.form.get('subject_name')
    
    course = Course.query.get_or_404(course_id)
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('coordinator.attendance', course_id=course.id, filter_applied=1))
        
    session_date_str = request.form.get('session_date')
    from datetime import date, datetime
    try:
        session_date = datetime.strptime(session_date_str, '%Y-%m-%d').date() if session_date_str else date.today()
    except ValueError:
        session_date = date.today()
        
    existing_session = ClassSession.query.filter_by(
        course_id=course.id,
        date=session_date,
        subject_name=subject_name
    ).first()
    
    if existing_session:
        flash(f"A session for {subject_name} is already scheduled on {session_date.strftime('%Y-%m-%d')}.", 'warning')
        return redirect(url_for('coordinator.attendance', course_id=course.id, filter_applied=1))
        
    new_session = ClassSession(
        course_id=course.id,
        date=session_date,
        subject_name=subject_name,
        created_by_id=current_user.id,
        status='Pending'
    )
    db.session.add(new_session)
    db.session.commit()
    
    from helpers import log_audit
    log_audit('Add', 'ClassSession', record_id=new_session.id, remarks=f"Created pending session for {course.name}")
    
    flash(f"Scheduled pending session for {subject_name} on {session_date.strftime('%Y-%m-%d')}.", 'success')
    return redirect(url_for('coordinator.attendance', course_id=course.id, filter_applied=1))

@coordinator_bp.route('/assign_cr', methods=['POST'])
@login_required
def assign_cr():
    course_id = request.form.get('course_id')
    student_id = request.form.get('student_id')
    
    course = Course.query.get_or_404(course_id)
    student = Student.query.get_or_404(student_id)
    
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index', course_id=course.id, filter_applied=1))
        
    # Check if student already has a user account
    existing_user = User.query.filter_by(linked_student_id=student.id).first()
    from helpers import generate_secure_password, provision_staff_account, generate_whatsapp_link
    
    import urllib.parse
    app_url = request.url_root.rstrip('/')
    
    if not existing_user:
        # Generate username: firstname + reg_id
        base_username = student.full_name.split()[0].lower() + student.registration_id
        raw_password = generate_secure_password()
        
        existing_user = provision_staff_account(
            username=base_username,
            raw_password=raw_password,
            role='CR',
            full_name=student.full_name,
            contact=student.phone,
            linked_student_id=student.id
        )
        
        phone = ''.join(filter(str.isdigit, str(student.phone)))
        wa_msg = f"Assalam-o-Alaikum {student.full_name}. Alhamdulillah, you have been chosen as the Class Representative (CR) for the '{course.name}'. Serving the students of the Quran is a beautiful privilege. Here are your secure login details to manage daily attendance:\nLink: {app_url}\nUsername: {base_username}\nPassword: {raw_password}\nMay Allah make this responsibility easy and rewarding for you. JazakAllah Khair!"
        wa_link = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(wa_msg)}"
        
        flash(f'CR Account Created! Username: {base_username} Password: {raw_password} <a href="{wa_link}" target="_blank" class="btn btn-sm btn-success rounded-pill ms-3 shadow-sm"><i class="bi bi-whatsapp"></i> Send on WhatsApp</a>', 'success')
    else:
        from werkzeug.security import generate_password_hash
        raw_password = generate_secure_password()
        existing_user.password_hash = generate_password_hash(raw_password)
        existing_user.status = 'Active'
        db.session.commit()
        
        phone = ''.join(filter(str.isdigit, str(student.phone)))
        wa_msg = f"Assalam-o-Alaikum {student.full_name}. Your CR access for the '{course.name}' has been successfully updated. Please use the new credentials below to continue your khidmat:\nLink: {app_url}\nUsername: {existing_user.username}\nPassword: {raw_password}\nMay Allah put Barakah in your continued efforts. JazakAllah!"
        wa_link = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(wa_msg)}"
        
        flash(f'CR Account Reactivated! Username: {existing_user.username} Password: {raw_password} <a href="{wa_link}" target="_blank" class="btn btn-sm btn-success rounded-pill ms-3 shadow-sm"><i class="bi bi-whatsapp"></i> Send on WhatsApp</a>', 'success')
    
    # Assign to CourseStaff
    existing_staff = CourseStaff.query.filter_by(course_id=course.id, user_id=existing_user.id).first()
    if not existing_staff:
        new_staff = CourseStaff(course_id=course.id, user_id=existing_user.id, role_in_course='CR')
        db.session.add(new_staff)
        db.session.commit()
        log_audit('Assign', 'CR', record_id=new_staff.id, remarks=f"Assigned {student.full_name} as CR to {course.name}")
        flash('Student successfully assigned as CR.', 'success')
    else:
        flash('Student is already assigned to this course.', 'warning')
        
    return redirect(url_for('dashboard.index', course_id=course.id, filter_applied=1))

@coordinator_bp.route('/revoke_cr/<int:staff_id>', methods=['POST'])
@login_required
def revoke_cr(staff_id):
    staff_record = CourseStaff.query.get_or_404(staff_id)
    course = Course.query.get(staff_record.course_id)
    
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index', course_id=course.id, filter_applied=1))
        
    target_user = User.query.get(staff_record.user_id)
    db.session.delete(staff_record)
    if target_user:
        target_user.status = 'Inactive'
    db.session.commit()
    
    import urllib.parse
    if target_user and target_user.contact:
        phone = ''.join(filter(str.isdigit, str(target_user.contact)))
        wa_msg = f"Assalam-o-Alaikum {target_user.full_name}. We want to express our heartfelt gratitude for your dedication and khidmat as the CR for the '{course.name}'. Your administrative duties have now been transitioned. May Allah (SWT) accept your efforts, bless your time, and reward you immensely for helping the class. JazakAllah Khair!"
        wa_link = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(wa_msg)}"
        flash(f'Staff access revoked from course. <a href="{wa_link}" target="_blank" class="btn btn-sm btn-success rounded-pill ms-3 shadow-sm"><i class="bi bi-whatsapp"></i> Notify on WhatsApp</a>', 'success')
    else:
        flash('Staff access revoked from course.', 'success')
        
    from helpers import log_audit
    log_audit('Revoke', 'CR', record_id=staff_id, remarks=f"Revoked CR access for {course.name}")
    return redirect(url_for('dashboard.index', course_id=course.id, filter_applied=1))

@coordinator_bp.route('/reset_cr_password/<int:staff_id>', methods=['POST'])
@login_required
def reset_cr_password(staff_id):
    staff_record = CourseStaff.query.get_or_404(staff_id)
    course = Course.query.get(staff_record.course_id)
    
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index', course_id=course.id, filter_applied=1))
        
    target_user = User.query.get(staff_record.user_id)
    if target_user:
        from helpers import generate_secure_password
        from werkzeug.security import generate_password_hash
        new_password = generate_secure_password()
        target_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        from helpers import log_audit
        log_audit('Update', 'User', record_id=target_user.id, remarks=f"Password reset for CR {target_user.username}")
        import urllib.parse
        app_url = request.url_root.rstrip('/')
        phone = ''.join(filter(str.isdigit, str(target_user.contact))) if target_user.contact else ''
        wa_msg = f"Assalam-o-Alaikum {target_user.full_name}. The password for your CR portal for the '{course.name}' has been securely reset. You can now log in and continue your khidmat using the new details below:\n\nLink: {app_url}\nUsername: {target_user.username}\nNew Password: {new_password}\n\nMay Allah bless your time and efforts. JazakAllah Khair!"
        wa_link = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(wa_msg)}"
        
        flash(f'Password reset successfully! New Password for {target_user.username} is: {new_password} <a href="{wa_link}" target="_blank" class="btn btn-sm btn-success rounded-pill ms-3 shadow-sm"><i class="bi bi-whatsapp"></i> Send on WhatsApp</a>', 'success')
    else:
        flash('User account not found.', 'danger')
        
    return redirect(url_for('dashboard.index', course_id=course.id, filter_applied=1))

@coordinator_bp.route('/attendance/<int:course_id>/<int:session_id>', methods=['GET', 'POST'])
@login_required
def attendance_bulk(course_id, session_id):
    course = Course.query.get_or_404(course_id)
    session_obj = ClassSession.query.get_or_404(session_id)
    
    if session_obj.course_id != course.id:
        flash('Invalid session!', 'danger')
        return redirect(url_for('coordinator.attendance', course_id=course.id))
        
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('coordinator.attendance'))
        
    students = Student.query.filter_by(course_id=course.id, status='Active').all()
    
    if request.method == 'POST':
        for s in students:
            status = request.form.get(f'status_{s.id}')
            if status:
                existing = Attendance.query.filter_by(session_id=session_obj.id, student_id=s.id).first()
                if existing:
                    existing.status = status
                else:
                    new_att = Attendance(session_id=session_obj.id, student_id=s.id, status=status)
                    db.session.add(new_att)
        db.session.commit()
        log_audit('Update', 'Attendance', remarks=f"Bulk attendance updated for Session ID {session_obj.id}")
        flash('Attendance saved successfully!', 'success')
        return redirect(url_for('coordinator.attendance', course_id=course.id))
        
    existing_attendance = Attendance.query.filter_by(session_id=session_obj.id).all()
    attendance_map = {att.student_id: att.status for att in existing_attendance}
    
    return render_template('attendance_bulk.html', course=course, session_obj=session_obj, students=students, attendance_map=attendance_map)



@coordinator_bp.route('/edit_session/<int:session_id>', methods=['POST'])
@login_required
def edit_session(session_id):
    session_obj = ClassSession.query.get_or_404(session_id)
    course = Course.query.get(session_obj.course_id)
    
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('coordinator.attendance', course_id=course.id))
        
    new_date_str = request.form.get('date')
    new_subject = request.form.get('subject_name')
    
    if new_date_str:
        session_obj.date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
    if new_subject:
        session_obj.subject_name = new_subject
        
    db.session.commit()
    log_audit('Update', 'ClassSession', record_id=session_id, remarks=f"Updated session {session_id} to {new_subject} on {new_date_str}")
    flash('Session updated successfully!', 'success')
    return redirect(url_for('coordinator.attendance', course_id=course.id))

@coordinator_bp.route('/delete_session/<int:session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    session_obj = ClassSession.query.get_or_404(session_id)
    course = Course.query.get(session_obj.course_id)
    
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('coordinator.attendance', course_id=course.id))
        
    db.session.delete(session_obj)
    db.session.commit()
    log_audit('Delete', 'ClassSession', record_id=session_id, remarks=f"Deleted session {session_id}")
    flash('Session and all associated attendance records deleted successfully!', 'success')
    return redirect(url_for('coordinator.attendance', course_id=course.id))

# --- Expenses Tracking ---
@coordinator_bp.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    if request.method == 'POST':
        title = request.form.get('title')
        if title == 'Other':
            title = request.form.get('custom_title')
            
        amount = float(request.form.get('amount'))
        payment_method = request.form.get('payment_method', 'Cash')
        
        course_id_str = request.form.get('course_id')
        course_id = int(course_id_str) if (course_id_str and course_id_str.isdigit()) else None
        
        if current_user.role == 'Coordinator':
            if not course_id or not Course.query.filter_by(id=course_id, coordinator_id=current_user.id).first():
                flash('Access denied! You must select an active course assigned to you.', 'danger')
                return redirect(url_for('coordinator.expenses'))
                
        expense_date_str = request.form.get('expense_date')
        if expense_date_str:
            expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d')
        else:
            expense_date = datetime.utcnow()
            
        new_expense = Expense(
            title=title, 
            amount=amount,
            payment_method=payment_method,
            course_id=course_id,
            expense_date=expense_date
        )
        db.session.add(new_expense)
        db.session.commit()
        
        log_audit('Create', 'Expense', record_id=new_expense.id,
                  new_values={'title': title, 'amount': amount, 'payment_method': payment_method, 'course_id': course_id, 'expense_date': expense_date.strftime('%Y-%m-%d')},
                  remarks=f'Coordinator created Expense Voucher #{new_expense.id}: {title} of Rs. {amount:.2f}')
                  
        flash('Expense recorded successfully!', 'success')
        return redirect(url_for('coordinator.expenses'))
        
    selected_course_id = request.args.get('course_id')
    selected_month = request.args.get('expense_month', datetime.now().strftime('%Y-%m'))
    
    try:
        target_year, target_month = map(int, selected_month.split('-'))
    except ValueError:
        target_year, target_month = datetime.now().year, datetime.now().month

    if current_user.role == 'Coordinator':
        assigned_courses = Course.query.filter_by(coordinator_id=current_user.id).all()
        courses_list = assigned_courses
    else:
        courses_list = Course.query.filter_by(status='Active').all()

    if not courses_list:
        return render_template('expenses.html', expenses=[], courses=[], selected_course_id=None, selected_month=selected_month, pagination=None)

    valid_course_ids = [str(c.id) for c in courses_list]
    if not selected_course_id or selected_course_id not in valid_course_ids:
        selected_course_id = valid_course_ids[0]

    c_filter = int(selected_course_id)
    
    all_expenses = Expense.query.filter(
        Expense.course_id == c_filter,
        Expense.is_deleted == False,
        db.extract('year', Expense.expense_date) == target_year,
        db.extract('month', Expense.expense_date) == target_month
    ).order_by(Expense.expense_date.desc()).all()
        
    return render_template('expenses.html', expenses=all_expenses, courses=courses_list, selected_course_id=selected_course_id, selected_month=selected_month, pagination=None)

# --- Approval Requests ---
@coordinator_bp.route('/request_edit', methods=['POST'])
@login_required
def request_edit():
    if current_user.role != 'Coordinator':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    module = request.form.get('module')
    record_id = int(request.form.get('record_id'))
    reason = request.form.get('reason')
    comments = request.form.get('comments', '')
    
    payload = {}
    if module == 'Fee':
        payload = {
            'amount_paid': float(request.form.get('amount_paid')),
            'payment_method': request.form.get('payment_method'),
            'date_collected': request.form.get('date_collected')
        }
        record = FeeCollection.query.filter_by(id=record_id, is_deleted=False).first_or_404()
    elif module == 'Expense':
        payload = {
            'title': request.form.get('title'),
            'amount': float(request.form.get('amount')),
            'payment_method': request.form.get('payment_method'),
            'course_id': int(request.form.get('course_id')) if request.form.get('course_id') else None,
            'expense_date': request.form.get('expense_date')
        }
        record = Expense.query.filter_by(id=record_id, is_deleted=False).first_or_404()
    else:
        flash('Invalid module!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    new_req = ApprovalRequest(
        request_type='Edit',
        module=module,
        record_id=record_id,
        requested_by_id=current_user.id,
        reason=reason,
        comments=comments,
        temporary_edit_payload=json.dumps(payload),
        status='Pending'
    )
    db.session.add(new_req)
    db.session.commit()
    
    log_audit('Request Edit', module, record_id=record_id, new_values=payload, remarks=f'Edit request submitted: {reason}')
    
    flash(f'{module} edit request submitted for approval.', 'success')
    return redirect(url_for('coordinator.fees' if module == 'Fee' else 'coordinator.expenses'))

@coordinator_bp.route('/request_delete', methods=['POST'])
@login_required
def request_delete():
    if current_user.role != 'Coordinator':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    module = request.form.get('module')
    record_id = int(request.form.get('record_id'))
    reason = request.form.get('reason')
    
    if module == 'Fee':
        record = FeeCollection.query.filter_by(id=record_id, is_deleted=False).first_or_404()
    elif module == 'Expense':
        record = Expense.query.filter_by(id=record_id, is_deleted=False).first_or_404()
    else:
        flash('Invalid module!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    new_req = ApprovalRequest(
        request_type='Delete',
        module=module,
        record_id=record_id,
        requested_by_id=current_user.id,
        reason=reason,
        status='Pending'
    )
    db.session.add(new_req)
    db.session.commit()
    
    log_audit('Request Delete', module, record_id=record_id, remarks=f'Delete request submitted. Reason: {reason}')
    
    flash(f'{module} delete request submitted for approval.', 'success')
    return redirect(url_for('coordinator.fees' if module == 'Fee' else 'coordinator.expenses'))

@coordinator_bp.route('/my_requests')
@login_required
def view_my_requests():
    if current_user.role != 'Coordinator':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    page = request.args.get('page', 1, type=int)
    pagination = ApprovalRequest.query.filter_by(requested_by_id=current_user.id).order_by(ApprovalRequest.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    requests_list = pagination.items
    
    # Pre-load only records for context
    fee_ids = [r.record_id for r in requests_list if r.module == 'Fee']
    exp_ids = [r.record_id for r in requests_list if r.module == 'Expense']
    
    fee_records = {f.id: f for f in FeeCollection.query.filter(FeeCollection.id.in_(fee_ids)).all()} if fee_ids else {}
    expense_records = {e.id: e for e in Expense.query.filter(Expense.id.in_(exp_ids)).all()} if exp_ids else {}
    
    return render_template('coordinator_requests.html', pagination=pagination, requests=requests_list, fee_records=fee_records, expense_records=expense_records, json=json)
