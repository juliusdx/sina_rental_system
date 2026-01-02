
from app import create_app
from models import db, Lease

app = create_app()

def list_lease_units():
    with app.app_context():
        leases = Lease.query.all()
        print(f"Total Leases: {len(leases)}")
        print("Sample Unit Numbers:")
        for l in leases[:20]:
            print(f" - '{l.unit_number}'")
            
        # Search for '7A'
        matches = Lease.query.filter(Lease.unit_number.like('%7A%')).all()
        print(f"\nLeases containing '7A': {len(matches)}")
        for l in matches:
             print(f" - '{l.unit_number}' (ID: {l.id})")

if __name__ == "__main__":
    list_lease_units()
