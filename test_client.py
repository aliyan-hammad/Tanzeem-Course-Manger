from app import create_app
from models import Course, User, db
from flask_login import login_user

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True

with app.test_client() as client:
    with app.app_context():
        admin = User.query.filter_by(role='Admin').first()
        
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        sess['_fresh'] = True
        
    response = client.post('/courses', data={
        'name': 'API Test Course',
        'duration': '1 Month',
        'coordinator_id': '1',
        'base_fee': '100',
        'subjects[]': ['Subj1', 'Subj2', 'Subj3', 'Subj4']
    })
    
    with app.app_context():
        c = Course.query.filter_by(name='API Test Course').first()
        print(f"Saved Subjects: {c.subjects}")
