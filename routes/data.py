import os
import json
import pandas as pd
from io import StringIO
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
import logging

from app import db
from models import LabData, Organization, Pathogen, Antibiogram, User
from firebase_admin import upload_file

logger = logging.getLogger(__name__)

data_bp = Blueprint('data', __name__, url_prefix='/data')

@data_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    organizations = Organization.query.all()
    pathogens = Pathogen.query.all()
    
    if request.method == 'POST':
        try:
            # Check if it's a file upload or direct form submission
            if 'lab_data_file' in request.files and request.files['lab_data_file'].filename:
                file = request.files['lab_data_file']
                organization_id = request.form.get('organization_id')
                
                # Process file based on its type
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                    process_csv_data(df, organization_id)
                elif file.filename.endswith('.json'):
                    content = file.read().decode('utf-8')
                    json_data = json.loads(content)
                    process_json_data(json_data, organization_id)
                else:
                    flash('Unsupported file format. Please upload CSV or JSON files.', 'danger')
                    return render_template('data_upload.html', organizations=organizations, pathogens=pathogens)
                
                # Store the raw file in Firebase Storage
                file.seek(0)
                file_content = file.read()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                organization = Organization.query.get(organization_id)
                org_name = organization.name.lower().replace(' ', '_') if organization else 'unknown'
                file_path = f"lab_data/{org_name}/{timestamp}_{file.filename}"
                
                file_url = upload_file(file_content, file_path)
                
                flash('Data uploaded successfully!', 'success')
                
            else:
                # Direct form submission for a single record
                process_form_data(request.form)
                flash('Data submitted successfully!', 'success')
                
            return redirect(url_for('data.upload'))
                
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            flash(f'Error processing data: {str(e)}', 'danger')
    
    return render_template('data_upload.html', organizations=organizations, pathogens=pathogens)

