from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

from app import db
from models import Pathogen, TreatmentGuideline, ResistanceProfile, Antibiotic

# Create blueprint
treatment_bp = Blueprint('treatment', __name__, url_prefix='/treatment')

@treatment_bp.route('/')
@login_required
def treatment_guidance():
    """Overview of all pathogens and their resistance data"""
    pathogens = Pathogen.query.all()
    guidelines = TreatmentGuideline.query.all()
    
    return render_template('treatment_guidance.html', 
                          pathogens=pathogens,
                          guidelines=guidelines,
                          pathogen=None)

@treatment_bp.route('/pathogen/<int:pathogen_id>')
@login_required
def pathogen_guidance(pathogen_id):
    """Show detailed treatment guidance for a specific pathogen"""
    pathogen = Pathogen.query.get_or_404(pathogen_id)
    guidelines = TreatmentGuideline.query.filter_by(pathogen_id=pathogen_id).all()
    
    # Get resistance statistics
    resistance_stats = []
    
    # Get list of antibiotics tested against this pathogen
    antibiotics = db.session.query(Antibiotic)\
        .join(ResistanceProfile, ResistanceProfile.antibiotic_id == Antibiotic.id)\
        .filter(ResistanceProfile.pathogen_id == pathogen_id)\
        .distinct()\
        .all()
    
    for antibiotic in antibiotics:
        # Count total tests and resistant results
        profiles = ResistanceProfile.query.filter_by(
            pathogen_id=pathogen_id,
            antibiotic_id=antibiotic.id
        ).all()
        
        total = len(profiles)
        resistant = sum(1 for p in profiles if p.result == 'R')
        
        # Calculate resistance percentage
        percentage = round((resistant / total) * 100) if total > 0 else 0
        
        resistance_stats.append({
            'antibiotic': antibiotic.name,
            'total': total,
            'resistant': resistant,
            'percentage': percentage
        })
    
    return render_template('treatment_guidance.html',
                          pathogen=pathogen,
                          guidelines=guidelines,
                          resistance_stats=resistance_stats)

@treatment_bp.route('/api/pathogen/<int:pathogen_id>/resistance')
@login_required
def pathogen_resistance_api(pathogen_id):
    """API endpoint for resistance data for charts"""
    # This would be implemented to return JSON data for the charts
    pass