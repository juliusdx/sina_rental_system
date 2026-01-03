import sqlite3
import os

DB_PATH = os.path.join('instance', 'rental.db')

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Starting LHDN e-Invoice Migration...")

        # 1. Update Tenant Table
        print("Migrating Tenant table...")
        tenant_columns = [
            ("classification_code", "TEXT DEFAULT '000'"),
            ("e_invoice_enabled", "BOOLEAN DEFAULT 1"), # SQLite uses 1 for True
        ]
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(tenant)")
        existing_cols = [row[1] for row in cursor.fetchall()]

        for col_name, col_type in tenant_columns:
            if col_name not in existing_cols:
                print(f"Adding '{col_name}' to tenant table.")
                cursor.execute(f"ALTER TABLE tenant ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column '{col_name}' already exists in tenant table.")

        # 2. Update Invoice Table
        print("Migrating Invoice table...")
        invoice_columns = [
            ("lhdn_uuid", "TEXT"), # SQLite ALTER TABLE can't add UNIQUE. We'll add index later if needed.
            ("lhdn_submission_uid", "TEXT"),
            ("lhdn_long_id", "TEXT"),
            ("lhdn_status", "TEXT DEFAULT 'Pending'"),
            ("lhdn_validation_url", "TEXT"),
            ("lhdn_submission_date", "DATETIME"),
            ("lhdn_type_code", "TEXT DEFAULT '01'"),
        ]

        cursor.execute("PRAGMA table_info(invoice)")
        existing_cols_inv = [row[1] for row in cursor.fetchall()]

        for col_name, col_type in invoice_columns:
            if col_name not in existing_cols_inv:
                print(f"Adding '{col_name}' to invoice table.")
                try:
                    cursor.execute(f"ALTER TABLE invoice ADD COLUMN {col_name} {col_type}")
                except Exception as e:
                     # UNIQUE constraint might fail on ADD COLUMN in some sqlite versions if not careful with syntax
                     # But basic TEXT UNIQUE usually works or we ignore error if needed
                     print(f"Warning adding {col_name}: {e}")
            else:
                print(f"Column '{col_name}' already exists in invoice table.")

        # 3. Create MyInvoisConfig Table
        print("Creating MyInvoisConfig table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS my_invois_config (
            id INTEGER PRIMARY KEY,
            environment VARCHAR(20) DEFAULT 'sandbox',
            client_id VARCHAR(200),
            client_secret VARCHAR(200),
            issuer_tin VARCHAR(50),
            issuer_msic VARCHAR(10),
            digital_certificate_path VARCHAR(200),
            certificate_password VARCHAR(200),
            updated_at DATETIME
        )
        """)

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
