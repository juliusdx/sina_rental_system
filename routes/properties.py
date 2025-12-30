from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, make_response
from models import db, Property, Lease, Tenant, Project, Invoice, Receipt, TenantNote
from datetime import date, datetime
import os
import io
import pandas as pd
from werkzeug.utils import secure_filename
from flask_login import login_required
from utils import log_audit
from sqlalchemy.exc import IntegrityError

properties_bp = Blueprint('properties', __name__, url_prefix='/properties')

def recalculate_property_statuses():
    """Recalculate all property statuses based on active leases"""
    today = date.today()
    properties = Property.query.all()
    
    for prop in properties:
        # Check if there's an active lease
        active_lease = Lease.query.filter(
            Lease.property_id == prop.id,
            Lease.start_date <= today,
            Lease.end_date >= today
        ).first()
        
        # Update status
        if active_lease:
            prop.status = 'occupied'
        elif prop.status == 'occupied':
             # Only revert to vacant if it was occupied (meaning lease expired/deleted)
             # This preserves manual statuses like 'maintenance' or 'reserved'
             prop.status = 'vacant'
    
    db.session.commit()

@properties_bp.route('/dashboard')
@properties_bp.route('/')
@login_required
def dashboard():
    # Recalculate property statuses based on active leases
    recalculate_property_statuses()
    
    # Filters
    status_filter = request.args.get('status')
    project_filter = request.args.get('project')
    type_filter = request.args.get('type')
    search_term = request.args.get('search')
    show_archived = request.args.get('show_archived') == 'true'
    
    query = Property.query
    
    # Exclude archived by default
    if not show_archived:
        query = query.filter(Property.archived == False)
    
    if status_filter:
        query = query.filter(Property.status == status_filter)
        
    if project_filter:
        query = query.filter(Property.project == project_filter)
        
    if type_filter:
        query = query.filter(Property.property_type.ilike(type_filter))
        
    if search_term:
        term = f"%{search_term}%"
        query = query.filter(
            db.or_(
                Property.unit_number.ilike(term),
                Property.project.ilike(term),
                Property.property_type.ilike(term)
            )
        )
        
    properties = query.order_by(Property.project, Property.unit_number).all()
    
    # Calculate stats (exclude archived)
    total = Property.query.filter_by(archived=False).count()
    occupancy = Property.query.filter_by(status='occupied', archived=False).count()
    vacancy = total - occupancy
    occupancy_rate = (occupancy / total * 100) if total > 0 else 0
    
    # Get filters data
    projects = Project.query.order_by(Project.name).all()
    
    # Group properties manually to avoid Jinja2 TypeError (sorting None vs str)
    grouped_properties = {}
    for p in properties:
        p_name = p.project if p.project else 'Unassigned'
        if p_name not in grouped_properties:
            grouped_properties[p_name] = []
        grouped_properties[p_name].append(p)
        
    # Sort projects: Real names first, alphabetical, then Unassigned
    sorted_keys = sorted(grouped_properties.keys(), key=lambda x: (x == 'Unassigned', x.lower()))
    property_groups = [(key, grouped_properties[key]) for key in sorted_keys]
    
    return render_template('properties/dashboard.html', 
                         property_groups=property_groups,
                         properties=properties, # Keep for safety if used elsewhere, though seemingly not needed for grouping anymore
                         stats={
                             'total': total, 
                             'occupancy': occupancy, 
                             'vacancy': vacancy,
                             'rate': occupancy_rate
                         },
                         projects=projects,
                         current_filters={
                             'status': status_filter,
                             'project': project_filter,
                             'type': type_filter,
                             'search': search_term,
                             'show_archived': show_archived
                         })

