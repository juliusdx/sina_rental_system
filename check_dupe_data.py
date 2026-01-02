
from app import create_app
from models import db, Tenant

app = create_app()

def check_dupe_data():
    with app.app_context():
        name = "EASTWIND GLOBAL SDN BHD" # Only checking this one for now
        tenants = Tenant.query.filter_by(name=name).all()
        for t in tenants:
            print(f"ID: {t.id}, Account: '{t.account_code}', Email: '{t.email}'")

if __name__ == "__main__":
    check_dupe_data()
