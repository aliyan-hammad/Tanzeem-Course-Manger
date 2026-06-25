import threading
from sqlalchemy import event
from models import Student, FeeCollection, Expense, Attendance
from google_sync import sync_admin_master_students, append_to_monthly_log
from extensions import db
from flask import current_app

def run_in_background(func, *args, **kwargs):
    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Background thread error: {e}")
            
    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()

def register_listeners(app):
    with app.app_context():
        @event.listens_for(Student, 'after_insert')
        @event.listens_for(Student, 'after_update')
        @event.listens_for(Student, 'after_delete')
        def sync_students_on_change(mapper, connection, target):
            # We need to sync the entire master list. But we can't query inside this connection easily.
            # We'll pass the app context to the background thread.
            def do_sync():
                with app.app_context():
                    all_students = Student.query.all()
                    data = []
                    for s in all_students:
                        data.append({
                            'id': s.id,
                            'registration_id': s.registration_id,
                            'full_name': s.full_name,
                            'father_name': s.father_name,
                            'course': s.course.name if s.course else 'N/A',
                            'phone': s.phone,
                            'status': s.status,
                            'enrollment_date': s.enrollment_date
                        })
                    try:
                        sync_admin_master_students(data)
                    except Exception as e:
                        print(f"Error syncing students: {e}")
            run_in_background(do_sync)

        @event.listens_for(FeeCollection, 'after_insert')
        def sync_fee_on_insert(mapper, connection, target):
            fee_id = target.id
            student_id = target.student_id
            amount = target.amount_paid
            method = target.payment_method
            month = target.fee_month
            date_collected = target.date_collected
            
            def do_sync():
                with app.app_context():
                    student = Student.query.get(student_id)
                    month_str = date_collected.strftime('%B %Y') # e.g. June 2026
                    row = [fee_id, student_id, student.full_name if student else 'Unknown', 
                           student.course.name if student and student.course else 'N/A', 
                           amount, method, month, str(date_collected)]
                    try:
                        append_to_monthly_log('Fees', month_str, row)
                    except Exception as e:
                        print(f"Error syncing fee: {e}")
            run_in_background(do_sync)
            
        @event.listens_for(Expense, 'after_insert')
        def sync_expense_on_insert(mapper, connection, target):
            exp_id = target.id
            title = target.title
            amount = target.amount
            method = target.payment_method
            course_id = target.course_id
            expense_date = target.expense_date
            
            def do_sync():
                with app.app_context():
                    from models import Course
                    course = Course.query.get(course_id) if course_id else None
                    month_str = expense_date.strftime('%B %Y')
                    row = [exp_id, title, amount, method, course.name if course else 'General', str(expense_date)]
                    try:
                        append_to_monthly_log('Expenses', month_str, row)
                    except Exception as e:
                        print(f"Error syncing expense: {e}")
            run_in_background(do_sync)

        # Attendance sync to Admin Sheet has been disabled per user request
        # @event.listens_for(Attendance, 'after_insert')
        # def sync_attendance_on_insert(mapper, connection, target):
        # ...
