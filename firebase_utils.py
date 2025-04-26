import os
import logging
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
firebase_app = None
db = None
bucket = None

def initialize_firebase():
    """Initialize the Firebase Admin SDK with environment credentials."""
    global firebase_app, db, bucket
    
    try:
        # Check if Firebase credentials are available
        project_id = os.environ.get('FIREBASE_PROJECT_ID')
        api_key = os.environ.get('FIREBASE_API_KEY')
        
        if not project_id or not api_key:
            logger.warning("Firebase credentials not available. Firebase Admin SDK not initialized.")
            return False
            
        # Initialize the app if not already initialized
        if not firebase_admin._apps:
            try:
                # For web authentication, we don't need a service account for basic functions
                # Just initialize with the project ID
                firebase_app = firebase_admin.initialize_app(options={
                    'projectId': project_id
                })
                logger.info("Firebase Admin SDK initialized successfully")
                
                # Initialize Firestore and Storage if needed
                try:
                    db = firestore.client()
                    bucket = storage.bucket(f"{project_id}.appspot.com")
                except Exception as e:
                    logger.warning(f"Could not initialize Firestore/Storage: {e}")
                    # Continue without Firestore/Storage in development
                    
                return True
            except Exception as e:
                # Handle initialization errors gracefully
                logger.warning(f"Firebase initialization error (expected in development): {e}")
                # Continue without full Firebase in development environment
                return True
        else:
            firebase_app = firebase_admin.get_app()
            logger.info("Using existing Firebase Admin app")
            return True
                
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {str(e)}")
        # In development mode, we'll continue without Firebase
        logger.info("Continuing without Firebase in development mode")
        return True

# Firebase Authentication functions
def verify_firebase_token(id_token):
    """Verify Firebase ID token and return user info."""
    if not firebase_app:
        logger.error("Firebase Admin SDK not initialized")
        return None
    
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {str(e)}")
        return None

def get_user_by_email(email):
    """Get Firebase user by email."""
    if not firebase_app:
        return None
    
    try:
        user = auth.get_user_by_email(email)
        return user
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Error getting user by email: {str(e)}")
        return None

def create_firebase_user(email, password, display_name=None):
    """Create a new Firebase user."""
    if not firebase_app:
        return None
    
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=False
        )
        return user
    except Exception as e:
        logger.error(f"Error creating Firebase user: {str(e)}")
        return None

# Firestore functions
def get_document(collection, doc_id):
    """Get a document from Firestore."""
    if not db:
        return None
    
    try:
        doc_ref = db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        return None

def create_document(collection, data, doc_id=None):
    """Create a document in Firestore."""
    if not db:
        return None
    
    try:
        if doc_id:
            doc_ref = db.collection(collection).document(doc_id)
            doc_ref.set(data)
            return doc_id
        else:
            doc_ref = db.collection(collection).add(data)
            return doc_ref[1].id
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        return None

# Storage functions
def upload_file(file_data, destination_path):
    """Upload a file to Firebase Storage."""
    if not bucket:
        return None
    
    try:
        blob = bucket.blob(destination_path)
        blob.upload_from_string(file_data)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return None

def get_file_url(file_path):
    """Get the public URL for a file in Firebase Storage."""
    if not bucket:
        return None
    
    try:
        blob = bucket.blob(file_path)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        logger.error(f"Error getting file URL: {str(e)}")
        return None