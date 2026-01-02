
import pandas as pd
from app import create_app
from models import db, Property, Lease, Tenant

app = create_app()

excel_path = r"E:\My Drive\Sina\rental_system\templates\Property_upload_template michael_JK_strip_formula.xlsx"

def analyze():
    with app.app_context():
        with open('debug_report.txt', 'w', encoding='utf-8') as f:
            def log(msg):
                print(msg)
                f.write(str(msg) + "\n")

            log("=== Database State ===")
            prop_count = Property.query.count()
            vacant_count = Property.query.filter_by(status='vacant').count()
            occupied_count = Property.query.filter_by(status='occupied').count()
            log(f"Total Properties in DB: {prop_count}")
            log(f"Vacant: {vacant_count}, Occupied: {occupied_count}")

            leases = Lease.query.all()
            log(f"Total Leases: {len(leases)}")
            
            active_leases = [l for l in leases if l.is_active]
            log(f"Active Leases: {len(active_leases)}")
            
            linked_active = [l for l in active_leases if l.property_id is not None]
            log(f"Active Leases with Linked Property: {len(linked_active)}")
            
            log("\n=== Excel Analysis ===")
            try:
                df = pd.read_excel(excel_path)
                log(f"Total Rows in Excel: {len(df)}")
                
                log(f"Columns: {df.columns.tolist()}")
                log("First 5 rows:")
                log(df.head().to_string())
                
                # Check for duplicates in potential ID columns
                if 'Universal ID' in df.columns:
                    dupes = df[df.duplicated('Universal ID', keep=False)]
                    if not dupes.empty:
                        log(f"Duplicate Universal IDs found: {len(dupes)}")
                        log(dupes['Universal ID'].value_counts().head())
                
                if 'Unit No' in df.columns:
                     dupes_unit = df[df.duplicated('Unit No', keep=False)]
                     if not dupes_unit.empty:
                         log(f"Duplicate Unit Nos found: {len(dupes_unit)}")
                         log(dupes_unit['Unit No'].value_counts().head())
                
                # Cross Reference
                log("\n=== Linkage Recovery Check ===")
                # Detailed Mismatch Analysis
                log("\n=== Detailed Mismatch Analysis ===")
                log("Active Lease Unit Numbers:")
                for l in active_leases:
                    log(f" - ID: {l.id}, Unit: '{l.unit_number}', Linked: {l.property_id}")

                log("\nSample DB Properties (Top 10):")
                sample_props = Property.query.limit(10).all()
                for p in sample_props:
                    log(f" - ID: {p.id}, Unit: '{p.unit_number}'")
                
                # Check duplicates in Excel
                if 'Unit Number' in df.columns:
                     dupes_unit = df[df.duplicated('Unit Number', keep=False)]
                     if not dupes_unit.empty:
                         log(f"\nDuplicate 'Unit Number' in Excel: {len(dupes_unit)}")
                         log(dupes_unit['Unit Number'].value_counts().head(10))
                # Search for specific missing units in DF
                log("\n=== Searching for 'P5' in Excel Data ===")
                # Convert all to string and search
                mask = df.apply(lambda x: x.astype(str).str.contains('P5', case=False, na=False)).any(axis=1)
                p5_rows = df[mask]
                if not p5_rows.empty:
                    log(f"Found {len(p5_rows)} rows containing 'P5':")
                    log(p5_rows.to_string())
                else:
                    log("No rows found containing 'P5'.")
            except Exception as e:
                log(f"Error reading Excel: {e}")

if __name__ == "__main__":
    analyze()
