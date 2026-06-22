import json
from flask_login import current_user
from extensions import db
from models import AuditLog, ClassSession, Attendance

def log_audit(action_type, module, record_id=None, old_values=None, new_values=None, remarks=None):
    try:
        user_id = current_user.id if (current_user and current_user.is_authenticated) else None
        role = current_user.role if (current_user and current_user.is_authenticated) else 'System'
        
        old_val_str = json.dumps(old_values) if isinstance(old_values, dict) else old_values
        new_val_str = json.dumps(new_values) if isinstance(new_values, dict) else new_values
        
        log = AuditLog(
            user_id=user_id,
            role=role,
            action_type=action_type,
            module=module,
            record_id=record_id,
            old_values=old_val_str,
            new_values=new_val_str,
            remarks=remarks
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")

def calculate_attendance(student_id, course_id):
    """
    Calculates exactly how many sessions have been created for the course (denominator)
    and how many times the student was explicitly marked 'Present' (numerator).
    """
    total_sessions = ClassSession.query.filter_by(course_id=course_id).count()
    
    if total_sessions == 0:
        return {
            'percentage': 0.0,
            'attended': 0,
            'total': 0,
            'formatted': "0% (0/0 Attended)"
        }
        
    attended_count = Attendance.query.join(ClassSession).filter(
        Attendance.student_id == student_id,
        ClassSession.course_id == course_id,
        Attendance.status == 'Present'
    ).count()
    
    percentage = (attended_count / total_sessions) * 100
    
    return {
        'percentage': round(percentage, 1),
        'attended': attended_count,
        'total': total_sessions,
        'formatted': f"{round(percentage)}% ({attended_count}/{total_sessions} Attended)"
    }
