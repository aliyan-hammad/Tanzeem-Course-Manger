with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if i == 229: # Line 230 is index 229
        skip = True
        
        # Insert the correct block
        new_lines.append("        active_course_staff = []\n")
        new_lines.append("        active_course_students = []\n")
        new_lines.append("        if selected_course_id:\n")
        new_lines.append("            active_course_staff = CourseStaff.query.filter_by(course_id=selected_course_id).all()\n")
        new_lines.append("            active_course_students = Student.query.filter_by(course_id=selected_course_id, status='Active').all()\n")
        new_lines.append("            \n")
        new_lines.append("        return render_template('dashboard.html', \n")
        new_lines.append("                                   total_active_students=total_active_students,\n")
        new_lines.append("                                   hand_cash=hand_cash,\n")
        new_lines.append("                                   in_account=in_account,\n")
        new_lines.append("                                   total_fees=total_fees,\n")
        new_lines.append("                                   total_expenses=total_expenses,\n")
        new_lines.append("                                   net_balance=net_balance,\n")
        new_lines.append("                                   students_paid_count=students_paid_count,\n")
        new_lines.append("                                   latest_fees=latest_fees,\n")
        new_lines.append("                                   latest_expenses=latest_expenses,\n")
        new_lines.append("                                   courses=courses_list,\n")
        new_lines.append("                                   selected_course_id=selected_course_id,\n")
        new_lines.append("                                   today_collections=today_collections,\n")
        new_lines.append("                                   monthly_collections=monthly_collections,\n")
        new_lines.append("                                   expenses_added=total_expenses,\n")
        new_lines.append("                                   pending_requests_count=pending_requests_count,\n")
        new_lines.append("                                   start_date_str=start_date_str, end_date_str=end_date_str,\n")
        new_lines.append("                                   yesterdays_absentees=yesterdays_absentees,\n")
        new_lines.append("                                   today_absentees=today_absentees,\n")
        new_lines.append("                                   consecutive_absences=consecutive_absences,\n")
        new_lines.append("                                   low_attendance=low_attendance,\n")
        new_lines.append("                                   active_course_staff=active_course_staff, active_course_students=active_course_students)\n")
        new_lines.append("                                   \n")
        
    if i == 261: # Line 262 is index 261 (else: # Admin)
        skip = False
        
    if not skip:
        new_lines.append(line)

with open('/home/alyan-hammad/tanzeem_webapp/routes/dashboard.py', 'w') as f:
    f.writelines(new_lines)
