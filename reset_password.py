from app import create_app, db
from models import User
from werkzeug.security import generate_password_hash

app = create_app()

def reset_admin_password():
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if user:
            print("Found admin user.")
            user.password_hash = generate_password_hash('admin123')
            db.session.commit()
            print("Password reset to: admin123")
        else:
            print("Admin user not found! Creating one...")
            new_admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(new_admin)
            db.session.commit()
            print("Created admin user with password: admin123")

if __name__ == '__main__':
    reset_admin_password()
