import pandas as pd
import json
import logging
from datetime import datetime
import uuid

from app import db
from models import (
    Pathogen, Antibiotic, LabReport, ResistanceProfile, 
    Facility, User, Alert, UserRole, EnvironmentalSample
)
from utils import hash_patient_id, format_date, generate_report_id, calculate_resistance_risk

def process_lab_data(data, facility_id, user_id):
    """Process lab data and save to database"""
    processed_count = 0
    
    try:
        # Get facility
        facility = Facility.query.get(facility_id)
        if not facility:
            raise ValueError("Invalid facility ID")
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Invalid user ID")
        
        # Process each record
        for record in data:
            try:
                # Check if required fields are present
                required_fields = ['pathogen', 'antibiotic', 'result']
                if not all(field in record for field in required_fields):
                    logging.warning(f"Missing required fields in record: {record}")
                    continue
                
                # Create or get pathogen
                pathogen_name = record['pathogen']
                pathogen = Pathogen.query.filter_by(name=pathogen_name).first()
                if not pathogen:
                    pathogen = Pathogen(
                        name=pathogen_name,
                        scientific_name=record.get('scientific_name', ''),
                        pathogen_type=record.get('pathogen_type', '')
                    )
                    db.session.add(pathogen)
                    db.session.flush()  # Get the ID
                
                # Create or get antibiotic
                antibiotic_name = record['antibiotic']
                antibiotic = Antibiotic.query.filter_by(name=antibiotic_name).first()
                if not antibiotic:
                    antibiotic = Antibiotic(
                        name=antibiotic_name,
                        drug_class=record.get('drug_class', '')
                    )
                    db.session.add(antibiotic)
                    db.session.flush()  # Get the ID
                
                # Process dates
                report_date = datetime.utcnow()
                if 'report_date' in record:
                    try:
                        report_date = format_date(record['report_date'])
                    except:
                        pass
                
                sample_date = None
                if 'sample_date' in record:
                    try:
                        sample_date = format_date(record['sample_date'])
                    except:
                        pass
                
                # Process patient info (with privacy protections)
                patient_id = record.get('patient_id', '')
                if patient_id:
                    patient_id = hash_patient_id(patient_id)
                
                # Create lab report
                lab_report = LabReport(
                    report_id=generate_report_id(),
                    facility_id=facility.id,
                    user_id=user.id,
                    report_date=report_date,
                    sample_collection_date=sample_date,
                    sample_type=record.get('sample_type', ''),
                    patient_age=record.get('patient_age'),
                    patient_gender=record.get('patient_gender', ''),
                    patient_identifier=patient_id,
                    clinical_diagnosis=record.get('clinical_diagnosis', '')
                )
                db.session.add(lab_report)
                db.session.flush()  # Get the ID
                
                # Create resistance profile
                resistance_profile = ResistanceProfile(
                    lab_report_id=lab_report.id,
                    pathogen_id=pathogen.id,
                    antibiotic_id=antibiotic.id,
                    result=record['result'],
                    mic_value=record.get('mic_value'),
                    mutation_data=record.get('mutation_data')
                )
                db.session.add(resistance_profile)
                
                processed_count += 1
                
                # Check for critical resistance and create alerts if necessary
                if record['result'] == 'R' and record.get('is_critical', False):
                    create_resistance_alert(resistance_profile, facility)
            
            except Exception as e:
                logging.error(f"Error processing record: {str(e)}")
                continue
        
        # Commit all changes
        db.session.commit()
        
        return processed_count
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in process_lab_data: {str(e)}")
        raise

def create_resistance_alert(resistance_profile, facility):
    """Create alerts for critical resistance patterns"""
    try:
        # Get related objects
        pathogen = Pathogen.query.get(resistance_profile.pathogen_id)
        antibiotic = Antibiotic.query.get(resistance_profile.antibiotic_id)
        
        # Create alert
        alert = Alert(
            title=f"Critical resistance detected: {pathogen.name} to {antibiotic.name}",
            message=f"A critical resistance pattern has been detected at {facility.name}. " +
                    f"{pathogen.name} showing resistance to {antibiotic.name}. " +
                    f"Consider revising treatment protocols for affected patients.",
            alert_type="critical_resistance",
            severity=4,  # High severity
            latitude=facility.latitude,
            longitude=facility.longitude,
            region=facility.state,
            pathogen_id=pathogen.id,
            antibiotic_id=antibiotic.id
        )
        
        # Create alerts for relevant users
        # Alert doctors and public health officials
        relevant_users = User.query.filter(
            User.role.in_([UserRole.DOCTOR, UserRole.PUBLIC_HEALTH_OFFICIAL])
        ).all()
        
        for user in relevant_users:
            alert_copy = Alert(**alert.__dict__)
            alert_copy.user_id = user.id
            db.session.add(alert_copy)
        
        db.session.flush()
        
    except Exception as e:
        logging.error(f"Error creating resistance alert: {str(e)}")

