import re
import os

routes_file = '/home/alyan-hammad/tanzeem_webapp/routes/coordinator.py'

with open(routes_file, 'r') as f:
    content = f.read()

# Replace the attendance route completely
new_attendance_route = """@coordinator_bp.route('/attendance', methods=['GET'])
@login_required
def attendance():
    if current_user.role == 'Coordinator':
        courses = Course.query.filter_by(coordinator_id=current_user.id, status='Active').all()
    else:
        courses = Course.query.filter_by(status='Active').all()

    if not courses:
        return render_template('attendance.html', courses=[], compliance_data=[])

    today = date.today()
    compliance_data = []

    for course in courses:
        session = ClassSession.query.filter_by(course_id=course.id, date=today).first()
        status = 'Submitted' if session else 'Pending'
        
        active_students = Student.query.filter_by(course_id=course.id, status='Active').all()
        staff = CourseStaff.query.filter_by(course_id=course.id).all()
        
        compliance_data.append({
            'course': course,
            'status': status,
            'session': session,
            'staff': staff,
            'students': active_students
        })
        
    return render_template('attendance.html', compliance_data=compliance_data, courses=courses, today=today.strftime('%Y-%m-%d'))

@coordinator_bp.route('/assign_cr', methods=['POST'])
@login_required
def assign_cr():
    course_id = request.form.get('course_id')
    student_id = request.form.get('student_id')
    
    course = Course.query.get_or_404(course_id)
    student = Student.query.get_or_404(student_id)
    
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('coordinator.attendance'))
        
    # Check if student already has a user account
    existing_user = User.query.filter_by(linked_student_id=student.id).first()
    from helpers import generate_secure_password, provision_staff_account, generate_whatsapp_link
    
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
        # In a real app we'd dispatch a background task to send WhatsApp, 
        # but here the Coordinator can click a link generated on the UI.
        flash(f'CR Account Created! Username: {base_username} Password: {raw_password}', 'success')
    
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
        
    return redirect(url_for('coordinator.attendance'))

@coordinator_bp.route('/revoke_cr/<int:staff_id>', methods=['POST'])
@login_required
def revoke_cr(staff_id):
    staff_record = CourseStaff.query.get_or_404(staff_id)
    course = Course.query.get(staff_record.course_id)
    
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('coordinator.attendance'))
        
    db.session.delete(staff_record)
    db.session.commit()
    log_audit('Revoke', 'CR', record_id=staff_id, remarks=f"Revoked CR access for {course.name}")
    flash('Staff access revoked from course.', 'success')
    return redirect(url_for('coordinator.attendance'))

@coordinator_bp.route('/attendance/<int:course_id>/<int:session_id>"""

# Using regex to replace the old def attendance() up to the next route
content = re.sub(
    r'@coordinator_bp\.route\(\'/attendance\', methods=\[\'GET\', \'POST\'\]\).*?@coordinator_bp\.route\(\'/attendance/<int:course_id>/<int:session_id>',
    new_attendance_route,
    content,
    flags=re.DOTALL
)

# Also need to import CourseStaff in coordinator.py
if 'CourseStaff' not in content:
    content = content.replace('from models import ', 'from models import CourseStaff, ')

with open(routes_file, 'w') as f:
    f.write(content)

print("Coordinator attendance routes updated!")
