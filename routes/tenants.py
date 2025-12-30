from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, make_response, jsonify
from models import db, Tenant, Lease, Property
import csv
try:
    import openpyxl
    from openpyxl import Workbook
except ImportError:
    openpyxl = None
    Workbook = None
import io
from flask_login import login_required, current_user
from routes.auth import role_required
from utils import log_audit

tenants_bp = Blueprint('tenants', __name__)

@tenants_bp.route('/')
@login_required
def list_tenants():
    params = request.args
    query = Tenant.query
    
    # Filter by Status
    status_filter = params.get('status')  # 'all', 'active', 'prospective', 'past'
    if status_filter and status_filter != 'all':
        query = query.filter(Tenant.status == status_filter)
    
    # Filter by Project
    project_filter = params.get('project')
    joined_lease = False
    
    if project_filter:
        query = query.join(Lease).filter(Lease.project == project_filter)
        joined_lease = True

    # Search Filter
    search_term = params.get('search')
    if search_term:
        if not joined_lease:
            query = query.outerjoin(Lease)
            joined_lease = True
            
        term = f"%{search_term}%"
        query = query.filter(
            db.or_(
                Tenant.name.ilike(term),
                Tenant.account_code.ilike(term),
                Lease.unit_number.ilike(term),
                Lease.project.ilike(term)
            )
        )

    sort_col = params.get('sort')
    sort_order = params.get('order', 'asc')
    
    if sort_col == 'account':
        col = Tenant.account_code
    elif sort_col == 'project':
        if not joined_lease:
            query = query.outerjoin(Lease)
            joined_lease = True
        col = Lease.project
    elif sort_col == 'unit':
        if not joined_lease:
            query = query.outerjoin(Lease)
            joined_lease = True
        col = Lease.unit_number
    else:
        col = Tenant.name
        
    if sort_order == 'desc':
        query = query.order_by(col.desc())
    else:
        query = query.order_by(col.asc())
        
    tenants = query.all()
    
    # Get distinct projects for filter dropdown
    projects = [p[0] for p in db.session.query(Lease.project).distinct().filter(Lease.project.isnot(None), Lease.project != '').order_by(Lease.project).all()]
    
    if params.get('partial'):
        return render_template('tenants/rows.html', tenants=tenants)

    return render_template('tenants/list.html', 
                         tenants=tenants, 
                         current_sort=sort_col, 
                         current_order=sort_order, 
                         projects=projects, 
                         current_project=project_filter, 
                         current_search=search_term,
                         current_status=status_filter or 'all')

@tenants_bp.route('/upload_doc/<int:lease_id>', methods=['POST'])
def upload_doc(lease_id):
    if 'file' not in request.files:
        flash('No file')
        return redirect(url_for('tenants.list_tenants'))
    file = request.files['file']
    if file.filename == '':
        flash('No file')
        return redirect(url_for('tenants.list_tenants'))
        
    if file:
        import os
        from werkzeug.utils import secure_filename
        filename = secure_filename(f"lease_{lease_id}_{file.filename}")
        upload_folder = os.path.join('static', 'uploads', 'agreements')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file.save(os.path.join(upload_folder, filename))
        
        lease = Lease.query.get_or_404(lease_id)
        lease.agreement_file = filename
        db.session.commit()
        flash('Agreement uploaded!')
        
    return redirect(url_for('tenants.list_tenants'))

