from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file
from models import db, Invoice, InvoiceLineItem, Tenant, Receipt, Lease
from datetime import datetime, date
from flask_login import login_required, current_user
from routes.auth import role_required
from utils import get_tenant_unpaid_items, log_audit
from utils_sst import get_sst_amount_if_applicable
from io import BytesIO
from io import BytesIO

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/dashboard')
@billing_bp.route('/')
@login_required
def dashboard():
    from models import Tenant, Invoice, Receipt
    from sqlalchemy import func
    
    # Efficiently calculate balances
    # 1. Total Invoiced per Tenant
    invoiced_query = db.session.query(
        Invoice.tenant_id, 
        func.sum(Invoice.total_amount).label('total_invoiced')
    ).group_by(Invoice.tenant_id).all()
    invoiced_map = {row.tenant_id: row.total_invoiced for row in invoiced_query}
    
    # 2. Total Paid per Tenant
    paid_query = db.session.query(
        Receipt.tenant_id, 
        func.sum(Receipt.amount).label('total_paid')
    ).group_by(Receipt.tenant_id).all()
    paid_map = {row.tenant_id: row.total_paid for row in paid_query}
    
    # 3. Calculate Balances & Aggregates
    tenants = Tenant.query.filter_by(status='active').all()
    debtors = []
    global_outstanding = 0
    global_overdue = 0 # Approximate for now (complex to track exact overdue portion per invoice if partial payments exist)
    
    # For global overdue, we might just sum unpaid invoices with due_date < today
    # But that ignores partial payments. 
    # Better approach for "Overdue": Sum of (Invoice Amount - Paid against that invoice) for overdue invoices.
    # But our Receipt model isn't strictly linked to Invoice IDs (optional). 
    # Simplified approach: If Total Balance > 0, we consider it "Outstanding".
    
    for t in tenants:
        inv_total = invoiced_map.get(t.id, 0)
        paid_total = paid_map.get(t.id, 0)
        balance = inv_total - paid_total
        
        if balance > 0.01: # Filter small floating point diffs
            debtors.append({
                'id': t.id,
                'name': t.name,
                'balance': balance,
                'last_payment': None # Could query last receipt date if needed
            })
            global_outstanding += balance

    # Sort debtors by balance descending
    debtors.sort(key=lambda x: x['balance'], reverse=True)
    
    # Recent Invoices (Existing Logic)
    invoices = Invoice.query.order_by(Invoice.issue_date.desc()).limit(50).all()
    
    return render_template('billing/dashboard.html', 
                         invoices=invoices,
                         debtors=debtors,
                         stats={'outstanding': global_outstanding, 'debtors_count': len(debtors)})

@billing_bp.route('/demand_letter/<int:tenant_id>')
@login_required
@role_required('admin', 'legal', 'accounts')
def generate_demand_letter(tenant_id):
    tenant = Tenant.query.get_or_404(tenant_id)
    today = date.today()
    
    # Get Unpaid Items
    unpaid_items = get_tenant_unpaid_items(tenant.id)
    
    if not unpaid_items:
        flash(f"Tenant {tenant.name} has no outstanding payments.", "info")
        return redirect(url_for('billing.aging_report'))
        
    # Calculate Total & Max Overdue
    total_due = sum(i['unpaid_amount'] for i in unpaid_items)
    max_days_overdue = 0
    if unpaid_items:
        max_days_overdue = max((today - i['due_date']).days for i in unpaid_items)
        
    # Determine Letter Type/Severity
    severity = "Reminder"
    if max_days_overdue > 90:
        severity = "Final Notice"
    elif max_days_overdue > 30:
        severity = "Demand Letter"
        
    # Generate Printable HTML
    return render_template('billing/print_demand_letter.html', 
                         tenant=tenant,
                         items=unpaid_items,
                         total_due=total_due,
                         date=today,
                         severity=severity)

