import os
from flask import Flask, render_template, redirect, url_for
from models import db, User
from routes.auth import auth_bp
from routes.tenants import tenants_bp
from routes.billing import billing_bp
from routes.properties import properties_bp
from routes.dashboard import dashboard_bp
from routes.agents import agents_bp
from flask_login import LoginManager, login_required

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-prod' # TODO: Use env var
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rental.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(tenants_bp, url_prefix='/tenants')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(properties_bp, url_prefix='/properties')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(agents_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()
        # Seed Admin User
        from werkzeug.security import generate_password_hash
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin', 
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Created default admin user.")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
