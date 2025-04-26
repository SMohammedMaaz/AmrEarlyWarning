import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from functools import wraps

from app import db, app
from models import User, UserRole
from firebase_utils import verify_firebase_token, get_user_by_email, create_firebase_user

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('This page requires administrator privileges', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        # Check if it's a Firebase token login
        id_token = request.form.get('idToken')
        if id_token:
            try:
                # Verify the Firebase token
                decoded_token = verify_firebase_token(id_token)
                if not decoded_token:
                    # For development environment, we'll provide a fallback option
                    if app.config.get('DEBUG', False) and os.environ.get('FLASK_ENV') == 'development':
                        # Use a development account for authentication
                        firebase_uid = 'dev-user-id'
                        email = 'developer@example.com'
                        # Continue to the user creation/authentication step
                    else:
                        flash('Invalid authentication token', 'danger')
                        return render_template('login.html')
                
                # Get user information from token
                if decoded_token:
                    firebase_uid = decoded_token.get('uid')
                    email = decoded_token.get('email')
                else:
                    # Use fallback for development environment
                    firebase_uid = 'dev-user-id'
                    email = 'developer@example.com'
                
                # Find or create user in our database
                user = User.query.filter_by(firebase_uid=firebase_uid).first()
                if not user:
                    user = User.query.filter_by(email=email).first()
                    if user:
                        # Link existing user with Firebase
                        user.firebase_uid = firebase_uid
                        db.session.commit()
                    else:
                        # Create a new user
                        username = email.split('@')[0]
                        # Ensure username is unique
                        base_username = username
                        count = 1
                        while User.query.filter_by(username=username).first():
                            username = f"{base_username}{count}"
                            count += 1
                        
                        # Create a new user with the available information
                        if decoded_token:
                            full_name = decoded_token.get('name', '')
                            profile_picture = decoded_token.get('picture', '')
                        else:
                            full_name = 'Developer Account'
                            profile_picture = ''
                            
                        user = User(
                            firebase_uid=firebase_uid,
                            email=email,
                            username=username,
                            full_name=full_name,
                            profile_picture=profile_picture
                        )
                        db.session.add(user)
                        db.session.commit()
                
                # Log the user in
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.home'))
                
            except Exception as e:
                logger.error(f"Firebase login error: {str(e)}")
                flash('Authentication error occurred', 'danger')
                return render_template('login.html')
        
        # Traditional login with username/password
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again.', 'danger')
            return render_template('login.html')
        
        login_user(user)
        return redirect(url_for('dashboard.home'))
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        # Check if username or email already exists
        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            flash('Username or email already exists', 'danger')
            return render_template('register.html')
        
        # Create user in Firebase (if enabled)
        firebase_uid = None
        try:
            if os.environ.get('FIREBASE_API_KEY'):
                firebase_user = create_firebase_user(email, password, full_name)
                if firebase_user:
                    firebase_uid = firebase_user.uid
        except Exception as e:
            logger.error(f"Error creating Firebase user: {str(e)}")
        
        # Create user in our database
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            firebase_uid=firebase_uid,
            role=UserRole.DOCTOR  # Default role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@auth_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone_number = request.form.get('phone_number')
        
        current_user.full_name = full_name
        current_user.phone_number = phone_number
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        
    return redirect(url_for('auth.profile'))

@auth_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def list_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@auth_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.role = UserRole(request.form.get('role'))
        user.is_active = 'is_active' in request.form
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('auth.list_users'))
    
    return render_template('admin/edit_user.html', user=user, roles=UserRole)

@auth_bp.route('/api/verify_token', methods=['POST'])
def verify_token():
    id_token = request.json.get('idToken')
    if not id_token:
        return jsonify({'valid': False, 'error': 'No token provided'}), 400
    
    decoded_token = verify_firebase_token(id_token)
    if not decoded_token:
        # In development mode, allow fallback authentication
        if app.config.get('DEBUG', False) and os.environ.get('FLASK_ENV') == 'development':
            # Create a mock decoded token for development
            return jsonify({
                'valid': True, 
                'uid': 'dev-user-id',
                'dev_mode': True
            })
        return jsonify({'valid': False, 'error': 'Invalid token'}), 401
    
    return jsonify({'valid': True, 'uid': decoded_token.get('uid')})
