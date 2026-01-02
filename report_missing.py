
from app import create_app
from models import db, Lease, Property
from datetime import date

app = create_app()

def generate_report():
    today = date.today()
    with app.app_context():
        # Get active leases
        active_leases = Lease.query.filter(Lease.start_date <= today, Lease.end_date >= today).all()
        
        missing_props = []
        for l in active_leases:
            if not l.property_obj:
                missing_props.append(l.unit_number)

        # distinct
        missing_uniq = sorted(list(set(missing_props)))
        
        with open("missing_properties_report.txt", "w") as f:
            f.write(f"Total Active Leases: {len(active_leases)}\n")
            f.write(f"Unlinked Leases: {len(missing_props)}\n")
            f.write("-" * 30 + "\n")
            f.write("The following Unit Numbers appear in Active Leases but NOT in the Property Database:\n")
            for u in missing_uniq:
                f.write(f"- {u}\n")

if __name__ == "__main__":
    generate_report()
