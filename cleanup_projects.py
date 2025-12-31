from app import create_app
from models import db, Property, Project

app = create_app()

with app.app_context():
    # Map Old Name -> New Name (Exact match for migration)
    # We will search for Destination Project by name.
    
    # Mapping: Bad Name -> Good Name
    migration_map = {
        'KC': 'Kolam Centre',
        'LAT 6': 'Latitud 6',
        'LEMB': 'Lembah Shantung',
        'MP1': 'Menggatal Plaza I',
        'MP2': 'Menggatal Plaza II',
        'SUR': 'Suria Shops',
        'P2 SHOPS': 'Elemen P2 Shops',
        'P2-A': 'Elemen P2', # Assumption: P2-A is part of Elemen P2
        'P2-B': 'Elemen P2', # Assumption
        'MISC': None, # Just check if empty
        'Test Property 1': None
    }
    
    print("Starting Project Cleanup...")
    
    for bad_name, good_name in migration_map.items():
        bad_proj = Project.query.filter_by(name=bad_name).first()
        if not bad_proj:
            continue
            
        print(f"Found Bad Project: {bad_name} (ID: {bad_proj.id})")
        
        # Find Good Project
        good_proj = None
        if good_name:
            good_proj = Project.query.filter_by(name=good_name).first()
        
        # Relink Properties
        props = Property.query.filter_by(project_id=bad_proj.id).all()
        if props:
            print(f"  - Relinking {len(props)} properties...")
            for p in props:
                if good_proj:
                    p.project_id = good_proj.id
                    p.project = good_proj.name # Ensure string consistency
                else:
                    # If no good project, just nullify or leave as is?
                    # If MISC and empty, ok.
                    print(f"  - Warning: No destination for {bad_name}, property {p.unit_number}")
                    p.project_id = None
        
        # Verify if safe to delete
        # Check again count
        remaining = Property.query.filter_by(project_id=bad_proj.id).count()
        if remaining == 0:
            print(f"  - Deleting {bad_name}...")
            db.session.delete(bad_proj)
        else:
            print(f"  - Error: Could not empty {bad_name}")
            
    db.session.commit()
    print("Cleanup Complete.")
