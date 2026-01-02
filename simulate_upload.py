
import pandas as pd
from app import create_app
from models import db, Property, Project

app = create_app()

excel_path = r"E:\My Drive\Sina\rental_system\templates\Property_upload_template michael_JK_strip_formula.xlsx"

def simulate():
    with app.app_context():
        print("=== SIMULATING UPLOAD LOGIC ===")
        
        try:
            df = pd.read_excel(excel_path)
            # data_rows = df.to_dict('records') # Logic in app iterates rows directly from openpyxl usually but pandas is close enough for logic check if we are careful with NaNs.
            # App uses openpyxl. Let's use openpyxl to be exact.
            import openpyxl
            wb = openpyxl.load_workbook(excel_path)
            ws = wb.active
            rows = list(ws.rows)
            headers = [cell.value for cell in rows[0]]
            
            data_rows = []
            for row in rows[1:]:
                row_data = {}
                for idx, cell in enumerate(row):
                    if idx < len(headers):
                        row_data[headers[idx]] = cell.value
                data_rows.append(row_data)

            print(f"Total Rows: {len(data_rows)}")
            
            added = []
            skipped = []
            
            # Cache DB
            existing_units = {p.unit_number.lower() for p in Property.query.all()}
            
            for i, row in enumerate(data_rows):
                # Helper
                def get_val(key, default=''):
                    v = row.get(key)
                    if v is None: return default
                    return str(v).strip()

                # 1. Extract Components
                proj_name = get_val('Project')
                block = get_val('Block')
                floor = get_val('Floor')
                unit_val = get_val('Unit')
                
                if block == 'nan': block = ''
                if floor == 'nan': floor = ''
                if unit_val == 'nan': unit_val = ''
                
                # 2. Determine Unit Number
                unit_number = get_val('Unit Number')
                if unit_number == 'nan': unit_number = ''
                
                # Construct if missing
                if not unit_number and (unit_val or floor):
                    # Fix: Don't include proj_name in the ID (redundant and causes mismatch)
                    # Fix: Avoid double prefixing if unit_val already contains info
                    
                    prefix = ""
                    clean_unit = unit_val
                    
                    # Build standard prefix: Block-Floor
                    prefix_parts = [p for p in [block, floor] if p]
                    if prefix_parts:
                        prefix = "-".join(prefix_parts)
                    
                    # Logic Fixes:
                    if 'lot' in clean_unit.lower() or 'sh' in clean_unit.lower() or clean_unit.lower().startswith('c-') or clean_unit.startswith('1-') or clean_unit.startswith('0-'):
                            unit_number = clean_unit
                    elif prefix and unit_val.startswith(prefix):
                        unit_number = unit_val
                    else:
                            parts = prefix_parts + [unit_val]
                            parts = [p for p in parts if p]
                            unit_number = "-".join(parts)
                
                if not unit_number:
                    skipped.append(f"Row {i+2}: Skipped (No ID generated). Block={block}, Unit={unit_val}")
                    continue 
                    
                # Check duplicate (Simulation against DB)
                if unit_number.lower() in existing_units:
                    skipped.append(f"Row {i+2}: Skipped (Duplicate in DB). ID={unit_number}")
                    continue
                
                # Check duplicate (Internal collision in this batch)
                # But wait, existing_units doesn't update in this sim?
                # Actually, duplicate check in App checks DB.
                # If DB is empty (user deleted all), then internal collision matters.
                # But here DB is partially full (222 imported).
                
                added.append(f"Row {i+2}: WOULD ADD {unit_number}")
                existing_units.add(unit_number.lower()) # Simulate add

            # Analyze results
            print(f"Would Add: {len(added)}")
            print(f"Would Skip: {len(skipped)}")
            
            print("\n=== SKIPPED SAMPLE ===")
            for s in skipped[:20]:
                print(s)
                
            print("\n=== P5 / C-0-1 SPECIFIC CHECK ===")
            for msg in added + skipped:
                if 'P5' in msg or 'C-0-1' in msg:
                    print(msg)
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    simulate()
