import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import json

from app import db
from models import ResistanceProfile, LabReport, Facility, Pathogen, Antibiotic

def predict_outbreak():
    """
    Predict potential antimicrobial resistance outbreaks
    Returns a list of potential outbreaks with location and severity
    """
    try:
        # Get data from the past 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Query for resistance data by location, pathogen, and date
        query = db.session.query(
            Facility.state,
            Facility.city,
            Facility.latitude,
            Facility.longitude,
            Pathogen.id.label('pathogen_id'),
            Pathogen.name.label('pathogen_name'),
            db.func.date(LabReport.report_date).label('date'),
            db.func.count(ResistanceProfile.id).label('total_samples'),
            db.func.sum(db.case([(ResistanceProfile.result == 'R', 1)], else_=0)).label('resistant_samples')
        ).join(
            LabReport, Facility.id == LabReport.facility_id
        ).join(
            ResistanceProfile, LabReport.id == ResistanceProfile.lab_report_id
        ).join(
            Pathogen, ResistanceProfile.pathogen_id == Pathogen.id
        ).filter(
            LabReport.report_date >= cutoff_date
        ).group_by(
            Facility.state,
            Facility.city,
            Facility.latitude,
            Facility.longitude,
            Pathogen.id,
            Pathogen.name,
            db.func.date(LabReport.report_date)
        ).all()
        
        # Convert to pandas DataFrame for analysis
        columns = ['state', 'city', 'latitude', 'longitude', 'pathogen_id', 'pathogen_name', 'date', 'total_samples', 'resistant_samples']
        df = pd.DataFrame([{c: getattr(row, c) for c in columns} for row in query])
        
        if df.empty:
            logging.info("No data available for outbreak prediction")
            return []
        
        # Calculate resistance percentage
        df['resistance_percentage'] = (df['resistant_samples'] / df['total_samples']) * 100
        
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Identify potential outbreaks
        potential_outbreaks = []
        
        # Group by location and pathogen
        for (state, city, path_id, path_name), group in df.groupby(['state', 'city', 'pathogen_id', 'pathogen_name']):
            # Sort by date
            group = group.sort_values('date')
            
            # Minimum number of samples needed for outbreak detection
            if len(group) < 3 or group['total_samples'].sum() < 10:
                continue
                
            # Check for increased resistance trend
            if len(group) >= 3:
                # Calculate 7-day moving average
                group['rolling_resistance'] = group['resistance_percentage'].rolling(window=min(3, len(group)), min_periods=1).mean()
                
                # Check if current resistance is significantly higher than the past
                latest = group.iloc[-1]
                previous_avg = group.iloc[:-1]['resistance_percentage'].mean() if len(group) > 1 else 0
                
                # Check if there's a significant increase
                threshold = 15  # percentage points
                if latest['resistance_percentage'] > 50 and (latest['resistance_percentage'] - previous_avg) > threshold:
                    # Get latest lat/long
                    lat = latest['latitude']
                    lng = latest['longitude']
                    
                    # Calculate severity (1-5 scale)
                    severity = 3  # Default medium severity
                    
                    if latest['resistance_percentage'] > 80:
                        severity = 5  # Very high
                    elif latest['resistance_percentage'] > 60:
                        severity = 4  # High
                    
                    # Add to potential outbreaks
                    outbreak = {
                        'pathogen': path_name,
                        'pathogen_id': path_id,
                        'location': f"{city}, {state}",
                        'latitude': lat,
                        'longitude': lng,
                        'resistance_level': f"{latest['resistance_percentage']:.1f}%",
                        'severity': severity,
                        'total_samples': int(latest['total_samples']),
                        'resistant_samples': int(latest['resistant_samples']),
                        'date': latest['date'].strftime('%Y-%m-%d')
                    }
                    
                    potential_outbreaks.append(outbreak)
        
        return potential_outbreaks
        
    except Exception as e:
        logging.error(f"Error in predict_outbreak: {str(e)}")
        return []