@billing_bp.route('/aging_report')
@login_required
@role_required('admin', 'accounts')
def aging_report():
    today = date.today()
    tenants = Tenant.query.filter_by(status='active').order_by(Tenant.name).all()
    
    report_data = []
    
    for t in tenants:
        unpaid_items = get_tenant_unpaid_items(t.id)
        if not unpaid_items:
            continue
            
        row = {
            'tenant': t,
            'total': 0,
            'current': 0,
            'd1_30': 0,
            'd31_60': 0,
            'd61_90': 0,
            'over_90': 0
        }
        
        for item in unpaid_items:
            amount = item['unpaid_amount']
            due_date = item['due_date']
            
            days_overdue = (today - due_date).days
            
            row['total'] += amount
            
            if days_overdue <= 0:
                row['current'] += amount
            elif days_overdue <= 30:
                row['d1_30'] += amount
            elif days_overdue <= 60:
                row['d31_60'] += amount
            elif days_overdue <= 90:
                row['d61_90'] += amount
            else:
                row['over_90'] += amount
                
        if row['total'] > 0.01:
            report_data.append(row)
            
    # Sort by Total Due Descending
    report_data.sort(key=lambda x: x['total'], reverse=True)
            
    return render_template('billing/aging.html', report=report_data)

@billing_bp.route('/invoices')
def list_invoices():
    query = Invoice.query
    
    # Filters
    status = request.args.get('status')
    if status:
        query = query.filter(Invoice.status == status)
        
    search = request.args.get('search')
    if search:
        term = f"%{search}%"
        query = query.join(Tenant).filter(
            db.or_(
                Tenant.name.ilike(term),
                Invoice.description.ilike(term),
                db.cast(Invoice.id, db.String).ilike(term)
            )
        )
        
    type_filter = request.args.get('type')
    if type_filter:
        # Join with LineItems to find invoices having this type
        query = query.join(InvoiceLineItem).filter(
            InvoiceLineItem.item_type.ilike(type_filter)
        ).distinct()

    # Sort
    invoices = query.order_by(Invoice.issue_date.desc(), Invoice.id.desc()).all()
    
    return render_template('billing/invoices.html', 
                         invoices=invoices, 
                         current_filters={
                             'status': status or '',
                             'search': search or '',
                             'type': type_filter or ''
                         })

@billing_bp.route('/generate_rent_preview')
def generate_rent_preview():
    # Helper to show who will be billed
    active_leases = Lease.query.join(Tenant).filter(Tenant.status == 'active').all()
    return jsonify([{
        'tenant': l.tenant.name,
        'unit': l.unit_number,
        'amount': l.rent_amount
    } for l in active_leases])

