import sqlite3
import os

DB_PATH = os.path.join(os.getcwd(), 'instance', 'rental.db')
if not os.path.exists(DB_PATH):
    # Fallback if instance folder logic differs
    DB_PATH = 'rental.db'

print(f"Migrating database at: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def column_exists(table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns

try:
    # 1. Update Tenant Table
    print("Checking Tenant table...")
    if not column_exists('tenant', 'company_reg_no'):
        print("Adding company_reg_no to Tenant...")
        cursor.execute("ALTER TABLE tenant ADD COLUMN company_reg_no TEXT")
    
    if not column_exists('tenant', 'contact_person'):
        print("Adding contact_person to Tenant...")
        cursor.execute("ALTER TABLE tenant ADD COLUMN contact_person TEXT")

    # 2. Create Property Table
    print("Checking Property table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS property (
        id INTEGER PRIMARY KEY,
        project TEXT,
        unit_number TEXT NOT NULL UNIQUE,
        property_type TEXT,
        status TEXT DEFAULT 'vacant'
    )
    """)

    # 3. Update Lease Table
    print("Checking Lease table...")
    if not column_exists('lease', 'property_id'):
        print("Adding property_id to Lease...")
        cursor.execute("ALTER TABLE lease ADD COLUMN property_id INTEGER REFERENCES property(id)")

    conn.commit()
    print("Schema updates committed.")

    # 4. Seed Properties from Existing Leases
    print("Seeding properties from existing leases...")
    
    # Get all distinct properties mentioned in leases
    cursor.execute("SELECT DISTINCT project, unit_number FROM lease")
    existing_units = cursor.fetchall()
    
    count = 0
    for project, unit in existing_units:
        # Check if property exists
        cursor.execute("SELECT id FROM property WHERE unit_number = ?", (unit,))
        res = cursor.fetchone()
        
        prop_id = None
        if not res:
            # Create Property
            cursor.execute("INSERT INTO property (project, unit_number, property_type, status) VALUES (?, ?, ?, ?)",
                          (project, unit, 'Shop', 'occupied')) # Default to occupied since it comes from a lease
            prop_id = cursor.lastrowid
            count += 1
        else:
            prop_id = res[0]
            
        # Link Lease to Property (Backfill)
        cursor.execute("UPDATE lease SET property_id = ? WHERE unit_number = ?", (prop_id, unit))
        
    conn.commit()
    print(f"Seeded {count} new properties and linked leases.")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()

finally:
    conn.close()
