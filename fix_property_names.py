from app import create_app
from models import db, Property

app = create_app()

with app.app_context():
    print("Starting Property Name Fix...")
    
    # Find candidates: properties with 'Lot' but not starting with it?
    # Actually just find all with 'Lot' and strictly sanitize.
    props = Property.query.filter(Property.unit_number.like('%Lot%')).all()
    
    count = 0
    for p in props:
        original = p.unit_number
        if 'Lot' in original and not original.startswith('Lot'):
            # Find index of Lot
            # Careful with case? User screenshot shows "Lot" capitalized.
            idx = original.find('Lot')
            if idx > 0:
                new_name = original[idx:]
                
                # Check if this new name causes collision?
                # e.g. if we have "B-1-Lot 1" and "B-2-Lot 1"... wait.
                # If "Lot 1" is the identifier, duplicates are bad.
                # But looking at screenshot: "Lot 17, B-1-5". unique.
                # "Lot 17, B-0-5". unique.
                # So stripping prefix is safe because suffix contains unique info.
                
                p.unit_number = new_name
                count += 1
                print(f"Renamed: {original} -> {new_name}")
                
    # Fix SH (Suria Shops) - e.g. 13-G-SH13-1-0 -> SH13-1-0
    props_sh = Property.query.filter(Property.unit_number.like('%SH%')).all()
    for p in props_sh:
        original = p.unit_number
        if 'SH' in original and not original.startswith('SH'):
            # Only fix if it looks like a prefix issue
            # e.g. "13-G-SH" means SH is later.
            idx = original.find('SH')
            if idx > 0:
                 new_name = original[idx:]
                 p.unit_number = new_name
                 count += 1
                 print(f"Renamed SH: {original} -> {new_name}")
                
                 p.unit_number = new_name
                 count += 1
                 print(f"Renamed SH: {original} -> {new_name}")
                 
    # Fix Elemen P2 Shops (G-C-0-1 -> C-0-1)
    props_c = Property.query.filter(Property.unit_number.like('G-C-%')).all()
    for p in props_c:
        original = p.unit_number
        if original.startswith('G-C-'):
             new_name = original[2:] # Strip "G-"
             p.unit_number = new_name
             count += 1
             print(f"Renamed Elemen C: {original} -> {new_name}")
             
    # Fix Kolam Centre (3-1-3-7B -> 1-3-7B)
    # Pattern: Digit-1-...
    props_kc = Property.query.filter(Property.unit_number.like('%-1-%')).all()
    for p in props_kc:
        original = p.unit_number
        # Check if it starts with digit + hyphen + '1-'
        # e.g. "3-1-"
        if len(original) > 4 and original[0].isdigit() and original[1] == '-' and original[2:4] == '1-':
             new_name = original[2:]
             p.unit_number = new_name
             count += 1
             print(f"Renamed Kolam: {original} -> {new_name}")

             new_name = original[2:]
             p.unit_number = new_name
             count += 1
             print(f"Renamed Kolam: {original} -> {new_name}")
             
    # Fix Latitud 6 (G-0-1 -> 0-1)
    props_lat = Property.query.filter(Property.unit_number.like('G-0-%')).all()
    for p in props_lat:
        original = p.unit_number
        if original.startswith('G-0-'):
             new_name = original[2:] # Strip "G-"
             p.unit_number = new_name
             count += 1
             print(f"Renamed Latitud: {original} -> {new_name}")

             new_name = original[2:] # Strip "G-"
             p.unit_number = new_name
             count += 1
             print(f"Renamed Latitud: {original} -> {new_name}")

    # Fix Elemen P2 Shops remaining (1-C-1-1 -> C-1-1, 2-C-2-1 -> C-2-1)
    # Pattern: Digit-C-...
    props_c_rem = Property.query.filter(Property.unit_number.like('%-C-%')).all()
    for p in props_c_rem:
        original = p.unit_number
        # Check if it starts with digit + hyphen + 'C-'
        if len(original) > 4 and original[0].isdigit() and original[1] == '-' and original[2:4] == 'C-':
             new_name = original[2:]
             p.unit_number = new_name
             count += 1
             print(f"Renamed Elemen C Rem: {original} -> {new_name}")

    db.session.commit()
    print(f"Fixed {count} properties.")