@billing_bp.route('/generate_rent', methods=['POST'])
@login_required
@role_required('admin', 'accounts')
def generate_rent():
    today = date.today()
    
    # Check for custom target date from modal
    target_date_str = request.form.get('target_date') # YYYY-MM
    if target_date_str:
        # e.g. "2026-01"
        try:
            year, month = map(int, target_date_str.split('-'))
            target_date = date(year, month, 1)
        except:
            target_date = date(today.year, today.month, 1)
    else:
        # Fallback Logic if no date provided (old behavior aligned with new logic?)
        # For safety, just use Today if not provided, or Default Logic?
        # Let's trust the form providing it. If not, default to current month 1st.
        target_date = date(today.year, today.month, 1)

    # Find all active leases
    active_leases = Lease.query.join(Tenant).filter(Tenant.status == 'active').all()
    
    count = 0
    skipped = 0
    description = f"Rent for {target_date.strftime('%B %Y')}"
    
    for lease in active_leases:
        if lease.rent_amount > 0:
            # Check for duplicate
            # Look for existing invoice for this tenant with same description
            existing = Invoice.query.filter_by(
                tenant_id=lease.tenant_id,
                description=description
            ).first()
            # Optionally check status to allow regenerating voided ones? 
            # For now, simplistic check: if it exists, skip.
            
            if existing:
                skipped += 1
                continue

            # Create Invoice Header
            inv = Invoice(
                tenant_id=lease.tenant_id,
                due_date=target_date, # Due on 1st of selected month
                description=description,
                total_amount=lease.rent_amount,
                status='unpaid'
            )
            db.session.add(inv)
            db.session.flush() # Get ID
            
            # Create Line Item
            item = InvoiceLineItem(
                invoice_id=inv.id,
                item_type='Rent',
                description=f"Monthly Rent ({lease.unit_number})",
                amount=lease.rent_amount
            )
            db.session.add(item)
            
            # --- SST Calculation ---
            import calendar
            last_day = calendar.monthrange(target_date.year, target_date.month)[1]
            period_end = date(target_date.year, target_date.month, last_day)
            
            sst_amount = get_sst_amount_if_applicable(lease.tenant, lease.rent_amount, target_date, period_start=target_date, period_end=period_end)
            if sst_amount > 0:
                sst_item = InvoiceLineItem(
                    invoice_id=inv.id,
                    item_type='sst',
                    description=f"Service Tax (8%)",
                    amount=sst_amount
                )
                db.session.add(sst_item)
                # Update Invoice Total
                inv.total_amount += sst_amount

            # --- Charge-back Expenses ---
            # Find unbilled expenses for this property meant for the tenant
            from models import PropertyExpense
            pending_expenses = PropertyExpense.query.filter_by(
                property_id=lease.property_id, 
                charge_tenant=True,
                tenant_invoice_id=None
            ).all()

            for exp in pending_expenses:
                # Add to invoice
                charge_item = InvoiceLineItem(
                    invoice_id=inv.id,
                    item_type='Chargeback', # or exp.expense_type
                    description=f"{exp.expense_type.replace('_', ' ').title()} - {exp.description or 'Reimbursement'}",
                    amount=exp.amount
                )
                db.session.add(charge_item)
                
                # Update Expense Record
                exp.tenant_invoice_id = inv.id
                
                # Update Total
                inv.total_amount += exp.amount

            count += 1
            
    db.session.commit()
    db.session.commit()
    
    if count > 0:
        log_audit('GENERATE', 'Invoice', 0, f"Generated {count} rent invoices for {target_date.strftime('%B %Y')}")
    
    msg = f"Generated {count} invoices for {target_date.strftime('%B %Y')}."
    if skipped > 0:
        msg += f" ({skipped} skipped as duplicates)"
        
    if count == 0 and skipped > 0:
        flash(f"No new invoices generated. All active tenants ({skipped}) already have invoices for {target_date.strftime('%B %Y')}.", "warning")
    elif count == 0:
        flash("No active leases found to bill.", "warning")
    else:
        flash(msg, "success")
        
    return redirect(url_for('billing.dashboard'))

