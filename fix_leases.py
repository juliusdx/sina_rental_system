from app import create_app, db
from models import Tenant, Lease, Invoice, InvoiceLineItem

app = create_app()

with app.app_context():
    # Find tenant
    tenant = Tenant.query.filter(Tenant.name.ilike('%markmaju%')).first()
    
    if not tenant:
        print("Tenant not found!")
    else:
        print(f"Processing tenant: {tenant.name} (ID: {tenant.id})")
        
        # Get all leases
        leases = Lease.query.filter_by(tenant_id=tenant.id).order_by(Lease.id).all()
        
        if not leases:
            print("No leases found.")
        else:
            # Keep the first one
            primary_lease = leases[0]
            duplicates = leases[1:]
            
            print(f"Keeping Lease ID: {primary_lease.id}")
            print(f"Updating Rent Amount: {primary_lease.rent_amount} -> 18000.0")
            primary_lease.rent_amount = 18000.0
            
            if duplicates:
                print(f"Deleting {len(duplicates)} duplicate leases...")
                for dup in duplicates:
                    print(f" - Deleting Lease ID: {dup.id} (Rent: {dup.rent_amount})")
                    db.session.delete(dup)
            else:
                print("No duplicate leases found.")

            # Optional: Delete created invoices for this tenant so user can regenerate fresh
            print("Cleaning up existing unpaid invoices for this tenant to allow regeneration...")
            invoices = Invoice.query.filter_by(tenant_id=tenant.id, status='unpaid').all()
            for inv in invoices:
                print(f" - Deleting Invoice ID: {inv.id} (Amount: {inv.total_amount})")
                db.session.delete(inv)
                
            db.session.commit()
            print("Cleanup complete!")
