from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, AuditLog, db
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Allow Admin to access everything
            if current_user.role == 'admin':
                return f(*args, **kwargs)
                
            if current_user.role not in roles:
                flash('You do not have permission to access this resource.', 'error')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

from utils import log_audit


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            log_audit('LOGIN', 'User', user.id, 'User logged in')
            # Redirect based on role? For now, all go to dashboard
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password')
            
    return render_template('index.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_audit('LOGOUT', 'User', current_user.id, 'User logged out')
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/audit_logs')
@login_required
@role_required('admin')
def view_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('audit_logs.html', logs=logs)

@auth_bp.route('/register_user', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        
        # Basic validation
        if not username or not password or not role:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('auth.register_user'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register_user'))
            
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register_user'))
            
        try:
            # Create user
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role
            )
            db.session.add(new_user)
            db.session.commit()
            
            # Audit log
            log_audit('CREATE', 'User', new_user.id, f"Created user {username} as {role}")
            db.session.commit()
            
            flash(f'User {username} created successfully!', 'success')
            return redirect(url_for('auth.register_user')) # Stay on page to add more? Or go to dashboard?
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
            
            
    # Fetch all users for the list
    users = User.query.order_by(User.id).all()
    return render_template('auth/register_user.html', users=users)