@billing_bp.route('/prepare_late_fees')
def prepare_late_fees():
    # 1. Determine Assessment Date
    date_param = request.args.get('date')
    if date_param:
        assessment_date = datetime.strptime(date_param, '%Y-%m-%d').date()
    else:
        # Default: 8th of current month
        today = date.today()
        # If we are before the 8th, maybe default to *last* month's 8th? 
        # Or just current month's 8th even if future (user will see it's future)
        # Decision: Current Month 8th.
        try:
            assessment_date = date(today.year, today.month, 8)
        except ValueError: # e.g. Day out of range? Unlikely for 8
            assessment_date = today

    tenants = Tenant.query.filter_by(status='active').all()
    proposed_fees = []
    
    for t in tenants:
        unpaid_items = get_tenant_unpaid_items(t.id)
        
        # Calculate Penalty Base
        penalty_base = 0.0
        total_fee = 0.0
        details = []
        overdue_invoice_ids = []
        
        for item in unpaid_items:
            # Filter Logic:
            # 1. Must be 'rent' (or other penalty-attracting type)
            if item['type'].lower() != 'rent': continue
            
            # 2. Check Lateness relative to Assessment Date
            # Rule: Due on 1st. Late if not paid by 8th.
            # So if assessment_date >= 8th AND assessment_date >= item.due_date + 7 days
            
            due_date = item['due_date']
            # Calculate the "Late Trigger Date" for this specific item
            # If due date is 1st Jan -> Late on 8th Jan.
            # safe_grace_period = 7 days.
            # late_trigger = due_date + timedelta(days=7)
            from datetime import timedelta
            late_trigger = due_date + timedelta(days=7)
            
            if assessment_date >= late_trigger:
                # CHECK FOR DUPLICATES: Has a late fee already been charged for this specific Invoice ID?
                # We look for any line item of type 'late_fee' whose description contains "Ref: #{invoice_id}"
                # This relies on the convention established in apply_late_fees below.
                existing_fee = InvoiceLineItem.query.filter(
                    InvoiceLineItem.item_type == 'late_fee',
                    InvoiceLineItem.description.contains(f"#{item['invoice_id']}")
                ).first()
                
                if existing_fee:
                    continue

                # Calculate Pro-rated Fee
                # Formula: Outstanding * 8% * (Days Late / 365)
                # User Policy: Interest applies only to days AFTER the grace period (from 8th onwards)
                
                # late_trigger is Due Date + 7 days.
                # If Assessment is 21st, and Trigger is 8th: Days Late = 13.
                
                days_late = (assessment_date - late_trigger).days
                
                # Ensure we don't have negative days (though the if check handles this)
                if days_late < 1: days_late = 1
                
                item_fee = item['unpaid_amount'] * 0.08 * (days_late / 365.0)
                
                penalty_base += item['unpaid_amount'] # Total outstanding subject to penalty
                total_fee += item_fee
                
                details.append(f"{item['description']} (Due {due_date}, {days_late} days overdue)")
                overdue_invoice_ids.append(str(item['invoice_id']))
        
        if total_fee > 0:
            proposed_fees.append({
                'tenant_id': t.id,
                'name': t.name,
                'outstanding_rent': penalty_base,
                'fee_amount': total_fee,
                'details': "; ".join(details),
                'invoice_ids': ",".join(list(set(overdue_invoice_ids))) # Dedupe just in case
            })
            
    return render_template('billing/late_fees.html', fees=proposed_fees, assessment_date=assessment_date)

@billing_bp.route('/apply_late_fees', methods=['POST'])
@login_required
@role_required('admin', 'accounts')
def apply_late_fees():
    data = request.get_json()
    items = data.get('fees', [])
    today = date.today()
    
    count = 0
    for item in items:
        tenant_id = item['tenant_id']
        amount = float(item['amount'])
        invoice_ids = item.get('invoice_ids', '')
        
        if amount > 0:
            # Create Invoice for Late Fee
            inv = Invoice(
                tenant_id=tenant_id,
                due_date=today,
                description=f"Late Fee - {today.strftime('%B %Y')}",
                total_amount=amount,
                status='unpaid'
            )
            db.session.add(inv)
            db.session.flush()
            
            # Helper text for reference
            ref_text = f" (Ref: #{invoice_ids})" if invoice_ids else ""
            
            line = InvoiceLineItem(
                invoice_id=inv.id,
                item_type='late_fee',
                description=f"8% Late Fee on Outstanding Rent{ref_text}",
                amount=amount
            )
            db.session.add(line)
            count += 1
            
    db.session.commit()
    
    if count > 0:
        log_audit('GENERATE', 'Invoice', 0, f"Generated {count} late fee invoices")
        
    return jsonify({'status': 'success', 'count': count})

