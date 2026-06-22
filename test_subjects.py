import requests
data = {
    'name': 'Test Course',
    'duration': '1 Month',
    'coordinator_id': 1,
    'base_fee': 100,
    'subjects[]': ['Math', 'Science', 'History']
}
# Using a local test
from app import create_app
from models import Course, User
app = create_app()
with app.app_context():
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        # We need to bypass login
        pass