@data_bp.route('/view')
@login_required
def view_data():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    org_id = request.args.get('organization_id', type=int)
    pathogen_id = request.args.get('pathogen_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build query with filters
    query = LabData.query
    
    if org_id:
        query = query.filter(LabData.organization_id == org_id)
    if pathogen_id:
        query = query.filter(LabData.pathogen_id == pathogen_id)
    if start_date:
        query = query.filter(LabData.collection_date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(LabData.collection_date <= datetime.strptime(end_date, '%Y-%m-%d'))
    
    # Order by most recent first
    query = query.order_by(LabData.collection_date.desc())
    
    # Paginate results
    data = query.paginate(page=page, per_page=per_page)
    
    organizations = Organization.query.all()
    pathogens = Pathogen.query.all()
    
    return render_template(
        'data_view.html', 
        data=data, 
        organizations=organizations, 
        pathogens=pathogens,
        selected_org=org_id,
        selected_pathogen=pathogen_id,
        start_date=start_date,
        end_date=end_date
    )

@data_bp.route('/api/latest')
@login_required
def get_latest_data():
    # Get latest 100 entries
    latest_data = LabData.query.order_by(LabData.collection_date.desc()).limit(100).all()
    
    data_list = []
    for data in latest_data:
        data_list.append({
            'id': data.id,
            'collection_date': data.collection_date.isoformat(),
            'organization': data.organization.name if data.organization else 'Unknown',
            'pathogen': data.pathogen.name if data.pathogen else 'Unknown',
            'latitude': data.latitude,
            'longitude': data.longitude,
            'resistance_profile': data.resistance_profile
        })
    
    return jsonify(data_list)

@data_bp.route('/api/resistance_by_region')
@login_required
def get_resistance_by_region():
    # Group resistance data by region
    results = db.session.query(
        Organization.state,
        Pathogen.name.label('pathogen'),
        db.func.count(Antibiogram.id).label('count'),
        db.func.sum(db.case([(Antibiogram.susceptibility == 'R', 1)], else_=0)).label('resistant_count')
    ).join(
        LabData, LabData.organization_id == Organization.id
    ).join(
        Pathogen, LabData.pathogen_id == Pathogen.id
    ).join(
        Antibiogram, Antibiogram.lab_data_id == LabData.id
    ).group_by(
        Organization.state, Pathogen.name
    ).all()
    
    data = {}
    for state, pathogen, count, resistant_count in results:
        if not state:
            continue
        
        if state not in data:
            data[state] = {}
        
        resistance_percent = (resistant_count / count * 100) if count > 0 else 0
        data[state][pathogen] = round(resistance_percent, 2)
    
    return jsonify(data)

def process_csv_data(df, organization_id):
    """Process CSV data upload."""
    # Example CSV processing logic - adjust according to your actual CSV format
    for index, row in df.iterrows():
        try:
            # Map CSV columns to database fields
            pathogen_name = row.get('pathogen', 'Unknown')
            pathogen = Pathogen.query.filter_by(name=pathogen_name).first()
            if not pathogen:
                pathogen = Pathogen(name=pathogen_name)
                db.session.add(pathogen)
                db.session.flush()
            
            # Create LabData entry
            lab_data = LabData(
                organization_id=organization_id,
                pathogen_id=pathogen.id,
                uploader_id=current_user.id,
                collection_date=datetime.strptime(row.get('collection_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'),
                latitude=row.get('latitude'),
                longitude=row.get('longitude'),
                sample_type=row.get('sample_type'),
                patient_demographics={
                    'age_group': row.get('age_group'),
                    'gender': row.get('gender'),
                    'region': row.get('region')
                }
            )
            
            # Process resistance data if available
            resistance_data = {}
            antibiotics = [col for col in df.columns if col.startswith('antibiotic_')]
            for antibiotic_col in antibiotics:
                antibiotic_name = antibiotic_col.replace('antibiotic_', '')
                susceptibility = row.get(antibiotic_col)
                if susceptibility:
                    resistance_data[antibiotic_name] = susceptibility
                    
                    # Also create an Antibiogram entry
                    antibiogram = Antibiogram(
                        antibiotic_name=antibiotic_name,
                        susceptibility=susceptibility[0].upper(),  # Use first letter (S, I, R)
                        testing_method=row.get('testing_method', 'unknown')
                    )
                    lab_data.antibiograms.append(antibiogram)
            
            lab_data.resistance_profile = resistance_data
            db.session.add(lab_data)
            
        except Exception as e:
            logger.error(f"Error processing row {index}: {str(e)}")
            continue
    
    db.session.commit()

def process_json_data(json_data, organization_id):
    """Process JSON data upload."""
    # Handle both single object and array formats
    records = json_data if isinstance(json_data, list) else [json_data]
    
    for record in records:
        try:
            # Get or create pathogen
            pathogen_name = record.get('pathogen', 'Unknown')
            pathogen = Pathogen.query.filter_by(name=pathogen_name).first()
            if not pathogen:
                pathogen = Pathogen(name=pathogen_name, 
                                   scientific_name=record.get('scientific_name'),
                                   pathogen_type=record.get('pathogen_type'))
                db.session.add(pathogen)
                db.session.flush()
            
            # Create LabData entry
            lab_data = LabData(
                organization_id=organization_id,
                pathogen_id=pathogen.id,
                uploader_id=current_user.id,
                collection_date=datetime.strptime(record.get('collection_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'),
                latitude=record.get('latitude'),
                longitude=record.get('longitude'),
                sample_type=record.get('sample_type'),
                patient_demographics=record.get('patient_demographics', {})
            )
            
            # Process resistance data
            resistance_profile = record.get('resistance_profile', {})
            lab_data.resistance_profile = resistance_profile
            
            # Add antibiograms
            for antibiotic, result in resistance_profile.items():
                susceptibility = result[0].upper() if isinstance(result, str) else 'U'  # Default to unknown
                antibiogram = Antibiogram(
                    antibiotic_name=antibiotic,
                    susceptibility=susceptibility,
                    testing_method=record.get('testing_method', 'unknown')
                )
                lab_data.antibiograms.append(antibiogram)
            
            db.session.add(lab_data)
            
        except Exception as e:
            logger.error(f"Error processing JSON record: {str(e)}")
            continue
    
    db.session.commit()

def process_form_data(form_data):
    """Process direct form submission."""
    organization_id = form_data.get('organization_id')
    pathogen_id = form_data.get('pathogen_id')
    collection_date_str = form_data.get('collection_date')
    collection_date = datetime.strptime(collection_date_str, '%Y-%m-%d') if collection_date_str else datetime.now()
    sample_type = form_data.get('sample_type')
    latitude = form_data.get('latitude')
    longitude = form_data.get('longitude')
    
    # Create patient demographics
    patient_demographics = {
        'age_group': form_data.get('age_group'),
        'gender': form_data.get('gender'),
        'region': form_data.get('region')
    }
    
    # Create resistance profile
    resistance_profile = {}
    antibiotics = [key for key in form_data.keys() if key.startswith('antibiotic_')]
    
    # Create lab data record
    lab_data = LabData(
        organization_id=organization_id,
        pathogen_id=pathogen_id,
        uploader_id=current_user.id,
        collection_date=collection_date,
        sample_type=sample_type,
        latitude=latitude,
        longitude=longitude,
        patient_demographics=patient_demographics,
        resistance_profile=resistance_profile
    )
    
    # Add antibiograms
    for antibiotic_key in antibiotics:
        antibiotic_name = antibiotic_key.replace('antibiotic_', '')
        susceptibility = form_data.get(antibiotic_key)
        
        if susceptibility:
            resistance_profile[antibiotic_name] = susceptibility
            
            antibiogram = Antibiogram(
                antibiotic_name=antibiotic_name,
                susceptibility=susceptibility[0].upper(),  # Use first letter (S, I, R)
                testing_method=form_data.get('testing_method', 'unknown')
            )
            lab_data.antibiograms.append(antibiogram)
    
    db.session.add(lab_data)
    db.session.commit()