@billing_bp.route('/create_custom', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'accounts')
def create_custom():
    if request.method == 'GET':
        tenants = Tenant.query.order_by(Tenant.name).all()
        return render_template('billing/create_custom.html', tenants=tenants)
    
    # Handle POST (JSON or Form)
    data = request.get_json() if request.is_json else None
    if not data:
        # Fallback for simple form? No, let's enforce JS submission for multi-line
        return "Invalid Data", 400
        
    tenant_id = data.get('tenant_id')
    due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()
    items = data.get('items', [])
    
    current_app_title = "Ad-hoc Invoice" # Could be dynamic
    
    total = sum(float(i['amount']) for i in items)
    
    inv = Invoice(
        tenant_id=tenant_id,
        due_date=due_date,
        description=data.get('description', 'Custom Invoice'),
        total_amount=total,
        status='unpaid'
    )
    db.session.add(inv)
    db.session.flush()
    
    for i in items:
        line = InvoiceLineItem(
            invoice_id=inv.id,
            item_type=i.get('type', 'General'),
            description=i.get('description'),
            amount=float(i['amount'])
        )
        db.session.add(line)
        
    db.session.commit()
    log_audit('CREATE', 'Invoice', inv.id, f"Created custom invoice for Tenant {tenant_id}, Amount: {total}")
    return jsonify({'status': 'success', 'invoice_id': inv.id})

@billing_bp.route('/receipts')
def receipts():
    receipts = Receipt.query.order_by(Receipt.date_received.desc()).all()
    return render_template('billing/receipts.html', receipts=receipts)

@billing_bp.route('/invoice/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'accounts')
def edit_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    
    if request.method == 'GET':
        return render_template('billing/edit_invoice.html', invoice=invoice)
        
    data = request.get_json()
    if not data:
        return "Invalid Data", 400
        
    # Update Header
    invoice.due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()
    invoice.description = data.get('description')
    
    # Update Items: Strategy is Delete All -> Re-add (Simpler than diffing)
    InvoiceLineItem.query.filter_by(invoice_id=invoice.id).delete()
    
    items = data.get('items', [])
    total = 0
    for i in items:
        amt = float(i['amount'])
        total += amt
        line = InvoiceLineItem(
            invoice_id=invoice.id,
            item_type=i.get('type', 'General'),
            description=i.get('description'),
            amount=amt
        )
        db.session.add(line)
    
    invoice.total_amount = total
    db.session.commit()
    return jsonify({'status': 'success'})

@billing_bp.route('/invoice/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'accounts')
def delete_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    if invoice.status == 'paid':
        return "Cannot delete paid invoice", 400
        
    db.session.delete(invoice)
    db.session.commit()
    log_audit('DELETE', 'Invoice', id, "Deleted invoice")
    flash('Invoice deleted.')
    return jsonify({'status': 'success'})

@billing_bp.route('/invoices/bulk_delete', methods=['POST'])
@login_required
@role_required('admin', 'accounts')
def bulk_delete_invoices():
    data = request.get_json()
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'status': 'error', 'message': 'No items selected'}), 400
        
    # Filter out paid invoices for safety
    # Find invoices
    invoices = Invoice.query.filter(Invoice.id.in_(ids)).all()
    
    deleted_count = 0
    skipped_count = 0
    
    for inv in invoices:
        if inv.status == 'paid':
            skipped_count += 1
            continue
            
        db.session.delete(inv)
        deleted_count += 1
        
    db.session.commit()
    
    if deleted_count > 0:
        log_audit('DELETE', 'Invoice', 0, f"Bulk deleted {deleted_count} invoices")
        
    msg = f"Deleted {deleted_count} invoices."
    if skipped_count > 0:
        msg += f" (Skipped {skipped_count} paid invoices)"
        
    flash(msg, 'success' if deleted_count > 0 else 'warning')
    return jsonify({'status': 'success', 'message': msg})

