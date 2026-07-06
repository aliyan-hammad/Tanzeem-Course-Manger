import re

with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for idx, line in enumerate(lines):
    if "return render_template('dashboard.html'" in line and "if not assigned_course_ids:" not in "".join(lines[idx-2:idx]):
        # Inject the logic before the return statement
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(indent + "active_course_staff = []\n")
        new_lines.append(indent + "active_course_students = []\n")
        new_lines.append(indent + "if selected_course_id:\n")
        new_lines.append(indent + "    active_course_staff = CourseStaff.query.filter_by(course_id=selected_course_id).all()\n")
        new_lines.append(indent + "    active_course_students = Student.query.filter_by(course_id=selected_course_id, status='Active').all()\n")
        new_lines.append(line)
    elif "selected_course_id=selected_course_id," in line or "start_date_str=start_date_str" in line:
        if "active_course_staff" not in line and "render_template" not in line:
            new_lines.append(line.rstrip() + ", active_course_staff=active_course_staff, active_course_students=active_course_students\n")
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'w') as f:
    f.writelines(new_lines)

print("Fixed returns in dashboard.py")
