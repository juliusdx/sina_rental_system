import sys
import os

# Ensure we can import from root
sys.path.append(os.getcwd())

try:
    from app import create_app, db
    print("App imported.")
except Exception as e:
    print(f"Failed to import app: {e}")

try:
    from services.lhdn_service import LHDNService
    print("LHDNService class imported successfully.")
except Exception as e:
    print(f"Failed to import LHDNService: {e}")
    sys.exit(1)

app = create_app()
with app.app_context():
    try:
        service = LHDNService()
        print("LHDNService instantiated successfully.")
        
        # Test Validate TIN (simple call that uses config)
        # print(f"Checking Config: {service.config.client_id}")
    except Exception as e:
        print(f"Failed to instantiate LHDNService: {e}")
