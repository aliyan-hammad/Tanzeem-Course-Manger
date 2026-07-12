from app import create_app
from extensions import db
from models import FeeCollection, Expense, Student, Course
from routes.admin import reports
from flask import request

app = create_app()
with app.app_context():
    pass
