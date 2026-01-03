from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db, MyInvoisConfig
from datetime import datetime

lhdn_bp = Blueprint('lhdn', __name__)

@lhdn_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # Ensure only authorized roles can access (e.g., admin, accounts)
    if current_user.role not in ['admin', 'accounts']:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard.index'))
        
    config = MyInvoisConfig.query.first()
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        client_secret = request.form.get('client_secret')
        issuer_tin = request.form.get('issuer_tin')
        issuer_msic = request.form.get('issuer_msic')
        environment = request.form.get('environment')
        digital_certificate_path = request.form.get('digital_certificate_path')
        certificate_password = request.form.get('certificate_password')
        
        if not config:
            config = MyInvoisConfig()
            db.session.add(config)
            
        config.client_id = client_id
        config.client_secret = client_secret
        config.issuer_tin = issuer_tin
        config.issuer_msic = issuer_msic
        config.environment = environment
        config.digital_certificate_path = digital_certificate_path
        if certificate_password: # Only update if provided to avoid clearing it accidentally if input left blank
            config.certificate_password = certificate_password
        config.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('LHDN Configuration saved successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving configuration: {str(e)}', 'error')
            
    return render_template('lhdn/settings.html', config=config)

@lhdn_bp.route('/submit/<int:invoice_id>', methods=['POST'])
@login_required
def submit_invoice(invoice_id):
    # Check permissions
    if current_user.role not in ['admin', 'accounts']:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    try:
        from services.lhdn_service import LHDNService
        from models import Invoice
        
        service = LHDNService()
        invoice = Invoice.query.get_or_404(invoice_id)
        
        # Ensure UUID exists
        service.ensure_uuid(invoice)
        
        # Submit
        submission_uid = service.submit_invoice(invoice_id)
        
        return jsonify({
            'status': 'success', 
            'message': 'Invoice submitted successfully to LHDN.',
            'submission_uid': submission_uid,
            'uuid': invoice.lhdn_uuid
        })
        
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        # Log full error
        print(f"LHDN Submission Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
