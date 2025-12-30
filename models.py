from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False) # 'admin', 'coordinator', 'accounts', 'legal'

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False) # e.g. 'DELETE', 'UPDATE', 'CREATE'
    target_type = db.Column(db.String(50)) # e.g. 'Invoice', 'Tenant'
    target_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_code = db.Column(db.String(50)) # Added from Rental Source
    company_reg_no = db.Column(db.String(50)) # New: SSM/Reg No
    contact_person = db.Column(db.String(100)) # New: PIC Name
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='active') # active, past, evicted

    # E-Invoice / Company Details
    is_sst_registered = db.Column(db.Boolean, default=False)
    sst_registration_number = db.Column(db.String(50))
    tax_identification_number = db.Column(db.String(50)) # TIN
    msic_code = db.Column(db.String(10))
    business_activity = db.Column(db.String(200))

    # Billing Address
    address_line_1 = db.Column(db.String(200))
    address_line_2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    postcode = db.Column(db.String(20))
    
    # Relationships
    notes = db.relationship('TenantNote', backref='tenant', lazy=True, cascade="all, delete-orphan")

    @property
    def outstanding_balance(self):
        # Calculate Total Invoiced
        invoices = Invoice.query.filter_by(tenant_id=self.id).all()
        total_invoiced = sum(inv.amount for inv in invoices)
        
        # Calculate Total Paid
        # Note: Ideally checking Receipt allocations, but for now assuming direct mapping if we had Receipts linked to Invoices
        # Simplified: Sum of all receipts for this tenant
        receipts = Receipt.query.filter_by(tenant_id=self.id).all()
        total_paid = sum(r.amount for r in receipts)
        
        return total_invoiced - total_paid

    @property
    def has_active_lease(self):
        """Check if tenant has at least one active lease (end_date >= today)"""
        from datetime import date
        if not self.leases:
            return False
        return any(lease.end_date >= date.today() for lease in self.leases)
    
    def validate_status(self):
        """Ensure active tenants have leases. Raises ValueError if invalid."""
        if self.status == 'active' and not self.has_active_lease:
            raise ValueError("Active tenant must have at least one active lease")
        return True

class TenantNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), default='General') # General, Complaint, Request, Notice
    note = db.Column(db.Text)
    attachment = db.Column(db.String(200)) # Path to uploaded file

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))
    properties = db.relationship('Property', backref='project_rel', lazy=True)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Linked Project (Optional for legacy support but encouraged)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    # Keeping 'project' string for now to avoid breaking legacy, but will deprecate
    project = db.Column(db.String(50)) 
    
    unit_number = db.Column(db.String(50), unique=True, nullable=False)
    property_type = db.Column(db.String(50)) # e.g. Shop, Apartment
    status = db.Column(db.String(20), default='vacant') # vacant, occupied, maintenance
    
    # Archive/Soft Delete
    archived = db.Column(db.Boolean, default=False)
    archived_date = db.Column(db.DateTime, nullable=True)
    
    # Additional Property Details
    size_sqft = db.Column(db.Float, nullable=True)
    target_rent = db.Column(db.Float, default=0.0) # Asking Price
    bedrooms = db.Column(db.Integer, default=0)
    bathrooms = db.Column(db.Integer, default=0)
    
    # Media
    image_path = db.Column(db.String(200)) # Path to file
    
    notes = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True) # Marketing Description
    furnishing_status = db.Column(db.String(50)) # Unfurnished, Partially Furnished, Fully Furnished
    
    # New Fields
    floor = db.Column(db.String(50)) # e.g. Ground, 1, 2
    block = db.Column(db.String(50)) # e.g. A, B, Podium
    unit = db.Column(db.String(50)) # e.g. 1, 3A (The simplified unit number)
    
    unit_position = db.Column(db.String(50)) # Corner, Intermediate, End Lot
    property_category = db.Column(db.String(50)) # Commercial, Residential, Industrial
    
    # Relationship
    leases = db.relationship('Lease', backref='property_obj', lazy=True)

class Lease(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id')) # Link to Property Inventory
    
    project = db.Column(db.String(50)) # Added for better filtering
    unit_number = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    rent_amount = db.Column(db.Float, nullable=False)
    
    # Deposits
    security_deposit = db.Column(db.Float, default=0.0)
    utility_deposit = db.Column(db.Float, default=0.0)
    misc_deposit = db.Column(db.Float, default=0.0)
    
    # Documents
    agreement_file = db.Column(db.String(200)) # Path to file
    
    tenant = db.relationship('Tenant', backref=db.backref('leases', lazy=True))

    @property
    def days_to_expiry(self):
        from datetime import date
        delta = self.end_date - date.today()
        return delta.days


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    tenant = db.relationship('Tenant', backref=db.backref('invoices', lazy=True))
    issue_date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, default=0.0) # Sum of line items
    # Removed specific type/amount fields, now calculated from items
    description = db.Column(db.String(200)) # Generic description e.g. "January 2024 Rent"
    status = db.Column(db.String(20), default='unpaid') # unpaid, paid, overdue, void
    
    line_items = db.relationship('InvoiceLineItem', backref='invoice', lazy=True, cascade="all, delete-orphan")

class InvoiceLineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False) # rent, water, electricity, late_fee, etc
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)

class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id')) # Optional: generic payment or specific invoice
    date_received = db.Column(db.Date, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    reference = db.Column(db.String(100)) # e.g. Cheque No, Transfer Ref
    
    invoice = db.relationship('Invoice', backref=db.backref('receipts', lazy=True))

class Agent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100)) # Agency Name
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active')
    
    # Relationship
    commissions = db.relationship('Commission', backref='agent', lazy=True)

class Commission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    lease_id = db.Column(db.Integer, db.ForeignKey('lease.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, paid
    
    # Payment Details
    payment_date = db.Column(db.Date)
    payment_reference = db.Column(db.String(100)) # Cheque/Trans ID
    payment_proof = db.Column(db.String(200)) # Path to PV/Receipt file
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    lease = db.relationship('Lease', backref=db.backref('commissions', lazy=True))
