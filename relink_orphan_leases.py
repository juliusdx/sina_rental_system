from app import create_app
from models import db, Lease, Property
from datetime import date

app = create_app()

with app.app_context():
    print("Starting Lease Re-Link Process...")
    
    # Get all leases without link
    orphans = Lease.query.filter(Lease.property_id == None).all()
    print(f"Found {len(orphans)} orphaned leases.")
    
    linked_count = 0
    today = date.today()
    
    for lease in orphans:
        unit = lease.unit_number
        if not unit: continue
            
        # Try finding property by unit number
        # 1. Exact Match
        prop = Property.query.filter_by(unit_number=unit).first()
        
        # 2. Try simple strip if exact fails (e.g. KC2/1-3-7 -> 1-3-7)
        if not prop and '/' in unit:
             cleaned = unit.split('/')[-1]
             prop = Property.query.filter_by(unit_number=cleaned).first()
             
        # 3. Fuzzy Suffix Match (Lease: "Lot 23", Prop: "G-11-Lot 23")
        if not prop:
             # This is expensive but necessary for the fix
             # Only scan properties that might match
             prop = Property.query.filter(Property.unit_number.contains(unit)).first()
             # Validate: Should end with the unit or strict containment
             if prop:
                 # Double check to avoid false positives (e.g. "1-1" matching "1-10")
                 if not prop.unit_number.endswith(unit) and f"-{unit}" not in prop.unit_number:
                     prop = None
             
        if prop:
            lease.property_id = prop.id
            
            # Sync Project Name if missing on Property or Lease
            if lease.project and not prop.project:
                prop.project = lease.project
            elif prop.project and not lease.project:
                lease.project = prop.project
                
            # Update Property Status
            if lease.end_date and lease.end_date >= today:
                prop.status = 'occupied'
                
            linked_count += 1
            print(f"Linked Lease {lease.id} ({unit}) -> Property {prop.id}")
            
    db.session.commit()
    print(f"Done. Re-linked {linked_count} leases.")
