import base64
import json
import requests
from datetime import datetime, timedelta

# Standalone Debug Script (No Flask/DB dependencies)
class MockConfig:
    client_id = "e622efa9-fdca-4bd3-aab6-adce71d363d4"
    client_secret = "de998802-a44f-4dd4-b3f5-ea6adb0cf975"

def get_token_and_tin():
    url = "https://preprod-api.myinvois.hasil.gov.my/connect/token"
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'client_id': MockConfig.client_id,
        'client_secret': MockConfig.client_secret,
        'grant_type': 'client_credentials',
        'scope': 'InvoicingAPI' 
    }
    
    print("Requesting Token...")
    try:
        res = requests.post(url, data=data, headers=headers)
        res.raise_for_status()
        token = res.json()['access_token']
        print("Token Received.")
        
        # Decode
        parts = token.split('.')
        payload = parts[1]
        payload += '=' * (-len(payload) % 4)
        decoded = base64.b64decode(payload)
        claims = json.loads(decoded)
        
        print("\n--- CLAIMS ---")
        tin = claims.get('sub') or claims.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier')
        print(f"Sub: {claims.get('sub')}")
        print(f"Run-as: {claims.get('run_as')}") # Sometimes TIN is here? No.
        print(json.dumps(claims, indent=2))
        
        # Look for TIN
        # Usually it is the SUBJECT? Or we can deduce it.
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_token_and_tin()
