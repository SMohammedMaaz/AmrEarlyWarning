import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
import logging

from app import db
from models import Alert, AlertPriority, AlertStatus, User, Organization, Pathogen

logger = logging.getLogger(__name__)

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')

@alerts_bp.route('/')
@login_required
def alerts_view():
    # Get filter parameters
    status = request.args.get('status')
    priority = request.args.get('priority')
    
    # Build query with filters
    query = Alert.query
    
    if status:
        query = query.filter(Alert.status == AlertStatus(status))
    if priority:
        query = query.filter(Alert.priority == AlertPriority(priority))
    
    # Get alerts for the current user
    alerts = query.filter(Alert.user_id == current_user.id).order_by(Alert.created_at.desc()).all()
    
    return render_template('alerts.html', alerts=alerts, 
                          alert_statuses=AlertStatus, 
                          alert_priorities=AlertPriority)

@alerts_bp.route('/acknowledge/<int:alert_id>', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    
    # Check if the alert belongs to the current user
    if alert.user_id != current_user.id:
        flash('You do not have permission to acknowledge this alert', 'danger')
        return redirect(url_for('alerts.alerts_view'))
    
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.utcnow()
    db.session.commit()
    
    flash('Alert acknowledged', 'success')
    return redirect(url_for('alerts.alerts_view'))

@alerts_bp.route('/resolve/<int:alert_id>', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    
    # Check if the alert belongs to the current user
    if alert.user_id != current_user.id:
        flash('You do not have permission to resolve this alert', 'danger')
        return redirect(url_for('alerts.alerts_view'))
    
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    db.session.commit()
    
    flash('Alert resolved', 'success')
    return redirect(url_for('alerts.alerts_view'))

@alerts_bp.route('/dismiss/<int:alert_id>', methods=['POST'])
@login_required
def dismiss_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    
    # Check if the alert belongs to the current user
    if alert.user_id != current_user.id:
        flash('You do not have permission to dismiss this alert', 'danger')
        return redirect(url_for('alerts.alerts_view'))
    
    alert.status = AlertStatus.DISMISSED
    db.session.commit()
    
    flash('Alert dismissed', 'success')
    return redirect(url_for('alerts.alerts_view'))

@alerts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_alert():
    pathogens = Pathogen.query.all()
    users = User.query.all()
    
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            message = request.form.get('message')
            priority = AlertPriority(request.form.get('priority'))
            user_id = request.form.get('user_id')
            lat = request.form.get('lat')
            lng = request.form.get('lng')
            radius = request.form.get('radius')
            pathogen_id = request.form.get('pathogen_id')
            recommendations = request.form.get('recommendations')
            
            alert = Alert(
                title=title,
                message=message,
                priority=priority,
                user_id=user_id,
                lat=lat if lat else None,
                lng=lng if lng else None,
                radius=radius if radius else None,
                pathogen_id=pathogen_id if pathogen_id else None,
                recommendations=recommendations
            )
            
            db.session.add(alert)
            db.session.commit()
            
            flash('Alert created successfully', 'success')
            return redirect(url_for('alerts.alerts_view'))
            
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
            flash(f'Error creating alert: {str(e)}', 'danger')
    
    return render_template('create_alert.html', 
                          pathogens=pathogens, 
                          users=users, 
                          alert_priorities=AlertPriority)

@alerts_bp.route('/api/latest')
@login_required
def get_latest_alerts():
    # Get the latest 10 alerts for the current user
    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.created_at.desc()).limit(10).all()
    
    alerts_list = []
    for alert in alerts:
        alerts_list.append({
            'id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'priority': alert.priority.value,
            'status': alert.status.value,
            'created_at': alert.created_at.isoformat(),
            'lat': alert.lat,
            'lng': alert.lng,
            'radius': alert.radius,
            'pathogen': alert.pathogen.name if alert.pathogen else None
        })
    
    return jsonify(alerts_list)

@alerts_bp.route('/api/counts')
@login_required
def get_alert_counts():
    # Count alerts by status for the current user
    new_count = Alert.query.filter_by(user_id=current_user.id, status=AlertStatus.NEW).count()
    acknowledged_count = Alert.query.filter_by(user_id=current_user.id, status=AlertStatus.ACKNOWLEDGED).count()
    resolved_count = Alert.query.filter_by(user_id=current_user.id, status=AlertStatus.RESOLVED).count()
    dismissed_count = Alert.query.filter_by(user_id=current_user.id, status=AlertStatus.DISMISSED).count()
    
    # Count alerts by priority for the current user
    low_count = Alert.query.filter_by(user_id=current_user.id, priority=AlertPriority.LOW).count()
    medium_count = Alert.query.filter_by(user_id=current_user.id, priority=AlertPriority.MEDIUM).count()
    high_count = Alert.query.filter_by(user_id=current_user.id, priority=AlertPriority.HIGH).count()
    critical_count = Alert.query.filter_by(user_id=current_user.id, priority=AlertPriority.CRITICAL).count()
    
    counts = {
        'status': {
            'new': new_count,
            'acknowledged': acknowledged_count,
            'resolved': resolved_count,
            'dismissed': dismissed_count
        },
        'priority': {
            'low': low_count,
            'medium': medium_count,
            'high': high_count,
            'critical': critical_count
        }
    }
    
    return jsonify(counts)

@alerts_bp.route('/guidance')
@login_required
def treatment_guidance():
    # Get alert for guidance if provided
    alert_id = request.args.get('alert_id')
    
    if alert_id:
        alert = Alert.query.get_or_404(alert_id)
        pathogen = alert.pathogen
    else:
        alert = None
        pathogen_id = request.args.get('pathogen_id')
        if pathogen_id:
            pathogen = Pathogen.query.get_or_404(pathogen_id)
        else:
            pathogen = None
    
    pathogens = Pathogen.query.all()
    
    # Get treatment guidelines for the selected pathogen
    guidelines = None
    if pathogen:
        # In a real application, you would query TreatmentGuideline model
        # For demonstration, we'll create some mock guidelines based on the pathogen
        guidelines = {
            'first_line': f"First-line treatment for {pathogen.name}",
            'second_line': f"Second-line treatment for {pathogen.name}",
            'alternatives': f"Alternative treatments for {pathogen.name}",
            'notes': "Follow standard protocols and adjust based on local antibiogram."
        }
    
    return render_template('guidance.html', 
                          alert=alert, 
                          pathogen=pathogen, 
                          pathogens=pathogens,
                          guidelines=guidelines)
