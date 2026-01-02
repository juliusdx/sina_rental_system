
from app import create_app
from models import db, Tenant, Lease

app = create_app()

def count():
    with app.app_context():
        t_count = Tenant.query.count()
        l_count = Lease.query.count()
        
        print(f"Total Tenants: {t_count}")
        print(f"Total Leases: {l_count}")
        
        # Check for multi-lease tenants
        multi = []
        for t in Tenant.query.all():
            if len(t.leases) > 1:
                multi.append(f"{t.name}: {len(t.leases)} leases")
                
        print(f"\nTenants with Multiple Leases ({len(multi)}):")
        for m in multi[:10]:
            print(m)

if __name__ == "__main__":
    count()
