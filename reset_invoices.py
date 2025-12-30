from app import create_app, db
from models import Invoice, InvoiceLineItem, Receipt

app = create_app()

with app.app_context():
    print("Deleting all Receipts...")
    Receipt.query.delete()
    
    print("Deleting all Invoice Line Items...")
    InvoiceLineItem.query.delete()
    
    print("Deleting all Invoices...")
    Invoice.query.delete()
    
    db.session.commit()
    print("Successfully deleted all billing records.")
