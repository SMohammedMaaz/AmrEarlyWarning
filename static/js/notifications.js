// Notifications management for AMR alerts
document.addEventListener('DOMContentLoaded', function() {
    // Initialize notification functionality
    initNotifications();
});

// Initialize notification system
async function initNotifications() {
    // Check if the browser supports notifications
    if (!('Notification' in window)) {
        console.log('This browser does not support desktop notifications');
        return;
    }

    // Request permission for notifications
    const notificationToggle = document.getElementById('notification-toggle');
    if (notificationToggle) {
        notificationToggle.addEventListener('change', function() {
            if (this.checked) {
                requestNotificationPermission();
            }
        });

        // Set toggle state based on current permission
        if (Notification.permission === 'granted') {
            notificationToggle.checked = true;
        }
    }

    // Setup periodical alerts checking
    if (Notification.permission === 'granted') {
        setupPeriodicAlertsCheck();
    }
}

// Request permission for browser notifications
async function requestNotificationPermission() {
    try {
        const permission = await Notification.requestPermission();
        
        if (permission === 'granted') {
            console.log('Notification permission granted');
            setupPeriodicAlertsCheck();
        } else {
            console.log('Notification permission denied');
            const notificationToggle = document.getElementById('notification-toggle');
            if (notificationToggle) {
                notificationToggle.checked = false;
            }
        }
    } catch (error) {
        console.error('Error requesting notification permission:', error);
    }
}

// Setup periodic checking for new alerts
function setupPeriodicAlertsCheck() {
    // Check for new alerts immediately
    checkForNewAlerts();
    
    // Then check every 5 minutes
    setInterval(checkForNewAlerts, 5 * 60 * 1000);
}

// Check for new alerts from the server
async function checkForNewAlerts() {
    try {
        const response = await fetch('/alerts/api/latest');
        const alerts = await response.json();
        
        // Filter for only new alerts
        const newAlerts = alerts.filter(alert => alert.status === 'new');
        
        // Show notifications for new alerts
        newAlerts.forEach(alert => {
            showNotification(alert);
        });
        
        // Update alert counter in navbar
        updateAlertCounter(newAlerts.length);
        
    } catch (error) {
        console.error('Error checking for new alerts:', error);
    }
}

// Show a browser notification for an alert
function showNotification(alert) {
    // Get appropriate icon based on priority
    const iconUrl = getAlertIconUrl(alert.priority);
    
    // Create and show notification
    const notification = new Notification('AMR Alert: ' + alert.title, {
        body: alert.message,
        icon: iconUrl,
        tag: 'amr-alert-' + alert.id
    });
    
    // Add click handler to open the alert details
    notification.onclick = function() {
        window.open('/alerts/#alert-' + alert.id, '_blank');
        notification.close();
    };
    
    // Close automatically after 10 seconds
    setTimeout(() => {
        notification.close();
    }, 10000);
}

// Get icon URL based on alert priority
function getAlertIconUrl(priority) {
    switch (priority) {
        case 'critical':
            return '/static/icons/alert-critical.svg';
        case 'high':
            return '/static/icons/alert-high.svg';
        case 'medium':
            return '/static/icons/alert-medium.svg';
        case 'low':
            return '/static/icons/alert-low.svg';
        default:
            return '/static/icons/alert.svg';
    }
}

// Update alert counter in the navbar
function updateAlertCounter(count) {
    const alertBadge = document.getElementById('alert-count-badge');
    if (alertBadge) {
        if (count > 0) {
            alertBadge.textContent = count;
            alertBadge.classList.remove('d-none');
        } else {
            alertBadge.classList.add('d-none');
        }
    }
}

// Send browser notification
function sendNotification(title, message, priority = 'medium', alertId = null) {
    if (Notification.permission !== 'granted') {
        return;
    }
    
    // Create notification data
    const alert = {
        id: alertId || Date.now(),
        title: title,
        message: message,
        priority: priority
    };
    
    // Show the notification
    showNotification(alert);
}

// Register for push notifications from server (if push API is supported)
async function registerForPushNotifications(vapidPublicKey) {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications not supported');
        return;
    }
    
    try {
        // Register service worker if not already registered
        const registration = await navigator.serviceWorker.ready;
        
        // Subscribe to push notifications
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
        });
        
        // Send subscription to server
        await fetch('/api/register-push', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                subscription: subscription
            })
        });
        
        console.log('Push notification subscription successful');
        
    } catch (error) {
        console.error('Error registering for push notifications:', error);
    }
}

// Convert base64 string to Uint8Array (for VAPID key)
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    
    return outputArray;
}

// Export functions for use in other modules
export { 
    initNotifications, 
    sendNotification, 
    registerForPushNotifications,
    checkForNewAlerts
};
