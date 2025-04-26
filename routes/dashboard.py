from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import json
from datetime import datetime, timedelta
import logging

from app import db
from models import LabReport, Facility, Pathogen, ResistanceProfile, User, Antibiotic

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def home():
    # Get summary data for dashboard
    total_samples = LabReport.query.count()
    total_facilities = Facility.query.count()
    total_pathogens = Pathogen.query.count()
    
    # Calculate resistance rates
    resistant_count = db.session.query(db.func.count(ResistanceProfile.id)).filter(ResistanceProfile.result == 'R').scalar() or 0
    total_tests = db.session.query(db.func.count(ResistanceProfile.id)).scalar() or 0
    resistance_rate = round((resistant_count / total_tests * 100) if total_tests > 0 else 0, 2)
    
    # Get recent lab data
    recent_data = LabReport.query.order_by(LabReport.report_date.desc()).limit(5).all()
    
    # Get most common resistant pathogens
    common_resistant_pathogens = db.session.query(
        Pathogen.name, 
        db.func.count(ResistanceProfile.id).label('count')
    ).join(
        ResistanceProfile, ResistanceProfile.pathogen_id == Pathogen.id
    ).filter(
        ResistanceProfile.result == 'R'
    ).group_by(
        Pathogen.id
    ).order_by(
        db.func.count(ResistanceProfile.id).desc()
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                          total_samples=total_samples,
                          total_facilities=total_facilities,
                          total_pathogens=total_pathogens,
                          resistance_rate=resistance_rate,
                          recent_data=recent_data,
                          common_resistant_pathogens=common_resistant_pathogens)

@dashboard_bp.route('/map')
@login_required
def map_view():
    return render_template('map.html')

@dashboard_bp.route('/api/map_data')
@login_required
def map_data():
    # Get all facilities with coordinates
    data_points = []
    
    # Get facilities with coordinates
    facilities = Facility.query.filter(
        Facility.latitude.isnot(None),
        Facility.longitude.isnot(None)
    ).all()
    
    for facility in facilities:
        # Calculate resistance level at this facility
        lab_reports = facility.reports.all()
        resistance_profiles = []
        for report in lab_reports:
            resistance_profiles.extend(report.resistance_profiles.all())
        
        resistant_count = sum(1 for profile in resistance_profiles if profile.result == 'R')
        resistance_level = (resistant_count / len(resistance_profiles) * 100) if resistance_profiles else 0
        
        data_point = {
            'id': facility.id,
            'lat': facility.latitude,
            'lng': facility.longitude,
            'type': 'facility',
            'resistance_level': resistance_level,
            'name': facility.name,
            'facility_type': facility.facility_type
        }
        data_points.append(data_point)
    
    return jsonify(data_points)

@dashboard_bp.route('/api/resistance_trends')
@login_required
def resistance_trends():
    # Calculate resistance trends over the past 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Get monthly resistance rates
    results = []
    
    # Iterate through each month
    current_date = start_date
    while current_date < end_date:
        month_end = min(datetime(current_date.year, current_date.month + 1, 1) - timedelta(days=1), end_date)
        
        # Query for that month
        month_resistant = db.session.query(db.func.count(ResistanceProfile.id)).join(
            LabReport, ResistanceProfile.lab_report_id == LabReport.id
        ).filter(
            ResistanceProfile.result == 'R',
            LabReport.report_date >= current_date,
            LabReport.report_date <= month_end
        ).scalar() or 0
        
        month_total = db.session.query(db.func.count(ResistanceProfile.id)).join(
            LabReport, ResistanceProfile.lab_report_id == LabReport.id
        ).filter(
            LabReport.report_date >= current_date,
            LabReport.report_date <= month_end
        ).scalar() or 0
        
        resistance_rate = (month_resistant / month_total * 100) if month_total > 0 else 0
        
        results.append({
            'date': current_date.strftime('%Y-%m'),
            'resistance_rate': round(resistance_rate, 2)
        })
        
        # Move to next month
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1)
    
    return jsonify(results)

@dashboard_bp.route('/api/pathogen_distribution')
@login_required
def pathogen_distribution():
    # Get distribution of different pathogens
    results = db.session.query(
        Pathogen.name,
        db.func.count(ResistanceProfile.id).label('count')
    ).join(
        ResistanceProfile, ResistanceProfile.pathogen_id == Pathogen.id
    ).group_by(
        Pathogen.id
    ).order_by(
        db.func.count(ResistanceProfile.id).desc()
    ).all()
    
    data = [{'name': name, 'count': count} for name, count in results]
    return jsonify(data)

@dashboard_bp.route('/api/antibiotic_effectiveness')
@login_required
def antibiotic_effectiveness():
    # Get effectiveness of different antibiotics
    results = db.session.query(
        Antibiotic.name,
        db.func.count(ResistanceProfile.id).label('total'),
        db.func.sum(db.case([(ResistanceProfile.result == 'S', 1)], else_=0)).label('susceptible'),
        db.func.sum(db.case([(ResistanceProfile.result == 'I', 1)], else_=0)).label('intermediate'),
        db.func.sum(db.case([(ResistanceProfile.result == 'R', 1)], else_=0)).label('resistant')
    ).join(
        ResistanceProfile, ResistanceProfile.antibiotic_id == Antibiotic.id
    ).group_by(
        Antibiotic.id
    ).all()
    
    data = []
    for antibiotic, total, susceptible, intermediate, resistant in results:
        if total > 0:
            data.append({
                'antibiotic': antibiotic,
                'susceptible_percent': round(susceptible / total * 100, 2),
                'intermediate_percent': round(intermediate / total * 100, 2),
                'resistant_percent': round(resistant / total * 100, 2),
                'total': total
            })
    
    return jsonify(data)

@dashboard_bp.route('/api/regional_comparison')
@login_required
def regional_comparison():
    # Compare resistance rates between regions
    results = db.session.query(
        Facility.state,
        db.func.count(ResistanceProfile.id).label('total'),
        db.func.sum(db.case([(ResistanceProfile.result == 'R', 1)], else_=0)).label('resistant')
    ).join(
        LabReport, LabReport.facility_id == Facility.id
    ).join(
        ResistanceProfile, ResistanceProfile.lab_report_id == LabReport.id
    ).filter(
        Facility.state.isnot(None)
    ).group_by(
        Facility.state
    ).all()
    
    data = []
    for state, total, resistant in results:
        if total > 0:
            data.append({
                'region': state,
                'resistance_rate': round(resistant / total * 100, 2)
            })
    
    return jsonify(data)

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')

@dashboard_bp.route('/predictions')
@login_required
def predictions():
    return render_template('predictions.html')