from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from models import db, Invoice, Receipt, Property, Lease, Tenant
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_, or_, extract, desc
from dateutil.relativedelta import relativedelta
from utils import get_tenant_unpaid_items

dashboard_bp = Blueprint('dashboard', __name__)

def get_dashboard_metrics():
    """Helper to calculate all dashboard metrics"""
    today = date.today()
    
    # 1. Financial Metrics (Last 6 Months)
    months = []
    revenue_data = []
    receipts_data = []
    
    for i in range(5, -1, -1):
        d = today - relativedelta(months=i)
        month_start = d.replace(day=1)
        next_month = d + relativedelta(months=1)
        month_end = next_month.replace(day=1) - timedelta(days=1)
        
        months.append(d.strftime('%b %Y'))
        
        # Revenue
        rev = db.session.query(func.sum(Invoice.total_amount))\
            .filter(Invoice.issue_date >= month_start, Invoice.issue_date <= month_end)\
            .filter(Invoice.status != 'void').scalar() or 0
        revenue_data.append(float(rev)) # Ensure float for JSON
        
        # Receipts
        rec = db.session.query(func.sum(Receipt.amount))\
            .filter(Receipt.date_received >= month_start, Receipt.date_received <= month_end)\
            .scalar() or 0
        receipts_data.append(float(rec))

    # 2. Occupancy Rate (Last 6 Months)
    occupancy_data = []
    
    # 3. Card Metrics
    total_properties = Property.query.filter_by(archived=False).count() or 1 # Ensure not zero for division
    occupied_count_current = Property.query.filter_by(status='occupied', archived=False).count()
    vacant_count = total_properties - occupied_count_current
    total_tenants = Tenant.query.filter_by(status='active').count()  # Only count active tenants
    lapsed_tenants = Tenant.query.filter(Tenant.status.in_(['lapse', 'lapsed'])).count()  # Count lapsed tenants
    
    for i in range(5, -1, -1):
        d = today - relativedelta(months=i)
        chk_date = d.replace(day=1)
        
        occupied_count_month = Lease.query.filter(
            and_(Lease.start_date <= chk_date, Lease.end_date >= chk_date)
        ).count()
        
        rate = (occupied_count_month / total_properties) * 100
        occupancy_data.append(round(rate, 1))

    # 3. Aging Metrics (Current Snapshot)
    aging_buckets = {'1-30 Days': 0, '31-60 Days': 0, '61-90 Days': 0, '>90 Days': 0}
    tenants = Tenant.query.filter_by(status='active').all()
    for t in tenants:
        unpaid = get_tenant_unpaid_items(t.id)
        for item in unpaid:
            days = (today - item['due_date']).days
            if days > 90: aging_buckets['>90 Days'] += float(item['unpaid_amount'])
            elif days > 60: aging_buckets['61-90 Days'] += float(item['unpaid_amount'])
            elif days > 60: aging_buckets['31-60 Days'] += float(item['unpaid_amount']) # Fix logic
            elif days > 30: aging_buckets['31-60 Days'] += float(item['unpaid_amount'])
            elif days > 0: aging_buckets['1-30 Days'] += float(item['unpaid_amount'])

    # 4. Lease Expiry Forecast (Next 6 Months)
    expiry_labels = []
    expiry_counts = []
    
    for i in range(1, 7):
        d = today + relativedelta(months=i)
        month_start = d.replace(day=1)
        next_month = d + relativedelta(months=1)
        month_end = next_month.replace(day=1) - timedelta(days=1)
        
        expiry_labels.append(d.strftime('%b %Y'))
        
        count = Lease.query.filter(
            and_(Lease.end_date >= month_start, Lease.end_date <= month_end)
        ).count()
        expiry_counts.append(count)
    
    # KPIs (Current)
    kpi_revenue_current = revenue_data[-1] if revenue_data else 0
    kpi_revenue_last = revenue_data[-2] if len(revenue_data) > 1 else 0
    
    kpi_collected_current = receipts_data[-1] if receipts_data else 0
    kpi_collected_last = receipts_data[-2] if len(receipts_data) > 1 else 0

    kpi_occupancy_current = occupancy_data[-1] if occupancy_data else 0
    kpi_occupancy_last = occupancy_data[-2] if len(occupancy_data) > 1 else 0

    # Overdue Comparison (Historical Approximation)
    def get_overdue_balance_at(target_date):
        """Calculate outstanding balance as of a specific date"""
        # Sum of all invoices due before or on target_date
        total_invoiced = db.session.query(func.sum(Invoice.total_amount))\
            .filter(Invoice.due_date <= target_date)\
            .filter(Invoice.status != 'void').scalar() or 0
            
        # Sum of all receipts received before or on target_date
        total_collected = db.session.query(func.sum(Receipt.amount))\
            .filter(Receipt.date_received <= target_date).scalar() or 0
            
        return max(0, total_invoiced - total_collected)

    # Current Overdue (Today)
    kpi_overdue_current = get_overdue_balance_at(today)
    
    # Last Month Overdue (Last day of last month)
    last_month_date = today.replace(day=1) - timedelta(days=1)
    kpi_overdue_last = get_overdue_balance_at(last_month_date)

    return {
        'months': months,
        'revenue_data': revenue_data,
        'receipts_data': receipts_data,
        'occupancy_data': occupancy_data,
        'aging_labels': list(aging_buckets.keys()),
        'aging_data': list(aging_buckets.values()),
        'expiry_labels': expiry_labels,
        'expiry_counts': expiry_counts,
        
        # New Comparison KPIs
        'kpi_revenue_current': kpi_revenue_current,
        'kpi_revenue_last': kpi_revenue_last,
        
        'kpi_collected_current': kpi_collected_current,
        'kpi_collected_last': kpi_collected_last,
        
        'kpi_occupancy_current': kpi_occupancy_current,
        'kpi_occupancy_last': kpi_occupancy_last,
        
        'kpi_overdue_current': kpi_overdue_current,
        'kpi_overdue_last': kpi_overdue_last,
        
        'kpi_active_tenants': total_tenants,
        'kpi_lapsed_tenants': lapsed_tenants
    }

@dashboard_bp.route('/api/dashboard/metrics')
@login_required
def dashboard_metrics():
    """JSON Endpoint for dashboard charts"""
    data = get_dashboard_metrics()
    return jsonify(data)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Main Dashboard View"""
    # specific KPIs for the top cards (server-side render)
    metrics = get_dashboard_metrics()
    
    return render_template('dashboard.html', **metrics)
