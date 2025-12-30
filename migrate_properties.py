"""
Simple standalone script to add columns to Property table
This doesn't import the app to avoid the syntax error issue
"""
import sqlite3
import os

# Check both possible database paths
DB_PATHS = ['instance/rental.db', 'rental_data.db']
DB_PATH = None

for path in DB_PATHS:
    if os.path.exists(path):
        DB_PATH = path
        break

if not DB_PATH:
    print("❌ No database file found!")
    print(f"Looked for: {DB_PATHS}")
    exit(1)

print(f"Using database: {DB_PATH}\n")

def add_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get existing columns
        cursor.execute("PRAGMA table_info(property)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns: {columns}\n")
        
        # Add missing columns
        if 'archived' not in columns:
            print("Adding 'archived' column...")
            cursor.execute("ALTER TABLE property ADD COLUMN archived BOOLEAN DEFAULT 0")
            print("✓ Added 'archived'")
        else:
            print("✓ 'archived' already exists")
        
        if 'archived_date' not in columns:
            print("Adding 'archived_date' column...")
            cursor.execute("ALTER TABLE property ADD COLUMN archived_date DATETIME")
            print("✓ Added 'archived_date'")
        else:
            print("✓ 'archived_date' already exists")
        
        if 'size_sqft' not in columns:
            print("Adding 'size_sqft' column...")
            cursor.execute("ALTER TABLE property ADD COLUMN size_sqft REAL")
            print("✓ Added 'size_sqft'")
        else:
            print("✓ 'size_sqft' already exists")
        
        if 'notes' not in columns:
            print("Adding 'notes' column...")
            cursor.execute("ALTER TABLE property ADD COLUMN notes TEXT")
            print("✓ Added 'notes'")
        else:
            print("✓ 'notes' already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("You can now restart your Flask server.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_columns()
