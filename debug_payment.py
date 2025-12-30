from app import create_app, db
from models import Invoice, Receipt

app = create_app()

with app.app_context():
    inv = Invoice.query.first()
    if inv:
        print(f"Invoice #{inv.id}: Total={inv.total_amount}, Status={inv.status}")
        receipts = Receipt.query.filter_by(invoice_id=inv.id).all()
        total_paid = 0
        for r in receipts:
            print(f" - Receipt #{r.id}: {r.amount}")
            total_paid += r.amount
        print(f"Calculated Total Paid: {total_paid}")