def process_environmental_sample(data, user_id):
    """Process environmental sensor data"""
    try:
        # Get user
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Invalid user ID")
        
        # Process the environmental sample data
        sample_id = data.get('sample_id', f"ENV-{uuid.uuid4().hex[:8].upper()}")
        sample_type = data.get('sample_type', 'unknown')
        collection_date = format_date(data.get('collection_date', datetime.utcnow().strftime('%Y-%m-%d')))
        latitude = data.get('latitude', 0)
        longitude = data.get('longitude', 0)
        location_description = data.get('location_description', '')
        
        # Check if pathogen was detected
        pathogen_detected = data.get('pathogen_detected', False)
        pathogen_id = None
        pathogen_load = None
        
        if pathogen_detected:
            # Get or create pathogen
            pathogen_name = data.get('pathogen_name')
            if pathogen_name:
                pathogen = Pathogen.query.filter_by(name=pathogen_name).first()
                if not pathogen:
                    pathogen = Pathogen(
                        name=pathogen_name,
                        scientific_name=data.get('scientific_name', ''),
                        pathogen_type=data.get('pathogen_type', 'bacteria')
                    )
                    db.session.add(pathogen)
                    db.session.flush()
                
                pathogen_id = pathogen.id
                pathogen_load = data.get('pathogen_load')
        
        # Create environmental sample record
        sample = EnvironmentalSample(
            sample_id=sample_id,
            sample_type=sample_type,
            collection_date=collection_date,
            latitude=latitude,
            longitude=longitude,
            location_description=location_description,
            pathogen_detected=pathogen_detected,
            pathogen_id=pathogen_id,
            pathogen_load=pathogen_load,
            user_id=user_id,
            notes=data.get('notes', '')
        )
        
        db.session.add(sample)
        db.session.commit()
        
        # Create alert if pathogen detected
        if pathogen_detected and pathogen_id:
            create_environmental_alert(sample)
        
        return sample.id
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in process_environmental_sample: {str(e)}")
        raise

def create_environmental_alert(sample):
    """Create alerts for environmental pathogen detection"""
    try:
        # Get pathogen
        pathogen = Pathogen.query.get(sample.pathogen_id)
        if not pathogen:
            return
        
        # Determine severity based on pathogen load
        severity = 3  # Medium by default
        if sample.pathogen_load:
            if sample.pathogen_load > 1000:
                severity = 5  # Very high
            elif sample.pathogen_load > 500:
                severity = 4  # High
        
        # Create alert
        alert = Alert(
            title=f"{pathogen.name} detected in environmental sample",
            message=f"{pathogen.name} has been detected in a {sample.sample_type} sample collected at {sample.location_description}. " +
                    f"Collection date: {sample.collection_date.strftime('%Y-%m-%d')}. " +
                    (f"Pathogen load: {sample.pathogen_load}. " if sample.pathogen_load else "") +
                    f"Please monitor the situation and consider preventive measures.",
            alert_type="environmental_detection",
            severity=severity,
            latitude=sample.latitude,
            longitude=sample.longitude,
            region=sample.location_description,
            pathogen_id=pathogen.id
        )
        
        # Alert public health officials
        users = User.query.filter_by(role=UserRole.PUBLIC_HEALTH_OFFICIAL).all()
        for user in users:
            alert_copy = Alert(**alert.__dict__)
            alert_copy.user_id = user.id
            db.session.add(alert_copy)
        
        db.session.commit()
        
    except Exception as e:
        logging.error(f"Error creating environmental alert: {str(e)}")

