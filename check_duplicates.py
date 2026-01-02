
from app import create_app
from models import db, Tenant

app = create_app()

def check_dupes():
    with app.app_context():
        # Find duplicates by name
        from sqlalchemy import func
        
        dupes = db.session.query(Tenant.name, func.count(Tenant.id)).group_by(Tenant.name).having(func.count(Tenant.id) > 1).all()
        
        print(f"Found {len(dupes)} sets of duplicates:")
        
        for name, count in dupes:
            print(f"\nName: '{name}' (Count: {count})")
            tenants = Tenant.query.filter_by(name=name).all()
            for t in tenants:
                print(f" - ID: {t.id}, Leases: {len(t.leases)}, Invoices: {len(t.invoices)}")

if __name__ == "__main__":
    check_dupes()
