
from app import create_app
from models import db, Property

app = create_app()

def check():
    with app.app_context():
        target = "P5-3"
        print(f"Checking for exact match: '{target}'")
        
        p = Property.query.filter_by(unit_number=target).first()
        if p:
            print(f"FOUND: ID={p.id}, Unit='{p.unit_number}'")
        else:
            print("NOT FOUND by exact match.")
            
        # Check by iterating (safest)
        all_props = Property.query.all()
        found = False
        for prop in all_props:
            if prop.unit_number.lower().strip() == target.lower().strip():
                print(f"FOUND by iteration: ID={prop.id}, Unit='{prop.unit_number}'")
                found = True
        
        if not found:
            print("NOT FOUND by iteration.")

if __name__ == "__main__":
    check()
