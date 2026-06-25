import random
from datetime import date, timedelta
from app import create_app
from extensions import db
from models import User, Course, Student, FeeCollection, Expense, ClassSession, Attendance

app = create_app()

with app.app_context():
    # Ensure there is a course
    course = Course.query.first()
    if not course:
        # Create a course if none exists
        coord = User.query.filter_by(role='Coordinator').first()
        course = Course(name='Test Course', duration='3 Months', base_fee=1500, coordinator_id=coord.id if coord else 1, status='Active')
        db.session.add(course)
        db.session.commit()
    
    # 1. Add 10 fake students
    names = ['Ali Khan', 'Fatima Zahra', 'Umar Farooq', 'Ayesha Siddiqa', 'Usman Ghani', 'Zainab Bint Ali', 'Hassan ibn Ali', 'Khadija Bint Khuwaylid', 'Bilal ibn Rabah', 'Hamza ibn Abd al-Muttalib']
    students = []
    
    # Count existing to generate unique registration IDs
    existing_count = Student.query.count()
    
    for i, name in enumerate(names):
        reg_id = f'REG-{1000 + existing_count + i}'
        student = Student(
            registration_id=reg_id,
            full_name=name,
            father_name='Fake Father',
            phone=f'0300{random.randint(1000000, 9999999)}',
            address='Test Address',
            course_id=course.id,
            status='Active'
        )
        db.session.add(student)
        students.append(student)
    
    db.session.commit()

    # 2. Make 5 Expense Vouchers
    expenses_titles = ['Office Supplies', 'Electricity Bill', 'Internet Bill', 'Refreshments', 'Marketing']
    for i in range(5):
        expense = Expense(
            title=expenses_titles[i],
            amount=random.uniform(500, 5000),
            payment_method='Cash',
            course_id=course.id
        )
        db.session.add(expense)
    
    db.session.commit()

    # 3. Fill all students fee vouchers
    admin = User.query.filter_by(role='Admin').first()
    for student in students:
        fee = FeeCollection(
            student_id=student.id,
            amount_paid=course.base_fee,
            payment_method=random.choice(['Cash', 'Online']),
            fee_month='2026-06',
            collected_by_id=admin.id if admin else 1
        )
        db.session.add(fee)
    
    db.session.commit()

    # 4. Mark 5 session attendance randomly
    today = date.today()
    sessions = []
    for i in range(5):
        session_date = today - timedelta(days=i)
        session_obj = ClassSession(
            course_id=course.id,
            date=session_date,
            subject_name=random.choice(['Arabic', 'Seerah', 'Tafseer', 'Tajweed'])
        )
        db.session.add(session_obj)
        sessions.append(session_obj)
    
    db.session.commit()

    for session_obj in sessions:
        for student in students:
            # 80% chance present, 20% absent
            status = 'Present' if random.random() < 0.8 else 'Absent'
            attendance = Attendance(
                session_id=session_obj.id,
                student_id=student.id,
                status=status
            )
            db.session.add(attendance)
    
    db.session.commit()

    print("Successfully seeded 10 students, 5 expenses, 10 fee vouchers, and 5 attendance sessions!")
