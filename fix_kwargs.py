import re

with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'r') as f:
    content = f.read()

# Remove all instances of the kwargs
content = content.replace(', active_course_staff=active_course_staff, active_course_students=active_course_students', '')
content = content.replace(', active_course_staff=active_course_staff', '')
content = content.replace(', active_course_students=active_course_students', '')
content = content.replace('active_course_students=active_course_students,\n', '')

# Now re-insert them exactly once before the closing parenthesis of render_template calls
# We'll use regex to find `render_template(..., ..., )` and insert our args.
# A simpler way is to just do a string replace on `)` but there are many `)` in the file.
# We'll target the known ends of render_template in dashboard.py

content = content.replace('end_date_str=\'\')', 'end_date_str=\'\', active_course_staff=active_course_staff, active_course_students=active_course_students)')
content = content.replace('low_attendance=low_attendance)', 'low_attendance=low_attendance, active_course_staff=active_course_staff, active_course_students=active_course_students)')
content = content.replace('active_courses=active_courses)', 'active_courses=active_courses, active_course_staff=active_course_staff, active_course_students=active_course_students)')


with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'w') as f:
    f.write(content)
