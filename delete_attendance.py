from app import create_app
from extensions import db
from models import Attendance

app = create_app()
with app.app_context():
    num_deleted = db.session.query(Attendance).delete()
    db.session.commit()
    print(f"Deleted {num_deleted} attendance records.")
