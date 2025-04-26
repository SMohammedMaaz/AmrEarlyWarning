from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import pandas as pd
from datetime import datetime
import uuid
import logging

from app import db
from models import User, UserRole, Facility, Pathogen, Antibiotic, LabReport, ResistanceProfile, Alert, TreatmentGuideline, EnvironmentalSample
from utils import allowed_file, parse_csv, parse_json, send_alert, calculate_resistance_risk
from data_processing import process_lab_data, generate_resistance_map
from ml_models import predict_outbreak

# Blueprints
auth_bp = Blueprint('auth', __name__)
dashboard_bp = Blueprint('dashboard', __name__)
data_bp = Blueprint('data', __name__)
alerts_bp = Blueprint('alerts', __name__)
admin_bp = Blueprint('admin', __name__)
treatment_bp = Blueprint('treatment', __name__)

# Error handlers
@current_app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found", code=404), 404

@current_app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error="Internal server error", code=500), 500

# Authentication routes
@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    return render_template(
        'index.html',
        firebase_api_key=os.environ.get('FIREBASE_API_KEY'),
        firebase_project_id=os.environ.get('FIREBASE_PROJECT_ID'),
        firebase_app_id=os.environ.get('FIREBASE_APP_ID')
    )

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.home'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('index.html')

@auth_bp.route('/firebase-auth', methods=['POST'])
def firebase_auth():
    # Handle Firebase authentication
    try:
        data = request.get_json()
        firebase_uid = data.get('uid')
        email = data.get('email')
        display_name = data.get('displayName')
        
        # Check if user exists
        user = User.query.filter_by(firebase_uid=firebase_uid).first()
        
        if not user:
            # Create new user
            user = User(
                username=display_name or email.split('@')[0],
                email=email,
                firebase_uid=firebase_uid,
                role=UserRole.LAB_TECHNICIAN,  # Default role
                full_name=display_name
            )
            db.session.add(user)
            db.session.commit()
        
        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log in the user
        login_user(user)
        
        return jsonify({'success': True, 'redirect': url_for('dashboard.home')})
    
    except Exception as e:
        logging.error(f"Firebase auth error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    try:
        current_user.full_name = request.form.get('full_name')
        current_user.organization = request.form.get('organization')
        current_user.phone_number = request.form.get('phone_number')
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'danger')
    
    return redirect(url_for('auth.profile'))

# Dashboard routes
@dashboard_bp.route('/dashboard')
@login_required
def home():
    # Get resistance statistics
    recent_reports = LabReport.query.order_by(LabReport.report_date.desc()).limit(10).all()
    resistance_count = ResistanceProfile.query.filter_by(result='R').count()
    facility_count = Facility.query.count()
    pathogen_count = Pathogen.query.count()
    
    # Get alerts for the user
    recent_alerts = Alert.query.filter_by(user_id=current_user.id, read=False).order_by(Alert.created_at.desc()).limit(5).all()
    
    # Generate resistance map data
    map_data = generate_resistance_map()
    
    return render_template(
        'dashboard.html',
        recent_reports=recent_reports,
        resistance_count=resistance_count,
        facility_count=facility_count,
        pathogen_count=pathogen_count,
        recent_alerts=recent_alerts,
        map_data=json.dumps(map_data)
    )

@dashboard_bp.route('/map')
@login_required
def view_map():
    map_data = generate_resistance_map()
    return render_template('maps.html', map_data=json.dumps(map_data))

# Data upload and management routes
@data_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Process the uploaded file
                filename = file.filename
                facility_id = request.form.get('facility_id')
                
                if filename.endswith('.csv'):
                    data = parse_csv(file)
                elif filename.endswith('.json'):
                    data = parse_json(file)
                else:
                    flash('Unsupported file format', 'danger')
                    return redirect(request.url)
                
                # Process the data and save to database
                processed_count = process_lab_data(data, facility_id, current_user.id)
                
                flash(f'Successfully processed {processed_count} records', 'success')
                
                # Check for potential outbreaks
                check_for_outbreaks()
                
                return redirect(url_for('dashboard.home'))
                
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'danger')
                logging.error(f"Data upload error: {str(e)}")
                return redirect(request.url)
        else:
            flash('File type not allowed', 'danger')
            return redirect(request.url)
    
    # GET request - show upload form
    facilities = Facility.query.all()
    return render_template('data_upload.html', facilities=facilities)

