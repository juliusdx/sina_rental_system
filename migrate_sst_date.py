
import sqlite3
import os

DB_PATH = 'instance/rental.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Attempting to add 'sst_start_date' column to 'tenant' table...")
    try:
        c.execute("ALTER TABLE tenant ADD COLUMN sst_start_date DATE")
        print("Successfully added 'sst_start_date' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'sst_start_date' already exists.")
        else:
            print(f"Error: {e}")
            
    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == '__main__':
    migrate()
