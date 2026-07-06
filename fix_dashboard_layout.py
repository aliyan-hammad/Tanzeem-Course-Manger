import re

with open('/home/alyan-hammad/tanzeem_webapp/templates/dashboard.html', 'r') as f:
    content = f.read()

# 1. Restore the original course dropdown column
old_bad_col = """            <div class="col-md-4">
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

restored_col = """            <div class="col-md-4">
                <label for="course_id" class="form-label fw-bold text-secondary">Course Filter</label>
                <select class="form-select" id="course_id" name="course_id" onchange="this.form.submit()">
                    <option value="" {% if not selected_course_id %}selected{% endif %}>All Courses</option>
                    {% for course in courses %}
                    <option value="{{ course.id }}" {% if selected_course_id|string == course.id|string %}selected{% endif %}>{{ course.name }}</option>
                    {% endfor %}
                </select>
            </div>"""

content = content.replace(old_bad_col, restored_col)

# 2. Add the CR management row OUTSIDE the form.
# The form ends with </form>\n    </div>\n</div> (around line 35 of the original file)
# We will inject the CR management row right after that card!

cr_management_html = """
{% if selected_course_id and selected_course_id != '' %}
<div class="card shadow-sm border-0 mb-4 border-start border-4 border-primary">
    <div class="card-body d-flex flex-wrap align-items-center justify-content-between gap-3">
        <div>
            <h6 class="mb-1 fw-bold text-secondary">Assigned Staff & CRs for Selected Course</h6>
            <div class="d-flex flex-wrap gap-2">
                {% if active_course_staff %}
                    {% for staff in active_course_staff %}
                    <div class="badge bg-light text-dark border p-2 d-flex align-items-center gap-2">
                        <span><strong class="text-primary">{{ staff.role_in_course }}:</strong> {{ staff.user.full_name }}</span>
                        <form action="{{ url_for('coordinator.revoke_cr', staff_id=staff.id) }}" method="POST" class="d-inline m-0 p-0" onsubmit="return confirm('Revoke this staff member\\'s access?');">
                            <button type="submit" class="btn btn-sm btn-danger py-0 px-1 rounded" title="Revoke"><i class="bi bi-x"></i></button>
                        </form>
                    </div>
                    {% endfor %}
                {% else %}
                    <span class="text-muted small">No CRs assigned yet.</span>
                {% endif %}
            </div>
        </div>
        <div>
            <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#assignCRModal"><i class="bi bi-person-plus me-1"></i> Assign CR</button>
        </div>
    </div>
</div>
{% endif %}
"""

# Find the end of the filter card
filter_card_end = "</form>\n    </div>\n</div>"
content = content.replace(filter_card_end, filter_card_end + "\n" + cr_management_html)

# Also, fix the modal logic. Currently it has {% if selected_course_id ... and not active_course_staff %}
# We want it to always be available if selected_course_id is present.
old_modal_cond = "{% if selected_course_id and selected_course_id != '' and not active_course_staff %}"
new_modal_cond = "{% if selected_course_id and selected_course_id != '' %}"
content = content.replace(old_modal_cond, new_modal_cond)

with open('/home/alyan-hammad/tanzeem_webapp/templates/dashboard.html', 'w') as f:
    f.write(content)
print("Fixed dashboard layout by moving CR management outside the form.")
