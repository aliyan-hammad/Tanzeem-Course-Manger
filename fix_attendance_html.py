with open('templates/attendance.html', 'r') as f:
    content = f.read()

content = content.replace("url_for('coordinator.attendance_course', course_id=active_course.id)", "url_for('coordinator.attendance')")
content = content.replace('name="date" required value="{{ selected_date }}">', 'name="date" required value="{{ selected_date }}">\n                    <input type="hidden" name="course_id" value="{{ active_course.id }}">')
content = content.replace("coordinator.attendance_course", "coordinator.attendance")

with open('templates/attendance.html', 'w') as f:
    f.write(content)
