from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import pandas as pd
import json
from datetime import datetime, timedelta
import numpy as np
import logging

from app import db
from models import LabData, Organization, Pathogen, Antibiogram, GeoPoint

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def home():
    # Get summary data for dashboard
    total_samples = LabData.query.count()
    total_organizations = Organization.query.count()
    total_pathogens = Pathogen.query.count()
    
    # Calculate resistance rates
    resistant_count = db.session.query(db.func.count(Antibiogram.id)).filter(Antibiogram.susceptibility == 'R').scalar()
    total_tests = db.session.query(db.func.count(Antibiogram.id)).scalar()
    resistance_rate = round((resistant_count / total_tests * 100) if total_tests > 0 else 0, 2)
    
    # Get recent lab data
    recent_data = LabData.query.order_by(LabData.created_at.desc()).limit(5).all()
    
    # Get most common resistant pathogens
    common_resistant_pathogens = db.session.query(
        Pathogen.name, 
        db.func.count(Antibiogram.id).label('count')
    ).join(
        LabData, LabData.pathogen_id == Pathogen.id
    ).join(
        Antibiogram, Antibiogram.lab_data_id == LabData.id
    ).filter(
        Antibiogram.susceptibility == 'R'
    ).group_by(
        Pathogen.id
    ).order_by(
        db.func.count(Antibiogram.id).desc()
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                          total_samples=total_samples,
                          total_organizations=total_organizations,
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
    # Get all geo points with resistance data
    data_points = []
    
    # Process lab data with coordinates
    lab_data = LabData.query.filter(
        LabData.latitude.isnot(None),
        LabData.longitude.isnot(None)
    ).all()
    
    for data in lab_data:
        # Calculate resistance level (percentage of resistant results)
        antibiograms = data.antibiograms.all()
        resistant_count = sum(1 for a in antibiograms if a.susceptibility == 'R')
        resistance_level = (resistant_count / len(antibiograms) * 100) if antibiograms else 0
        
        data_point = {
            'id': data.id,
            'lat': data.latitude,
            'lng': data.longitude,
            'type': 'lab_data',
            'resistance_level': resistance_level,
            'pathogen': data.pathogen.name if data.pathogen else 'Unknown',
            'date': data.collection_date.strftime('%Y-%m-%d'),
            'organization': data.organization.name if data.organization else 'Unknown'
        }
        data_points.append(data_point)
    
    # Also get organization locations
    orgs = Organization.query.filter(
        Organization.latitude.isnot(None),
        Organization.longitude.isnot(None)
    ).all()
    
    for org in orgs:
        data_point = {
            'id': f"org_{org.id}",
            'lat': org.latitude,
            'lng': org.longitude,
            'type': 'organization',
            'name': org.name,
            'org_type': org.org_type.value if org.org_type else 'Unknown'
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
        month_resistant = db.session.query(db.func.count(Antibiogram.id)).join(
            LabData, Antibiogram.lab_data_id == LabData.id
        ).filter(
            Antibiogram.susceptibility == 'R',
            LabData.collection_date >= current_date,
            LabData.collection_date <= month_end
        ).scalar()
        
        month_total = db.session.query(db.func.count(Antibiogram.id)).join(
            LabData, Antibiogram.lab_data_id == LabData.id
        ).filter(
            LabData.collection_date >= current_date,
            LabData.collection_date <= month_end
        ).scalar()
        
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
        db.func.count(LabData.id).label('count')
    ).join(
        LabData, LabData.pathogen_id == Pathogen.id
    ).group_by(
        Pathogen.id
    ).order_by(
        db.func.count(LabData.id).desc()
    ).all()
    
    data = [{'name': name, 'count': count} for name, count in results]
    return jsonify(data)

@dashboard_bp.route('/api/antibiotic_effectiveness')
@login_required
def antibiotic_effectiveness():
    # Get effectiveness of different antibiotics
    results = db.session.query(
        Antibiogram.antibiotic_name,
        db.func.count(Antibiogram.id).label('total'),
        db.func.sum(db.case([(Antibiogram.susceptibility == 'S', 1)], else_=0)).label('susceptible'),
        db.func.sum(db.case([(Antibiogram.susceptibility == 'I', 1)], else_=0)).label('intermediate'),
        db.func.sum(db.case([(Antibiogram.susceptibility == 'R', 1)], else_=0)).label('resistant')
    ).group_by(
        Antibiogram.antibiotic_name
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
        Organization.state,
        db.func.count(Antibiogram.id).label('total'),
        db.func.sum(db.case([(Antibiogram.susceptibility == 'R', 1)], else_=0)).label('resistant')
    ).join(
        LabData, LabData.organization_id == Organization.id
    ).join(
        Antibiogram, Antibiogram.lab_data_id == LabData.id
    ).filter(
        Organization.state.isnot(None)
    ).group_by(
        Organization.state
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
