from app import create_app
from models import Tenant, Lease

app = create_app()

with app.app_context():
    # Find tenant matching "markmaju"
    tenants = Tenant.query.filter(Tenant.name.ilike('%markmaju%')).all()
    
    for t in tenants:
        print(f"Tenant: {t.name} (ID: {t.id})")
        print(f"Status: {t.status}")
        
        leases = Lease.query.filter_by(tenant_id=t.id).all()
        print(f"Leases ({len(leases)}):")
        for l in leases:
            print(f"  - ID: {l.id}")
            print(f"    Unit: {l.unit_number}")
            print(f"    Project: {l.project}")
            print(f"    Rent: {l.rent_amount}")
            print(f"    Dates: {l.start_date} to {l.end_date}")
