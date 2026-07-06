import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'tanzeem.db')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE class_session ADD COLUMN created_by_id INTEGER REFERENCES user(id)')
        conn.commit()
        print("Successfully added created_by_id to class_session table.")
    except sqlite3.OperationalError as e:
        print(f"Column might already exist or error: {e}")
    conn.close()
else:
    print("Database file not found!")
