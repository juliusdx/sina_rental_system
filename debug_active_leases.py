
from app import create_app
from models import db, Lease, Property
from datetime import date

app = create_app()

def check_active_leases():
    today = date.today()
    with app.app_context():
        active = Lease.query.filter(Lease.start_date <= today, Lease.end_date >= today).all()
        print(f"Total Active Leases (Today): {len(active)}")
        
        # Check their properties
        prop_stats = {'occupied': 0, 'vacant': 0, 'other': 0}
        
        for l in active:
            if l.property_obj:
                status = l.property_obj.status
                prop_stats[status] = prop_stats.get(status, 0) + 1
                if status == 'vacant':
                    print(f" - Lease {l.id} (Unit {l.unit_number}) -> Property {l.property_obj.unit_number} is VACANT")
            else:
                 print(f" - Lease {l.id} (Unit {l.unit_number}) -> NO PROPERTY LINKED")

if __name__ == "__main__":
    check_active_leases()
