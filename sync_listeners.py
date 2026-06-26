import threading
from sqlalchemy import event
from models import Student, FeeCollection, Expense, Attendance
from google_sync import sync_admin_master_students, append_to_monthly_log
from extensions import db
from flask import current_app

def run_in_background(func, *args, **kwargs):
    # Vercel serverless functions pause execution after response.
    # Therefore, we MUST run this synchronously.
    try:
        func(*args, **kwargs)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Background thread error: {e}")

def trigger_sync_fee_month(app, month_str):
    def do_sync():
        with app.app_context():
            from models import FeeCollection
            all_fees = FeeCollection.query.filter(FeeCollection.is_deleted == False).all()
            month_fees = [f for f in all_fees if f.date_collected and f.date_collected.strftime("%B %Y") == month_str]
            data_rows = []
            for f in month_fees:
                data_rows.append([f.id, f.student_id, f.student.full_name if f.student else "Unknown",
                                  f.student.course.name if f.student and f.student.course else "N/A",
                                  f.amount_paid, f.payment_method, f.fee_month, str(f.date_collected)])
            from google_sync import sync_entire_month_log
            try:
                sync_entire_month_log("Fees", month_str, data_rows)
            except Exception as e:
                print(f"Error syncing fee month: {e}")
    run_in_background(do_sync)

def trigger_sync_expense_month(app, month_str):
    def do_sync():
        with app.app_context():
            from models import Expense, Course
            all_expenses = Expense.query.filter(Expense.is_deleted == False).all()
            month_expenses = [e for e in all_expenses if e.expense_date and e.expense_date.strftime("%B %Y") == month_str]
            data_rows = []
            for e in month_expenses:
                course = Course.query.get(e.course_id) if e.course_id else None
                data_rows.append([e.id, e.title, e.amount, e.payment_method, course.name if course else "General", str(e.expense_date)])
            from google_sync import sync_entire_month_log
            try:
                sync_entire_month_log("Expenses", month_str, data_rows)
            except Exception as e:
                print(f"Error syncing expense month: {e}")
    run_in_background(do_sync)

def register_listeners(app):
    with app.app_context():
        def _sync_students_action(action, target):
            def do_sync():
                with app.app_context():
                    all_students = Student.query.all()
                    from models import Course
                    data = []
                    
                    target_added = False
                    for s in all_students:
                        if action == 'delete' and s.id == target.id:
                            continue
                            
                        if (action == 'update' or action == 'insert') and s.id == target.id:
                            student_to_use = target
                            target_added = True
                        else:
                            student_to_use = s
                            
                        # Safely resolve course name for the target
                        if student_to_use == target:
                            c = Course.query.get(target.course_id) if target.course_id else None
                            course_name = c.name if c else 'N/A'
                        else:
                            course_name = student_to_use.course.name if student_to_use.course else 'N/A'
                            
                        data.append({
                            'id': student_to_use.id,
                            'registration_id': student_to_use.registration_id,
                            'full_name': student_to_use.full_name,
                            'father_name': student_to_use.father_name,
                            'course': course_name,
                            'phone': student_to_use.phone,
                            'status': student_to_use.status,
                            'enrollment_date': student_to_use.enrollment_date
                        })
                        
                    if action == 'insert' and not target_added:
                        c = Course.query.get(target.course_id) if target.course_id else None
                        data.append({
                            'id': target.id,
                            'registration_id': target.registration_id,
                            'full_name': target.full_name,
                            'father_name': target.father_name,
                            'course': c.name if c else 'N/A',
                            'phone': target.phone,
                            'status': target.status,
                            'enrollment_date': target.enrollment_date
                        })
                        
                    try:
                        sync_admin_master_students(data)
                    except Exception as e:
                        print(f"Error syncing students: {e}")
            run_in_background(do_sync)

        @event.listens_for(Student, 'after_insert')
        def sync_students_on_insert(mapper, connection, target):
            _sync_students_action('insert', target)
            
        @event.listens_for(Student, 'after_update')
        def sync_students_on_update(mapper, connection, target):
            _sync_students_action('update', target)
            
        @event.listens_for(Student, 'after_delete')
        def sync_students_on_delete(mapper, connection, target):
            _sync_students_action('delete', target)

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
