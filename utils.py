import os
import csv
import json
import pandas as pd
import io
import hashlib
import logging
from datetime import datetime
import requests
from flask import current_app

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv', 'json'}

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_csv(file):
    """Parse CSV file into a pandas DataFrame"""
    try:
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        df = pd.read_csv(stream)
        # Convert to dict for easier handling
        result = df.to_dict(orient='records')
        return result
    except Exception as e:
        logging.error(f"Error parsing CSV: {str(e)}")
        raise

def parse_json(file):
    """Parse JSON file into a dict"""
    try:
        # Read JSON file
        stream = io.StringIO(file.stream.read().decode("UTF8"))
        result = json.load(stream)
        return result
    except Exception as e:
        logging.error(f"Error parsing JSON: {str(e)}")
        raise

def hash_patient_id(patient_id, salt=None):
    """Hash patient identifier for privacy"""
    if not salt:
        salt = os.environ.get('PATIENT_ID_SALT', 'default_salt')
    
    # Create a hash of patient ID with salt
    combined = f"{patient_id}{salt}"
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    return hashed

def calculate_resistance_risk(pathogen_id, region):
    """Calculate resistance risk score for a pathogen in a region"""
    from models import ResistanceProfile, LabReport, Facility
    from app import db
    
    try:
        # Get resistance profiles for this pathogen in the region
        resistance_count = db.session.query(db.func.count(ResistanceProfile.id)).join(
            LabReport, ResistanceProfile.lab_report_id == LabReport.id
        ).join(
            Facility, LabReport.facility_id == Facility.id
        ).filter(
            ResistanceProfile.pathogen_id == pathogen_id,
            ResistanceProfile.result == 'R',
            Facility.state == region
        ).scalar() or 0
        
        total_count = db.session.query(db.func.count(ResistanceProfile.id)).join(
            LabReport, ResistanceProfile.lab_report_id == LabReport.id
        ).join(
            Facility, LabReport.facility_id == Facility.id
        ).filter(
            ResistanceProfile.pathogen_id == pathogen_id,
            Facility.state == region
        ).scalar() or 0
        
        # Calculate risk score (0-100)
        if total_count > 0:
            risk_score = (resistance_count / total_count) * 100
        else:
            risk_score = 0
            
        return risk_score
    
    except Exception as e:
        logging.error(f"Error calculating resistance risk: {str(e)}")
        return 0

def send_alert(user, alert):
    """Send alert notification to user via appropriate channels"""
    try:
        # Log the alert
        logging.info(f"Sending alert to {user.email}: {alert.title}")
        
        # Email notification
        if user.email:
            send_email_alert(user.email, alert)
        
        # SMS notification for high severity alerts
        if user.phone_number and alert.severity >= 4:
            send_sms_alert(user.phone_number, alert)
        
        # Push notification (if using Firebase)
        if current_app.config.get('FIREBASE_INITIALIZED', False):
            send_push_notification(user, alert)
            
    except Exception as e:
        logging.error(f"Error sending alert: {str(e)}")

def send_email_alert(email, alert):
    """Send email alert - placeholder for actual implementation"""
    # This would use an email service like SMTP, SendGrid, etc.
    logging.info(f"Email alert would be sent to {email}: {alert.title}")
    
    # Mock implementation - in a real app, you would use an email service
    print(f"[EMAIL] To: {email}, Subject: AMR Alert: {alert.title}, Body: {alert.message}")

def send_sms_alert(phone_number, alert):
    """Send SMS alert - placeholder for actual implementation"""
    # This would use an SMS service like Twilio, Vonage, etc.
    logging.info(f"SMS alert would be sent to {phone_number}: {alert.title}")
    
    # Mock implementation - in a real app, you would use an SMS service
    print(f"[SMS] To: {phone_number}, Message: AMR Alert: {alert.title[:50]}...")

def send_push_notification(user, alert):
    """Send push notification via Firebase Cloud Messaging"""
    # This would use Firebase Cloud Messaging
    logging.info(f"Push notification would be sent to user {user.id}: {alert.title}")
    
    # Mock implementation - in a real app, you would use Firebase Cloud Messaging
    print(f"[PUSH] To: User {user.id}, Title: {alert.title}, Body: {alert.message[:100]}...")

def validate_genomic_data(data):
    """Validate genomic sequencing data"""
    # Placeholder for genomic data validation
    return True

def format_date(date_string):
    """Convert date string to datetime object"""
    try:
        # Try different date formats
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        # If none of the formats match, raise an error
        raise ValueError(f"Date format not recognized: {date_string}")
    
    except Exception as e:
        logging.error(f"Error formatting date: {str(e)}")
        raise

def generate_report_id():
    """Generate a unique report ID"""
    import uuid
    return f"REP-{uuid.uuid4().hex[:8].upper()}"

def geocode_address(address):
    """Convert address to lat/long coordinates"""
    # This would use a geocoding service like Google Maps API
    # Placeholder implementation
    return {
        'latitude': 0,
        'longitude': 0
    }
