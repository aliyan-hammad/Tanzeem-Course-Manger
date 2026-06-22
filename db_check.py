from app import create_app
from extensions import db
from models import Attendance

app = create_app()
with app.app_context():
    records = Attendance.query.limit(5).all()
    print(f"Total attendance records: {Attendance.query.count()}")
    for r in records:
        print(f"ID: {r.id}, Student ID: {r.student_id}, Subject: {r.subject}, Date: {r.date} ({type(r.date)}), Status: {r.status}")
