from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
import json
from models import db, Course, Student, ClassSession, Attendance, CourseStaff
from datetime import date

staff_bp = Blueprint('staff', __name__)

def is_teaching_staff():
    return current_user.role in ['Teacher', 'CR', 'TA']

@staff_bp.route('/portal')
@login_required
def portal():
    if not is_teaching_staff():
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    # Get courses assigned to this user
    staff_records = CourseStaff.query.filter_by(user_id=current_user.id).all()
    assigned_course_ids = [r.course_id for r in staff_records]
    courses = Course.query.filter(Course.id.in_(assigned_course_ids), Course.status == 'Active').all()
    
    # Get all pending sessions for these courses
    today = date.today()
    all_pending_sessions = ClassSession.query.filter(ClassSession.course_id.in_(assigned_course_ids), ClassSession.status == 'Pending').order_by(ClassSession.date.desc()).all()
    
    # Group pending sessions by course_id and date
    today_pending_by_course = {}
    past_pending_by_course = {}
    
    for course_id in assigned_course_ids:
        today_pending_by_course[course_id] = []
        past_pending_by_course[course_id] = []
        
    for session in all_pending_sessions:
        if session.date == today:
            today_pending_by_course[session.course_id].append(session)
        else:
            past_pending_by_course[session.course_id].append(session)
            
    return render_template('staff_portal.html', 
                           courses=courses, 
                           today_pending_by_course=today_pending_by_course,
                           past_pending_by_course=past_pending_by_course,
                           today=today.strftime('%B %d, %Y'))

@staff_bp.route('/mark_attendance/<int:session_id>', methods=['GET', 'POST'])
@login_required
def mark_attendance(session_id):
    if not is_teaching_staff():
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard.index'))
        
    session_obj = ClassSession.query.get_or_404(session_id)
    course = Course.query.get(session_obj.course_id)
    
    # Verify assignment
    staff_record = CourseStaff.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not staff_record:
        flash('You are not assigned to this course.', 'danger')
        return redirect(url_for('staff.portal'))
        
    if session_obj.status == 'Submitted':
        flash('This session has already been submitted. Please contact your coordinator to make changes.', 'warning')
        return redirect(url_for('staff.portal'))
        
    if request.method == 'POST':
        students = Student.query.filter_by(course_id=course.id, status='Active').all()
        
        # Mark attendance
        for student in students:
            status = request.form.get(f'status_{student.id}', 'Present') # Default present
            
            attendance_record = Attendance(
                session_id=session_obj.id,
                student_id=student.id,
                status=status
            )
            db.session.add(attendance_record)
            
        session_obj.status = 'Submitted'
        session_obj.marked_by_id = current_user.id
        db.session.commit()
        from helpers import log_audit
        log_audit('Add', 'Attendance', record_id=session_obj.id, remarks=f"Session {session_obj.subject_name} marked by {current_user.full_name} for {course.name}")
        flash('Attendance submitted successfully!', 'success')
        return redirect(url_for('staff.portal'))
            
    students = Student.query.filter_by(course_id=course.id, status='Active').all()
    return render_template('staff_attendance.html', course=course, students=students, session_obj=session_obj)
