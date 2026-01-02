
from app import create_app
from models import db, Property

app = create_app()

def check():
    with app.app_context():
        # Case insensitive search
        props = Property.query.filter(Property.unit_number.ilike('%P5%')).all()
        print(f"Found {len(props)} properties matching 'P5':")
        for p in props:
            print(f"ID: {p.id}, Unit: '{p.unit_number}', Status: {p.status}, Archived: {p.archived}")
            
        if not props:
            print("No properties found matching 'P5'.")
            
        print("\nChecking for any property with ID=1 (referenced by lease):")
        p1 = Property.query.get(1)
        if p1:
             print(f"ID: 1, Unit: '{p1.unit_number}'")
        else:
             print("Property ID 1 is missing.")

if __name__ == "__main__":
    check()
