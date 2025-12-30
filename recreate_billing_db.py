from app import create_app
from models import db, Invoice, InvoiceLineItem

app = create_app()

with app.app_context():
    # Drop existing tables
    print("Dropping tables...")
    try:
        InvoiceLineItem.__table__.drop(db.engine)
    except Exception as e:
        print(f"LineItem drop failed (maybe didn't exist): {e}")
        
    try:
        Invoice.__table__.drop(db.engine)
    except Exception as e:
        print(f"Invoice drop failed: {e}")

    # Recreate tables
    print("Creating tables...")
    db.create_all()
    print("Database updated.")
