import threading
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from google_sync import sync_daily_coordinator_report
from datetime import date, datetime
from models import Student, ClassSession, Attendance, Course

sync_bp = Blueprint('sync_bp', __name__)

def run_in_background(func, *args, **kwargs):
    # Vercel serverless functions pause execution after response.
    # Therefore, we MUST run this synchronously.
    func(*args, **kwargs)

@sync_bp.route('/dashboard/sync_sheets', methods=['POST'])
@login_required
def sync_dashboard_sheets():
    data = request.json
    target_date_str = data.get('target_date', date.today().strftime('%Y-%m-%d'))
    
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = date.today()

    if target_date == date.today():
        today_absentees = data.get('today', [])
        yesterday_absentees = data.get('yesterday', [])
        consecutive_absentees = data.get('consecutive', [])
        low_attendance = data.get('low', [])
    else:
        # Historical Sync
        today_absentees = []
        if current_user.role == 'Coordinator':
            assigned_courses = Course.query.filter_by(coordinator_id=current_user.id).all()
            c_ids = [c.id for c in assigned_courses]
        else:
            c_ids = [c.id for c in Course.query.all()]

        active_students = Student.query.filter(Student.course_id.in_(c_ids), Student.status == 'Active').all()
        sessions = ClassSession.query.filter(ClassSession.course_id.in_(c_ids), ClassSession.date == target_date).all()
        
        if sessions:
            course_sessions = {}
            for s in sessions:
                course_sessions.setdefault(s.course_id, []).append(s)
                
            session_ids = [s.id for s in sessions]
            attendances = Attendance.query.filter(Attendance.session_id.in_(session_ids)).all()
            
            att_dict = {}
            for a in attendances:
                att_dict.setdefault(a.student_id, {})[a.session_id] = a.status
                
            for student in active_students:
                s_sessions = course_sessions.get(student.course_id, [])
                total_sessions = len(s_sessions)
                if total_sessions == 0:
                    continue
                    
                present_count = 0
                missed_subjects = []
                for s in s_sessions:
                    status = att_dict.get(student.id, {}).get(s.id)
                    if status == 'Present':
                        present_count += 1
                    else:
                        missed_subjects.append(s.subject_name)
                        
                if present_count == 0:
                    today_absentees.append([student.full_name, student.course.name if student.course else 'N/A', 'Full', 'All', student.phone])
                elif present_count < total_sessions:
                    today_absentees.append([student.full_name, student.course.name if student.course else 'N/A', 'Partial', ', '.join(missed_subjects), student.phone])
        
        yesterday_absentees = []
        consecutive_absentees = [
            ["ℹ️ Historical Sync Mode: Consecutive absences are only calculated for real-time daily syncs.", "", "", ""]
        ]
        low_attendance = []

    def do_sync():
        try:
            sync_daily_coordinator_report(target_date_str, today_absentees, yesterday_absentees, consecutive_absentees, low_attendance)
        except Exception as e:
            print(f"Error syncing coordinator dashboard: {e}")
            
    run_in_background(do_sync)
    return jsonify({"status": "success", "message": "Sync started in background."})

