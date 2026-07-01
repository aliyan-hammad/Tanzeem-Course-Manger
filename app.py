import os
from flask import Flask
from extensions import db, login_manager
from werkzeug.security import generate_password_hash
import models  # Triggers model registration and login manager callbacks
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    
    database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/tanzeem.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.admin import admin_bp
    from routes.coordinator import coordinator_bp
    from routes.sync import sync_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(coordinator_bp)
    app.register_blueprint(sync_bp)

    @app.context_processor
    def inject_pending_requests():
        from flask_login import current_user
        if current_user.is_authenticated and current_user.role == 'Admin':
            from models import ApprovalRequest
            count = ApprovalRequest.query.filter_by(status='Pending').count()
            return dict(global_pending_requests_count=count)
        return dict(global_pending_requests_count=0)

    @app.template_filter('wa_link')
    def wa_link(student, msg_type, extra_info=""):
        import urllib.parse
        import re
        from datetime import date
        
        phone = student.phone
        name = student.full_name
        course_name = student.course.name if student.course else "your enrolled course"
        
        clean_phone = re.sub(r'\D', '', str(phone))
        if clean_phone.startswith('92') and len(clean_phone) >= 12:
            pass
        elif clean_phone.startswith('0'):
            clean_phone = '92' + clean_phone[1:]
        else:
            if len(clean_phone) == 10:  # e.g. 3001234567
                clean_phone = '92' + clean_phone
            
        today_str = date.today().strftime('%d %B, %Y')
        
        if msg_type == 'yesterday':
            text = f"Dear {name},\n\nThis is an official notification from Adminitration.\nWe noticed you were absent from your '{course_name}' yesterday. Regular attendance is crucial for your success. Please ensure you do not miss your upcoming classes.\n\nRegards,\nCoordinator"
        elif msg_type == 'today':
            text = f"Dear {name},\n\nThis is an official notification from Adminitration.\nYou have been marked absent today ({today_str}) in your '{course_name}'. Please make sure to attend the upcoming classes to stay on track.\n\nRegards,\nCoordinator"
        elif msg_type == 'consecutive':
            text = f"Dear {name},\n\nURGENT: This is an official notice from Adminitration regarding your '{course_name}'.\nYou have been consecutively absent from your recent classes. Please contact your coordinator immediately to explain your absence, otherwise strict action may be taken.\n\nRegards,\nCoordinator"
        elif msg_type == 'risk':
            text = f"Dear {name},\n\nATTENTION: This is an official alert from Adminitration.\nYour overall attendance in the '{course_name}' class has fallen to {extra_info}, which is critically below the 70% requirement. Immediate improvement is required to maintain your active enrollment status.\n\nRegards,\nCoordinator"
        else:
            text = f"Dear {name},\n\nThis is a message from Adminitration."
            
        encoded_text = urllib.parse.quote(text)
        return f"https://wa.me/{clean_phone}?text={encoded_text}"

    # Initialize Database & Seeds
    with app.app_context():
        db.create_all()
        # Seed default Admin User
        if not models.User.query.filter_by(username='admin').first():
            hashed_admin = generate_password_hash('admin123')
            admin_user = models.User(
                username='admin', 
                password_hash=hashed_admin, 
                role='Admin', 
                full_name='System Admin', 
                status='Active'
            )
            db.session.add(admin_user)
            db.session.commit()

    # Register SQLAlchemy background sync listeners
    from sync_listeners import register_listeners
    register_listeners(app)

    return app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
