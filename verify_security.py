from app import create_app, db
from models import User, AuditLog, Invoice
from flask import url_for
from werkzeug.security import generate_password_hash

app = create_app()

def run_test():
    with app.app_context():
        # Setup: Create Users
        # Admin
        admin = User.query.filter_by(username='test_admin').first()
        if not admin:
            admin = User(username='test_admin', password_hash=generate_password_hash('pass'), role='admin')
            db.session.add(admin)
            
        # Legal (Restricted)
        legal = User.query.filter_by(username='test_legal').first()
        if not legal:
            legal = User(username='test_legal', password_hash=generate_password_hash('pass'), role='legal')
            db.session.add(legal)
            
        db.session.commit()
        
        # Test 1: Admin Access to Audit Logs
        with app.test_client() as client:
            client.post('/login', data={'username': 'test_admin', 'password': 'pass'})
            resp = client.get('/audit_logs', follow_redirects=True)
            if resp.status_code == 200 and b'System Audit Log' in resp.data:
                print("[PASS] Admin can access Audit Logs")
            else:
                print(f"[FAIL] Admin failed access Audit Logs: {resp.status_code}")
                
        # Test 2: Legal Access to Generate Rent (Should Fail/Redirect)
        with app.test_client() as client:
            client.post('/login', data={'username': 'test_legal', 'password': 'pass'})
            # /generate_rent is POST usually
            resp = client.post('/billing/generate_rent', follow_redirects=False)
            
            # Expect Redirect to dashboard (302)
            if resp.status_code == 302 and 'dashboard' in resp.location:
                print("[PASS] Legal user redirected from /generate_rent")
            else:
                print(f"[FAIL] Legal user NOT redirected properly: {resp.status_code}")

        # Test 3: Audit Logging Trigger
        # Log in as Admin and delete a fake invoice (if we can create one easily)
        # Or easier: Access 'create_custom' endpoint if we can mock JSON
        with app.test_client() as client:
            client.post('/login', data={'username': 'test_admin', 'password': 'pass'})
            
            # Create a dummy invoice logic (simplified, calling create_custom)
            # We need a tenant first
            from models import Tenant
            tenant = Tenant.query.first()
            if not tenant:
                print("[SKIP] No tenant found for Audit Log test")
            else:
                initial_count = AuditLog.query.count()
                
                # Mock call to create_custom
                import json
                data = {
                    'tenant_id': tenant.id,
                    'due_date': '2025-01-01',
                    'items': [{'amount': 100, 'description': 'Audit Test Item'}],
                    'description': 'Audit Test Invoice'
                }
                resp = client.post('/billing/create_custom', 
                                 data=json.dumps(data),
                                 content_type='application/json')
                
                if resp.status_code == 200:
                    final_count = AuditLog.query.count()
                    if final_count > initial_count:
                        print("[PASS] Audit Log entry created")
                        # Verify details
                        last_log = AuditLog.query.order_by(AuditLog.id.desc()).first()
                        print(f"       Log Entry: {last_log.action} on {last_log.target_type} #{last_log.target_id}")
                    else:
                        print("[FAIL] Audit Log count did not increase")
                else:
                    print(f"[FAIL] Failed to create custom invoice: {resp.status_code}")

if __name__ == '__main__':
    run_test()
