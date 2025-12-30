
from app import create_app, db
from models import Property

def migrate_data():
    app = create_app()
    with app.app_context():
        properties = Property.query.all()
        print(f"Migrating {len(properties)} properties...")
        
        count = 0
        for p in properties:
            original = p.unit_number
            # Default values
            proj = p.project
            blk = None
            flr = None
            unt = None
            
            # Logic 1: Handle Project Prefix if present
            # e.g. "P2 SHOPS-GF-1"
            working_str = original
            if proj and working_str.startswith(proj):
                working_str = working_str[len(proj):].strip(' -/')
            
            # Logic 2: Split remaining by '-'
            parts = working_str.split('-')
            
            if len(parts) == 3:
                # e.g. "SH13-1-0" -> Block="SH13", Floor="1", Unit="0" ??
                # Or "Block-Floor-Unit"
                blk = parts[0]
                flr = parts[1]
                unt = parts[2]
            elif len(parts) == 2:
                # e.g. "GF-1" -> Floor="GF", Unit="1" (No block)
                # e.g. "B7-3" -> Block="B7", Unit="3" (Implicit floor?)
                # Heuristic: If part[0] looks like floor (GF, 1F), assign floor.
                if 'F' in parts[0].upper() or parts[0].upper() in ['G', 'LG', 'UG', 'GF']:
                    flr = parts[0]
                    unt = parts[1]
                else:
                    blk = parts[0]
                    unt = parts[1]
            elif len(parts) == 1:
                # e.g. "L03", "G01"
                unt = parts[0]
                
            # Update Model
            p.block = blk
            if not p.floor: p.floor = flr # Only update if not set (Property might already have floor)
            p.unit = unt
            
            print(f"Parsed '{original}' -> P={proj}, B={blk}, F={flr}, U={unt}")
            count += 1
            
        db.session.commit()
        print(f"Data Migration Complete. Updated {count} records.")

if __name__ == "__main__":
    migrate_data()
