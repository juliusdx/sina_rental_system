
import pandas as pd
from app import create_app

app = create_app()

prop_file = r"E:\My Drive\Sina\rental_system\templates\Property_upload_template michael_JK_strip_formula.xlsx"
tenant_file = r"E:\My Drive\Sina\rental_system\templates\rental_source_template(strip formula).xlsx"

def analyze():
    print("=== NEW ID LOGIC ANALYSIS (PROJECT + UNIT) ===")
    
    try:
        df_prop = pd.read_excel(prop_file)
        df_tenant = pd.read_excel(tenant_file)
        
        print(f"Property Rows: {len(df_prop)}")
        print(f"Tenant Rows: {len(df_tenant)}")
        
        # 1. Generate IDs for Property File
        def gen_prop_id(row):
            proj = str(row.get('Project', '')).strip()
            # Try 'Unit', then 'Unit Number'
            unit = str(row.get('Unit', '')).strip()
            if not unit or unit.lower() == 'nan':
                 unit = str(row.get('Unit Number', '')).strip()
            
            if proj.lower() == 'nan': proj = ''
            if unit.lower() == 'nan': unit = ''
            
            if not proj or not unit:
                return None
            
            return f"{proj} {unit}".lower()

        df_prop['NewID'] = df_prop.apply(gen_prop_id, axis=1)
        prop_ids = set(df_prop['NewID'].dropna())
        print(f"Generated {len(prop_ids)} unique Property IDs.")
        
        # 2. Generate IDs for Tenant File
        # Check col names
        # print("Tenant Cols:", df_tenant.columns.tolist())
        
        def gen_tenant_id(row):
             # Find project col
             proj = str(row.get('project', '')).strip()
             unit = str(row.get('Unit', '')).strip()
             
             if proj.lower() == 'nan': proj = ''
             if unit.lower() == 'nan': unit = ''
             
             if not proj or not unit:
                 return None
                 
             return f"{proj} {unit}".lower()
             
        df_tenant['NewLinkID'] = df_tenant.apply(gen_tenant_id, axis=1)
        tenant_ids = set(df_tenant['NewLinkID'].dropna())
        print(f"Generated {len(tenant_ids)} unique Tenant Link IDs.")
        
        # 3. Match
        matched = tenant_ids.intersection(prop_ids)
        missing = tenant_ids - prop_ids
        
        print(f"\nMATCH RESULTS:")
        print(f"Matched: {len(matched)}")
        print(f"Missing: {len(missing)}")
        
        if missing:
            print("\nSAMPLE MISSING (Tenants that still won't link):")
            print(list(missing)[:20])
            
            # Diagnose why
            print("\nDIAGNOSIS:")
            for m in list(missing)[:5]:
                print(f"Missing ID: '{m}'")
                # Does project exist in props?
                proj_part = " ".join(m.split()[:-1]) # Rough guess
                # Find props with similar project
                similar_props = [p for p in prop_ids if proj_part in p]
                if similar_props:
                    print(f" -> Similar Props found: {similar_props[:3]}")
                else:
                    print(" -> No properties found with similar project prefix.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    sys.stdout = open('final_id_analysis.txt', 'w', encoding='utf-8')
    analyze()
