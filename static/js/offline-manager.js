// Offline functionality manager for AMR Network
document.addEventListener('DOMContentLoaded', function() {
    // Initialize offline functionality
    initOfflineManager();
});

// Initialize offline manager
function initOfflineManager() {
    // Check if service workers are supported
    if ('serviceWorker' in navigator) {
        registerServiceWorker();
        setupOfflineUI();
        setupSyncManager();
    } else {
        console.log('Service workers are not supported in this browser');
        
        // Show warning for browsers that don't support offline mode
        const offlineWarning = document.getElementById('offline-warning');
        if (offlineWarning) {
            offlineWarning.classList.remove('d-none');
        }
    }
    
    // Setup online/offline event listeners
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Initial status check
    updateOnlineStatus();
}

// Register service worker
async function registerServiceWorker() {
    try {
        const registration = await navigator.serviceWorker.register('/static/service-worker.js');
        console.log('ServiceWorker registration successful with scope:', registration.scope);
    } catch (error) {
        console.error('ServiceWorker registration failed:', error);
    }
}

// Setup UI elements related to offline functionality
function setupOfflineUI() {
    // Setup offline mode toggle
    const offlineToggle = document.getElementById('offline-mode-toggle');
    if (offlineToggle) {
        offlineToggle.addEventListener('change', function() {
            if (this.checked) {
                enableOfflineMode();
            } else {
                disableOfflineMode();
            }
        });
        
        // Check local storage to set initial state
        const offlineModeEnabled = localStorage.getItem('offlineModeEnabled') === 'true';
        offlineToggle.checked = offlineModeEnabled;
        
        if (offlineModeEnabled) {
            enableOfflineMode(false); // Don't show notification on load
        }
    }
    
    // Setup data sync status indicator
    const syncStatus = document.getElementById('sync-status');
    if (syncStatus) {
        updateSyncStatus('up-to-date');
    }
}

// Enable offline mode
function enableOfflineMode(showNotification = true) {
    // Save preference to localStorage
    localStorage.setItem('offlineModeEnabled', 'true');
    
    // Trigger cache of important resources
    if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
            type: 'CACHE_RESOURCES',
            resources: [
                '/',
                '/dashboard/',
                '/alerts/',
                '/static/css/styles.css',
                '/static/js/offline-manager.js',
                // Add other critical resources here
            ]
        });
    }
    
    // Update UI to show offline mode is enabled
    const offlineIndicator = document.getElementById('offline-mode-indicator');
    if (offlineIndicator) {
        offlineIndicator.classList.remove('d-none');
    }
    
    // Show notification if requested
    if (showNotification) {
        showOfflineNotification('Offline mode enabled', 'Essential data will be cached for offline use.');
    }
}

// Disable offline mode
function disableOfflineMode() {
    // Save preference to localStorage
    localStorage.setItem('offlineModeEnabled', 'false');
    
    // Update UI to hide offline mode indicator
    const offlineIndicator = document.getElementById('offline-mode-indicator');
    if (offlineIndicator) {
        offlineIndicator.classList.add('d-none');
    }
    
    // Show notification
    showOfflineNotification('Offline mode disabled', 'Data will only be available when online.');
}

// Setup background sync for data uploads
function setupSyncManager() {
    // Check if Background Sync API is supported
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
        navigator.serviceWorker.ready.then(registration => {
            // Setup sync handlers in the service worker
            console.log('Background sync is available');
        });
    } else {
        console.log('Background sync is not supported in this browser');
        
        // Update UI to show sync not supported
        const syncNotSupported = document.getElementById('sync-not-supported');
        if (syncNotSupported) {
            syncNotSupported.classList.remove('d-none');
        }
    }
}

// Update online/offline status UI
function updateOnlineStatus() {
    const isOnline = navigator.onLine;
    
    // Update status indicator in UI
    const statusIndicator = document.getElementById('connection-status');
    if (statusIndicator) {
        if (isOnline) {
            statusIndicator.textContent = 'Online';
            statusIndicator.classList.remove('text-danger');
            statusIndicator.classList.add('text-success');
        } else {
            statusIndicator.textContent = 'Offline';
            statusIndicator.classList.remove('text-success');
            statusIndicator.classList.add('text-danger');
            
            // Show offline banner
            showOfflineBanner();
        }
    }
    
    // Handle offline forms
    const forms = document.querySelectorAll('form[data-offline-enabled]');
    forms.forEach(form => {
        setupOfflineForm(form, !isOnline);
    });
}

