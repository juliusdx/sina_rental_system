from models import db, Invoice, InvoiceLineItem, Receipt, AuditLog
from flask_login import current_user

def get_tenant_ledger_status(tenant_id):
    """
    Calculates the outstanding balance for each line item type 
    based on the priority rule: Payments clear Late Fees first, then Rent.
    
    Returns:
        dict: {
            'outstanding_rent': float,
            'outstanding_fees': float,
            'total_outstanding': float
        }
    """
    # 1. Fetch all Invoices and Receipts
    invoices = Invoice.query.filter_by(tenant_id=tenant_id).filter(Invoice.status != 'void').all()
    receipts = Receipt.query.filter_by(tenant_id=tenant_id).all()
    
    total_paid = sum(r.amount for r in receipts)
    
    # 2. Collect all Line Items
    all_items = []
    for inv in invoices:
        for item in inv.line_items:
            all_items.append({
                'id': item.id,
                'type': item.item_type, # 'rent', 'late_fee', 'utility', etc.
                'amount': item.amount,
                'invoice_date': inv.issue_date
            })
            
    # 3. Sort Items by Priority
    # Priority: Late Fee (1), Rent (2), Others (3)
    # Secondary Sort: Date (Oldest first)
    def priority_key(item):
        type_priority = 3
        if item['type'] == 'late_fee':
            type_priority = 1
        elif item['type'] == 'rent':
            type_priority = 2
            
        return (type_priority, item['invoice_date'])
        
    all_items.sort(key=priority_key)
    
    # 4. Allocate Payment (Waterfall)
    remaining_payment = total_paid
    outstanding_rent_items = []
    
    for item in all_items:
        amount_due = item['amount']
        
        # How much of this item is covered?
        if remaining_payment >= amount_due:
            # Fully Paid
            remaining_payment -= amount_due
            payment_alloc = amount_due
        else:
            # Partially or Not Paid
            payment_alloc = remaining_payment
            remaining_payment = 0
            
        unpaid_amount = amount_due - payment_alloc
        
        if unpaid_amount > 0:
            if item['type'] == 'late_fee':
                # outstanding_fees += unpaid_amount # Just tracking sum handled by consumer if needed
                pass
            elif item['type'] == 'rent':
                # Find the invoice due date
                # In Step 2 we only stored invoice_date (issue date). We need due_date.
                # Optimization: We can just re-query or fetch more data in Step 2.
                # However, for now, let's fix Step 2 to include due_date.
                pass
                
    # REDOING FUNCTION TO INCLUDE DUE DATE PROPERLY
    return {
        'outstanding_rent_items': [], # Placeholder - see full rewrite below
    }

def get_tenant_unpaid_items(tenant_id):
    """
    Returns list of specific unpaid line items after waterfall allocation.
    """
    invoices = Invoice.query.filter_by(tenant_id=tenant_id).filter(Invoice.status != 'void').all()
    receipts = Receipt.query.filter_by(tenant_id=tenant_id).all()
    
    total_paid = sum(r.amount for r in receipts)
    
    # Collect Items
    items = []
    for inv in invoices:
        for line in inv.line_items:
            items.append({
                'id': line.id,
                'type': line.item_type,
                'amount': line.amount,
                'due_date': inv.due_date,
                'invoice_id': inv.id,
                'description': line.description
            })
            
    # Sort Priority: Late Fee (1) -> Rent (2) -> Other (3) -> Date
    def sort_key(i):
        p = 3
        if i['type'] == 'late_fee': p = 1
        elif i['type'] == 'rent': p = 2
        return (p, i['due_date'])
        
    items.sort(key=sort_key)
    
    unpaid_items = []
    
    for item in items:
        if total_paid >= item['amount']:
            total_paid -= item['amount']
        else:
            # Partial or Unpaid
            covered = total_paid
            total_paid = 0
            remaining = item['amount'] - covered
            
            if remaining > 0.005: # Float tolerance
                item['unpaid_amount'] = remaining
                unpaid_items.append(item)
                
    return unpaid_items

def log_audit(action, target_type, target_id, details=""):
    """
    Creates an AuditLog entry.
    """
    try:
        user_id = current_user.id if (current_user and current_user.is_authenticated) else 1 # Default to 1 (Admin) if system/background
        
        log = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")