@billing_bp.route('/receive_payment', methods=['POST'])
@login_required
@role_required('admin', 'accounts')
def receive_payment():
    data = request.get_json()
    if not data:
        return "Invalid Data", 400
        
    invoice_id = data.get('invoice_id')
    amount = float(data.get('amount', 0))
    date_str = data.get('date')
    payment_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    reference = data.get('reference')
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Create Receipt
    receipt = Receipt(
        tenant_id=invoice.tenant_id,
        invoice_id=invoice.id,
        amount=amount,
        date_received=payment_date,
        reference=reference
    )
    db.session.add(receipt)
    
    # Update Status
    # Calculate total paid including the new receipt (not yet committed but in session)
    # To be safe, flush first so it's queryable or sum manually
    db.session.flush()
    
    update_invoice_status(invoice)
    
    db.session.commit()
    log_audit('CREATE', 'Receipt', receipt.id, f"Received payment of {amount} for Invoice #{invoice.id}")
    flash('Payment recorded successfully.')
    return jsonify({'status': 'success'})

@billing_bp.route('/receipt/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'accounts')
def delete_receipt(id):
    receipt = Receipt.query.get_or_404(id)
    invoice_id = receipt.invoice_id # Store ID before deletion
    
    db.session.delete(receipt)
    db.session.commit() # Commit deletion first to ensure it's gone from DB
    
    # Re-fetch invoice and update status
    if invoice_id:
        invoice = Invoice.query.get(invoice_id)
        if invoice:
            update_invoice_status(invoice)
            db.session.commit() # Commit status update
            
    log_audit('DELETE', 'Receipt', id, "Deleted payment receipt")
            
    flash('Receipt deleted.')
    return jsonify({'status': 'success'})

def update_invoice_status(invoice):
    total_paid = db.session.query(db.func.sum(Receipt.amount)).filter(Receipt.invoice_id == invoice.id).scalar() or 0
    
    if total_paid >= invoice.total_amount - 0.01:
        invoice.status = 'paid'
    elif total_paid > 0:
        invoice.status = 'partial'
    else:
        invoice.status = 'unpaid'

@billing_bp.route('/statement/<int:tenant_id>')
def tenant_statement(tenant_id):
    tenant = Tenant.query.get_or_404(tenant_id)
    
    # Fetch Invoices and Receipts
    invoices = Invoice.query.filter_by(tenant_id=tenant_id).all()
    receipts = Receipt.query.filter_by(tenant_id=tenant_id).all()
    
    # Combine into a ledger
    ledger = []
    for inv in invoices:
        ledger.append({
            'date': inv.issue_date,
            'type': 'Invoice',
            'ref': f"#{inv.id}",
            'desc': inv.description,
            'debit': inv.total_amount,
            'credit': 0,
            'obj': inv
        })
        
    for r in receipts:
        ledger.append({
            'date': r.date_received,
            'type': 'Payment',
            'ref': f"R-{r.id}",
            'desc': f"Ref: {r.reference}" if r.reference else "Payment",
            'debit': 0,
            'credit': r.amount,
            'obj': r
        })
        
    # Sort by date
    ledger.sort(key=lambda x: x['date'])
    
    # Calculate Running Balance
    balance = 0
    for entry in ledger:
        balance += entry['debit'] - entry['credit']
        entry['balance'] = balance
        
    return render_template('billing/statement.html', tenant=tenant, ledger=ledger, balance=balance)

@billing_bp.route('/invoice/<int:id>/pdf')
def download_invoice_pdf(id):
    invoice = Invoice.query.get_or_404(id)
    # Render HTML for printing instead of PDF
    return render_template('billing/print_invoice.html', invoice=invoice)

@billing_bp.route('/receipt/<int:id>/pdf')
def download_receipt_pdf(id):
    receipt = Receipt.query.get_or_404(id)
    # Render HTML for printing instead of PDF
    return render_template('billing/print_receipt.html', receipt=receipt)
