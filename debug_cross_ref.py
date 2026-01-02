
import pandas as pd
from app import create_app
from models import db, Property, Lease

app = create_app()

prop_file = r"E:\My Drive\Sina\rental_system\templates\Property_upload_template michael_JK_strip_formula.xlsx"
tenant_file = r"E:\My Drive\Sina\rental_system\templates\rental_source_template(strip formula).xlsx"

def analyze():
    print("=== CROSS REFERENCE ANALYSIS ===")
    
    # 1. Load Files
    try:
        df_prop = pd.read_excel(prop_file)
        df_tenant = pd.read_excel(tenant_file)
        
        print(f"Property File Rows: {len(df_prop)}")
        print(f"Tenant File Rows: {len(df_tenant)}")
        
        # 2. Extract Keys
        # Property File: Unit Number
        # Helper to construct Unit Number if missing (mimic app logic)
        def construct_prop_id(row):
            # Safe extraction helper
            def clean_str(val):
                s = str(val).strip()
                return '' if s.lower() == 'nan' else s

            unit_no = clean_str(row.get('Unit Number'))
            if unit_no:
                 return unit_no
                 
            # Construct from parts
            block = clean_str(row.get('Block'))
            floor = clean_str(row.get('Floor'))
            unit = clean_str(row.get('Unit'))
            
            parts = [p for p in [block, floor, unit] if p]
            return "-".join(parts)

        df_prop['ConstructedID'] = df_prop.apply(construct_prop_id, axis=1)
        prop_ids_source = set(df_prop['ConstructedID'].str.lower())
        
        # Tenant File: Unit (assuming column name 'Unit' or similar)
        # Inspect columns first
        print(f"Tenant Columns: {df_tenant.columns.tolist()}")
        
        # Adjust based on likely column name. Usually 'Unit' or 'Unit No'
        tenant_unit_col = next((c for c in df_tenant.columns if 'unit' in c.lower()), None)
        if not tenant_unit_col:
            print("ERROR: Could not find Unit column in Tenant file.")
            return

        tenant_units_source = set(df_tenant[tenant_unit_col].astype(str).str.strip().str.lower())
        
        print(f"Unique Property IDs in Prop Source: {len(prop_ids_source)}")
        print(f"Unique Unit Refs in Tenant Source: {len(tenant_units_source)}")
        
        # 3. Check Mismatches
        # Which tenants are pointing to units NOT in the property source?
        missing_in_prop_source = tenant_units_source - prop_ids_source
        
        if missing_in_prop_source:
            print(f"\nWARNING: {len(missing_in_prop_source)} Tenant Units match NOTHING in Property File.")
            print("Sample Missing in Prop Source:")
            print(list(missing_in_prop_source)[:10])
        else:
            print("\nOK: All Tenant units exist in Property Source file.")

        # 4. Check DB Linkage
        with app.app_context():
            db_props = set([p.unit_number.lower() for p in Property.query.all()])
            print(f"\nTotal Properties in DB: {len(db_props)}")
            
            # Check what's missing from DB that IS in Prop Source
            missing_in_db = prop_ids_source - db_props
            # Filter out empty string
            missing_in_db = {x for x in missing_in_db if x}
            
            if missing_in_db:
                print(f"CRITICAL: {len(missing_in_db)} Properties from Source are MISSING in DB (Import Failed/Skipped).")
                print("Sample Missing in DB:")
                print(list(missing_in_db)[:10])
                
                # Check specific P5 example if relevant
                p5_missing = [x for x in missing_in_db if 'p5' in x]
                if p5_missing:
                    print(f" - Found {len(p5_missing)} missing 'P5' units.")
            
            # Check Tenant Linkage
            # Which tenant units are NOT in DB?
            tenant_missing_in_db = tenant_units_source - db_props
            tenant_missing_in_db = {x for x in tenant_missing_in_db if x and x != 'nan'}
            
            if tenant_missing_in_db:
                print(f"\nCRITICAL: {len(tenant_missing_in_db)} Tenant Units do not exist in DB.")
                print("Sample Tenant units with no DB property:")
                print(list(tenant_missing_in_db)[:10])
                
        # 5. P5 Deep Dive
        print("\n=== P5 / Elemen Deep Dive (Property File) ===")
        # Filter rows where Project contains 'Elemen' or 'P5'
        p5_mask = df_prop.apply(lambda x: x.astype(str).str.contains('Elemen', case=False, na=False)).any(axis=1)
        p5_rows = df_prop[p5_mask]
        
        if not p5_rows.empty:
            print(f"Found {len(p5_rows)} 'Elemen' rows in Property File.")
            # Print ALL columns for these rows to see what data exists
            print(p5_rows.to_string())
        else:
            print("No 'Elemen' rows found in Property File.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    sys.stdout = open('p5_dump.txt', 'w', encoding='utf-8')
    analyze()

