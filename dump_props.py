
from app import create_app
from models import db, Property

app = create_app()

def dump_props():
    with app.app_context():
        props = Property.query.all()
        print(f"Total Properties: {len(props)}")
        with open("all_properties.txt", "w", encoding='utf-8') as f:
            for p in props:
                f.write(f"ID: {p.id} | Unit: {p.unit_number} | Status: {p.status}\n")

if __name__ == "__main__":
    dump_props()
