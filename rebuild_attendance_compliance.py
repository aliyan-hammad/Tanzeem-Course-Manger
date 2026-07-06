html_content = """{% extends "base.html" %}

{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
    <div class="d-flex flex-wrap align-items-center gap-3 w-100">
        <h2 class="mb-0">Attendance Compliance</h2>
        
        {% if courses %}
        <form method="GET" action="{{ url_for('coordinator.attendance') }}" class="d-flex align-items-center gap-2 ms-auto">
            <label for="course_id" class="text-nowrap fw-bold mb-0 text-secondary">Course:</label>
            <select class="form-select border-primary" id="course_id" name="course_id" onchange="this.form.submit()" style="min-width: 200px;">
                {% for course in courses %}
                <option value="{{ course.id }}" {% if active_course and active_course.id|string == course.id|string %}selected{% endif %}>{{ course.name }}</option>
                {% endfor %}
            </select>
        </form>
        {% endif %}
    </div>
</div>

{% if not courses %}
<div class="alert alert-info text-center shadow-sm border-0 rounded-3 mt-5 p-5">
    <i class="bi bi-journal-check display-1 text-info d-block mb-3 opacity-50"></i>
    <h3 class="alert-heading fw-bold text-dark mb-3">No Courses Assigned</h3>
    <p class="text-muted fs-5 mb-0">Your workspace is ready, but you haven't been assigned to any active courses yet.</p>
</div>
{% else %}

<!-- Today's Compliance Status -->
<div class="card shadow-sm border-0 mb-4 border-start border-4 border-primary">
    <div class="card-header bg-white py-3">
        <h5 class="mb-0 fw-bold text-primary"><i class="bi bi-calendar2-day me-2"></i>Today's Sessions ({{ today }})</h5>
    </div>
    <div class="card-body">
        {% if todays_sessions %}
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Subject / Session</th>
                            <th>Marked By</th>
                            <th>Status</th>
                            <th>Date</th>
                            <th class="text-end">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for session in todays_sessions %}
                        <tr>
                            <td class="fw-bold">{{ session.subject_name }}</td>
                            <td>
                                {% if session.created_by %}
                                    <span class="badge bg-secondary"><i class="bi bi-person me-1"></i>{{ session.created_by.full_name }}</span>
                                {% else %}
                                    <span class="text-muted small">System / Unknown</span>
                                {% endif %}
                            </td>
                            <td><span class="badge bg-success rounded-pill px-3"><i class="bi bi-check-circle me-1"></i> Submitted</span></td>
                            <td>{{ session.date.strftime('%Y-%m-%d') }}</td>
                            <td class="text-end">
                                <a href="{{ url_for('coordinator.attendance_bulk', course_id=active_course.id, session_id=session.id) }}" class="btn btn-sm btn-outline-primary">
                                    <i class="bi bi-pencil-square"></i> Override
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        {% else %}
            <div class="text-center py-4">
                <h5 class="text-muted mb-3">There is no new session for today.</h5>
                <p class="text-muted small mb-4">You can nudge the assigned staff to remind them to mark attendance.</p>
                <button class="btn btn-success px-4 rounded-pill shadow-sm" data-bs-toggle="modal" data-bs-target="#nudgeModal">
                    <i class="bi bi-whatsapp me-2"></i> Nudge Staff
                </button>
            </div>
        {% endif %}
    </div>
</div>

<!-- Past Sessions -->
<div class="card shadow-sm border-0">
    <div class="card-header bg-light py-3">
        <h5 class="mb-0 text-secondary"><i class="bi bi-clock-history me-2"></i>Past Recorded Sessions</h5>
    </div>
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover mb-0 w-100 nowrap" id="pastSessionsTable">
                <thead class="table-light">
                    <tr>
                        <th data-priority="1">Date</th>
                        <th data-priority="2">Subject</th>
                        <th data-priority="2">Marked By</th>
                        <th data-priority="1">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for session in past_sessions %}
                    <tr>
                        <td class="align-middle">{{ session.date.strftime('%Y-%m-%d') }}</td>
                        <td class="align-middle fw-bold">{{ session.subject_name }}</td>
                        <td class="align-middle">
                            {% if session.created_by %}
                                {{ session.created_by.full_name }}
                            {% else %}
                                <span class="text-muted">Unknown</span>
                            {% endif %}
                        </td>
                        <td class="align-middle">
                            <a href="{{ url_for('coordinator.attendance_bulk', course_id=active_course.id, session_id=session.id) }}" class="btn btn-sm btn-primary">
                                <i class="bi bi-pencil"></i> Override
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Nudge Modal -->
<div class="modal fade" id="nudgeModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
            <div class="modal-header bg-success text-white">
                <h5 class="modal-title"><i class="bi bi-whatsapp me-2"></i>Whom to Nudge?</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="mb-4 text-muted">Select an assigned staff member to send a WhatsApp reminder for today's attendance.</p>
                {% if active_course_staff %}
                    <div class="list-group">
                        {% for staff in active_course_staff %}
                        <a href="https://api.whatsapp.com/send?phone={{ staff.user.contact|default('', true) | urlencode }}&text=Assalam%20o%20Alaikum%20{{ staff.user.full_name|urlencode }},%20Please%20submit%20today's%20attendance%20for%20{{ active_course.name|urlencode }}." target="_blank" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-0 fw-bold">{{ staff.user.full_name }}</h6>
                                <small class="text-muted">{{ staff.role_in_course }}</small>
                            </div>
                            <i class="bi bi-send-fill text-success"></i>
                        </a>
                        {% endfor %}
                    </div>
                {% else %}
                    <div class="alert alert-warning">No staff or CR is assigned to this course yet. Please assign a CR from the Dashboard.</div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

{% endif %}
{% endblock %}

{% block scripts %}
{% if courses %}
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css"/>
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/responsive/2.5.0/css/responsive.bootstrap5.min.css"/>
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/responsive/2.5.0/js/dataTables.responsive.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/responsive/2.5.0/js/responsive.bootstrap5.min.js"></script>
<script>
$(document).ready(function() {
    $('#pastSessionsTable').DataTable({
        responsive: true,
        "pageLength": 10,
        "lengthChange": false,
        "order": [[ 0, "desc" ]],
        "dom": "<'row px-3 pt-3'<'col-sm-12 col-md-6'><'col-sm-12 col-md-6'f>>" +
               "<'row'<'col-sm-12'tr>>" +
               "<'row px-3 pb-3 pt-2'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
        "language": {
            "search": "Filter Sessions:"
        }
    });
});
</script>
{% endif %}
{% endblock %}
"""

with open('/home/alyan-hammad/tanzeem_webapp/templates/attendance.html', 'w') as f:
    f.write(html_content)

print("Attendance Compliance HTML successfully rebuilt.")
