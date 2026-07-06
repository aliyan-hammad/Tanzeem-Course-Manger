import re

# Update dashboard.py
with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'r') as f:
    dashboard_content = f.read()

# Add CourseStaff to imports
if 'CourseStaff' not in dashboard_content:
    dashboard_content = dashboard_content.replace('from models import ', 'from models import CourseStaff, ')

# Add the logic right before render_template in dashboard.py
dashboard_injection = """
    active_course_staff = []
    active_course_students = []
    if selected_course_id:
        active_course_staff = CourseStaff.query.filter_by(course_id=selected_course_id).all()
        active_course_students = Student.query.filter_by(course_id=selected_course_id, status='Active').all()
        
    return render_template('dashboard.html',"""

dashboard_content = re.sub(r'return render_template\(\'dashboard\.html\',', dashboard_injection, dashboard_content)

with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'w') as f:
    f.write(dashboard_content)

# Update coordinator.py
with open('/home/alyan-hammad/tanzeem_webapp/routes/coordinator.py', 'r') as f:
    coord_content = f.read()

new_attendance_route = """@coordinator_bp.route('/attendance', methods=['GET'])
@login_required
def attendance():
    if current_user.role == 'Coordinator':
        courses = Course.query.filter_by(coordinator_id=current_user.id, status='Active').all()
    else:
        courses = Course.query.filter_by(status='Active').all()

    if not courses:
        return render_template('attendance.html', courses=[])

    selected_course_id = request.args.get('course_id')
    if not selected_course_id and courses:
        selected_course_id = courses[0].id
        
    course = next((c for c in courses if str(c.id) == str(selected_course_id)), courses[0] if courses else None)
    
    from datetime import date
    today = date.today()
    todays_sessions = []
    past_sessions = []
    active_course_staff = []
    
    if course:
        todays_sessions = ClassSession.query.filter_by(course_id=course.id, date=today).order_by(ClassSession.id.desc()).all()
        past_sessions = ClassSession.query.filter(ClassSession.course_id==course.id, ClassSession.date < today).order_by(ClassSession.date.desc()).all()
        active_course_staff = CourseStaff.query.filter_by(course_id=course.id).all()
        
    return render_template('attendance.html', courses=courses, active_course=course, todays_sessions=todays_sessions, past_sessions=past_sessions, active_course_staff=active_course_staff, today=today.strftime('%Y-%m-%d'))

@coordinator_bp.route('/assign_cr'"""

# Using regex to replace the old def attendance() up to def assign_cr()
coord_content = re.sub(
    r'@coordinator_bp\.route\(\'/attendance\', methods=\[\'GET\'\]\).*?@coordinator_bp\.route\(\'/assign_cr\'',
    new_attendance_route,
    coord_content,
    flags=re.DOTALL
)

with open('/home/alyan-hammad/tanzeem_webapp/routes/coordinator.py', 'w') as f:
    f.write(coord_content)
    
print("Routes updated successfully.")
