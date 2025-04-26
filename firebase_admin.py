import os
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    # Check if Firebase credentials are available
    project_id = os.environ.get('FIREBASE_PROJECT_ID')
    
    if project_id:
        # Use service account credentials if available
        cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            # Use default application credentials
            cred = credentials.ApplicationDefault()
        
        firebase_app = firebase_admin.initialize_app(cred, {
            'projectId': project_id,
            'storageBucket': f"{project_id}.appspot.com"
        })
        
        db = firestore.client()
        bucket = storage.bucket()
        
        logger.info("Firebase Admin SDK initialized successfully")
    else:
        logger.warning("Firebase Project ID not provided. Firebase Admin SDK not initialized.")
        firebase_app = None
        db = None
        bucket = None
        
except Exception as e:
    logger.error(f"Error initializing Firebase Admin SDK: {str(e)}")
    firebase_app = None
    db = None
    bucket = None

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
