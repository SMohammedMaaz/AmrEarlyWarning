// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Update unread alerts count
    function updateAlertCount() {
        fetch('/api/unread-alerts-count')
            .then(response => response.json())
            .then(data => {
                const alertCountElement = document.getElementById('alertCount');
                if (alertCountElement) {
                    alertCountElement.textContent = data.count;
                }
            })
            .catch(error => console.error('Error fetching alert count:', error));
    }

    // If we're on the dashboard page
    if (document.getElementById('resistanceMap')) {
        // Initial load of alert count
        updateAlertCount();
        
        // Set interval to refresh data
        setInterval(() => {
            updateAlertCount();
        }, 60000); // Every minute
    }
});
