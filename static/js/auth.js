// Firebase authentication functionality
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js';
import { 
    getAuth, 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword,
    signInWithPopup,
    GoogleAuthProvider,
    signOut 
} from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js';

// Initialize Firebase with configuration from the backend
const firebaseConfig = {
    apiKey: document.getElementById('firebase-api-key')?.value,
    projectId: document.getElementById('firebase-project-id')?.value,
    appId: document.getElementById('firebase-app-id')?.value,
    authDomain: `${document.getElementById('firebase-project-id')?.value}.firebaseapp.com`,
    storageBucket: `${document.getElementById('firebase-project-id')?.value}.appspot.com`
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// Sign in with email/password
async function signInWithEmail(email, password) {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        
        // Get ID token for backend authentication
        const idToken = await user.getIdToken();
        
        // Send token to backend
        await sendTokenToBackend(idToken);
        
        return user;
    } catch (error) {
        console.error("Sign in error:", error);
        throw error;
    }
}

// Sign in with Google
async function signInWithGoogle() {
    try {
        const result = await signInWithPopup(auth, provider);
        const user = result.user;
        
        // Get ID token for backend authentication
        const idToken = await user.getIdToken();
        
        // Send token to backend
        await sendTokenToBackend(idToken);
        
        return user;
    } catch (error) {
        console.error("Google sign in error:", error);
        throw error;
    }
}

// Register with email/password
async function registerWithEmail(email, password) {
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        
        // Get ID token for backend authentication
        const idToken = await user.getIdToken();
        
        // Send token to backend
        await sendTokenToBackend(idToken);
        
        return user;
    } catch (error) {
        console.error("Registration error:", error);
        throw error;
    }
}

// Sign out current user
async function signOutUser() {
    try {
        await signOut(auth);
        
        // Redirect to logout endpoint on backend
        window.location.href = '/auth/logout';
    } catch (error) {
        console.error("Sign out error:", error);
        throw error;
    }
}

// Send ID token to backend for session creation
async function sendTokenToBackend(idToken) {
    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'idToken': idToken
            })
        });
        
        if (response.redirected) {
            window.location.href = response.url;
        }
    } catch (error) {
        console.error("Error sending token to backend:", error);
        throw error;
    }
}

// Event listeners for authentication forms
document.addEventListener('DOMContentLoaded', () => {
    // Login form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                await signInWithEmail(email, password);
                // Redirect handled by sendTokenToBackend
            } catch (error) {
                document.getElementById('login-error').textContent = error.message;
                document.getElementById('login-error').classList.remove('d-none');
            }
        });
    }
    
    // Google sign-in button
    const googleSignInBtn = document.getElementById('google-sign-in');
    if (googleSignInBtn) {
        googleSignInBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            try {
                await signInWithGoogle();
                // Redirect handled by sendTokenToBackend
            } catch (error) {
                document.getElementById('login-error').textContent = error.message;
                document.getElementById('login-error').classList.remove('d-none');
            }
        });
    }
    
    // Registration form
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm-password').value;
            
            if (password !== confirmPassword) {
                document.getElementById('register-error').textContent = "Passwords do not match";
                document.getElementById('register-error').classList.remove('d-none');
                return;
            }
            
            try {
                await registerWithEmail(email, password);
                // Redirect handled by sendTokenToBackend
            } catch (error) {
                document.getElementById('register-error').textContent = error.message;
                document.getElementById('register-error').classList.remove('d-none');
            }
        });
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            try {
                await signOutUser();
                // Redirect handled by signOutUser
            } catch (error) {
                console.error("Logout error:", error);
            }
        });
    }
});

// Export functions for use in other modules
export { signInWithEmail, signInWithGoogle, registerWithEmail, signOutUser };
