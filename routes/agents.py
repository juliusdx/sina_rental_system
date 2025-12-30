from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from models import db, Agent, Commission
from flask_login import login_required
from datetime import datetime
from utils import log_audit

agents_bp = Blueprint('agents', __name__, url_prefix='/agents')

@agents_bp.route('/')
@login_required
def list_agents():
    agents = Agent.query.order_by(Agent.name).all()
    # Calculate stats per agent
    for agent in agents:
        agent.total_commissions = sum(c.amount for c in agent.commissions)
        agent.pending_commissions = sum(c.amount for c in agent.commissions if c.status == 'pending')
        
    return render_template('agents/list.html', agents=agents)

@agents_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_agent():
    if request.method == 'POST':
        name = request.form.get('name')
        company = request.form.get('company')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        if not name:
            flash('Agent Name is required', 'error')
            return redirect(url_for('agents.add_agent'))
            
        try:
            new_agent = Agent(
                name=name,
                company=company,
                phone=phone,
                email=email
            )
            db.session.add(new_agent)
            db.session.commit()
            log_audit('CREATE', 'Agent', new_agent.id, f"Created agent {name}")
            flash(f'Agent {name} added successfully', 'success')
            return redirect(url_for('agents.list_agents'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding agent: {str(e)}', 'error')
            
    return render_template('agents/add.html')

@agents_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_agent(id):
    agent = Agent.query.get_or_404(id)
    
    if request.method == 'POST':
        agent.name = request.form.get('name')
        agent.company = request.form.get('company')
        agent.phone = request.form.get('phone')
        agent.email = request.form.get('email')
        agent.status = request.form.get('status', 'active')
        
        try:
            db.session.commit()
            log_audit('UPDATE', 'Agent', agent.id, f"Updated agent {agent.name} details")
            flash(f'Agent {agent.name} updated successfully', 'success')
            return redirect(url_for('agents.list_agents'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating agent: {str(e)}', 'error')
            
    return render_template('agents/edit.html', agent=agent)

@agents_bp.route('/commissions')
@login_required
def commissions_dashboard():
    # List all commissions, filterable by status
    status = request.args.get('status', 'pending')
    
    query = Commission.query
    if status != 'all':
        query = query.filter(Commission.status == status)
        
    commissions = query.order_by(Commission.created_at.desc()).all()
    
    return render_template('agents/commissions.html', commissions=commissions, current_status=status)

@agents_bp.route('/commissions/pay/<int:id>', methods=['POST'])
@login_required
def pay_commission(id):
    commission = Commission.query.get_or_404(id)
    
    payment_date = request.form.get('payment_date')
    reference = request.form.get('reference')
    
    try:
        from werkzeug.utils import secure_filename
        import os
        
        # Handle Proof Upload
        proof_path = None
        if 'proof' in request.files:
            file = request.files['proof']
            if file and file.filename != '':
                filename = secure_filename(f"comm_{commission.id}_{file.filename}")
                upload_folder = os.path.join(request.root_path, 'static', 'uploads', 'commissions')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                proof_path = f"uploads/commissions/{filename}"
        
        commission.status = 'paid'
        commission.payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date() if payment_date else datetime.today().date()
        commission.payment_reference = reference
        if proof_path:
            commission.payment_proof = proof_path
            
        db.session.commit()
        log_audit('PAYMENT', 'Commission', commission.id, f"Paid commission RM{commission.amount} to Agent {commission.agent.name}")
        flash('Commission marked as paid!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
        
    return redirect(url_for('agents.commissions_dashboard'))

@agents_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_agent(id):
    agent = Agent.query.get_or_404(id)
    
    # Check for commissions
    if agent.commissions:
        return jsonify({'status': 'error', 'message': 'Cannot delete agent with existing commissions. Mark as Inactive instead.'}), 400
        
    try:
        db.session.delete(agent)
        db.session.commit()
        log_audit('DELETE', 'Agent', id, f"Deleted agent {agent.name}")
        flash('Agent deleted successfully', 'success')
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@agents_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    data = request.get_json()
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'status': 'error', 'message': 'No agents selected'}), 400
        
    deleted_count = 0
    skipped_count = 0
    
    for agent_id in ids:
        agent = Agent.query.get(agent_id)
        if not agent: continue
        
        if agent.commissions:
            skipped_count += 1
            continue
            
        db.session.delete(agent)
        deleted_count += 1
        
    db.session.commit()
    
    if deleted_count > 0:
        log_audit('DELETE', 'Agent', 0, f"Bulk deleted {deleted_count} agents")
        
    msg = f"Deleted {deleted_count} agents."
    if skipped_count > 0:
        msg += f" (Skipped {skipped_count} with existing commissions)"
        
    flash(msg, 'success' if deleted_count > 0 else 'warning')
    return jsonify({'status': 'success', 'message': msg})
