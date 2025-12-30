from app import create_app, db
from models import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='admin').first()
    if not user:
        print("Creating admin user...")
        user = User(username='admin', password_hash=generate_password_hash('password'), role='admin')
        db.session.add(user)
        db.session.commit()
        print("Admin user created (admin/password).")
    else:
        print("Admin user already exists.")
        # Reset password to ensure I know it
        user.password_hash = generate_password_hash('password')
        db.session.commit()
        print("Admin password reset to 'password'.")
