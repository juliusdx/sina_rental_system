from app import create_app
from models import db, Property, Lease
from datetime import date

app = create_app()

with app.app_context():
    print("--- Starting Status Fix ---")
    
    # 1. Fix Missing Property Links in Leases
    # (If leases were imported with unit_number but not property_id)
    leases_without_link = Lease.query.filter(Lease.property_id == None).all()
    print(f"Found {len(leases_without_link)} leases without property_id links.")
    
    linked_count = 0
    for lease in leases_without_link:
        # Find property by unit number
        prop = Property.query.filter_by(unit_number=lease.unit_number).first()
        if prop:
            lease.property_id = prop.id
            linked_count += 1
            print(f"Linked Lease {lease.id} ({lease.unit_number}) -> Property {prop.id}")
        else:
            print(f"WARNING: Could not find Property for Lease {lease.id} ({lease.unit_number})")
            
    db.session.commit()
    print(f"Successfully linked {linked_count} leases.")
    
    # 2. Recalculate Statuses
    print("\nRecalculating Statuses...")
    today = date.today()
    properties = Property.query.all()
    
    occupied_count = 0
    vacant_count = 0
    
    for prop in properties:
        # Check if there's an active lease
        active_lease = Lease.query.filter(
            Lease.property_id == prop.id,
            Lease.start_date <= today,
            Lease.end_date >= today
        ).first()
        
        # Determine correct status
        old_status = prop.status
        
        if active_lease:
            prop.status = 'occupied'
            occupied_count += 1
            if old_status != 'occupied':
                print(f"Unit {prop.unit_number}: {old_status} -> occupied")
        else:
            # Revert to vacant only if it was falsely occupied
            # or if we want to reset everything?
            # Let's trust the logic: Only revert 'occupied' to 'vacant', preserve manual tags
            if prop.status == 'occupied':
                prop.status = 'vacant'
                print(f"Unit {prop.unit_number}: occupied -> vacant (Lease expired)")
            
            if prop.status == 'vacant':
                vacant_count += 1
    
    db.session.commit()
    print(f"\nFinal Counts -> Occupied: {occupied_count}, Others (Vacant/Maint): {len(properties) - occupied_count}")
    print("--- Fix Complete ---")
