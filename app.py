import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
import firebase_admin
from firebase_admin import credentials

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
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///amr_network.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Firebase Admin SDK
try:
    # Check if running in a production environment with Firebase credentials
    if os.environ.get("FIREBASE_PROJECT_ID"):
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
            "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        })
        firebase_admin.initialize_app(cred)
        app.config["FIREBASE_INITIALIZED"] = True
    else:
        app.config["FIREBASE_INITIALIZED"] = False
        logging.warning("Firebase credentials not found. Firebase functionality will be limited.")
except Exception as e:
    app.config["FIREBASE_INITIALIZED"] = False
    logging.error(f"Failed to initialize Firebase: {e}")

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
from routes import auth_bp, dashboard_bp, data_bp, alerts_bp, admin_bp, treatment_bp
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

# Import error handlers
import routes