def check_for_outbreaks():
    """Check for potential outbreaks based on recent data"""
    try:
        # Use machine learning model to predict outbreaks
        potential_outbreaks = predict_outbreak()
        
        if potential_outbreaks:
            for outbreak in potential_outbreaks:
                # Create alerts for the outbreak
                alert = Alert(
                    title=f"Potential {outbreak['pathogen']} outbreak detected",
                    message=f"Our system has detected a potential outbreak of {outbreak['pathogen']} in {outbreak['location']}. " +
                            f"Resistance level: {outbreak['resistance_level']}. Please take appropriate measures.",
                    alert_type="outbreak",
                    severity=outbreak['severity'],
                    latitude=outbreak['latitude'],
                    longitude=outbreak['longitude'],
                    region=outbreak['location'],
                    pathogen_id=outbreak['pathogen_id']
                )
                
                # Send alert to all public health officials
                users = User.query.filter_by(role=UserRole.PUBLIC_HEALTH_OFFICIAL).all()
                for user in users:
                    alert_copy = Alert(**alert.__dict__)
                    alert_copy.user_id = user.id
                    db.session.add(alert_copy)
                    
                    # Send notification (email, SMS, etc.)
                    send_alert(user, alert_copy)
                
                db.session.commit()
    
    except Exception as e:
        logging.error(f"Error checking for outbreaks: {str(e)}")

# Alert routes
@alerts_bp.route('/alerts')
@login_required
def view_alerts():
    page = request.args.get('page', 1, type=int)
    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.created_at.desc()).paginate(
        page=page, per_page=10
    )
    return render_template('alerts.html', alerts=alerts)

