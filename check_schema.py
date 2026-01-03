import sqlite3
import os

DB_PATH = os.path.join('instance', 'rental.db')

def check_schema():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Checking Invoice Table Columns:")
    cursor.execute("PRAGMA table_info(invoice)")
    columns = cursor.fetchall()
    
    found_uuid = False
    for col in columns:
        print(col)
        if col[1] == 'lhdn_uuid':
            found_uuid = True
            
    if found_uuid:
        print("\nSUCCESS: 'lhdn_uuid' column found.")
    else:
        print("\nFAILURE: 'lhdn_uuid' column NOT found.")
        
    conn.close()

if __name__ == "__main__":
    check_schema()
