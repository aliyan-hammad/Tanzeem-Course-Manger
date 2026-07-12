from app import create_app
from extensions import db
from models import FeeCollection, Expense, Student, Course

app = create_app()
with app.app_context():
    print("COURSES:")
    courses = Course.query.all()
    for c in courses:
        print(f"Course {c.id}: {c.name}")
        
    print("\nEXPENSES COURSE NONE:")
    exps = Expense.query.filter_by(course_id=None).all()
    for e in exps:
        print(f"Exp {e.id} - Amt: {e.amount} - Date: {e.expense_date}")
        
