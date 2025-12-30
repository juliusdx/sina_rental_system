from app import create_app, db
from models import Agent, Commission
import sqlalchemy

app = create_app()

def migrate():
    with app.app_context():
        # Create tables if they don't exist
        engine = db.engine
        inspector = sqlalchemy.inspect(engine)
        
        tables = inspector.get_table_names()
        
        if 'agent' not in tables:
            print("Creating 'agent' table...")
            Agent.__table__.create(engine)
            print("Done.")
        else:
            print("'agent' table already exists.")
            
        if 'commission' not in tables:
            print("Creating 'commission' table...")
            Commission.__table__.create(engine)
            print("Done.")
        else:
            print("'commission' table already exists.")

if __name__ == '__main__':
    migrate()
