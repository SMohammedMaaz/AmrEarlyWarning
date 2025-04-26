from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps

from app import db
from models import User, Facility, UserRole

# Helper function to check if user is admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('This page requires administrator privileges', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with overview of system statistics"""
    # Get counts for dashboard
    lab_reports_count = 0  # To be implemented
    active_users_count = User.query.filter_by(is_active=True).count()
    alerts_count = 0  # To be implemented
    resistance_patterns_count = 0  # To be implemented
    
    # Get users and facilities for management
    users = User.query.all()
    facilities = Facility.query.all()
    
    return render_template('admin.html', 
                          users=users,
                          facilities=facilities,
                          lab_reports_count=lab_reports_count,
                          active_users_count=active_users_count,
                          alerts_count=alerts_count,
                          resistance_patterns_count=resistance_patterns_count)

@admin_bp.route('/facility/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_facility():
    """Add a new healthcare facility"""
    if request.method == 'POST':
        name = request.form.get('name')
        facility_type = request.form.get('facility_type')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        country = request.form.get('country')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        contact_email = request.form.get('contact_email')
        contact_phone = request.form.get('contact_phone')
        
        # Validate required fields
        if not name or not city or not country:
            flash('Name, city and country are required', 'danger')
            return redirect(url_for('admin.add_facility'))
        
        # Create new facility
        facility = Facility(
            name=name,
            facility_type=facility_type,
            address=address,
            city=city,
            state=state,
            country=country,
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None,
            contact_email=contact_email,
            contact_phone=contact_phone
        )
        
        db.session.add(facility)
        db.session.commit()
        
        flash('Facility added successfully', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('admin/add_facility.html')