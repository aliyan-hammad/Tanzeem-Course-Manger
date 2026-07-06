from datetime import datetime
from flask_login import UserMixin
from extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='General Staff')  # Admin, Coordinator, Teacher, TA, CR, General Staff
    full_name = db.Column(db.String(100), nullable=True)
    contact = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Active')
    
    # Payroll fields
    salary_type = db.Column(db.String(20), nullable=True)  # 'Fixed Monthly' or 'Per Session'
    salary_amount = db.Column(db.Float, nullable=True, default=0.0)
    bank_details = db.Column(db.String(255), nullable=True)
    linked_student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)  # Links CR role to actual Student
    managed_courses = db.relationship('Course', backref='coordinator', lazy=True)
    fees_collected = db.relationship('FeeCollection', backref='collected_by', lazy=True, foreign_keys="[FeeCollection.collected_by_id]")
    linked_student = db.relationship('Student', foreign_keys=[linked_student_id], backref='user_account', lazy=True)

class CourseStaff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_in_course = db.Column(db.String(50), nullable=False)  # Primary Teacher, TA, CR
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='course_assignments', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    duration = db.Column(db.String(50), nullable=False)  # e.g., 1 Month, 2 Months, 1 Year
    coordinator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # References User (Coordinator)
    base_fee = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default='Active')  # Active, Upcoming, Completed
    batch = db.Column(db.String(50), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    subjects = db.Column(db.Text, nullable=True)  # Store as JSON string or comma-separated
    students = db.relationship('Student', backref='course', lazy=True, foreign_keys="[Student.course_id]")
    expenses = db.relationship('Expense', backref='course', lazy=True)
    staff = db.relationship('CourseStaff', backref='course', lazy=True, cascade="all, delete-orphan")

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    father_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=True)
    qualification = db.Column(db.String(50), nullable=True)
    profession = db.Column(db.String(100), nullable=True)
    cnic = db.Column(db.String(20), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)
    status = db.Column(db.String(20), default='Active')  # Active or Inactive
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    fees = db.relationship('FeeCollection', backref='student', lazy=True)

class FeeCollection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash or Online
    fee_month = db.Column(db.String(7), nullable=True)  # Format: YYYY-MM
    date_collected = db.Column(db.DateTime, default=datetime.utcnow)
    collected_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Soft Delete fields
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    delete_reason = db.Column(db.String(255), nullable=True)

    deleted_by = db.relationship('User', foreign_keys=[deleted_by_id], backref='fees_deleted')

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash or Online
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)

    # Soft Delete fields
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    delete_reason = db.Column(db.String(255), nullable=True)

    deleted_by = db.relationship('User', foreign_keys=[deleted_by_id], backref='expenses_deleted')

class ClassSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    subject_name = db.Column(db.String(50), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Teacher or CR who created it
    marked_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)   # User who marked the attendance
    status = db.Column(db.String(20), default='Submitted') # Pending, Submitted
    attendances = db.relationship('Attendance', backref='session', lazy=True, cascade="all, delete-orphan")
    course = db.relationship('Course', backref='sessions', lazy=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='sessions_created', lazy=True)
    marked_by = db.relationship('User', foreign_keys=[marked_by_id], backref='sessions_marked', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_session.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Present, Absent, Leave
    student = db.relationship('Student', backref='attendances', lazy=True)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    role = db.Column(db.String(50), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=True)
    old_values = db.Column(db.Text, nullable=True)
    new_values = db.Column(db.Text, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs', lazy=True)

class ApprovalRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(20), nullable=False)  # Edit, Delete
    module = db.Column(db.String(50), nullable=False)  # Fee, Expense
    record_id = db.Column(db.Integer, nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    comments = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Pending')  # Pending, Approved, Rejected
    temporary_edit_payload = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    actioned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    actioned_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)

    requested_by = db.relationship('User', foreign_keys=[requested_by_id], backref='requests_made')
    actioned_by = db.relationship('User', foreign_keys=[actioned_by_id], backref='requests_actioned')
