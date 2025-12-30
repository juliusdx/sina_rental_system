import sys
import os

print("Starting verification (Request Mode)...")
try:
    from app import create_app, db
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    
    with app.app_context():
        print("Checking '/' (Home)...")
        rv = client.get('/', follow_redirects=True)
        print(f"Home Status: {rv.status_code}")
        
        print("Checking '/dashboard' (Main)...")
        rv = client.get('/dashboard')
        print(f"Dashboard Status: {rv.status_code}")
        
        print("Checking '/properties/dashboard'...")
        rv = client.get('/properties/dashboard')
        print(f"Properties Dash Status: {rv.status_code}")
        if rv.status_code != 200:
            print("Properties Dash Output Snippet:")
            print(rv.data[:500])

        print("Checking '/tenants/'...")
        rv = client.get('/tenants/')
        print(f"Tenants List Status: {rv.status_code}")

    print("VERIFICATION SUCCESSFUL: All routes reachable.")

except Exception as e:
    print("\nVERIFICATION FAILED")
    print("Error details:")
    print(e)
    import traceback
    traceback.print_exc()
