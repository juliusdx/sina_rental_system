import base64
import json
from services.lhdn_service import LHDNService
from app import app

def debug_identity():
    print("--- LHDN Identity Debugger ---")
    with app.app_context():
        try:
            service = LHDNService()
            print(f"Environment: {'Production' if service.is_prod else 'Sandbox'}")
            print("Authenticating...")
            token = service.get_access_token()
            print("Token received.")
            
            # Decode JWT (Parts: Header.Payload.Signature)
            parts = token.split('.')
            if len(parts) == 3:
                payload = parts[1]
                # Pad base64
                payload += '=' * (-len(payload) % 4)
                decoded = base64.b64decode(payload)
                claims = json.loads(decoded)
                
                print("\n--- Token Claims ---")
                print(json.dumps(claims, indent=2))
                
                tin = claims.get('sub') or claims.get('tin') or "Unknown"
                print(f"\nEXTRACTED TIN: {tin}")
                
            else:
                print("Token is not a valid JWT format.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    debug_identity()
