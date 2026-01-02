
from app import create_app
from models import db, Property, Lease
from datetime import date

app = create_app()

def check_status_distribution():
    with app.app_context():
        # Count by status
        from sqlalchemy import func
        stats = db.session.query(Property.status, func.count(Property.id)).group_by(Property.status).all()
        print("--- Status Distribution ---")
        for status, count in stats:
            print(f"{status}: {count}")
            
        # Check mismatches
        # Properties marked 'vacant' but have active lease
        today = date.today()
        mismatches = []
        occupied_props = Property.query.filter_by(status='occupied').all()
        vacant_props = Property.query.filter_by(status='vacant').all()
        
        print("\n--- Checking Vacant Properties with Active Leases ---")
        for p in vacant_props:
            active_lease = Lease.query.filter(
                Lease.property_id == p.id,
                Lease.start_date <= today,
                Lease.end_date >= today
            ).first()
            if active_lease:
                print(f"MISMATCH: Property {p.unit_number} is 'vacant' but has active lease (ID {active_lease.id})")
                mismatches.append(p)
                
        print(f"Found {len(mismatches)} mismatches.")
        
        # Check Occupied with NO active lease
        print("\n--- Checking Occupied Properties with NO Active Leases ---")
        bad_occupied = []
        for p in occupied_props:
             active_lease = Lease.query.filter(
                Lease.property_id == p.id,
                Lease.start_date <= today,
                Lease.end_date >= today
            ).first()
             if not active_lease:
                 print(f"MISMATCH: Property {p.unit_number} is 'occupied' but NO active lease found!")
                 bad_occupied.append(p)

if __name__ == "__main__":
    check_status_distribution()
