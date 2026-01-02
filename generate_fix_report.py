
import pandas as pd
import difflib

prop_file = r"E:\My Drive\Sina\rental_system\templates\Property_upload_template michael_JK_strip_formula.xlsx"
tenant_file = r"E:\My Drive\Sina\rental_system\templates\rental_source_template(strip formula).xlsx"

def normalize(s):
    return str(s).strip().lower() if pd.notna(s) else ""

def generate_report():
    print("Loading files...")
    df_prop = pd.read_excel(prop_file)
    df_tenant = pd.read_excel(tenant_file)
    
    # 1. Build Index of Valid Property Keys
    valid_props = {} # Key -> Original Unit String
    
    for i, row in df_prop.iterrows():
        proj = normalize(row.get('Project', ''))
        
        # Determine the "Valid Unit Number" as per the app import logic
        # For matching purposes, we trust the 'Unit' column if it exists, or 'Unit Number'
        u_val = normalize(row.get('Unit', '')) 
        u_num = normalize(row.get('Unit Number', '')) # Current Import Logic often relies on this being generated or explicit
        
        # The cross-referencing logic the user agreed to is "Project + Unit"
        # In Prop file, 'Unit' usually contains the short identifier (e.g. '1', 'C-0-1')
        # In 'Elemen P5' rows, Unit is '1', '2', '3'.
        
        key_token = u_val if u_val else u_num
        
        # Create a linkage key: "projslug|unitslug"
        full_key = f"{proj}|{key_token}"
        valid_props[full_key] = key_token

    print(f"Indexed {len(valid_props)} valid property keys.")
    
    # 2. Check Tenants
    corrections = []
    
    for i, row in df_tenant.iterrows():
        # Adjust for 1-based index in Excel (Header=1, data starts=2)
        excel_row = i + 2
        
        ten_proj = normalize(row.get('project', ''))
        ten_unit = normalize(row.get('Unit', ''))
        ten_name = row.get('Tenant Name', 'Unknown')
        
        if not ten_proj or not ten_unit:
            continue # specific logic for empty rows?
            
        full_key = f"{ten_proj}|{ten_unit}"
        
        if full_key in valid_props:
            continue
            
        # Mismatch Found!
        # Try to find a suggestion
        # Filter valid props to same project
        project_matches = {k: v for k, v in valid_props.items() if k.startswith(ten_proj + "|")}
        
        suggestion = "No match found"
        
        if project_matches:
            # Try fuzzy match on the Unit part
            # e.g. Ten='P5-3', Valid='3' (Full key 'elemen p5|3')
            
            # Simple check: Does Tenant Unit contain Valid Unit?
            # or Is Valid Unit contained in Tenant Unit?
            
            best_match = None
            highest_ratio = 0.0
            
            for k, real_unit in project_matches.items():
                # k is "proj|unit"
                # compare ten_unit vs real_unit
                
                # Direct containment check
                if real_unit in ten_unit or ten_unit in real_unit:
                    # e.g. '1' in 'p5-1'
                    best_match = real_unit
                    break
                    
                # SequenceMatcher
                ratio = difflib.SequenceMatcher(None, ten_unit, real_unit).ratio()
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    best_match = real_unit
            
            if best_match:
                suggestion = f"Change Unit to '{best_match}'"
            else:
                 suggestion = f"Check Project '{ten_proj}' or Unit format"
        else:
            suggestion = "Project name mismatch?"

        corrections.append({
            'Row': excel_row,
            'Project': row.get('project', ''),
            'Current_Unit': row.get('Unit', ''),
            'Tenant': ten_name,
            'Suggestion': suggestion
        })

    with open('tenant_fix_list.txt', 'w', encoding='utf-8') as f:
        f.write(f"\nFound {len(corrections)} rows requiring updates.\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Row':<5} | {'Project':<15} | {'Current Unit':<15} | {'Suggestion':<30}\n")
        f.write("-" * 80 + "\n")
        
        for c in corrections:
            p = str(c['Project'])[:15]
            u = str(c['Current_Unit'])[:15]
            s = c['Suggestion']
            f.write(f"{c['Row']:<5} | {p:<15} | {u:<15} | {s:<30}\n")
            
    # Also print to stdout
    print(f"Report written to tenant_fix_list.txt with {len(corrections)} items.")

if __name__ == "__main__":
    generate_report()
