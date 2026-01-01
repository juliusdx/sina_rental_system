from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE property ADD COLUMN land_size FLOAT"))
            conn.commit()
        print("Migration successful: Added land_size column.")
    except Exception as e:
        print(f"Migration failed (Column might exist): {e}")
