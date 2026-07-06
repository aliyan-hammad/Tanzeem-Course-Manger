import sqlite3

def migrate():
    conn = sqlite3.connect('instance/tanzeem.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE class_session ADD COLUMN marked_by_id INTEGER REFERENCES user(id)")
        print("Column 'marked_by_id' added.")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("Column 'marked_by_id' already exists.")
        else:
            print(f"Error: {e}")
            
    # For all existing sessions where status='Submitted' and marked_by_id is NULL,
    # set marked_by_id to created_by_id
    cursor.execute("UPDATE class_session SET marked_by_id = created_by_id WHERE marked_by_id IS NULL AND created_by_id IS NOT NULL")
    
    conn.commit()
    conn.close()
    print("Migration successful.")

if __name__ == '__main__':
    migrate()
