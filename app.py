import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Setup base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///amr_network.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Make Firebase configuration available to templates
app.config["FIREBASE_API_KEY"] = os.environ.get("FIREBASE_API_KEY")
app.config["FIREBASE_PROJECT_ID"] = os.environ.get("FIREBASE_PROJECT_ID")
app.config["FIREBASE_APP_ID"] = os.environ.get("FIREBASE_APP_ID")

# Initialize Firebase
try:
    import firebase_utils
    firebase_initialized = firebase_utils.initialize_firebase()
    app.config["FIREBASE_INITIALIZED"] = firebase_initialized
    if firebase_initialized:
        logging.info("Firebase initialized successfully")
    else:
        logging.warning("Firebase initialization failed")
except Exception as e:
    app.config["FIREBASE_INITIALIZED"] = False
    logging.error(f"Error initializing Firebase: {e}")

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import models to ensure they're registered with SQLAlchemy
with app.app_context():
    import models
    
    # Create database tables
    db.create_all()

# Import and register blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.data import data_bp
from routes.alerts import alerts_bp
from routes.admin import admin_bp
from routes.treatment import treatment_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(data_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(treatment_bp)

# Setup login manager user loader
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Add route for the root URL
from flask import redirect, url_for

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

# Import error handlers
import routes
