// Data upload functionality
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-upload');
    const fileLabel = document.querySelector('.custom-file-label');
    const uploadForm = document.getElementById('upload-form');
    const previewContainer = document.getElementById('data-preview');
    const submitButton = document.getElementById('submit-upload');
    
    // Update filename display when file is selected
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const fileName = this.files[0].name;
                fileLabel.textContent = fileName;
                
                // Show preview for CSV/JSON
                if (fileName.endsWith('.csv') || fileName.endsWith('.json')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        let content = e.target.result;
                        let previewHTML = '<div class="alert alert-info">File loaded successfully. Preview:</div>';
                        
                        if (fileName.endsWith('.csv')) {
                            // Simple CSV preview (just first few lines)
                            const lines = content.split('\n').slice(0, 5);
                            previewHTML += '<div class="table-responsive"><table class="table table-sm table-bordered">';
                            
                            lines.forEach((line, index) => {
                                const cells = line.split(',');
                                previewHTML += '<tr>';
                                cells.forEach(cell => {
                                    // Use th for header row
                                    if (index === 0) {
                                        previewHTML += `<th>${cell}</th>`;
                                    } else {
                                        previewHTML += `<td>${cell}</td>`;
                                    }
                                });
                                previewHTML += '</tr>';
                            });
                            
                            previewHTML += '</table></div>';
                        } else {
                            // JSON preview
                            try {
                                const jsonData = JSON.parse(content);
                                previewHTML += '<pre class="bg-dark text-light p-3" style="max-height: 200px; overflow-y: auto;">';
                                previewHTML += JSON.stringify(jsonData, null, 2).substring(0, 500);
                                if (JSON.stringify(jsonData, null, 2).length > 500) {
                                    previewHTML += '...\n[Content truncated]';
                                }
                                previewHTML += '</pre>';
                            } catch (e) {
                                previewHTML = '<div class="alert alert-danger">Error parsing JSON file</div>';
                            }
                        }
                        
                        previewContainer.innerHTML = previewHTML;
                        submitButton.disabled = false;
                    };
                    
                    reader.readAsText(this.files[0]);
                } else {
                    previewContainer.innerHTML = '<div class="alert alert-warning">Unsupported file format. Please upload CSV or JSON files.</div>';
                    submitButton.disabled = true;
                }
            }
        });
    }
    
    // Facility selection validation
    const facilitySelect = document.getElementById('facility-select');
    if (facilitySelect) {
        facilitySelect.addEventListener('change', function() {
            validateForm();
        });
    }
    
    // Form validation
    function validateForm() {
        if (submitButton) {
            const fileValid = fileInput && fileInput.files && fileInput.files[0];
            const facilityValid = facilitySelect && facilitySelect.value;
            
            submitButton.disabled = !(fileValid && facilityValid);
        }
    }
    
    // Form submission with loading indicator
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'text-center mt-3';
            loadingIndicator.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Processing data, please wait...</p>
            `;
            
            uploadForm.appendChild(loadingIndicator);
            submitButton.disabled = true;
        });
    }
});
