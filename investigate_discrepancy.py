
from app import create_app, db
from models import Tenant, Lease, Property
from datetime import date

def investigate():
    app = create_app()
    with app.app_context():
        print("--- GAP ANALYSIS REPORT ---")
        
        # 1. Get Active Tenants
        active_tenants = Tenant.query.filter_by(status='active').all()
        print(f"Total Active Tenants: {len(active_tenants)}")
        
        linked_active = 0
        unlinked_active = 0
        expired_lease = 0
        
        unlinked_units = []
        
        # for t in active_tenants:
        #    ... (logic to collect unlinked_units) ...
        
        # Simplified loop for collecting data only
        for t in active_tenants:
            lease = Lease.query.filter_by(tenant_id=t.id).order_by(Lease.end_date.desc()).first()
            if not lease:
                unlinked_active += 1
                continue
            
            if lease.property_id:
                if lease.end_date < date.today(): expired_lease += 1
                else: linked_active += 1
            else:
                unlinked_active += 1
                unlinked_units.append(lease.unit_number)

        print("-" * 30)
        print(f"Summary:")
        print(f"Linked & Occupied: {linked_active}")
        print(f"Linked but Expired: {expired_lease}")
        print(f"Unlinked (Bad Unit #): {unlinked_active}")
        
        if unlinked_units:
            print(f"\nTop Examples of Unlinked Unit Numbers:")
            from collections import Counter
            common = Counter(unlinked_units).most_common(20)
            for unit, count in common:
                print(f" - '{unit}' ({count} cases)")
                
        # Sample Property Unit Numbers for comparison
        print(f"\nSample Property Inventory (Valid Codes):")
        props = Property.query.limit(20).all()
        print(", ".join([p.unit_number for p in props]))
        print(f"\nSummary:")
        print(f"Linked & Occupied: {linked_active}")
        print(f"Linked but Expired: {expired_lease}")
        print(f"Unlinked (Bad Unit #): {unlinked_active}")
        
        if unlinked_units:
            print(f"\nTop 10 Unlinked Unit Numbers:")
            from collections import Counter
            common = Counter(unlinked_units).most_common(10)
            for unit, count in common:
                print(f" - {unit} ({count} times)")
                
        # Sample Property Unit Numbers for comparison
        print(f"\nSample Valid Property Unit Numbers (from DB):")
        props = Property.query.limit(10).all()
        print([p.unit_number for p in props])

if __name__ == "__main__":
    investigate()
