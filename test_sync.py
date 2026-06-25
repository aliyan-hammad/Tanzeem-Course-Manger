from app import app
from models import Expense, Course
from extensions import db
from datetime import datetime

with app.app_context():
    new_expense = Expense(
        title='Test Background Sync',
        amount=150.0,
        payment_method='Cash',
        expense_date=datetime.utcnow()
    )
    db.session.add(new_expense)
    db.session.commit()
    print("Expense committed.")
import time; time.sleep(5)
