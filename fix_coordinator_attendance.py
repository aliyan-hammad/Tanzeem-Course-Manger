import re

with open('routes/coordinator.py', 'r') as f:
    content = f.read()

old_routes = """@coordinator_bp.route('/attendance')
@login_required
def attendance():
    if current_user.role == 'Coordinator':
        courses = Course.query.filter_by(coordinator_id=current_user.id).all()
        if len(courses) == 1:
            return redirect(url_for('coordinator.attendance_course', course_id=courses[0].id))
    else:
        courses = Course.query.filter_by(status='Active').all()
    return render_template('attendance.html', courses=courses, active_course=None)

@coordinator_bp.route('/attendance/<int:course_id>', methods=['GET', 'POST'])
@login_required
def attendance_course(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role == 'Coordinator' and course.coordinator_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('coordinator.attendance'))
        
    if request.method == 'POST':
        date_str = request.form.get('date')
        subject_name = request.form.get('subject_name')
        
        session_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        new_session = ClassSession(course_id=course.id, date=session_date, subject_name=subject_name)
        db.session.add(new_session)
        db.session.commit()
        log_audit('Create', 'ClassSession', record_id=new_session.id, remarks=f"Created session for {subject_name} on {date_str}")
        flash('Session created successfully!', 'success')
        return redirect(url_for('coordinator.attendance_bulk', course_id=course.id, session_id=new_session.id))
        
    if current_user.role == 'Coordinator':
        courses = Course.query.filter_by(coordinator_id=current_user.id).all()
    else:
        courses = Course.query.filter_by(status='Active').all()
        
    session_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        session_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
    except ValueError:
        session_date = date.today()

    all_sessions = ClassSession.query.filter_by(course_id=course.id, date=session_date).order_by(ClassSession.id.desc()).all()
    
    return render_template('attendance.html', courses=courses, active_course=course, sessions=all_sessions, selected_date=session_date_str, today=date.today().strftime('%Y-%m-%d'), json=json, pagination=None)"""

new_routes = """@coordinator_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    if current_user.role == 'Coordinator':
        courses = Course.query.filter_by(coordinator_id=current_user.id).all()
    else:
        courses = Course.query.filter_by(status='Active').all()

    if not courses:
        flash('No courses assigned or available.', 'warning')
        return redirect(url_for('coordinator.dashboard'))

    selected_course_id = request.args.get('course_id')
    if not selected_course_id and request.method == 'GET':
        selected_course_id = courses[0].id
    
    if request.method == 'POST':
        selected_course_id = request.form.get('course_id')

    course = next((c for c in courses if str(c.id) == str(selected_course_id)), courses[0])

    if request.method == 'POST':
        date_str = request.form.get('date')
        subject_name = request.form.get('subject_name')
        
        session_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        new_session = ClassSession(course_id=course.id, date=session_date, subject_name=subject_name)
        db.session.add(new_session)
        db.session.commit()
        log_audit('Create', 'ClassSession', record_id=new_session.id, remarks=f"Created session for {subject_name} on {date_str}")
        flash('Session created successfully!', 'success')
        return redirect(url_for('coordinator.attendance_bulk', course_id=course.id, session_id=new_session.id))
        
    session_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        session_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
    except ValueError:
        session_date = date.today()

    all_sessions = ClassSession.query.filter_by(course_id=course.id, date=session_date).order_by(ClassSession.id.desc()).all()
    
    return render_template('attendance.html', courses=courses, active_course=course, sessions=all_sessions, selected_date=session_date_str, today=date.today().strftime('%Y-%m-%d'), json=json, pagination=None)"""

if old_routes in content:
    content = content.replace(old_routes, new_routes)
    with open('routes/coordinator.py', 'w') as f:
        f.write(content)
    print("Success")
else:
    print("Failed to find old routes")

