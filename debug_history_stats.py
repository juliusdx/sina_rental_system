
from app import create_app
from models import db, Property, Lease

app = create_app()

def check_137A():
    with app.app_context():
        # Find Property
        prop = Property.query.filter(Property.unit_number.like('%1-3-7A%')).first()
        if not prop:
            print("Property 1-3-7A not found.")
            # Try case insensitive search or partial?
            props = Property.query.filter(Property.unit_number.ilike('%1-3-7A%')).all()
            if props:
                print(f"Found {len(props)} matches via ilike:")
                for p in props:
                    print(f" - ID: {p.id}, Unit: '{p.unit_number}', Status: {p.status}")
                    prop = p # use first match
            else:
                return

        if prop:
            print(f"\nProperty: {prop.unit_number} (ID: {prop.id})")
            
            # Check Leases by Property ID
            leases_id = Lease.query.filter_by(property_id=prop.id).all()
            print(f"Leases linked by Property ID: {len(leases_id)}")
            
            # Check Leases by Unit Number String
            leases_str = Lease.query.filter_by(unit_number=prop.unit_number).all()
            print(f"Leases linked by Unit Number '{prop.unit_number}': {len(leases_str)}")
            
            # Check for Mismatch strings
            # e.g. '1-3-7a' vs '1-3-7A'
            leases_ilike = Lease.query.filter(Lease.unit_number.ilike(prop.unit_number)).all()
            print(f"Leases linked by ILIKE Unit Number: {len(leases_ilike)}")
            
            if len(leases_ilike) > 0:
                print("\nLease Details:")
                for l in leases_ilike:
                    print(f" - Lease ID: {l.id}, Unit: '{l.unit_number}', Tenant: {l.tenant.name if l.tenant else 'None'}, PropID: {l.property_id}")

if __name__ == "__main__":
    check_137A()