@tenants_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'coordinator')
def add_tenant():
    from models import Agent, Commission # Local import to avoid circular dep if any

    if request.method == 'GET':
        # Get vacant properties for dropdown
        preselected_unit = request.args.get('unit')
        properties = Property.query.filter_by(status='vacant').order_by(Property.unit_number).all()
        # Get Active Agents
        agents = Agent.query.filter_by(status='active').order_by(Agent.name).all()
        
        return render_template('tenants/add.html', properties=properties, preselected_unit=preselected_unit, agents=agents)
    
    # POST Logic
    try:
        # Get tenant status from form
        tenant_status = request.form.get('status', 'prospective')  # Default to prospective
        
        # 1. Create Tenant
        new_tenant = Tenant(
            name=request.form.get('name'),
            account_code=request.form.get('account_code'),
            company_reg_no=request.form.get('company_reg_no'),
            contact_person=request.form.get('contact_person'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            status=tenant_status,  # Set from form
            
            # New Fields
            is_sst_registered = True if request.form.get('is_sst_registered') else False,
            sst_registration_number = request.form.get('sst_registration_number'),
            tax_identification_number = request.form.get('tax_identification_number'),
            msic_code = request.form.get('msic_code'),
            business_activity = request.form.get('business_activity'),
            
            address_line_1 = request.form.get('address_line_1'),
            address_line_2 = request.form.get('address_line_2'),
            city = request.form.get('city'),
            state = request.form.get('state'),
            postcode = request.form.get('postcode')
        )
        db.session.add(new_tenant)
        db.session.flush() # Get ID
        
        # 2. Handle Property & Lease
        prop_id_val = request.form.get('property_id')
        property_obj = None
        lease_created = False
        new_lease = None
        
        # Only process property if property_id is provided (for active tenants)
        if prop_id_val and prop_id_val.strip():  # Check if not empty
            if prop_id_val == 'NEW':
                # Create new property
                property_obj = Property(
                    project=request.form.get('new_project'),
                    unit_number=request.form.get('new_unit_number'),
                    property_type='Shop', # Default or add field
                    status='occupied'
                )
                db.session.add(property_obj)
                db.session.flush()
            else:
                # Use existing property
                property_obj = Property.query.get(int(prop_id_val))
                if property_obj:
                    property_obj.status = 'occupied'
        
        # 3. Create Lease (if property provided)
        if property_obj:
            from datetime import datetime
            s_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            e_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            
            new_lease = Lease(
                tenant_id=new_tenant.id,
                property_id=property_obj.id,
                project=property_obj.project, # Snapshotted for convenience
                unit_number=property_obj.unit_number,
                start_date=s_date,
                end_date=e_date,
                rent_amount=float(request.form.get('rent_amount') or 0),
                security_deposit=float(request.form.get('security_deposit') or 0),
                utility_deposit=float(request.form.get('utility_deposit') or 0),
                misc_deposit=float(request.form.get('misc_deposit') or 0)
            )
            db.session.add(new_lease)
            db.session.flush() # Get ID for commission
            lease_created = True
            
            # --- AGENT COMMISSION LOGIC ---
            agent_id = request.form.get('agent_id')
            comm_amount = request.form.get('commission_amount')
            
            if agent_id and comm_amount:
                try:
                    commission = Commission(
                        agent_id=int(agent_id),
                        lease_id=new_lease.id,
                        amount=float(comm_amount),
                        status='pending'
                    )
                    db.session.add(commission)
                except ValueError:
                    flash('Invalid commission amount ignored', 'warning')
            
        # 4. Validate: Active tenant must have lease
        if tenant_status == 'active' and not lease_created:
            db.session.rollback()
            flash('Error: Active tenant must have a lease. Please create a lease or select "Prospective" status.', 'error')
            return redirect(url_for('tenants.add_tenant'))
            
        db.session.commit()
        
        log_audit('CREATE', 'Tenant', new_tenant.id, f"Created tenant {new_tenant.name} via Web UI")
        
        status_msg = "active tenant with lease" if tenant_status == 'active' else "prospective tenant"
        flash(f'{status_msg.capitalize()} created successfully!')
        return redirect(url_for('tenants.list_tenants'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating tenant: {str(e)}')
        return redirect(url_for('tenants.add_tenant'))

@tenants_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'coordinator')
def edit_tenant(id):
    from models import Agent, Commission # Local import
    tenant = Tenant.query.get_or_404(id)
    
    # Get agents for dropdown
    agents = Agent.query.filter_by(status='active').order_by(Agent.name).all()
    
    # Simple logic: get the first active lease
    active_lease = None
    existing_commission = None
    
    if tenant.leases:
        for l in tenant.leases:
            if l.rent_amount > 0 or l.security_deposit > 0:
                active_lease = l
        if not active_lease:
            active_lease = tenant.leases[-1]
            
    # Check for existing commission linked to active lease
    if active_lease:
        existing_commission = Commission.query.filter_by(lease_id=active_lease.id).first()

    if request.method == 'POST':
        # Update Tenant
        tenant.name = request.form.get('name')
        tenant.account_code = request.form.get('account_code')
        tenant.company_reg_no = request.form.get('company_reg_no')
        tenant.contact_person = request.form.get('contact_person')
        
        email = request.form.get('email')
        tenant.email = email if email else None
        
        tenant.phone = request.form.get('phone')
        tenant.status = request.form.get('status')
        
        # Update New Fields
        tenant.is_sst_registered = True if request.form.get('is_sst_registered') else False
        tenant.sst_registration_number = request.form.get('sst_registration_number')
        tenant.tax_identification_number = request.form.get('tax_identification_number')
        tenant.msic_code = request.form.get('msic_code')
        tenant.business_activity = request.form.get('business_activity')
        
        tenant.address_line_1 = request.form.get('address_line_1')
        tenant.address_line_2 = request.form.get('address_line_2')
        tenant.city = request.form.get('city')
        tenant.state = request.form.get('state')
        tenant.postcode = request.form.get('postcode')
        
        # Update Lease (if exists and id matches form)
        lease_id = request.form.get('lease_id')
        current_lease_for_comm = active_lease # Default to current active lease
        
        # New: Handle Lease Creation if no active lease but fields provided
        if not active_lease and request.form.get('rent_amount'):
             from datetime import datetime
             # Create new lease
             try:
                 new_start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
                 new_end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
                 
                 # Determine project/unit from form or fallback
                 proj_field = request.form.get('project', '')
                 unit_field = request.form.get('unit_number', '')
                 
                 new_lease = Lease(
                    tenant_id=tenant.id,
                    project=proj_field,
                    unit_number=unit_field,
                    start_date=new_start_date,
                    end_date=new_end_date,
                    rent_amount=float(request.form.get('rent_amount') or 0),
                    security_deposit=float(request.form.get('security_deposit') or 0),
                    utility_deposit=float(request.form.get('utility_deposit') or 0),
                    misc_deposit=float(request.form.get('misc_deposit') or 0)
                 )
                 # Handle file if present
                 if 'agreement_file' in request.files:
                    file = request.files['agreement_file']
                    if file and file.filename != '':
                        import os
                        from werkzeug.utils import secure_filename
                        # We need an ID for filename, so flush first
                        db.session.add(new_lease)
                        db.session.flush()
                        
                        filename = secure_filename(f"lease_{new_lease.id}_{file.filename}")
                        upload_folder = os.path.join('static', 'uploads', 'agreements')
                        if not os.path.exists(upload_folder):
                            os.makedirs(upload_folder)
                        file.save(os.path.join(upload_folder, filename))
                        new_lease.agreement_file = filename
                 else:
                    db.session.add(new_lease)
                    db.session.flush() # Need ID for commission

                 current_lease_for_comm = new_lease # Use this new lease for commission
                 flash('New lease created successfully.')
             except ValueError:
                 flash('Error creating lease: Invalid date format.', 'error')
             except Exception as e:
                 flash(f'Error creating lease: {str(e)}', 'error')

        elif lease_id and active_lease and str(active_lease.id) == str(lease_id):
            active_lease.project = request.form.get('project')
            active_lease.unit_number = request.form.get('unit_number')
            active_lease.rent_amount = float(request.form.get('rent_amount') or 0)
            
            # Dates
            import datetime
            s_date = request.form.get('start_date')
            e_date = request.form.get('end_date')
            if s_date: active_lease.start_date = datetime.datetime.strptime(s_date, '%Y-%m-%d').date()
            if e_date: active_lease.end_date = datetime.datetime.strptime(e_date, '%Y-%m-%d').date()

            active_lease.security_deposit = float(request.form.get('security_deposit') or 0)
            active_lease.utility_deposit = float(request.form.get('utility_deposit') or 0)
            active_lease.misc_deposit = float(request.form.get('misc_deposit') or 0)

            # File Upload
            if 'agreement_file' in request.files:
                file = request.files['agreement_file']
                if file and file.filename != '':
                    import os
                    from werkzeug.utils import secure_filename
                    filename = secure_filename(f"lease_{active_lease.id}_{file.filename}")
                    upload_folder = os.path.join('static', 'uploads', 'agreements')
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                    file.save(os.path.join(upload_folder, filename))
                    active_lease.agreement_file = filename

        # --- UPDATE/CREATE COMMISSION LOGIC ---
        # Only if we have a valid lease to attach to
        if current_lease_for_comm:
            agent_id = request.form.get('agent_id')
            comm_amount = request.form.get('commission_amount')
            
            # Case 1: Existing Commission - Update or Delete
            if existing_commission:
                if not agent_id: # User cleared agent selection -> Delete commission? Or just update?
                    # Design choice: If unchecked/cleared, maybe mark cancelled or delete.
                    # For now, let's assume they want to update agent/amount.
                    # If they explicitly clear it, we might want to delete.
                    if request.form.get('has_agent') != 'on':
                         db.session.delete(existing_commission)
                else:
                    existing_commission.agent_id = int(agent_id)
                    existing_commission.amount = float(comm_amount or 0)
            
            # Case 2: No Existing Commission - Create New
            elif agent_id and comm_amount:
                try:
                    new_comm = Commission(
                        agent_id=int(agent_id),
                        lease_id=current_lease_for_comm.id,
                        amount=float(comm_amount),
                        status='pending'
                    )
                    db.session.add(new_comm)
                except ValueError:
                    pass

        db.session.commit()
        log_audit('UPDATE', 'Tenant', tenant.id, f"Updated details for {tenant.name}")
        flash('Tenant details updated successfully')
        return redirect(url_for('tenants.list_tenants'))

    return render_template('tenants/edit.html', tenant=tenant, lease=active_lease, agents=agents, commission=existing_commission)

@tenants_bp.route('/add_note/<int:id>', methods=['POST'])
@login_required
@role_required('admin', 'coordinator', 'legal') 
def add_note(id):
    from models import TenantNote # Local Import
    tenant = Tenant.query.get_or_404(id)
    
    note_content = request.form.get('note')
    category = request.form.get('category')
    
    if note_content:
        new_note = TenantNote(
            tenant_id=tenant.id,
            category=category,
            note=note_content
        )
        
        # Handle Attachment
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                import os
                from werkzeug.utils import secure_filename
                
                # Ensure filename is safe and unique-ish
                timestamp = os.path.splitext(file.filename)[0] # Just using original name part
                import time
                ts = int(time.time())
                filename = secure_filename(f"{ts}_{file.filename}")
                
                upload_folder = os.path.join('static', 'uploads', 'notes')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                    
                file.save(os.path.join(upload_folder, filename))
                new_note.attachment = filename

        db.session.add(new_note)
        db.session.commit()
        log_audit('CREATE', 'TenantNote', new_note.id, f"Added note to tenant {tenant.name}: {category}")
        flash('Note added successfully.')
        
    return redirect(url_for('tenants.edit_tenant', id=id))

@tenants_bp.route('/download_template')
def download_template():
    if not openpyxl:
        return "Server config error: openpyxl missing", 500

    import tempfile
    import os
    
    # Create Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Rent Listing"

    # Columns matching 'Rental Source.xlsx'
    columns = ['Account Code', 'project', 'floor', 'lot', 'Agreement status', 'Tenant Name', 
               'Security', 'Utility', 'MISC', 'Rent RM', 'Start Date', 'End Date']
    
    ws.append(columns)

    # Example Row
    ws.append(['3060/G02', 'MISC', 'G', '02', 'active', 'EXAMPLE TENANT SDN BHD', 
               2000, 1000, 0, 3000, '2024-01-01', '2025-01-01'])
    
    # Save to buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Send file
    try:
        response = send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='rental_source_template.xlsx'
        )
        return response
    except TypeError:
        # Fallback for old Flask
        response = send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            attachment_filename='rental_source_template.xlsx'
        )
        return response

