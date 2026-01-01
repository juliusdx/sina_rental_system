
import sqlite3
import os

DB_PATH = 'instance/rental.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Attempting to create 'sst_exemption' table...")
    try:
        c.execute('''
            CREATE TABLE IF NOT EXISTS sst_exemption (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                description VARCHAR(200),
                evidence_file VARCHAR(200),
                created_at DATETIME,
                FOREIGN KEY(tenant_id) REFERENCES tenant(id)
            )
        ''')
        print("Successfully created 'sst_exemption' table.")
    except Exception as e:
        print(f"Error: {e}")
            
    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == '__main__':
    migrate()
