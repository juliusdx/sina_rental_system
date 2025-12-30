from app import create_app, db
from models import Invoice, Receipt

app = create_app()

with app.app_context():
    invoices = Invoice.query.all()
    for inv in invoices:
        total_paid = sum(r.amount for r in Receipt.query.filter_by(invoice_id=inv.id).all())
        print(f"Checking Invoice {inv.id}: Total {inv.total_amount} Paid {total_paid}")
        
        if total_paid >= inv.total_amount - 0.01:
            if inv.status != 'paid':
                inv.status = 'paid'
                print(" -> Set to PAID")
        elif total_paid > 0:
            if inv.status != 'partial':
                inv.status = 'partial'
                print(" -> Set to PARTIAL")
        else:
            if inv.status != 'unpaid':
                inv.status = 'unpaid'
                print(" -> Set to UNPAID")
                
    db.session.commit()
