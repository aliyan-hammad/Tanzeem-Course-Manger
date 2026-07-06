import sqlite3

def migrate():
    conn = sqlite3.connect('instance/tanzeem.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE class_session ADD COLUMN status VARCHAR(20) DEFAULT 'Submitted'")
        print("Column 'status' added to 'class_session' successfully.")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("Column 'status' already exists.")
        else:
            print(f"Error: {e}")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
