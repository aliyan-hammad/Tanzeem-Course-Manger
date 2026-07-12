from app import create_app
from extensions import db
from models import FeeCollection, Expense, Student, Course
from datetime import datetime

app = create_app()
with app.app_context():
    end_date = datetime(2026, 8, 14, 23, 59, 59)
    course_id = 2
    
    cum_fee_q = FeeCollection.query.filter(FeeCollection.date_collected <= end_date, FeeCollection.is_deleted == False)
    cum_fee_q = cum_fee_q.join(Student).filter(Student.course_id == course_id)
    
    cum_exp_q = Expense.query.filter(Expense.expense_date <= end_date, Expense.is_deleted == False)
    cum_exp_q = cum_exp_q.filter_by(course_id=course_id)
    
    fees = sum([f.amount_paid for f in cum_fee_q.all()])
    exps = sum([e.amount for e in cum_exp_q.all()])
    print(f"Course 2 - Fees: {fees}, Exps: {exps}, Net: {fees - exps}")

