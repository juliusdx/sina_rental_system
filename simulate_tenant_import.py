
import pandas as pd
from datetime import datetime, date
from app import create_app
from models import Tenant, Lease, Property

app = create_app()

tenant_file = r"E:\My Drive\Sina\rental_system\templates\rental_source_template(strip formula).xlsx"

def simulate_import():
    print("=== SIMULATING TENANT IMPORT ===")
    
    try:
        df = pd.read_excel(tenant_file)
        print(f"Total Rows in File: {len(df)}")
        
        skipped_no_name = 0
        skipped_duplicate_lease = 0
        added_lease = 0
        existing_tenants_used = 0
        new_tenants_created = 0
        
        debug_log = []

        with app.app_context():
            # Cache for simulation performance
            existing_tenant_codes = {t.account_code: t for t in Tenant.query.all() if t.account_code}
            existing_tenant_names = {t.name: t for t in Tenant.query.all() if t.name}
            
            for i, row in df.iterrows():
                # Mimic get_val
                def get_val(key, default=None):
                    v = row.get(key)
                    return v if pd.notna(v) else default
                
                name = get_val('Tenant Name')
                if not name:
                    skipped_no_name += 1
                    debug_log.append(f"Row {i+2}: Skipped (No Name)")
                    continue
                
                acct_code = get_val('Account Code')
                
                # Check Tenant Dupes
                existing = None
                if acct_code:
                    existing = existing_tenant_codes.get(str(acct_code))
                if not existing:
                    existing = existing_tenant_names.get(name)
                
                tenant_id_sim = -1
                if existing:
                    existing_tenants_used += 1
                    tenant_id_sim = existing.id
                else:
                    new_tenants_created += 1
                    tenant_id_sim = 99999 + i # Mock ID
                    
                # Lease Check
                proj = str(get_val('project', ''))
                raw_unit = str(get_val('Unit', '')).strip()
                
                if raw_unit and raw_unit != 'None':
                     unit_no = raw_unit
                else:
                    floor = str(get_val('floor', ''))
                    lot = str(get_val('lot', ''))
                    unit_no = f"{floor}-{lot}".strip('-')
                
                if not unit_no and acct_code:
                     unit_no = str(acct_code)
                
                # Date Parsing
                s_date_raw = get_val('Start Date')
                # (Skipping deep date parsing for simulation, ensuring basic mapping)
                
                # Check DB for existing lease
                # We query the REAL DB to see if this lease actually exists
                if existing:
                     real_leases = Lease.query.filter_by(tenant_id=existing.id, unit_number=unit_no).all()
                     # If any matches start date roughly? 
                     # The code uses strict start_date match.
                     if real_leases:
                         skipped_duplicate_lease += 1
                         debug_log.append(f"Row {i+2}: Skipped (Duplicate Lease for {name} @ {unit_no})")
                         continue
                
                added_lease += 1
                debug_log.append(f"Row {i+2}: WOULD ADD Lease for {name} @ {unit_no}")

        print(f"\nStats:")
        print(f"Skipped (No Name): {skipped_no_name}")
        print(f"Skipped (Existing Lease): {skipped_duplicate_lease}")
        print(f"Would Add New Lease: {added_lease}")
        print(f"Total Processed: {skipped_no_name + skipped_duplicate_lease + added_lease}")
        
        if skipped_duplicate_lease > 0:
            print("\nSample Skipped (Duplicate):")
            for l in [x for x in debug_log if 'Duplicate' in x][:10]:
                print(l)

    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    simulate_import()
