
from app import create_app
from models import db, Property

app = create_app()

def check_props():
    with app.app_context():
        units = ['3', '2', '1-3-8B', 'C-0-3A']
        for u in units:
            p = Property.query.filter(Property.unit_number.ilike(u)).first()
            if p:
                print(f"Found Property '{u}': ID {p.id}, Unit '{p.unit_number}'")
            else:
                print(f"Property '{u}' NOT FOUND.")

if __name__ == "__main__":
    check_props()
