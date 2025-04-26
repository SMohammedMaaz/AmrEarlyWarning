from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import pandas as pd
import json
import os
import logging
from datetime import datetime

from app import db
from models import LabReport, Facility, Pathogen, Antibiotic, ResistanceProfile
from utils import allowed_file, parse_csv, parse_json, hash_patient_id, generate_report_id

logger = logging.getLogger(__name__)

data_bp = Blueprint('data', __name__, url_prefix='/data')

@data_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Handle data uploads from various sources"""
    if request.method == 'POST':
        # Check what type of upload it is
        upload_type = request.form.get('upload_type')
        
        if upload_type == 'file':
            # File upload
            if 'file' not in request.files:
                flash('No file part', 'danger')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                facility_id = request.form.get('facility_id')
                
                try:
                    if filename.endswith('.csv'):
                        data = parse_csv(file)
                        success_count = process_csv_data(data, facility_id)
                    elif filename.endswith('.json'):
                        data = parse_json(file)
                        success_count = process_json_data(data, facility_id)
                    else:
                        flash('Unsupported file format', 'danger')
                        return redirect(request.url)
                    
                    flash(f'Successfully processed {success_count} records', 'success')
                    return redirect(url_for('dashboard.home'))
                
                except Exception as e:
                    logger.error(f"Error processing uploaded file: {str(e)}")
                    flash(f'Error processing file: {str(e)}', 'danger')
                    return redirect(request.url)
            else:
                flash('File type not allowed', 'danger')
                return redirect(request.url)
        
        elif upload_type == 'form':
            # Direct form input
            try:
                success = process_form_data(request.form)
                if success:
                    flash('Data successfully submitted', 'success')
                    return redirect(url_for('dashboard.home'))
                else:
                    flash('Error processing the form data', 'danger')
                    return redirect(request.url)
            except Exception as e:
                logger.error(f"Error processing form data: {str(e)}")
                flash(f'Error: {str(e)}', 'danger')
                return redirect(request.url)
    
    # GET request - render the upload form
    facilities = Facility.query.all()
    pathogens = Pathogen.query.all()
    antibiotics = Antibiotic.query.all()
    
    return render_template('upload.html', 
                          facilities=facilities,
                          pathogens=pathogens,
                          antibiotics=antibiotics)

@data_bp.route('/view')
@login_required
def view_data():
    """View all submitted data with filtering options"""
    # Get filter parameters
    facility_id = request.args.get('facility_id', type=int)
    pathogen_id = request.args.get('pathogen_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Base query
    query = LabReport.query
    
    # Apply filters
    if facility_id:
        query = query.filter(LabReport.facility_id == facility_id)
    
    if pathogen_id:
        query = query.join(ResistanceProfile, LabReport.id == ResistanceProfile.lab_report_id) \
                    .filter(ResistanceProfile.pathogen_id == pathogen_id)
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(LabReport.report_date >= date_from)
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        query = query.filter(LabReport.report_date <= date_to)
    
    # Execute query with pagination
    page = request.args.get('page', 1, type=int)
    reports = query.order_by(LabReport.report_date.desc()).paginate(page=page, per_page=20)
    
    # Get facilities and pathogens for filters
    facilities = Facility.query.all()
    pathogens = Pathogen.query.all()
    
    return render_template('view_data.html',
                          reports=reports,
                          facilities=facilities,
                          pathogens=pathogens,
                          current_filters={
                              'facility_id': facility_id,
                              'pathogen_id': pathogen_id,
                              'date_from': date_from,
                              'date_to': date_to
                          })

@data_bp.route('/api/latest')
@login_required
def get_latest_data():
    """API endpoint to get the latest data for dashboard"""
    latest_reports = LabReport.query.order_by(LabReport.report_date.desc()).limit(10).all()
    
    results = []
    for report in latest_reports:
        facility_name = report.facility.name if report.facility else 'Unknown'
        
        # Get resistance profiles for this report
        resistance_data = []
        for profile in report.resistance_profiles:
            resistance_data.append({
                'pathogen': profile.pathogen.name if profile.pathogen else 'Unknown',
                'antibiotic': profile.antibiotic.name if profile.antibiotic else 'Unknown',
                'result': profile.result
            })
        
        results.append({
            'id': report.id,
            'report_date': report.report_date.strftime('%Y-%m-%d'),
            'facility': facility_name,
            'sample_type': report.sample_type,
            'resistance_data': resistance_data
        })
    
    return jsonify(results)

@data_bp.route('/api/resistance_by_region')
@login_required
def get_resistance_by_region():
    """API endpoint to get resistance data by region for maps"""
    regions = db.session.query(
        Facility.state,
        db.func.count(ResistanceProfile.id).label('total_tests'),
        db.func.sum(db.case([(ResistanceProfile.result == 'R', 1)], else_=0)).label('resistant_count')
    ).join(
        LabReport, LabReport.facility_id == Facility.id
    ).join(
        ResistanceProfile, ResistanceProfile.lab_report_id == LabReport.id
    ).filter(
        Facility.state.isnot(None)
    ).group_by(
        Facility.state
    ).all()
    
    results = []
    for region, total, resistant in regions:
        resistance_rate = round((resistant / total * 100) if total > 0 else 0, 2)
        results.append({
            'region': region,
            'total_tests': total,
            'resistant_count': resistant,
            'resistance_rate': resistance_rate
        })
    
    return jsonify(results)

def process_csv_data(df, facility_id):
    """Process CSV data upload."""
    success_count = 0
    
    # TODO: Implement actual CSV processing logic
    
    return success_count

def process_json_data(json_data, facility_id):
    """Process JSON data upload."""
    success_count = 0
    
    # TODO: Implement actual JSON processing logic
    
    return success_count

def process_form_data(form_data):
    """Process direct form submission."""
    try:
        # Extract basic report info
        facility_id = form_data.get('facility_id')
        sample_type = form_data.get('sample_type')
        sample_collection_date = datetime.strptime(form_data.get('sample_collection_date'), '%Y-%m-%d')
        patient_age = form_data.get('patient_age')
        patient_gender = form_data.get('patient_gender')
        patient_identifier = form_data.get('patient_identifier')
        clinical_diagnosis = form_data.get('clinical_diagnosis')
        
        # Hash the patient identifier for privacy
        hashed_patient_id = hash_patient_id(patient_identifier)
        
        # Create the lab report
        report = LabReport(
            report_id=generate_report_id(),
            facility_id=facility_id,
            user_id=current_user.id,
            sample_collection_date=sample_collection_date,
            sample_type=sample_type,
            patient_age=patient_age if patient_age else None,
            patient_gender=patient_gender,
            patient_identifier=hashed_patient_id,
            clinical_diagnosis=clinical_diagnosis
        )
        
        db.session.add(report)
        db.session.flush()  # Get the report ID without committing
        
        # Process resistance profiles
        # Assuming form has pathogen_id, antibiotic_id, and result fields
        pathogen_id = form_data.get('pathogen_id')
        
        # Handle multiple antibiotics (could be a list from checkbox/select)
        antibiotics = request.form.getlist('antibiotic_id')
        results = request.form.getlist('result')
        
        # Create resistance profiles
        for i in range(len(antibiotics)):
            if i < len(results):  # Ensure we have both antibiotic and result
                profile = ResistanceProfile(
                    lab_report_id=report.id,
                    pathogen_id=pathogen_id,
                    antibiotic_id=antibiotics[i],
                    result=results[i],
                    mic_value=form_data.get(f'mic_value_{antibiotics[i]}'),
                    mutation_data=form_data.get(f'mutation_data_{antibiotics[i]}')
                )
                db.session.add(profile)
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in process_form_data: {str(e)}")
        raise