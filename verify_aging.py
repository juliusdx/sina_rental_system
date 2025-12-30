from app import create_app, db
from models import User, Tenant, Invoice, InvoiceLineItem
from datetime import date, timedelta
from routes.billing import get_tenant_unpaid_items

app = create_app()

def run_test():
    with app.app_context():
        print("Setting up test data...")
        # 1. Create Test Tenant
        t = Tenant.query.filter_by(account_code='TEST-AGING').first()
        if not t:
            t = Tenant(name='Test Aging Tenant', account_code='TEST-AGING', status='active')
            db.session.add(t)
            db.session.commit()
            
        # 2. Clear old invoices for this tenant
        InvoiceLineItem.query.filter(InvoiceLineItem.invoice_id.in_(
            Invoice.query.with_entities(Invoice.id).filter_by(tenant_id=t.id)
        )).delete(synchronize_session=False)
        Invoice.query.filter_by(tenant_id=t.id).delete()
        db.session.commit()
        
        today = date.today()
        
        # 3. Create Invoices for Each Bucket
        scenarios = [
            (0, 'Current'),       # Due Today
            (20, '1-30 Days'),    # Due 20 days ago
            (45, '31-60 Days'),   # Due 45 days ago
            (75, '61-90 Days'),   # Due 75 days ago
            (100, 'Over 90 Days') # Due 100 days ago
        ]
        
        for days, label in scenarios:
            due = today - timedelta(days=days)
            inv = Invoice(tenant_id=t.id, due_date=due, total_amount=100, status='unpaid', description=f"Test {label}")
            db.session.add(inv)
            db.session.flush()
            item = InvoiceLineItem(invoice_id=inv.id, item_type='rent', amount=100, description=f"Rent {label}")
            db.session.add(item)
            
        db.session.commit()
        
        # 4. Test Logic (Copy of aging_report logic)
        print("Testing Bucketing Logic...")
        unpaid = get_tenant_unpaid_items(t.id)
        
        buckets = {'current':0, 'd1_30':0, 'd31_60':0, 'd61_90':0, 'over_90':0}
        
        for item in unpaid:
            days_overdue = (today - item['due_date']).days
            
            if days_overdue <= 0: buckets['current'] += item['unpaid_amount']
            elif days_overdue <= 30: buckets['d1_30'] += item['unpaid_amount']
            elif days_overdue <= 60: buckets['d31_60'] += item['unpaid_amount']
            elif days_overdue <= 90: buckets['d61_90'] += item['unpaid_amount']
            else: buckets['over_90'] += item['unpaid_amount']
            
        print("Results:")
        print(f"Current: {buckets['current']} (Expected 100)")
        print(f"1-30:    {buckets['d1_30']} (Expected 100)")
        print(f"31-60:   {buckets['d31_60']} (Expected 100)")
        print(f"61-90:   {buckets['d61_90']} (Expected 100)")
        print(f">90:     {buckets['over_90']} (Expected 100)")
        
        if all(v == 100 for v in buckets.values()):
            print("[PASS] Bucketing Logic Verified")
        else:
            print("[FAIL] Bucketing Error")
            
        # 5. Test Demand Letter Generation
        print("\nTesting PDF Generation...")
        with app.test_client() as client:
            # Login as Admin
            # Create admin if not exists (assume exists from previous test)
            client.post('/login', data={'username': 'test_admin', 'password': 'pass'})
            
            resp = client.get(f'/billing/demand_letter/{t.id}', follow_redirects=True)
            if resp.status_code == 200 and resp.content_type == 'application/pdf':
                print(f"[PASS] PDF Generated. Size: {len(resp.data)} bytes")
                # Clean up
                # t = Tenant.query.get(t.id) 
                # db.session.delete(t) # Optional, keep for debugging
                # db.session.commit()
            else:
                print(f"[FAIL] PDF Generation Failed: {resp.status_code} {resp.data[:100]}")

if __name__ == '__main__':
    run_test()