def generate_resistance_map():
    """Generate geospatial data for resistance mapping"""
    try:
        # Get facilities with resistance data
        facilities = db.session.query(
            Facility.id, Facility.name, Facility.latitude, Facility.longitude,
            Facility.city, Facility.state, Facility.country
        ).all()
        
        map_data = []
        
        for facility in facilities:
            # Skip facilities without coordinates
            if not facility.latitude or not facility.longitude:
                continue
                
            # Get resistance data for this facility
            resistance_data = db.session.query(
                Pathogen.name, 
                db.func.count(ResistanceProfile.id).label('total'),
                db.func.sum(db.case([(ResistanceProfile.result == 'R', 1)], else_=0)).label('resistant')
            ).join(
                ResistanceProfile, ResistanceProfile.pathogen_id == Pathogen.id
            ).join(
                LabReport, LabReport.id == ResistanceProfile.lab_report_id
            ).filter(
                LabReport.facility_id == facility.id
            ).group_by(
                Pathogen.name
            ).all()
            
            # Calculate overall resistance percentage
            total_samples = sum(row.total for row in resistance_data)
            total_resistant = sum(row.resistant for row in resistance_data)
            
            resistance_percentage = 0
            if total_samples > 0:
                resistance_percentage = (total_resistant / total_samples) * 100
            
            # Determine risk level based on percentage
            risk_level = "Low"
            color = "#28a745"  # Green
            
            if resistance_percentage >= 75:
                risk_level = "Very High"
                color = "#dc3545"  # Red
            elif resistance_percentage >= 50:
                risk_level = "High"
                color = "#fd7e14"  # Orange
            elif resistance_percentage >= 25:
                risk_level = "Medium"
                color = "#ffc107"  # Yellow
            
            # Add pathogen breakdown
            pathogen_breakdown = []
            for row in resistance_data:
                if row.total > 0:
                    pathogen_breakdown.append({
                        "name": row.name,
                        "total": row.total,
                        "resistant": row.resistant,
                        "percentage": round((row.resistant / row.total) * 100, 1)
                    })
            
            # Sort by percentage
            pathogen_breakdown.sort(key=lambda x: x["percentage"], reverse=True)
            
            # Add to map data
            map_data.append({
                "id": facility.id,
                "name": facility.name,
                "latitude": facility.latitude,
                "longitude": facility.longitude,
                "location": f"{facility.city}, {facility.state}, {facility.country}",
                "resistancePercentage": round(resistance_percentage, 1),
                "riskLevel": risk_level,
                "color": color,
                "totalSamples": total_samples,
                "totalResistant": total_resistant,
                "pathogens": pathogen_breakdown
            })
        
        # Add environmental samples
        env_samples = db.session.query(
            EnvironmentalSample.id, EnvironmentalSample.sample_id, 
            EnvironmentalSample.latitude, EnvironmentalSample.longitude,
            EnvironmentalSample.location_description, EnvironmentalSample.sample_type,
            EnvironmentalSample.pathogen_detected, EnvironmentalSample.pathogen_load,
            Pathogen.name.label('pathogen_name')
        ).outerjoin(
            Pathogen, EnvironmentalSample.pathogen_id == Pathogen.id
        ).filter(
            EnvironmentalSample.pathogen_detected == True
        ).all()
        
        for sample in env_samples:
            # Skip samples without coordinates
            if not sample.latitude or not sample.longitude:
                continue
            
            # Determine risk level based on pathogen load
            risk_level = "Medium"
            color = "#ffc107"  # Yellow
            
            if sample.pathogen_load:
                if sample.pathogen_load > 1000:
                    risk_level = "Very High"
                    color = "#dc3545"  # Red
                elif sample.pathogen_load > 500:
                    risk_level = "High"
                    color = "#fd7e14"  # Orange
            
            # Add to map data
            map_data.append({
                "id": f"env-{sample.id}",
                "name": f"Environmental Sample: {sample.sample_id}",
                "latitude": sample.latitude,
                "longitude": sample.longitude,
                "location": sample.location_description,
                "resistancePercentage": None,  # Not applicable
                "riskLevel": risk_level,
                "color": color,
                "isEnvironmentalSample": True,
                "sampleType": sample.sample_type,
                "pathogen": sample.pathogen_name,
                "pathogenLoad": sample.pathogen_load
            })
        
        return map_data
        
    except Exception as e:
        logging.error(f"Error generating resistance map: {str(e)}")
        return []