def clean_numeric(value):
    """
    Clean numeric value by removing non-numeric characters (except . and -)
    Returns float or 0.0 if invalid
    """
    if value is None:
        return 0.0
    
    # Convert to string
    str_val = str(value).strip()
    
    # Remove common non-numeric characters: °, comma, space, etc.
    # Keep only digits, decimal point, and minus sign
    cleaned = ''
    for char in str_val:
        if char.isdigit() or char in '.-':
            cleaned += char
    
    # Try to convert
    try:
        return float(cleaned) if cleaned and cleaned not in ['-', '.', '-.'] else 0.0
    except ValueError:
        return 0.0

@tenants_bp.route('/import', methods=['POST'])
def import_tenants():
    if 'file' not in request.files:
        flash('No file received')
        return redirect(url_for('tenants.list_tenants'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('tenants.list_tenants'))

    try:
        data_rows = []
        headers = []

        if file.filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            headers = csv_reader.fieldnames
            data_rows = list(csv_reader)
        else:
            if not openpyxl:
                flash('Server missing openpyxl library', 'error')
                return redirect(url_for('tenants.list_tenants'))
                
            # Handle Excel with openpyxl
            wb = openpyxl.load_workbook(file)
            ws = wb.active
            rows = list(ws.rows)
            
            # Find header row with naive approach
            header_idx = 0
            for i, row in enumerate(rows[:20]): # Check first 20 rows
                vals = [str(c.value) for c in row if c.value]
                if 'Account Code' in vals or 'Tenant Name' in vals:
                    header_idx = i
                    break
            
            # Extract headers
            headers = [cell.value for cell in rows[header_idx] if cell.value]
            
            # Map rows
            for row in rows[header_idx+1:]:
                row_data = {}
                # Create a simple mapping based on index
                current_col = 0
                for cell in row:
                    if current_col < len(headers):
                        header = headers[current_col]
                        row_data[header] = cell.value
                    current_col += 1
                data_rows.append(row_data)

        success_count = 0
        errors = []
        
        for index, row in enumerate(data_rows):
            try:
                # Helper
                def get_val(key, default=None):
                    v = row.get(key)
                    return v if v is not None else default

                # 1. Tenant Name
                name = get_val('Tenant Name')
                if not name: continue # Skip if no name

                # 2. Account Code / ID
                acct_code = get_val('Account Code')
                
                # Check duplicates by Account Code or Name
                existing = None
                if acct_code:
                    existing = Tenant.query.filter_by(account_code=str(acct_code)).first()
                if not existing:
                    existing = Tenant.query.filter_by(name=name).first() # Fallback
                
                if existing:
                    tenant = existing
                else:
                    tenant = Tenant(
                        name=name,
                        account_code=str(acct_code) if acct_code else None,
                        status=get_val('Agreement status', 'active')
                    )
                    db.session.add(tenant)
                    db.session.flush()

                # 3. Create Lease
                # Construct Unit Number
                proj = str(get_val('project', ''))
                floor = str(get_val('floor', ''))
                lot = str(get_val('lot', ''))
                
                # Clean unit number parts
                if floor == 'None': floor = ''
                if lot == 'None': lot = ''
                if proj == 'None': proj = ''
                
                unit_no = f"{floor}-{lot}".strip('-')
                if not unit_no and acct_code: 
                    unit_no = str(acct_code)
                    # Try to clean project prefix if present in account code
                    if proj and unit_no.startswith(proj):
                        cleaned = unit_no[len(proj):].strip('/- ')
                        if cleaned: unit_no = cleaned

                # Create dates - handling openpyxl datetime objects or strings
                def parse_date(d):
                    if not d: return None
                    if isinstance(d, (datetime, date)): return d
                    try:
                        return datetime.strptime(str(d), '%Y-%m-%d').date()
                    except:
                        try:
                            return datetime.strptime(str(d), '%d/%m/%Y').date()
                        except:
                            return None

                start_date = parse_date(get_val('Start Date'))
                end_date = parse_date(get_val('End Date'))
                
                # Default dates if missing
                from datetime import date
                if not start_date: start_date = date.today() 
                if not end_date: end_date = date.today().replace(year=date.today().year + 1)
 
                # Smart Linking
                # 1. Try exact match
                prop_obj = Property.query.filter_by(unit_number=unit_no).first()
                
                # 2. Try Prefix Match (Smart Link)
                if not prop_obj and proj and unit_no:
                    candidate = f"{proj}-{unit_no}"
                    prop_obj = Property.query.filter_by(unit_number=candidate).first()
                    
                # If found, use its canonical data
                prop_id = None
                if prop_obj:
                    prop_id = prop_obj.id
                    unit_no = prop_obj.unit_number # Canonical name
                    # Update status
                    if end_date >= date.today():
                        prop_obj.status = 'occupied'

                # Only create lease if we have some property info
                if unit_no or proj:
                    try:
                        lease = Lease(
                            tenant_id=tenant.id,
                            property_id=prop_id, # LINKED!
                            project=proj, # Save the project
                            unit_number=unit_no,
                            start_date=start_date,
                            end_date=end_date,
                            rent_amount=clean_numeric(get_val('Rent RM', 0)),
                            security_deposit=clean_numeric(get_val('Security', 0)),
                            utility_deposit=clean_numeric(get_val('Utility', 0)),
                            misc_deposit=clean_numeric(get_val('MISC', 0))
                        )
                        db.session.add(lease)
                        success_count += 1
                    except Exception as lease_error:
                        # If lease creation fails, still count tenant as successful
                        errors.append(f"Row {index}: Tenant created but lease failed - {str(lease_error)}")
                        success_count += 1
                
            except Exception as e:
                errors.append(f"Error row {index}: {str(e)}")
        
        db.session.commit()
        flash(f'Imported {success_count} records. Alerts: {len(errors)}')
        for err in errors[:5]:
            flash(err)
            
    except Exception as e:
        flash(f'Critical Import Error: {str(e)}')
        print(e)
        
    return redirect(url_for('tenants.list_tenants'))

@tenants_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    """Bulk delete tenants and all related data (leases, invoices, receipts, notes)"""
    try:
        data = request.get_json()
        tenant_ids = data.get('tenant_ids', [])
        
        if not tenant_ids:
            return jsonify({'status': 'error', 'message': 'No tenants selected'}), 400
        
        deleted_count = 0
        
        # Import related models
        from models import Invoice, Receipt, TenantNote
        
        for tenant_id in tenant_ids:
            tenant = Tenant.query.get(int(tenant_id))
            if not tenant:
                continue
            
            # Delete all related data (cascade)
            # 1. Delete receipts and invoices (invoices are linked to tenant)
            for invoice in Invoice.query.filter_by(tenant_id=tenant.id).all():
                Receipt.query.filter_by(invoice_id=invoice.id).delete()
                db.session.delete(invoice)
            
            # 2. Delete leases
            Lease.query.filter_by(tenant_id=tenant.id).delete()
            
            # 3. Delete notes
            TenantNote.query.filter_by(tenant_id=tenant.id).delete()
            
            # 4. Delete tenant
            db.session.delete(tenant)
            deleted_count += 1
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} tenant(s)'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
