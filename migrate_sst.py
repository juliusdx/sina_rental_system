
import sqlite3
import os

DB_PATH = 'instance/rental.db'

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Attempting to add 'charge_sst' column to 'tenant' table...")
        cursor.execute("ALTER TABLE tenant ADD COLUMN charge_sst BOOLEAN DEFAULT 0")
        print("Successfully added 'charge_sst' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("'charge_sst' column already exists.")
        else:
            print(f"Error adding column: {e}")
            conn.close()
            return

    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == '__main__':
    run_migration()
