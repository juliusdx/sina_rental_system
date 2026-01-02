
from app import create_app
from models import db, Property, Lease

app = create_app()

def check():
    with app.app_context():
        # Check P5-3
        p = Property.query.filter_by(unit_number='P5-3').first()
        if p:
            print(f"Property P5-3 Status: {p.status}")
            lease = Lease.query.filter_by(property_id=p.id, is_active=True).first()
            if lease:
                print(f" -> Linked to Lease ID: {lease.id} (Unit: {lease.unit_number})")
            else:
                print(" -> No active lease linked.")
        else:
            print("Property P5-3 not found.")

        # Check Aggregates
        total = Property.query.count()
        occupied = Property.query.filter_by(status='occupied').count()
        print(f"Total: {total}")
        print(f"Occupied: {occupied}")

if __name__ == "__main__":
    check()