def get_treatment_recommendations(pathogen_id, region=None):
    """
    Get treatment recommendations based on local resistance patterns
    """
    try:
        # Get antibiotic resistance data for this pathogen
        query = db.session.query(
            Antibiotic.id,
            Antibiotic.name,
            db.func.count(ResistanceProfile.id).label('total_samples'),
            db.func.sum(db.case([(ResistanceProfile.result == 'R', 1)], else_=0)).label('resistant_samples')
        ).join(
            ResistanceProfile, ResistanceProfile.antibiotic_id == Antibiotic.id
        ).filter(
            ResistanceProfile.pathogen_id == pathogen_id
        )
        
        # Filter by region if provided
        if region:
            query = query.join(
                LabReport, ResistanceProfile.lab_report_id == LabReport.id
            ).join(
                Facility, LabReport.facility_id == Facility.id
            ).filter(
                Facility.state == region
            )
        
        # Group by antibiotic
        query = query.group_by(
            Antibiotic.id,
            Antibiotic.name
        ).all()
        
        # Calculate resistance percentages
        recommendations = []
        
        for row in query:
            if row.total_samples > 0:
                resistance_percentage = (row.resistant_samples / row.total_samples) * 100
                
                recommendation = {
                    'antibiotic_id': row.id,
                    'antibiotic_name': row.name,
                    'resistance_percentage': resistance_percentage,
                    'total_samples': row.total_samples,
                    'effectiveness': 'High' if resistance_percentage < 20 else 'Medium' if resistance_percentage < 50 else 'Low'
                }
                
                recommendations.append(recommendation)
        
        # Sort by effectiveness (most effective first)
        recommendations.sort(key=lambda x: x['resistance_percentage'])
        
        return recommendations
        
    except Exception as e:
        logging.error(f"Error in get_treatment_recommendations: {str(e)}")
        return []

def predict_resistance_spread(days_ahead=14):
    """
    Predict the spread of resistance patterns for the next X days
    Returns geospatial data with predicted resistance levels
    """
    try:
        # This is a simplified placeholder for an actual ML model
        # In a real implementation, this would use a more sophisticated model
        
        # Get current resistance map
        from data_processing import generate_resistance_map
        current_map = generate_resistance_map()
        
        # Simulate predictions by slightly increasing resistance levels
        predicted_map = []
        
        for location in current_map:
            # Skip environmental samples
            if location.get('isEnvironmentalSample', False):
                continue
                
            # Create a copy of the location data
            predicted = location.copy()
            
            # Modify for prediction
            if 'resistancePercentage' in predicted and predicted['resistancePercentage'] is not None:
                # Add a small random increase (more sophisticated models would be used in practice)
                random_increase = np.random.uniform(2, 8)
                predicted['resistancePercentage'] = min(100, predicted['resistancePercentage'] + random_increase)
                
                # Update risk level
                if predicted['resistancePercentage'] >= 75:
                    predicted['riskLevel'] = "Very High"
                    predicted['color'] = "#dc3545"  # Red
                elif predicted['resistancePercentage'] >= 50:
                    predicted['riskLevel'] = "High"
                    predicted['color'] = "#fd7e14"  # Orange
                elif predicted['resistancePercentage'] >= 25:
                    predicted['riskLevel'] = "Medium"
                    predicted['color'] = "#ffc107"  # Yellow
                else:
                    predicted['riskLevel'] = "Low"
                    predicted['color'] = "#28a745"  # Green
                
                # Mark as prediction
                predicted['isPrediction'] = True
                predicted['predictionDays'] = days_ahead
                predicted['name'] = f"{predicted['name']} (Prediction)"
                
                predicted_map.append(predicted)
        
        return predicted_map
        
    except Exception as e:
        logging.error(f"Error in predict_resistance_spread: {str(e)}")
        return []
