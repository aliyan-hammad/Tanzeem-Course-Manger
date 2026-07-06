import re

with open('/home/alyan-hammad/tanzeem_webapp/templates/dashboard.html', 'r') as f:
    content = f.read()

# Replace the course_id column in dashboard.html
old_col = """            <div class="col-md-4">
                <label for="course_id" class="form-label fw-bold text-secondary">Course</label>
                <select class="form-select" id="course_id" name="course_id">
                    <option value="" {% if not selected_course_id %}selected{% endif %}>All Courses</option>
                    {% for course in courses %}
                    <option value="{{ course.id }}" {% if selected_course_id|string == course.id|string %}selected{% endif %}>{{ course.name }}</option>
                    {% endfor %}
                </select>
            </div>"""

new_col = """            <div class="col-md-5">
                <div class="d-flex justify-content-between align-items-end">
                    <label for="course_id" class="form-label fw-bold text-secondary mb-1">Course</label>
                    {% if selected_course_id and selected_course_id != '' %}
                        {% if active_course_staff %}
                            <div class="d-flex gap-1 mb-1">
                            {% for staff in active_course_staff %}
                                <span class="badge bg-secondary d-flex align-items-center gap-1">
                                    {{ staff.role_in_course }}: {{ staff.user.full_name }}
                                    <form action="{{ url_for('coordinator.revoke_cr', staff_id=staff.id) }}" method="POST" class="d-inline m-0 p-0" onsubmit="return confirm('Revoke this staff member\\'s access?');">
                                        <button type="submit" class="btn btn-sm btn-link text-white p-0 m-0 text-decoration-none" title="Revoke"><i class="bi bi-x-circle-fill"></i></button>
                                    </form>
                                </span>
                            {% endfor %}
                            </div>
                        {% else %}
                            <button type="button" class="btn btn-sm btn-outline-primary py-0 mb-1" data-bs-toggle="modal" data-bs-target="#assignCRModal">+ Assign CR</button>
                        {% endif %}
                    {% endif %}
                </div>
                <select class="form-select" id="course_id" name="course_id" onchange="this.form.submit()">
                    <option value="" {% if not selected_course_id %}selected{% endif %}>All Courses</option>
                    {% for course in courses %}
                    <option value="{{ course.id }}" {% if selected_course_id|string == course.id|string %}selected{% endif %}>{{ course.name }}</option>
                    {% endfor %}
                </select>
            </div>"""

content = content.replace(old_col, new_col)

# Make sure we don't break the layout by changing col-md-4 to col-md-5.
# The original row had: 4 (course), 3 (start date), 3 (end date), 2 (submit btn) = 12.
# Wait, if I change it to col-md-5, it will be 5+3+3+2 = 13 which wraps!
# So I must keep it col-md-4, or change the submit button to col-md-2 -> col-lg-2... let's just use col-md-5 and change the others to 3, 2, 2.
# Let's just keep it col-md-4 and use a compact layout for the badges.
content = content.replace('class="col-md-5"', 'class="col-md-4"')

# Add the Assign CR modal at the bottom of the content block
modal_html = """
{% if selected_course_id and selected_course_id != '' and not active_course_staff %}
<!-- Assign CR Modal -->
<div class="modal fade" id="assignCRModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title">Assign CR</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <form action="{{ url_for('coordinator.assign_cr') }}" method="POST">
                <div class="modal-body">
                    <input type="hidden" name="course_id" value="{{ selected_course_id }}">
                    <div class="mb-3">
                        <label class="form-label fw-bold">Select Enrolled Student</label>
                        <select class="form-select" name="student_id" required>
                            <option value="" disabled selected>-- Choose Student --</option>
                            {% for student in active_course_students %}
                            <option value="{{ student.id }}">{{ student.full_name }} (Reg: {{ student.registration_id }})</option>
                            {% else %}
                            <option value="" disabled>No active students in this course</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="alert alert-warning small">
                        Assigning a student as a CR will automatically generate a secure login for them.
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create & Assign CR</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endif %}
"""

content = re.sub(r'\{%\s*endblock\s*%\}', modal_html + '\n{% endblock %}', content, count=1)

with open('/home/alyan-hammad/tanzeem_webapp/templates/dashboard.html', 'w') as f:
    f.write(content)
print("Dashboard HTML updated.")
