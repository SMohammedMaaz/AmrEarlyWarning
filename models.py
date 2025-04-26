from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum

# Role-based access control
class UserRole(enum.Enum):
    ADMIN = "admin"
    LAB_TECHNICIAN = "lab_technician"
    DOCTOR = "doctor"
    RESEARCHER = "researcher"
    PUBLIC_HEALTH_OFFICIAL = "public_health_official"
    FIELD_WORKER = "field_worker"

# User model for authentication and role-based access
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    firebase_uid = db.Column(db.String(128), unique=True)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.LAB_TECHNICIAN)
    full_name = db.Column(db.String(100))
    # organization field removed to match existing database schema
    profile_picture = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    phone_number = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    reports = db.relationship('LabReport', backref='submitted_by', lazy='dynamic')
    alerts_received = db.relationship('Alert', foreign_keys='Alert.user_id', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Facility/Hospital model
class Facility(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    facility_type = db.Column(db.String(50))  # hospital, lab, clinic, etc.
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reports = db.relationship('LabReport', backref='facility', lazy='dynamic')
    
    def __repr__(self):
        return f'<Facility {self.name}>'

# Pathogen model
class Pathogen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    scientific_name = db.Column(db.String(150))
    pathogen_type = db.Column(db.String(50))  # bacteria, virus, fungus, etc.
    description = db.Column(db.Text)
    
    # Relationships
    resistance_profiles = db.relationship('ResistanceProfile', backref='pathogen', lazy='dynamic')
    
    def __repr__(self):
        return f'<Pathogen {self.name}>'

# Antibiotic model
class Antibiotic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    drug_class = db.Column(db.String(100))
    description = db.Column(db.Text)
    
    # Relationships
    resistance_profiles = db.relationship('ResistanceProfile', backref='antibiotic', lazy='dynamic')
    
    def __repr__(self):
        return f'<Antibiotic {self.name}>'

# Lab report model
class LabReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(50), unique=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facility.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    report_date = db.Column(db.DateTime, default=datetime.utcnow)
    sample_collection_date = db.Column(db.DateTime)
    sample_type = db.Column(db.String(50))  # blood, urine, etc.
    patient_age = db.Column(db.Integer)
    patient_gender = db.Column(db.String(20))
    patient_identifier = db.Column(db.String(100))  # hashed identifier
    clinical_diagnosis = db.Column(db.String(200))
    
    # Relationships
    resistance_profiles = db.relationship('ResistanceProfile', backref='lab_report', lazy='dynamic')
    
    def __repr__(self):
        return f'<LabReport {self.report_id}>'

# Resistance profile model
class ResistanceProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_report_id = db.Column(db.Integer, db.ForeignKey('lab_report.id'), nullable=False)
    pathogen_id = db.Column(db.Integer, db.ForeignKey('pathogen.id'), nullable=False)
    antibiotic_id = db.Column(db.Integer, db.ForeignKey('antibiotic.id'), nullable=False)
    
    # Susceptibility result (R: Resistant, I: Intermediate, S: Susceptible)
    result = db.Column(db.String(1), nullable=False)
    
    # Optional minimum inhibitory concentration value
    mic_value = db.Column(db.Float)
    
    # Optional genomic mutation information
    mutation_data = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ResistanceProfile {self.id}>'

# Alert model for notification system
class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    alert_type = db.Column(db.String(50))  # outbreak, new resistance, etc.
    severity = db.Column(db.Integer)  # 1-5 scale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    action_taken = db.Column(db.Boolean, default=False)
    
    # Geographic information
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    region = db.Column(db.String(100))
    
    # Related entities
    pathogen_id = db.Column(db.Integer, db.ForeignKey('pathogen.id'))
    antibiotic_id = db.Column(db.Integer, db.ForeignKey('antibiotic.id'))
    
    # Relationships
    pathogen = db.relationship('Pathogen')
    antibiotic = db.relationship('Antibiotic')
    
    def __repr__(self):
        return f'<Alert {self.id}: {self.title}>'

# Treatment Guideline model
class TreatmentGuideline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pathogen_id = db.Column(db.Integer, db.ForeignKey('pathogen.id'), nullable=False)
    condition = db.Column(db.String(200), nullable=False)
    first_line_treatment = db.Column(db.Text, nullable=False)
    alternative_treatments = db.Column(db.Text)
    notes = db.Column(db.Text)
    source = db.Column(db.String(200))  # WHO, CDC, local health ministry, etc.
    published_date = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    pathogen = db.relationship('Pathogen')
    
    def __repr__(self):
        return f'<TreatmentGuideline {self.id}: {self.condition}>'

# Environmental sample data
class EnvironmentalSample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.String(50), unique=True)
    sample_type = db.Column(db.String(50))  # wastewater, water supply, soil, etc.
    collection_date = db.Column(db.DateTime, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_description = db.Column(db.String(200))
    pathogen_detected = db.Column(db.Boolean, default=False)
    pathogen_id = db.Column(db.Integer, db.ForeignKey('pathogen.id'))
    pathogen_load = db.Column(db.Float)  # quantitative measure
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text)
    
    # Relationship
    pathogen = db.relationship('Pathogen')
    collector = db.relationship('User', backref='environmental_samples')
    
    def __repr__(self):
        return f'<EnvironmentalSample {self.sample_id}>'
