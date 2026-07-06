html_content = """{% extends "base.html" %}

{% block content %}
{% if not courses %}
<div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
    <h2 class="mb-0">Compliance Monitor</h2>
</div>
<div class="alert alert-info text-center shadow-sm border-0 rounded-3 mt-5 p-5">
    <i class="bi bi-journal-check display-1 text-info d-block mb-3 opacity-50"></i>
    <h3 class="alert-heading fw-bold text-dark mb-3">No Courses Assigned</h3>
    <p class="text-muted fs-5 mb-0">Your workspace is ready, but you haven't been assigned to any active courses. Once an administrator assigns a course to your account, you will monitor attendance compliance here.</p>
</div>
{% else %}
<div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
    <h2 class="mb-0">Compliance Monitor</h2>
</div>

<div class="card shadow-sm border-0">
    <div class="card-header bg-light d-flex flex-wrap justify-content-between align-items-center gap-2">
        <h5 class="mb-0">Today's Attendance Status ({{ today }})</h5>
    </div>
    <div class="card-body p-0">
        <table class="table table-hover mb-0 w-100 nowrap" id="complianceTable">
            <thead class="table-light">
                <tr>
                    <th data-priority="1">Course Name</th>
                    <th data-priority="2">Assigned Staff / CRs</th>
                    <th data-priority="1">Status</th>
                    <th data-priority="1">Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for item in compliance_data %}
                <tr>
                    <td class="align-middle fw-bold">{{ item.course.name }}</td>
                    <td class="align-middle">
                        {% if item.staff %}
                            {% for staff in item.staff %}
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span><span class="badge bg-secondary me-1">{{ staff.role_in_course }}</span> {{ staff.user.full_name }}</span>
                                <form action="{{ url_for('coordinator.revoke_cr', staff_id=staff.id) }}" method="POST" class="d-inline" onsubmit="return confirm('Revoke this staff member\\'s access?');">
                                    <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-1" title="Revoke Access"><i class="bi bi-person-x"></i></button>
                                </form>
                            </div>
                            {% endfor %}
                        {% else %}
                            <span class="text-muted small">No Staff Assigned</span>
                        {% endif %}
                        <button class="btn btn-sm btn-link p-0 mt-1" data-bs-toggle="modal" data-bs-target="#assignCRModal{{ item.course.id }}">
                            + Assign CR
                        </button>
                    </td>
                    <td class="align-middle">
                        {% if item.status == 'Submitted' %}
                            <span class="badge bg-success rounded-pill px-3 py-2"><i class="bi bi-check-circle me-1"></i> Submitted</span>
                        {% else %}
                            <span class="badge bg-warning text-dark rounded-pill px-3 py-2"><i class="bi bi-clock me-1"></i> Pending</span>
                        {% endif %}
                    </td>
                    <td class="align-middle">
                        {% if item.status == 'Submitted' %}
                            <a href="{{ url_for('coordinator.attendance_bulk', course_id=item.course.id, session_id=item.session.id) }}" class="btn btn-sm btn-primary text-nowrap">
                                <i class="bi bi-pencil-square"></i> Override
                            </a>
                        {% else %}
                            <a href="https://api.whatsapp.com/send?text=Please%20submit%20attendance%20for%20{{ item.course.name|urlencode }}." target="_blank" class="btn btn-sm btn-success text-nowrap">
                                <i class="bi bi-whatsapp"></i> Nudge
                            </a>
                        {% endif %}
                    </td>
                </tr>
                
                <!-- Assign CR Modal -->
                <div class="modal fade" id="assignCRModal{{ item.course.id }}" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content border-0 shadow">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title">Assign CR for {{ item.course.name }}</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <form action="{{ url_for('coordinator.assign_cr') }}" method="POST">
                                <div class="modal-body">
                                    <input type="hidden" name="course_id" value="{{ item.course.id }}">
                                    <div class="mb-3">
                                        <label class="form-label fw-bold">Select Enrolled Student</label>
                                        <select class="form-select" name="student_id" required>
                                            <option value="" disabled selected>-- Choose Student --</option>
                                            {% for student in item.students %}
                                            <option value="{{ student.id }}">{{ student.full_name }} (Reg: {{ student.registration_id }})</option>
                                            {% else %}
                                            <option value="" disabled>No active students in this course</option>
                                            {% endfor %}
                                        </select>
                                    </div>
                                    <div class="alert alert-warning small">
                                        Assigning a student as a CR will automatically generate a secure login for them so they can mark attendance.
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
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endif %}
{% endblock %}

{% block scripts %}
{% if courses %}
<!-- DataTables CSS & JS -->
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css"/>
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/responsive/2.5.0/css/responsive.bootstrap5.min.css"/>
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/responsive/2.5.0/js/dataTables.responsive.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/responsive/2.5.0/js/responsive.bootstrap5.min.js"></script>
<script>
$(document).ready(function() {
    $('#complianceTable').DataTable({
        responsive: true,
        "pageLength": 10,
        "lengthChange": false,
        "dom": "<'row px-3 pt-3'<'col-sm-12 col-md-6'><'col-sm-12 col-md-6'f>>" +
               "<'row'<'col-sm-12'tr>>" +
               "<'row px-3 pb-3 pt-2'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
        "language": {
            "search": "Search Courses:"
        }
    });
});
</script>
{% endif %}
{% endblock %}
"""

with open('/home/alyan-hammad/tanzeem_webapp/templates/attendance.html', 'w') as f:
    f.write(html_content)
    
print("Rebuilt attendance.html as Compliance Monitor.")
