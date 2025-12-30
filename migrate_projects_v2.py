import sqlite3
import os

DB_PATH = 'instance/rental.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Create Project Table
        print("Creating Project table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS project (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description VARCHAR(200)
        )
        ''')

        # 2. Add Columns to Property (if they don't exist)
        print("Adding columns to Property table...")
        
        # Helper to safely add column
        def add_column(table, col_def):
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
                print(f"Added column {col_def}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e):
                    print(f"Column already exists: {col_def}")
                else:
                    raise e

        add_column('property', 'project_id INTEGER REFERENCES project(id)')
        add_column('property', 'target_rent FLOAT DEFAULT 0.0')
        add_column('property', 'bedrooms INTEGER DEFAULT 0')
        add_column('property', 'bathrooms INTEGER DEFAULT 0')
        add_column('property', 'image_path VARCHAR(200)')

        # 3. Backfill Projects from existing Property.project strings
        print("Backfilling Projects...")
        cursor.execute("SELECT DISTINCT project FROM property WHERE project IS NOT NULL AND project != ''")
        existing_projects = cursor.fetchall()
        
        for p_row in existing_projects:
            p_name = p_row[0]
            # Insert into Project if not exists
            cursor.execute("INSERT OR IGNORE INTO project (name) VALUES (?)", (p_name,))
            
            # Get the ID
            cursor.execute("SELECT id FROM project WHERE name = ?", (p_name,))
            p_id = cursor.fetchone()[0]
            
            # Update Properties
            cursor.execute("UPDATE property SET project_id = ? WHERE project = ?", (p_id, p_name))
            print(f"Linked properties in '{p_name}' to Project ID {p_id}")

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