@alerts_bp.route('/alerts/<int:alert_id>/mark-read', methods=['POST'])
@login_required
def mark_alert_read(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    
    # Check if alert belongs to current user
    if alert.user_id != current_user.id:
        abort(403)
    
    alert.read = True
    db.session.commit()
    
    return jsonify({'success': True})

@alerts_bp.route('/alerts/<int:alert_id>/mark-action', methods=['POST'])
@login_required
def mark_alert_action(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    
    # Check if alert belongs to current user
    if alert.user_id != current_user.id:
        abort(403)
    
    alert.action_taken = True
    db.session.commit()
    
    return jsonify({'success': True})

# Admin routes
@admin_bp.route('/admin')
@login_required
def admin_dashboard():
    # Check if user has admin role
    if current_user.role != UserRole.ADMIN:
        abort(403)
    
    users = User.query.all()
    facilities = Facility.query.all()
    
    return render_template('admin.html', users=users, facilities=facilities)

@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_user(user_id):
    # Check if user has admin role
    if current_user.role != UserRole.ADMIN:
        abort(403)
    
    user = User.query.get_or_404(user_id)
    
    try:
        user.full_name = request.form.get('full_name')
        user.role = UserRole(request.form.get('role'))
        user.is_active = 'is_active' in request.form
        
        db.session.commit()
        flash('User updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/facilities/add', methods=['POST'])
@login_required
def add_facility():
    # Check if user has admin role
    if current_user.role != UserRole.ADMIN:
        abort(403)
    
    try:
        name = request.form.get('name')
        facility_type = request.form.get('facility_type')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        country = request.form.get('country')
        latitude = float(request.form.get('latitude'))
        longitude = float(request.form.get('longitude'))
        
        facility = Facility(
            name=name,
            facility_type=facility_type,
            address=address,
            city=city,
            state=state,
            country=country,
            latitude=latitude,
            longitude=longitude,
            contact_email=request.form.get('contact_email'),
            contact_phone=request.form.get('contact_phone')
        )
        
        db.session.add(facility)
        db.session.commit()
        
        flash('Facility added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding facility: {str(e)}', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

# Treatment guidance routes
@treatment_bp.route('/treatment-guidance')
@login_required
def treatment_guidance():
    pathogens = Pathogen.query.all()
    guidelines = TreatmentGuideline.query.all()
    
    return render_template('treatment_guidance.html', pathogens=pathogens, guidelines=guidelines)

@treatment_bp.route('/treatment-guidance/pathogen/<int:pathogen_id>')
@login_required
def pathogen_guidance(pathogen_id):
    pathogen = Pathogen.query.get_or_404(pathogen_id)
    guidelines = TreatmentGuideline.query.filter_by(pathogen_id=pathogen_id).all()
    
    # Get resistance data for this pathogen
    resistance_data = db.session.query(
        Antibiotic.name,
        db.func.count(ResistanceProfile.id).label('total'),
        db.func.sum(db.case([(ResistanceProfile.result == 'R', 1)], else_=0)).label('resistant')
    ).join(
        ResistanceProfile, ResistanceProfile.antibiotic_id == Antibiotic.id
    ).filter(
        ResistanceProfile.pathogen_id == pathogen_id
    ).group_by(
        Antibiotic.name
    ).all()
    
    # Calculate resistance percentages
    resistance_stats = []
    for name, total, resistant in resistance_data:
        if total > 0:
            percentage = (resistant / total) * 100
            resistance_stats.append({
                'antibiotic': name,
                'percentage': round(percentage, 1),
                'total': total,
                'resistant': resistant
            })
    
    return render_template(
        'treatment_guidance.html',
        pathogen=pathogen,
        guidelines=guidelines,
        resistance_stats=resistance_stats
    )

# API routes for AJAX calls

@dashboard_bp.route('/api/resistance-trends')
@login_required
def resistance_trends_api():
    # Get resistance trends over time
    # We'll calculate monthly resistance percentages for the past year
    
    try:
        # Get current date
        now = datetime.utcnow()
        
        # Build query for monthly resistance data
        monthly_data = []
        
        for i in range(11, -1, -1):
            # Calculate month start and end
            month_start = datetime(now.year - ((now.month - i - 1) // 12), 
                                ((now.month - i - 1) % 12) + 1, 1)
            
            if i > 0:
                month_end = datetime(now.year - ((now.month - i) // 12), 
                                    ((now.month - i) % 12) + 1, 1)
            else:
                # Current month - use current date
                month_end = now
            
            # Get counts for this month
            total_count = db.session.query(db.func.count(ResistanceProfile.id)).join(
                LabReport, ResistanceProfile.lab_report_id == LabReport.id
            ).filter(
                LabReport.report_date >= month_start,
                LabReport.report_date < month_end
            ).scalar() or 0
            
            resistant_count = db.session.query(db.func.count(ResistanceProfile.id)).join(
                LabReport, ResistanceProfile.lab_report_id == LabReport.id
            ).filter(
                LabReport.report_date >= month_start,
                LabReport.report_date < month_end,
                ResistanceProfile.result == 'R'
            ).scalar() or 0
            
            # Calculate percentage
            percentage = 0
            if total_count > 0:
                percentage = (resistant_count / total_count) * 100
            
            # Add to monthly data
            monthly_data.append({
                'month': month_start.strftime('%b %Y'),
                'percentage': round(percentage, 1),
                'total': total_count,
                'resistant': resistant_count
            })
        
        return jsonify(monthly_data)
        
    except Exception as e:
        logging.error(f"Error generating resistance trends: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/top-pathogens')
@login_required
def top_pathogens_api():
    # Get top pathogens by resistance prevalence
    try:
        top_pathogens = db.session.query(
            Pathogen.name,
            db.func.count(ResistanceProfile.id).label('total'),
            db.func.sum(db.case([(ResistanceProfile.result == 'R', 1)], else_=0)).label('resistant')
        ).join(
            ResistanceProfile, ResistanceProfile.pathogen_id == Pathogen.id
        ).group_by(
            Pathogen.name
        ).order_by(
            db.desc('resistant')
        ).limit(10).all()
        
        result = []
        for name, total, resistant in top_pathogens:
            if total > 0:
                percentage = (resistant / total) * 100
                result.append({
                    'pathogen': name,
                    'percentage': round(percentage, 1),
                    'total': total,
                    'resistant': resistant
                })
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error generating top pathogens: {str(e)}")
        return jsonify({'error': str(e)}), 500
