// Alerts functionality
document.addEventListener('DOMContentLoaded', function() {
    // Mark alert as read
    const markReadButtons = document.querySelectorAll('.mark-read-btn');
    markReadButtons.forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.getAttribute('data-alert-id');
            
            fetch(`/alerts/${alertId}/mark-read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI to show alert is read
                    const alertCard = document.getElementById(`alert-${alertId}`);
                    if (alertCard) {
                        alertCard.classList.remove('border-danger');
                        alertCard.classList.add('border-secondary');
                        // Update read badge
                        const readBadge = alertCard.querySelector('.read-badge');
                        if (readBadge) {
                            readBadge.textContent = 'Read';
                            readBadge.classList.remove('bg-danger');
                            readBadge.classList.add('bg-secondary');
                        }
                        // Update button state
                        this.disabled = true;
                        this.textContent = 'Read';
                    }
                }
            })
            .catch(error => console.error('Error marking alert as read:', error));
        });
    });

    // Mark alert as action taken
    const markActionButtons = document.querySelectorAll('.mark-action-btn');
    markActionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.getAttribute('data-alert-id');
            
            fetch(`/alerts/${alertId}/mark-action`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI to show action taken
                    const actionBadge = document.getElementById(`action-badge-${alertId}`);
                    if (actionBadge) {
                        actionBadge.textContent = 'Action Taken';
                        actionBadge.classList.remove('bg-warning');
                        actionBadge.classList.add('bg-success');
                    }
                    // Update button state
                    this.disabled = true;
                    this.textContent = 'Action Taken';
                }
            })
            .catch(error => console.error('Error marking action taken:', error));
        });
    });

    // Filter alerts by type
    const alertFilterSelect = document.getElementById('alert-filter');
    if (alertFilterSelect) {
        alertFilterSelect.addEventListener('change', function() {
            const filterValue = this.value;
            const alertCards = document.querySelectorAll('.alert-card');
            
            alertCards.forEach(card => {
                const alertType = card.getAttribute('data-alert-type');
                if (filterValue === 'all' || alertType === filterValue) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
});
