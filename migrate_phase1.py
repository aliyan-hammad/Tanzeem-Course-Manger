import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'tanzeem.db')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE user ADD COLUMN linked_student_id INTEGER REFERENCES student(id)')
        conn.commit()
        print("Successfully added linked_student_id to user table.")
    except sqlite3.OperationalError as e:
        print(f"Column might already exist or error: {e}")
    conn.close()
else:
    print("Database file not found!")

# Now load app to create CourseStaff table
from app import create_app
from extensions import db
app = create_app()

with app.app_context():
    db.create_all()
    print("Successfully created CourseStaff and any missing tables.")
