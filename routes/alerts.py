from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging
from datetime import datetime, timedelta

from app import db
from models import Alert, Pathogen, Antibiotic, User, UserRole
from utils import send_alert

logger = logging.getLogger(__name__)

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')

@alerts_bp.route('/')
@login_required
def alerts_view():
    """View all alerts with filtering options"""
    # Get filter parameters
    alert_type = request.args.get('alert_type')
    severity = request.args.get('severity', type=int)
    read = request.args.get('read')
    action_taken = request.args.get('action_taken')
    
    # Base query - get alerts for current user
    query = Alert.query.filter(Alert.user_id == current_user.id)
    
    # Apply filters
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    if read is not None:
        read_bool = read.lower() == 'true'
        query = query.filter(Alert.read == read_bool)
    
    if action_taken is not None:
        action_bool = action_taken.lower() == 'true'
        query = query.filter(Alert.action_taken == action_bool)
    
    # Execute query with pagination
    page = request.args.get('page', 1, type=int)
    alerts = query.order_by(Alert.created_at.desc()).paginate(page=page, per_page=20)
    
    # Count unread alerts
    unread_count = Alert.query.filter(Alert.user_id == current_user.id, Alert.read == False).count()
    
    return render_template('alerts.html',
                          alerts=alerts,
                          unread_count=unread_count,
                          current_filters={
                              'alert_type': alert_type,
                              'severity': severity,
                              'read': read,
                              'action_taken': action_taken
                          })

@alerts_bp.route('/acknowledge/<int:alert_id>', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    """Mark an alert as read"""
    alert = Alert.query.get_or_404(alert_id)
    
    # Check if alert belongs to current user
    if alert.user_id != current_user.id:
        flash('You do not have permission to access this alert', 'danger')
        return redirect(url_for('alerts.alerts_view'))
    
    alert.read = True
    db.session.commit()
    
    flash('Alert marked as read', 'success')
    return redirect(url_for('alerts.alerts_view'))

@alerts_bp.route('/resolve/<int:alert_id>', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """Mark an alert as action taken"""
    alert = Alert.query.get_or_404(alert_id)
    
    # Check if alert belongs to current user
    if alert.user_id != current_user.id:
        flash('You do not have permission to access this alert', 'danger')
        return redirect(url_for('alerts.alerts_view'))
    
    alert.action_taken = True
    db.session.commit()
    
    flash('Alert marked as resolved', 'success')
    return redirect(url_for('alerts.alerts_view'))

@alerts_bp.route('/dismiss/<int:alert_id>', methods=['POST'])
@login_required
def dismiss_alert(alert_id):
    """Mark an alert as read and action taken"""
    alert = Alert.query.get_or_404(alert_id)
    
    # Check if alert belongs to current user
    if alert.user_id != current_user.id:
        flash('You do not have permission to access this alert', 'danger')
        return redirect(url_for('alerts.alerts_view'))
    
    alert.read = True
    alert.action_taken = True
    db.session.commit()
    
    flash('Alert dismissed', 'success')
    return redirect(url_for('alerts.alerts_view'))

@alerts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_alert():
    """Create a manual alert (admin only)"""
    if current_user.role != UserRole.ADMIN:
        flash('Only administrators can create manual alerts', 'danger')
        return redirect(url_for('alerts.alerts_view'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        alert_type = request.form.get('alert_type')
        severity = request.form.get('severity', type=int)
        pathogen_id = request.form.get('pathogen_id')
        antibiotic_id = request.form.get('antibiotic_id')
        
        # Get user IDs to send alert to (by role or all)
        target_role = request.form.get('target_role')
        
        if target_role == 'all':
            users = User.query.filter(User.is_active == True).all()
        else:
            users = User.query.filter(User.role == UserRole(target_role), User.is_active == True).all()
        
        # Create alerts for each user
        for user in users:
            alert = Alert(
                user_id=user.id,
                title=title,
                message=message,
                alert_type=alert_type,
                severity=severity,
                pathogen_id=pathogen_id if pathogen_id else None,
                antibiotic_id=antibiotic_id if antibiotic_id else None
            )
            db.session.add(alert)
            
            # Send notifications
            send_alert(user, alert)
        
        db.session.commit()
        flash(f'Alert sent to {len(users)} users', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    
    # GET request - render the form
    pathogens = Pathogen.query.all()
    antibiotics = Antibiotic.query.all()
    
    return render_template('admin/create_alert.html',
                          pathogens=pathogens,
                          antibiotics=antibiotics,
                          user_roles=UserRole)

@alerts_bp.route('/api/latest')
@login_required
def get_latest_alerts():
    """API endpoint to get latest alerts for notification checks"""
    # Get alerts from the last 24 hours that are unread
    since = datetime.now() - timedelta(days=1)
    alerts = Alert.query.filter(
        Alert.user_id == current_user.id,
        Alert.read == False,
        Alert.created_at >= since
    ).order_by(Alert.created_at.desc()).all()
    
    results = []
    for alert in alerts:
        results.append({
            'id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(results)

@alerts_bp.route('/api/counts')
@login_required
def get_alert_counts():
    """API endpoint to get counts of different alert types"""
    unread_count = Alert.query.filter(Alert.user_id == current_user.id, Alert.read == False).count()
    
    # Count by severity
    severity_counts = db.session.query(
        Alert.severity,
        db.func.count(Alert.id).label('count')
    ).filter(
        Alert.user_id == current_user.id,
        Alert.read == False
    ).group_by(
        Alert.severity
    ).all()
    
    # Format results
    severity_data = {}
    for severity, count in severity_counts:
        severity_data[str(severity)] = count
    
    return jsonify({
        'unread_count': unread_count,
        'severity_counts': severity_data
    })

@alerts_bp.route('/treatment')
@login_required
def treatment_guidance():
    """Get treatment guidance based on alerts"""
    # Get alerts with pathogen information
    alerts = Alert.query.filter(
        Alert.user_id == current_user.id, 
        Alert.pathogen_id.isnot(None)
    ).order_by(Alert.created_at.desc()).limit(10).all()
    
    return render_template('treatment_alert.html', alerts=alerts)