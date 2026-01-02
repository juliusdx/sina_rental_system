
from app import create_app
from models import db, Tenant, Lease, Invoice, Receipt, TenantNote

app = create_app()

def merge_dupes():
    print("=== MERGING DUPLICATE TENANTS ===")
    with app.app_context():
        # Find duplicates by name
        from sqlalchemy import func
        
        dupes_sets = db.session.query(Tenant.name).group_by(Tenant.name).having(func.count(Tenant.id) > 1).all()
        
        if not dupes_sets:
            print("No duplicates found.")
            return

        for (name,) in dupes_sets:
            print(f"\nProcessing Duplicate Set: '{name}'")
            
            # Get all tenants with this name
            tenants = Tenant.query.filter_by(name=name).order_by(Tenant.id).all()
            
            # Keep the first one (primary)
            primary = tenants[0]
            duplicates = tenants[1:]
            
            print(f" -> Keeping ID {primary.id} (Leases: {len(primary.leases)})")
            
            for dup in duplicates:
                print(f" -> Merging ID {dup.id} (Leases: {len(dup.leases)})...")
                
                # 1. Reassign Leases
                for lease in dup.leases:
                    lease.tenant_id = primary.id
                
                # 2. Reassign Invoices
                for inv in dup.invoices:
                    inv.tenant_id = primary.id
                    
                # 3. Reassign Receipts
                # Receipts are linked to Tenant AND Invoice. 
                # If linked to Invoice, invoice reassignment covers it (usually).
                # But we should update tenant_id explicitly.
                # query receipts by tenant_id (lazy load might not catch all if not in relationship?)
                receipts = Receipt.query.filter_by(tenant_id=dup.id).all()
                for r in receipts:
                    r.tenant_id = primary.id
                    
                # 5. Reassign SST Exemptions
                from models import SSTExemption
                exemptions = SSTExemption.query.filter_by(tenant_id=dup.id).all()
                for ex in exemptions:
                    ex.tenant_id = primary.id
                
                # 6. Delete Duplicate Tenant (DISABLED FOR DEBUG)
                db.session.flush() 
                # db.session.delete(dup)
                # print(f"    -> ID {dup.id} Deleted.")
                
                # Mark as archived instead
                dup.name = f"{dup.name} (ARCHIVED {dup.id})"
                dup.status = 'past'
        
        try:
            db.session.commit()
            print("\nMerge Complete.")
        except Exception as e:
            db.session.rollback()
            print(f"MERGE FAILED: {str(e)}")

if __name__ == "__main__":
    merge_dupes()
