from app import create_app, db
from models import AuditLog
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating Database: Creating AuditLog table...")
    
    try:
        # Create table
        db.create_all()
        print("Tables checked/created. Verifying audit_log...")
        
        # Verify
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log';"))
        if result.fetchone():
            print("AuditLog table exists.")
        else:
            print("Error: Table not created.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