@properties_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_property():
    projects = Project.query.order_by(Project.name).all()
    
    if request.method == 'POST':
        try:
            # Handle Project: If ID provided, use it. If 'new_project' text provided, create it?
            # For now, simplistic: Form provides project_id via dropdown.
            # If user wants a new project, they might need a separate flow or "Other" logic.
            # Let's support a simple "Add New Project" modal in frontend that posts to separate route, OR handle generic text if allowed.
            
            project_id = request.form.get('project_id')
            project_name = None
            
            if project_id and project_id != '':
                proj = Project.query.get(int(project_id))
                if proj:
                    project_name = proj.name
            
            # Handle File Upload
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = secure_filename(f"{request.form.get('unit_number', 'unknown')}_{file.filename}")
                    # Save to static/uploads/properties
                    upload_folder = os.path.join(request.root_path, 'static', 'uploads', 'properties')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, filename))
                    image_path = f"uploads/properties/{filename}"

            # Universal ID Generation Logic
            block = request.form.get('block', '').strip()
            floor = request.form.get('floor', '').strip()
            unit_val = request.form.get('unit', '').strip()
            
            # If components provided, regenerate ID
            # Else fallback to manual unit_number input
            unit_number = request.form.get('unit_number', '').strip()
            if not unit_number and (unit_val or floor):
                 parts = [p for p in [project_name, block, floor, unit_val] if p]
                 unit_number = "-".join(parts)

            new_property = Property(
                unit_number=unit_number,
                project_id=int(project_id) if project_id else None,
                project=project_name, # Legacy Sync
                property_type=request.form.get('property_type', ''),
                size_sqft=float(request.form['size_sqft']) if request.form.get('size_sqft') else None,
                target_rent=float(request.form.get('target_rent', 0)) if request.form.get('target_rent') else 0.0,
                bedrooms=int(request.form.get('bedrooms', 0)),
                bathrooms=int(request.form.get('bathrooms', 0)),
                image_path=image_path,
                notes=request.form.get('notes', ''),
                description=request.form.get('description', ''),
                furnishing_status=request.form.get('furnishing_status') if request.form.get('property_type') in ['Apartment', 'Condo', 'House', 'Residential'] else None,
                
                # Split Fields
                block=block,
                floor=floor,
                unit=unit_val,
                
                unit_position=request.form.get('unit_position', ''),
                property_category=request.form.get('property_category', ''),
                status=request.form.get('status', 'vacant')
            )
            db.session.add(new_property)
            db.session.commit()
            log_audit('CREATE', 'Property', new_property.id, f"Added Property {new_property.unit_number}")
            flash(f'Property {new_property.unit_number} added successfully!', 'success')
            return redirect(url_for('properties.dashboard'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Unit number already exists!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding property: {str(e)}', 'error')
            # raise e # Debug
    
    return render_template('properties/add.html', projects=projects)

@properties_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_property(id):
    property = Property.query.get_or_404(id)
    projects = Project.query.order_by(Project.name).all()
    
    if request.method == 'POST':
        try:
            # Update core fields
            project_id = request.form.get('project_id')
            if project_id:
                property.project_id = int(project_id)
                proj = Project.query.get(property.project_id)
                if proj:
                    property.project = proj.name # Sync legacy
            
            # Split Fields
            property.block = request.form.get('block', '').strip()
            property.floor = request.form.get('floor', '').strip()
            property.unit = request.form.get('unit', '').strip()
            
            # ID Generation or Manual
            # If manual unit_number is different from auto-gen, respect manual? 
            # Or enforce auto-gen?
            # Let's enforce auto-gen IF user didn't type a custom one.
            # Realistically, form will send 'unit_number'.
            # We'll trust form 'unit_number' but update components too.
            property.unit_number = request.form['unit_number'].strip()
            
            property.property_type = request.form.get('property_type', '')
            property.size_sqft = float(request.form['size_sqft']) if request.form.get('size_sqft') else None
            property.target_rent = float(request.form.get('target_rent', 0)) if request.form.get('target_rent') else 0.0
            property.bedrooms = int(request.form.get('bedrooms', 0))
            property.bathrooms = int(request.form.get('bathrooms', 0))
            
            property.notes = request.form.get('notes', '')
            property.description = request.form.get('description', '')
            property.unit_position = request.form.get('unit_position', '')
            property.property_category = request.form.get('property_category', '')
            
            # Handle Manual Status Change
            new_status = request.form.get('status')
            if new_status and new_status in ['vacant', 'maintenance', 'reserved']:
                # prevent setting to vacant if actively leased? Recalculate will handle it but let's be safe
                # If currently occupied and trying to set to something else:
                if property.status == 'occupied' and new_status != 'occupied':
                     # We can allow it? The recalculator will override it if lease exists. 
                     # But user might want to force maintenance even if leased? (Unlikely).
                     # Let's just allow it, recalculate handles the truth.
                     pass
                property.status = new_status
            
            # Handle Furnishing
            if property.property_type in ['Apartment', 'Condo', 'House', 'Residential']:
                 property.furnishing_status = request.form.get('furnishing_status')
            else:
                 property.furnishing_status = None
            
            # Handle File Upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = secure_filename(f"{property.unit_number}_{file.filename}")
                    upload_folder = os.path.join(request.root_path, 'static', 'uploads', 'properties')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, filename))
                    property.image_path = f"uploads/properties/{filename}"
            
            db.session.commit()
            log_audit('UPDATE', 'Property', property.id, f"Updated Property {property.unit_number} details")
            flash(f'Property {property.unit_number} updated successfully!', 'success')
            return redirect(url_for('properties.dashboard'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Unit number already exists!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating property: {str(e)}', 'error')
    
    return render_template('properties/edit.html', property=property, projects=projects)

@properties_bp.route('/history/<int:id>')
@login_required
def history(id):
    property = Property.query.get_or_404(id)
    
    # 1. Fetch Leases (Past & Present)
    # Try linking by ID first, fallback to unit_number match if legacy data
    leases = Lease.query.filter(
        (Lease.property_id == id) | (Lease.unit_number == property.unit_number)
    ).order_by(Lease.end_date.desc()).all()
    
    # 2. Aggregated Tenant History
    tenancy_history = []
    current_lease = None
    today = date.today()
    
    for lease in leases:
        tenant = lease.tenant
        
        # Calculate Financials for this Tenant
        # Note: This aggregates ALL time for the tenant. If a tenant had multiple leases for different units, 
        # this might over-count. Ideally, receipt/invoice should link to lease or property.
        # For now, assuming 1-to-1 or 1-to-many sequential relationship (Tenant -> Lease).
        
        # Fetch Invoices for this tenant
        tenant_invoices = Invoice.query.filter_by(tenant_id=tenant.id).all()
        total_invoiced = sum(inv.total_amount for inv in tenant_invoices)
        
        # Fetch Receipts
        tenant_receipts = Receipt.query.filter_by(tenant_id=tenant.id).all()
        total_paid = sum(r.amount for r in tenant_receipts)
        
        balance = total_invoiced - total_paid
        
        # Check active
        is_active = lease.start_date <= today <= lease.end_date
        if is_active:
            current_lease = lease
            
        tenancy_history.append({
            'lease': lease,
            'tenant': tenant,
            'financials': {
                'invoiced': total_invoiced,
                'paid': total_paid,
                'balance': balance
            },
            'is_active': is_active
        })
        
    # 3. Issues / Notes (Linked to Tenants)
    # Collect all notes from all tenants who have leased this property
    # This might include notes from their time at OTHER properties if they moved. 
    # Limitation accepted for now.
    issues = []
    tenant_ids = [l.tenant_id for l in leases]
    if tenant_ids:
        raw_notes = TenantNote.query.filter(
            TenantNote.tenant_id.in_(tenant_ids),
            TenantNote.category.in_(['Complaint', 'Maintenance', 'Request'])
        ).order_by(TenantNote.date.desc()).all()
        
        for note in raw_notes:
            issues.append({
                'date': note.date,
                'category': note.category,
                'note': note.note,
                'tenant_name': note.tenant.name,
                'attachment': note.attachment
            })

    return render_template('properties/history.html', 
                         property=property,
                         tenancy_history=tenancy_history,
                         issues=issues,
                         current_lease=current_lease)

@properties_bp.route('/archive/<int:id>', methods=['POST'])
@login_required
def archive_property(id):
    property = Property.query.get_or_404(id)
    
    # Check if property is occupied
    if property.status == 'occupied':
        return jsonify({'status': 'error', 'message': 'Cannot archive an occupied property. Please terminate the lease first.'}), 400
    
    try:
        property.archived = True
        property.archived_date = datetime.utcnow()
        db.session.commit()
        log_audit('ARCHIVE', 'Property', property.id, f"Archived Property {property.unit_number}")
        return jsonify({'status': 'success', 'message': f'Property {property.unit_number} archived successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@properties_bp.route('/unarchive/<int:id>', methods=['POST'])
@login_required
def unarchive_property(id):
    property = Property.query.get_or_404(id)
    
    try:
        property.archived = False
        property.archived_date = None
        db.session.commit()
        log_audit('RESTORE', 'Property', property.id, f"Restored Property {property.unit_number}")
        return jsonify({'status': 'success', 'message': f'Property {property.unit_number} restored successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@properties_bp.route('/add_project', methods=['POST'])
@login_required
def add_project():
    name = request.form.get('name')
    if not name:
        return jsonify({'status': 'error', 'message': 'Project Name required'}), 400
        
    try:
        new_proj = Project(name=name.strip())
        db.session.add(new_proj)
        db.session.commit()
        return jsonify({'status': 'success', 'id': new_proj.id, 'name': new_proj.name})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Project already exists'}), 400

@properties_bp.route('/download_template')
@login_required
def download_template():
    # Create a DataFrame with sample data
    data = {
        'Unit Number': ['MP2-G-0-9', ''], # Example of manually provided or empty (to be auto-generated)
        'Project': ['MP2', 'Sunrise Towers'],
        'Block': ['G', 'A'],
        'Floor': ['0', '1'],
        'Unit': ['9', '01'],
        'Type': ['Shop', 'Apartment'],
        'Category': ['Commercial', 'Residential'],
        'Position': ['Intermediate', 'Corner'],
        'Size (sqft)': [1200, 850],
        'Target Rent': [2500, 1800],
        'Bedrooms': [0, 3],
        'Bathrooms': [1, 2],
        'Furnishing': ['', 'Partially Furnished'],
        'Description': ['Nice frontage', 'Near lift'],
        'Status': ['vacant', 'maintenance'],
        'Notes': ['Corner unit', 'Pool view']
    }
    df = pd.DataFrame(data)
    
    # Save to buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=property_upload_template.xlsx"
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return response

@properties_bp.route('/bulk_upload', methods=['GET', 'POST'])
@login_required
def bulk_upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file:
            try:
                # Determine file type
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                    
                added_count = 0
                skipped_count = 0
                
                for _, row in df.iterrows():
                    # 1. Extract Components
                    proj_name = str(row.get('Project', '')).strip()
                    block = str(row.get('Block', '')).strip()
                    floor = str(row.get('Floor', '')).strip()
                    unit_val = str(row.get('Unit', '')).strip()
                    
                    if block == 'nan': block = ''
                    if floor == 'nan': floor = ''
                    if unit_val == 'nan': unit_val = ''
                    if proj_name == 'nan': proj_name = ''
                    
                    # 2. Determine Unit Number (Universal ID)
                    unit_number = str(row.get('Unit Number', '')).strip()
                    if unit_number == 'nan': unit_number = ''
                    
                    # If Unit Number invalid/missing, try to construct it
                    if not unit_number and (unit_val or floor):
                        parts = [p for p in [proj_name, block, floor, unit_val] if p]
                        if parts:
                            unit_number = "-".join(parts)
                    
                    if not unit_number:
                        continue # Skip invalid row
                        
                    # Check duplicate
                    if Property.query.filter_by(unit_number=unit_number).first():
                        skipped_count += 1
                        continue
                        
                    # Handle Project Linking
                    project_id = None
                    if proj_name:
                        # Case insensitive check
                        existing_proj = Project.query.filter(Project.name.ilike(proj_name)).first()
                        if existing_proj:
                            project_id = existing_proj.id
                            proj_name = existing_proj.name # Use canonical name
                        else:
                            # Create new project
                            new_proj = Project(name=proj_name)
                            db.session.add(new_proj)
                            db.session.flush() # Get ID
                            project_id = new_proj.id

                    # Create Property
                    try:
                        size = float(row.get('Size (sqft)', 0))
                        if pd.isna(size): size = 0
                    except: size = 0
                    
                    try:
                        rent = float(row.get('Target Rent', 0))
                        if pd.isna(rent): rent = 0
                    except: rent = 0
                    
                    try:
                        beds = int(row.get('Bedrooms', 0))
                        if pd.isna(beds): beds = 0
                    except: beds = 0
                    
                    try:
                        baths = int(row.get('Bathrooms', 0))
                        if pd.isna(baths): baths = 0
                    except: baths = 0
                    
                    notes = str(row.get('Notes', ''))
                    if notes == 'nan': notes = ''
                    
                    desc = str(row.get('Description', ''))
                    if desc == 'nan': desc = ''
                    
                    pos = str(row.get('Position', ''))
                    if pos == 'nan': pos = ''
                    
                    cat = str(row.get('Category', ''))
                    if cat == 'nan': cat = ''
                    
                    furn = str(row.get('Furnishing', ''))
                    if furn == 'nan': furn = None
                    
                    status = str(row.get('Status', 'vacant')).lower()
                    if status not in ['vacant', 'maintenance', 'reserved']: status = 'vacant'

                    new_prop = Property(
                        unit_number=unit_number,
                        project_id=project_id,
                        project=proj_name, # Legacy
                        block=block,
                        floor=floor,
                        unit=unit_val,
                        property_type=str(row.get('Type', '')),
                        property_category=cat,
                        unit_position=pos,
                        size_sqft=size,
                        target_rent=rent,
                        bedrooms=beds,
                        bathrooms=baths,
                        notes=notes,
                        description=desc,
                        furnishing_status=furn,
                        status=status
                    )
                    db.session.add(new_prop)
                    added_count += 1
                
                db.session.commit()
                log_audit('IMPORT', 'Property', 0, f"Bulk imported {added_count} properties")
                flash(f'Success! Added {added_count} properties. Skipped {skipped_count} duplicates.', 'success')
                return redirect(url_for('properties.dashboard'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing file: {str(e)}', 'error')
                
    return render_template('properties/bulk_upload.html')

@properties_bp.route('/quick_add_tenant', methods=['POST'])
@login_required
def quick_add_tenant():
    """Quick add tenant from property card modal - creates tenant + lease + marks property occupied"""
    try:
        from datetime import datetime
        
        # Get form data
        property_id = request.form.get('property_id')
        tenant_name = request.form.get('tenant_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        rent_amount = request.form.get('rent_amount')
        
        # Validation - check for None values
        if not property_id:
            return jsonify({'status': 'error', 'message': 'Property ID is missing'}), 400
            
        if not all([tenant_name, start_date_str, end_date_str, rent_amount]):
            return jsonify({'status': 'error', 'message': 'Missing required fields (name, dates, or rent)'}), 400
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Get property
        property_obj = Property.query.get_or_404(int(property_id))
        
        # Check if property is vacant
        if property_obj.status != 'vacant':
            return jsonify({'status': 'error', 'message': 'Property is not vacant'}), 400
        
        # Create Tenant with status='active'
        new_tenant = Tenant(
            name=tenant_name.strip(),
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            status='active'  # Active because we're creating a lease
        )
        db.session.add(new_tenant)
        db.session.flush()  # Get tenant ID
        
        # Create Lease
        new_lease = Lease(
            tenant_id=new_tenant.id,
            property_id=property_obj.id,
            project=property_obj.project,
            unit_number=property_obj.unit_number,
            start_date=start_date,
            end_date=end_date,
            rent_amount=float(rent_amount),
            security_deposit=0.0,
            utility_deposit=0.0,
            misc_deposit=0.0
        )
        db.session.add(new_lease)
        
        # Mark property as occupied
        property_obj.status = 'occupied'
        
        db.session.commit()
        
        log_audit('CREATE', 'Tenant', new_tenant.id, f"Quick Added Tenant {new_tenant.name} to {property_obj.unit_number}")
        
        
        return jsonify({
            'status': 'success',
            'tenant_id': new_tenant.id,
            'tenant_name': new_tenant.name,
            'message': f'Tenant "{new_tenant.name}" created and assigned to {property_obj.unit_number}',
            'redirect_url': url_for('tenants.edit_tenant', id=new_tenant.id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@properties_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    """Bulk delete properties and all related data (leases, invoices, receipts)"""
    try:
        data = request.get_json()
        property_ids = data.get('property_ids', [])
        
        if not property_ids:
            return jsonify({'status': 'error', 'message': 'No properties selected'}), 400
        
        deleted_count = 0
        
        # Import related models
        from models import Invoice, Receipt, TenantNote
        
        for property_id in property_ids:
            property_obj = Property.query.get(int(property_id))
            if not property_obj:
                continue
            
            # Delete all related data (cascade)
            # Find all leases for this property
            leases = Lease.query.filter_by(property_id=property_obj.id).all()
            
            for lease in leases:
                # Delete invoices and receipts for this lease's tenant
                tenant = lease.tenant
                if tenant:
                    # Delete receipts linked to tenant's invoices
                    for invoice in Invoice.query.filter_by(tenant_id=tenant.id).all():
                        Receipt.query.filter_by(invoice_id=invoice.id).delete()
                        db.session.delete(invoice)
                    
                    # Delete tenant notes
                    TenantNote.query.filter_by(tenant_id=tenant.id).delete()
                
                # Delete the lease
                db.session.delete(lease)
            
            # Delete the property
            db.session.delete(property_obj)
            deleted_count += 1
        
        db.session.commit()
        
        log_audit('DELETE', 'Property', 0, f"Bulk deleted {deleted_count} properties: {', '.join(map(str, property_ids))}")

        return jsonify({
            'status': 'success',
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} propert{"ies" if deleted_count != 1 else "y"}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
