
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

def check_schema():
    with app.app_context():
        print("--- Lease Indices ---")
        indices = db.session.execute(text("PRAGMA index_list('lease')")).fetchall()
        for idx in indices:
            print(f"Index: {idx.name} (Unique: {idx.unique})")
            cols = db.session.execute(text(f"PRAGMA index_info('{idx.name}')")).fetchall()
            print(f"  Columns: {[c.name for c in cols]}")

        print("\n--- Tenant Indices ---")
        indices = db.session.execute(text("PRAGMA index_list('tenant')")).fetchall()
        for idx in indices:
            print(f"Index: {idx.name} (Unique: {idx.unique})")
            cols = db.session.execute(text(f"PRAGMA index_info('{idx.name}')")).fetchall()
            print(f"  Columns: {[c.name for c in cols]}")

if __name__ == "__main__":
    check_schema()
