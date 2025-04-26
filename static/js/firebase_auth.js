// Firebase Authentication functionality
document.addEventListener('DOMContentLoaded', function() {
    // Firebase auth state change listener
    if (typeof auth !== 'undefined') {
        auth.onAuthStateChanged(function(user) {
            if (user) {
                console.log('User signed in:', user.email);
                
                // Get ID token
                user.getIdToken().then(function(idToken) {
                    // Send token to backend to create session
                    fetch('/firebase-auth', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            uid: user.uid,
                            email: user.email,
                            displayName: user.displayName,
                            idToken: idToken
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.redirect) {
                            window.location.href = data.redirect;
                        }
                    })
                    .catch(error => {
                        console.error('Error sending auth data to backend:', error);
                    });
                });
            } else {
                console.log('User signed out');
            }
        });
    }
    
    // Login with Email/Password
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            
            // Show spinner
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Logging in...';
            submitBtn.disabled = true;
            
            signInWithEmailAndPassword(auth, email, password)
                .catch(error => {
                    console.error('Login error:', error);
                    
                    // Reset button
                    submitBtn.innerHTML = originalBtnText;
                    submitBtn.disabled = false;
                    
                    // Show error message
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'alert alert-danger mt-3';
                    errorDiv.textContent = error.message;
                    loginForm.appendChild(errorDiv);
                    
                    // Remove error message after 5 seconds
                    setTimeout(() => {
                        errorDiv.remove();
                    }, 5000);
                });
        });
    }
    
    // Register with Email/Password
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const name = document.getElementById('registerName').value;
            const organization = document.getElementById('registerOrganization').value || '';
            
            // Show spinner
            const submitBtn = registerForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Registering...';
            submitBtn.disabled = true;
            
            createUserWithEmailAndPassword(auth, email, password)
                .then(userCredential => {
                    // Update profile
                    return userCredential.user.updateProfile({
                        displayName: name
                    });
                })
                .catch(error => {
                    console.error('Registration error:', error);
                    
                    // Reset button
                    submitBtn.innerHTML = originalBtnText;
                    submitBtn.disabled = false;
                    
                    // Show error message
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'alert alert-danger mt-3';
                    errorDiv.textContent = error.message;
                    registerForm.appendChild(errorDiv);
                    
                    // Remove error message after 5 seconds
                    setTimeout(() => {
                        errorDiv.remove();
                    }, 5000);
                });
        });
    }
    
    // Google Sign-in
    const googleButtons = document.querySelectorAll('.google-auth-btn');
    googleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const provider = new GoogleAuthProvider();
            
            // Show spinner
            const originalBtnText = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Connecting...';
            this.disabled = true;
            
            signInWithPopup(auth, provider)
                .catch(error => {
                    console.error('Google sign-in error:', error);
                    
                    // Reset button
                    this.innerHTML = originalBtnText;
                    this.disabled = false;
                    
                    // Show error message
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'alert alert-danger mt-3';
                    errorDiv.textContent = error.message;
                    this.parentNode.appendChild(errorDiv);
                    
                    // Remove error message after 5 seconds
                    setTimeout(() => {
                        errorDiv.remove();
                    }, 5000);
                });
        });
    });
    
    // Logout
    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            auth.signOut().then(() => {
                window.location.href = '/logout';
            });
        });
    }
});
