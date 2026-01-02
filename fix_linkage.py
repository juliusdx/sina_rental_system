
from app import create_app
from models import db, Property, Lease

app = create_app()

def fix():
    with app.app_context():
        # Get active leases without property_id
        active_leases = Lease.query.all()
        
        print(f"Total Leases: {len(active_leases)}")
        
        relinked_count = 0
        missing_properties = []
        
        for lease in active_leases:
            if not lease.property_id:
                # Try to find property by unit_number
                # Try exact match first
                target_unit = lease.unit_number.strip()
                # Debug Check
                if 'P5' in target_unit:
                     print(f"DEBUG: Checking Lease Unit '{target_unit}' (Len: {len(target_unit)})")
                     # Find ANY P5 property
                     p5_props = Property.query.filter(Property.unit_number.ilike('%P5%')).all()
                     for p in p5_props:
                         print(f"   Candidate: '{p.unit_number}' (ID: {p.id}, Len: {len(p.unit_number)})")
                         if p.unit_number == target_unit:
                             print("   -> EXACT STRING MATCH!")
                         else:
                             print(f"   -> Mismatch. Target vs Cand: {list(target_unit)} vs {list(p.unit_number)}")

                prop = Property.query.filter(Property.unit_number == target_unit).first()
                if not prop:
                     prop = Property.query.filter(Property.unit_number.ilike(target_unit)).first()
                
                if prop:
                    print(f"MATCH FOUND: Lease '{lease.unit_number}' -> Property '{prop.unit_number}' (ID: {prop.id})")
                    lease.property_id = prop.id
                    relinked_count += 1
                else:
                    # Try fuzzy variations? 
                    # e.g. "C-0-3A" vs "C-0-03A" or "C-G-3A"
                    print(f"MISSING: Property for Lease '{lease.unit_number}' not found in DB.")
                    missing_properties.append(lease.unit_number)
            else:
                 # Check if linked property actually exists
                 prop = Property.query.get(lease.property_id)
                 if not prop:
                     print(f"BROKEN LINK: Lease '{lease.unit_number}' points to Dead ID {lease.property_id}")
                     lease.property_id = None # Reset
        
        if relinked_count > 0:
            db.session.commit()
            print(f"Successfully relinked {relinked_count} leases.")
            
            # Recalculate statuses
            from routes.properties import recalculate_property_statuses
            recalculate_property_statuses()
            print("Property statuses recalculated.")
            
        else:
            print("No leases could be automatically relinked.")
            
        if missing_properties:
            print("\nThe following Lease Units do NOT exist in the Property Database:")
            for m in missing_properties:
                print(f" - {m}")
            print("\nPossible reasons: Import failed for these units, or Unit Number changed (e.g. formatting).")

if __name__ == "__main__":
    fix()
