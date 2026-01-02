from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        # Get existing columns to avoid duplicate errors
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('property')]
        
        new_columns = [
            ('expected_quit_rent', 'FLOAT DEFAULT 0.0'),
            ('expected_assessment', 'FLOAT DEFAULT 0.0'),
            ('expected_fire_insurance', 'FLOAT DEFAULT 0.0'),
            ('expected_management_fee', 'FLOAT DEFAULT 0.0'),
            ('expected_sinking_fund', 'FLOAT DEFAULT 0.0'),
            ('expected_water', 'FLOAT DEFAULT 0.0')
        ]
        
        with db.engine.connect() as conn:
            for col_name, col_type in new_columns:
                if col_name not in columns:
                    print(f"Adding column {col_name}...")
                    try:
                        conn.execute(text(f'ALTER TABLE property ADD COLUMN {col_name} {col_type}'))
                        print(f"Successfully added {col_name}")
                    except Exception as e:
                        print(f"Error adding {col_name}: {str(e)}")
                else:
                    print(f"Column {col_name} already exists.")
            
            conn.commit()

if __name__ == '__main__':
    migrate()