// Setup form for offline submission
function setupOfflineForm(form, isOffline) {
    const submitButton = form.querySelector('button[type="submit"]');
    const offlineMessage = form.querySelector('.offline-message');
    
    if (isOffline) {
        // Modify form to store data locally instead of submitting
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Store form data in IndexedDB
            storeFormData(form);
            
            // Show success message
            if (offlineMessage) {
                offlineMessage.textContent = 'Data saved locally. Will sync when online.';
                offlineMessage.classList.remove('d-none');
            }
        });
        
        // Update button text
        if (submitButton) {
            submitButton.textContent = 'Save Offline';
        }
    } else {
        // Restore normal form behavior
        if (submitButton) {
            submitButton.textContent = 'Submit';
        }
        
        if (offlineMessage) {
            offlineMessage.classList.add('d-none');
        }
    }
}

// Store form data in IndexedDB for later sync
async function storeFormData(form) {
    try {
        // Get form data
        const formData = new FormData(form);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        // Store in local storage as a simple solution
        // In a real app, IndexedDB would be better
        const pendingUploads = JSON.parse(localStorage.getItem('pendingUploads') || '[]');
        pendingUploads.push({
            url: form.action,
            method: form.method,
            data: data,
            timestamp: new Date().toISOString()
        });
        
        localStorage.setItem('pendingUploads', JSON.stringify(pendingUploads));
        
        // Update sync status
        updateSyncStatus('pending');
        
        // Register for background sync if supported
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('sync-data');
        }
    } catch (error) {
        console.error('Error storing form data for offline use:', error);
    }
}

// Try to sync pending uploads when online
async function syncPendingUploads() {
    if (!navigator.onLine) {
        return;
    }
    
    try {
        updateSyncStatus('syncing');
        
        const pendingUploads = JSON.parse(localStorage.getItem('pendingUploads') || '[]');
        
        if (pendingUploads.length === 0) {
            updateSyncStatus('up-to-date');
            return;
        }
        
        const failedUploads = [];
        
        for (const upload of pendingUploads) {
            try {
                // Convert data back to FormData
                const formData = new FormData();
                for (const [key, value] of Object.entries(upload.data)) {
                    formData.append(key, value);
                }
                
                // Send the request
                const response = await fetch(upload.url, {
                    method: upload.method,
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}`);
                }
            } catch (error) {
                console.error('Error syncing data:', error);
                failedUploads.push(upload);
            }
        }
        
        // Update pending uploads with only failed ones
        localStorage.setItem('pendingUploads', JSON.stringify(failedUploads));
        
        // Update sync status
        if (failedUploads.length > 0) {
            updateSyncStatus('pending');
        } else {
            updateSyncStatus('up-to-date');
            showOfflineNotification('Sync completed', 'All offline data has been synchronized.');
        }
    } catch (error) {
        console.error('Error during sync process:', error);
        updateSyncStatus('error');
    }
}

// Update sync status indicator
function updateSyncStatus(status) {
    const syncIndicator = document.getElementById('sync-status');
    if (!syncIndicator) return;
    
    // Remove all status classes
    syncIndicator.classList.remove('text-success', 'text-warning', 'text-danger', 'text-info');
    
    // Set appropriate class and text based on status
    switch (status) {
        case 'up-to-date':
            syncIndicator.textContent = 'Synced';
            syncIndicator.classList.add('text-success');
            break;
        case 'pending':
            syncIndicator.textContent = 'Pending Sync';
            syncIndicator.classList.add('text-warning');
            break;
        case 'syncing':
            syncIndicator.textContent = 'Syncing...';
            syncIndicator.classList.add('text-info');
            break;
        case 'error':
            syncIndicator.textContent = 'Sync Error';
            syncIndicator.classList.add('text-danger');
            break;
    }
}

// Show offline banner when connection is lost
function showOfflineBanner() {
    // Create banner if it doesn't exist
    let banner = document.getElementById('offline-banner');
    
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'offline-banner';
        banner.className = 'offline-banner alert alert-warning alert-dismissible fade show';
        banner.innerHTML = `
            <strong>You are offline.</strong> Some features may be limited.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.body.insertBefore(banner, document.body.firstChild);
    }
}

// Show offline notification
function showOfflineNotification(title, message) {
    // Create a toast notification
    const toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        return;
    }
    
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.id = toastId;
    
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${title}</strong>
            <small>just now</small>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Show the toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Get count of pending uploads
function getPendingUploadsCount() {
    const pendingUploads = JSON.parse(localStorage.getItem('pendingUploads') || '[]');
    return pendingUploads.length;
}

// Export functions for use in other modules
export { 
    enableOfflineMode, 
    disableOfflineMode, 
    syncPendingUploads,
    getPendingUploadsCount
};

// Setup periodic sync check when online
window.addEventListener('online', function() {
    // Sync pending uploads
    syncPendingUploads();
});
