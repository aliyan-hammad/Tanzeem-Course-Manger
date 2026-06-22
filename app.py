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
    
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///tanzeem.db')
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(coordinator_bp)

    @app.context_processor
    def inject_pending_requests():
        from flask_login import current_user
        if current_user.is_authenticated and current_user.role == 'Admin':
            from models import ApprovalRequest
            count = ApprovalRequest.query.filter_by(status='Pending').count()
            return dict(global_pending_requests_count=count)
        return dict(global_pending_requests_count=0)

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

    return app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
