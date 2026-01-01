from app import create_app
from models import db, Tenant, Lease, Property
from datetime import date

app = create_app()

with app.app_context():
    today = date.today()
    
    # Get all active leases
    active_leases = Lease.query.filter(
        Lease.start_date <= today,
        Lease.end_date >= today
    ).all()
    
    # Group by Property
    prop_leases = {}
    for lease in active_leases:
        pid = lease.property_id
        if pid not in prop_leases:
            prop_leases[pid] = []
        prop_leases[pid].append(lease)
        
    # Filter for > 1
    multi_lease_props = {k: v for k, v in prop_leases.items() if len(v) > 1}
    
    output_path = r"C:\Users\juliu\.gemini\antigravity\brain\f592ea04-b02d-45d2-8acf-75c618f24986\conflicting_leases.md"
    
    with open(output_path, "w") as f:
        f.write("# Properties with Multiple Active Leases\n\n")
        f.write(f"**Found {len(multi_lease_props)} properties with conflicting active leases.**\n\n")
        
        for pid, leases in multi_lease_props.items():
            prop = Property.query.get(pid)
            if not prop:
                f.write(f"## Property ID {pid} (Orphaned)\n")
            else:
                f.write(f"## Property: {prop.unit_number} (ID: {prop.id})\n")
                
            for l in leases:
                t_name = l.tenant.name if l.tenant else "Unknown"
                f.write(f"- **Tenant**: {t_name}\n")
                f.write(f"  - **Lease ID**: {l.id}\n")
                f.write(f"  - **Period**: {l.start_date} to {l.end_date}\n")
            f.write("\n---\n")
            
    print(f"Report generated at {output_path}")
