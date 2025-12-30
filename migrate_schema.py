
from app import create_app, db
from sqlalchemy import text

def run_migration():
    app = create_app()
    with app.app_context():
        print("Migrating Schema...")
        try:
            # Check if columns exist first (idempotent)
            # SQLite specific check
            conn = db.engine.connect()
            result = conn.execute(text("PRAGMA table_info(property)"))
            columns = [row[1] for row in result.fetchall()] # column name is index 1
            
            if 'block' not in columns:
                print("Adding 'block' column...")
                conn.execute(text("ALTER TABLE property ADD COLUMN block VARCHAR(50)"))
            else:
                print("'block' column already exists.")

            if 'unit' not in columns:
                print("Adding 'unit' column...")
                conn.execute(text("ALTER TABLE property ADD COLUMN unit VARCHAR(50)"))
            else:
                print("'unit' column already exists.")
                
            if 'floor' not in columns:
                print("Adding 'floor' column...")
                conn.execute(text("ALTER TABLE property ADD COLUMN floor VARCHAR(50)"))
            else:
                print("'floor' column already exists.")
                
            conn.commit()
            conn.close()
            print("Schema Migration Complete.")
            
        except Exception as e:
            print(f"Migration Failed: {e}")

if __name__ == "__main__":
    run_migration()
