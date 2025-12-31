from app import create_app
from models import db, Property

app = create_app()

with app.app_context():
    print("Renaming 'Stall' to 'Acc. Parcel'...")
    
    # Update 'Stall' (case insensitive)
    # Using 'Acc. Parcel' as requested (user wrote "acc. parcel", I will capitalize for UI)
    
    # Find all variants
    props = Property.query.filter(Property.property_type.ilike('stall')).all()
    count = 0
    
    for p in props:
        p.property_type = 'Acc. Parcel'
        count += 1
        
    db.session.commit()
    print(f"Updated {count} properties from 'Stall' to 'Acc. Parcel'.")
