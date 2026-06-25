import os
from app import create_app
from extensions import db
from models import Student, FeeCollection, Expense, Attendance, ClassSession, Course
from google_sync import get_gspread_client, get_or_create_worksheet, ADMIN_SPREADSHEET_ID

app = create_app()

def sync_all_history():
    with app.app_context():
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(ADMIN_SPREADSHEET_ID)

        # 1. Sync All Students
        print("Syncing all students...")
        all_students = Student.query.all()
        student_ws = get_or_create_worksheet(spreadsheet, "Master Students", ["ID", "Registration ID", "Full Name", "Father Name", "Course", "Phone", "Status", "Enrollment Date"])
        student_ws.clear()
        rows = [["ID", "Registration ID", "Full Name", "Father Name", "Course", "Phone", "Status", "Enrollment Date"]]
        for s in all_students:
            rows.append([s.id, s.registration_id, s.full_name, s.father_name, s.course.name if s.course else 'N/A', s.phone, s.status, str(s.enrollment_date)])
        student_ws.update('A1', rows)

        # 2. Sync Fees (Grouped by Month)
        print("Syncing fees...")
        all_fees = FeeCollection.query.all()
        fees_by_month = {}
        for f in all_fees:
            month_str = f.date_collected.strftime('%B %Y')
            if month_str not in fees_by_month:
                fees_by_month[month_str] = [["Fee ID", "Student ID", "Student Name", "Course", "Amount Paid", "Payment Method", "Fee Month", "Date Collected"]]
            fees_by_month[month_str].append([f.id, f.student_id, f.student.full_name if f.student else 'Unknown', f.student.course.name if f.student and f.student.course else 'N/A', f.amount_paid, f.payment_method, f.fee_month, str(f.date_collected)])
        
        for month_str, rows in fees_by_month.items():
            ws = get_or_create_worksheet(spreadsheet, f"{month_str} Fees", rows[0])
            ws.clear()
            ws.update('A1', rows)

        # 3. Sync Expenses (Grouped by Month)
        print("Syncing expenses...")
        all_expenses = Expense.query.all()
        expenses_by_month = {}
        for e in all_expenses:
            month_str = e.expense_date.strftime('%B %Y')
            if month_str not in expenses_by_month:
                expenses_by_month[month_str] = [["Expense ID", "Title", "Amount", "Payment Method", "Course", "Expense Date"]]
            course_name = Course.query.get(e.course_id).name if e.course_id else 'General'
            expenses_by_month[month_str].append([e.id, e.title, e.amount, e.payment_method, course_name, str(e.expense_date)])

        for month_str, rows in expenses_by_month.items():
            ws = get_or_create_worksheet(spreadsheet, f"{month_str} Expenses", rows[0])
            ws.clear()
            ws.update('A1', rows)

        # 4. Sync Attendance (Grouped by Month)
        print("Syncing attendance...")
        all_att = Attendance.query.all()
        att_by_month = {}
        for att in all_att:
            session = ClassSession.query.get(att.session_id)
            student = Student.query.get(att.student_id)
            if not session or not student:
                continue
            month_str = session.date.strftime('%B %Y')
            if month_str not in att_by_month:
                att_by_month[month_str] = [["Attendance ID", "Session ID", "Course", "Subject", "Session Date", "Student Name", "Status"]]
            att_by_month[month_str].append([att.id, att.session_id, session.course.name if session.course else 'N/A', session.subject_name, str(session.date), student.full_name, att.status])

        for month_str, rows in att_by_month.items():
            ws = get_or_create_worksheet(spreadsheet, f"{month_str} Attendance", rows[0])
            ws.clear()
            ws.update('A1', rows)

        print("Successfully synced all historical data to Admin Master Sheet.")

if __name__ == "__main__":
    sync_all_history()
