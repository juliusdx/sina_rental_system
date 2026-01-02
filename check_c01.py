
from app import create_app
from models import db, Property

app = create_app()

def check():
    with app.app_context():
        # Check for C-0-1 specifically
        print("Checking for 'C-0-1' variants...")
        props = Property.query.filter(Property.unit_number.ilike('%C-0-1%')).all()
        for p in props:
            print(f"ID: {p.id}, Unit: '{p.unit_number}'")
            
        if not props:
            print("No properties found matching 'C-0-1'.")
            
if __name__ == "__main__":
    check()
