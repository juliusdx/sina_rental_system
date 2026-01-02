
from app import create_app
from models import Tenant

app = create_app()

def check():
    with app.app_context():
         t = Tenant.query.filter(Tenant.name.like("EASTWIND GLOBAL%")).all()
         for tenant in t:
             print(f"Name: {tenant.name}, Status: {tenant.status}, Leases: {len(tenant.leases)}")

if __name__ == "__main__":
    check()
