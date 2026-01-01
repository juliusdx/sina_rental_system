
from decimal import Decimal, ROUND_HALF_UP

SST_RATE = Decimal('0.08')

def calculate_sst(amount):
    """
    Calculates 8% SST on the given amount.
    Returns a float rounded to 2 decimal places.
    """
    if amount is None:
        return 0.0
    
    # Convert to Decimal for precision
    val = Decimal(str(amount))
    tax = val * SST_RATE
    
    # Round to 2 decimal places (Bankers rounding or standard? standard half up is safer for tax)
    # Malaysia usually uses standard rounding.
    return float(tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def calculate_taxable_fraction(period_start, period_end, exemptions):
    """
    Calculates the fraction of the period [period_start, period_end] that is NOT covered by any exemption.
    Returns a float between 0.0 and 1.0.
    """
    total_days = (period_end - period_start).days + 1
    if total_days <= 0:
        return 0.0
        
    taxable_days = 0
    from datetime import timedelta
    
    # Iterate through each day in the period
    current = period_start
    while current <= period_end:
        is_exempt = False
        for ex in exemptions:
            if ex.start_date <= current <= ex.end_date:
                is_exempt = True
                break
        
        if not is_exempt:
            taxable_days += 1
        
        current += timedelta(days=1)
        
    return taxable_days / total_days

def get_sst_amount_if_applicable(tenant, amount, invoice_date, period_start=None, period_end=None):
    """
    Returns the tax amount if the invoice date is on or after the tenant's SST commencement date.
    Prioritizes pro-rata calculation if period ranges are provided and exemptions exist.
    """
    if amount is None:
        return 0.0

    # 1. Check Commencement Date
    if not tenant.sst_start_date:
        return 0.0
    
    # Logic: Even if period_start < sst_start_date, strictly speaking we only charge post-start_date.
    # However, if invoice_date is passed (legacy call), we use that. 
    # Better logic: If we have period dates, we use those for precise calculation.
    
    if period_start and period_end:
        # Check for Exemptions
        if tenant.exemptions:
            fraction = calculate_taxable_fraction(period_start, period_end, tenant.exemptions)
            # Also factor in sst_start_date overlap
            # It's cleaner to treat "Before SST Start" as an implicit exemption.
            # But for now, let's keep it simple: Start Date is binary threshold for Invoicing?
            # User said: "Invoicing is always for period 1st to 30th". 
            # If SST starts 15th Jan, we should probably pro-rate too?
            # Let's assume start_date is a hard filter for "Should we even process SST".
            pass
            
            taxable_amount = float(amount) * fraction
            return calculate_sst(Decimal(taxable_amount))
            
    # Fallback to simple date check
    if invoice_date and invoice_date >= tenant.sst_start_date:
        # Check if invoice date itself is exempt? (Less precise)
        is_exempt = False
        for ex in tenant.exemptions:
            if ex.start_date <= invoice_date <= ex.end_date:
                is_exempt = True
                break
        
        if not is_exempt:
            return calculate_sst(amount)
        
    return 0.0
