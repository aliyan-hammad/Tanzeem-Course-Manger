with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'r') as f:
    content = f.read()

content = content.replace('active_course_students=active_course_students\n', 'active_course_students=active_course_students,\n')

with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'w') as f:
    f.write(content)
