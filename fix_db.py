import sqlite3
import os

db_path = os.path.join('instance', 'rental.db')

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists to be safe
    cursor.execute("PRAGMA table_info(lease)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'agreement_file' in columns:
        print("Column 'agreement_file' already exists in table 'lease'.")
    else:
        print("Adding column 'agreement_file' to table 'lease'...")
        cursor.execute("ALTER TABLE lease ADD COLUMN agreement_file VARCHAR(200)")
        conn.commit()
        print("Success: Column added.")

    conn.close()

except Exception as e:
    print(f"An error occurred: {e}")
