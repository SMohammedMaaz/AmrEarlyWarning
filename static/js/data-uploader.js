// Data uploader functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize file uploader if available on the page
    initializeFileUploader();
    
    // Initialize form validation for direct data entry
    initializeFormValidation();
    
    // Initialize sample type dependent fields
    initializeSampleTypeFields();
});

// Initialize file uploader with preview and validation
function initializeFileUploader() {
    const fileUpload = document.getElementById('lab_data_file');
    
    if (!fileUpload) return;
    
    fileUpload.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Update file name display
        const fileNameDisplay = document.getElementById('file-name-display');
        if (fileNameDisplay) {
            fileNameDisplay.textContent = file.name;
        }
        
        // Check file type
        if (!validateFileType(file)) {
            showUploadError('Please upload a CSV or JSON file');
            fileUpload.value = '';
            return;
        }
        
        // Show file details
        showFileDetails(file);
        
        // Preview file content if possible
        previewFileContent(file);
    });
    
    // Handle form submission
    const uploadForm = document.getElementById('upload-form');
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const file = fileUpload.files[0];
            const organizationSelect = document.getElementById('organization_id');
            
            if (!file) {
                e.preventDefault();
                showUploadError('Please select a file to upload');
                return;
            }
            
            if (!organizationSelect.value) {
                e.preventDefault();
                showUploadError('Please select an organization');
                return;
            }
            
            // Show loading indicator
            showUploadLoading();
        });
    }
}

// Validate file type (only CSV and JSON allowed)
function validateFileType(file) {
    const validTypes = ['text/csv', 'application/json'];
    const fileName = file.name.toLowerCase();
    
    // Check MIME type if available
    if (validTypes.includes(file.type)) {
        return true;
    }
    
    // Also check file extension as fallback
    if (fileName.endsWith('.csv') || fileName.endsWith('.json')) {
        return true;
    }
    
    return false;
}

// Show file details
function showFileDetails(file) {
    const fileDetails = document.getElementById('file-details');
    if (!fileDetails) return;
    
    const size = (file.size / 1024).toFixed(2);
    fileDetails.innerHTML = `
        <div class="mt-2">
            <strong>File:</strong> ${file.name}<br>
            <strong>Size:</strong> ${size} KB<br>
            <strong>Type:</strong> ${file.type || 'Unknown'}<br>
        </div>
    `;
}

// Preview file content
function previewFileContent(file) {
    const previewContainer = document.getElementById('file-preview');
    if (!previewContainer) return;
    
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const content = e.target.result;
        
        try {
            if (file.name.endsWith('.csv')) {
                // Preview CSV content
                previewCsvContent(content, previewContainer);
            } else if (file.name.endsWith('.json')) {
                // Preview JSON content
                previewJsonContent(content, previewContainer);
            }
        } catch (error) {
            console.error('Error previewing file:', error);
            previewContainer.innerHTML = `
                <div class="alert alert-warning">
                    Unable to preview file content. The file may be too large or in an invalid format.
                </div>
            `;
        }
    };
    
    reader.onerror = function() {
        previewContainer.innerHTML = `
            <div class="alert alert-danger">
                Error reading file. Please try again or select a different file.
            </div>
        `;
    };
    
    reader.readAsText(file);
}

// Preview CSV content
function previewCsvContent(content, container) {
    // Parse CSV (simple parsing for preview purposes)
    const lines = content.split('\n');
    if (lines.length <= 1) {
        container.innerHTML = '<div class="alert alert-warning">CSV file appears to be empty or invalid.</div>';
        return;
    }
    
    const headers = lines[0].split(',').map(h => h.trim());
    
    // Create table for preview (show max 5 rows)
    let tableHtml = '<div class="table-responsive"><table class="table table-sm table-striped">';
    
    // Headers
    tableHtml += '<thead><tr>';
    headers.forEach(header => {
        tableHtml += `<th>${header}</th>`;
    });
    tableHtml += '</tr></thead><tbody>';
    
    // Data rows (up to 5)
    const maxRows = Math.min(lines.length, 6);
    for (let i = 1; i < maxRows; i++) {
        if (!lines[i].trim()) continue;
        
        tableHtml += '<tr>';
        const cells = lines[i].split(',').map(c => c.trim());
        cells.forEach(cell => {
            tableHtml += `<td>${cell}</td>`;
        });
        tableHtml += '</tr>';
    }
    
    tableHtml += '</tbody></table></div>';
    
    if (lines.length > 6) {
        tableHtml += `<p class="text-muted">Showing first 5 rows of ${lines.length - 1} total rows.</p>`;
    }
    
    container.innerHTML = tableHtml;
}

// Preview JSON content
function previewJsonContent(content, container) {
    try {
        const jsonData = JSON.parse(content);
        
        // Check if it's an array or object
        if (Array.isArray(jsonData)) {
            // It's an array of objects, show first few items
            const itemsToShow = Math.min(jsonData.length, 3);
            let previewHtml = '<div><strong>JSON Array Preview:</strong></div>';
            previewHtml += '<pre class="bg-dark text-light p-3 rounded">';
            
            const previewData = jsonData.slice(0, itemsToShow);
            previewHtml += JSON.stringify(previewData, null, 2);
            
            if (jsonData.length > itemsToShow) {
                previewHtml += `\n\n// ${jsonData.length - itemsToShow} more items...`;
            }
            
            previewHtml += '</pre>';
            container.innerHTML = previewHtml;
        } else {
            // It's a single object, show it directly
            let previewHtml = '<div><strong>JSON Object Preview:</strong></div>';
            previewHtml += '<pre class="bg-dark text-light p-3 rounded">';
            previewHtml += JSON.stringify(jsonData, null, 2);
            previewHtml += '</pre>';
            container.innerHTML = previewHtml;
        }
    } catch (error) {
        console.error('Error parsing JSON:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                Error parsing JSON content. Please make sure the file contains valid JSON.
            </div>
        `;
    }
}

// Initialize form validation for direct data entry
function initializeFormValidation() {
    const directEntryForm = document.getElementById('direct-entry-form');
    
    if (!directEntryForm) return;
    
    directEntryForm.addEventListener('submit', function(e) {
        const organization = document.getElementById('organization_id');
        const pathogen = document.getElementById('pathogen_id');
        const collectionDate = document.getElementById('collection_date');
        
        let isValid = true;
        
        // Check required fields
        if (!organization.value) {
            showFieldError(organization, 'Please select an organization');
            isValid = false;
        } else {
            clearFieldError(organization);
        }
        
        if (!pathogen.value) {
            showFieldError(pathogen, 'Please select a pathogen');
            isValid = false;
        } else {
            clearFieldError(pathogen);
        }
        
        if (!collectionDate.value) {
            showFieldError(collectionDate, 'Please enter a collection date');
            isValid = false;
        } else {
            clearFieldError(collectionDate);
        }
        
        // Check at least one antibiotic result is entered
        const antibioticFields = document.querySelectorAll('select[name^="antibiotic_"]');
        let hasAntibioticData = false;
        
        antibioticFields.forEach(field => {
            if (field.value) {
                hasAntibioticData = true;
            }
        });
        
        if (!hasAntibioticData) {
            showFormError('Please enter at least one antibiotic result');
            isValid = false;
        }
        
        if (!isValid) {
            e.preventDefault();
        } else {
            // Show loading indicator
            showFormLoading();
        }
    });
}

// Initialize sample type dependent fields
function initializeSampleTypeFields() {
    const sampleTypeField = document.getElementById('sample_type');
    
    if (!sampleTypeField) return;
    
    sampleTypeField.addEventListener('change', function() {
        updateFieldsBasedOnSampleType(this.value);
    });
    
    // Initial update based on current value
    if (sampleTypeField.value) {
        updateFieldsBasedOnSampleType(sampleTypeField.value);
    }
}

// Update fields based on sample type
function updateFieldsBasedOnSampleType(sampleType) {
    const antibioticSection = document.getElementById('antibiotic-section');
    
    if (!antibioticSection) return;
    
    // Sample type specific antibiotics (simplified example)
    const antibioticsBySampleType = {
        'blood': ['Penicillin', 'Ceftriaxone', 'Meropenem', 'Vancomycin', 'Gentamicin'],
        'urine': ['Ciprofloxacin', 'Nitrofurantoin', 'Trimethoprim-Sulfamethoxazole', 'Amoxicillin-Clavulanate'],
        'stool': ['Ciprofloxacin', 'Azithromycin', 'Ampicillin', 'Ceftriaxone'],
        'sputum': ['Azithromycin', 'Doxycycline', 'Levofloxacin', 'Amoxicillin-Clavulanate'],
        'wound': ['Clindamycin', 'Cefazolin', 'Gentamicin', 'Vancomycin', 'Trimethoprim-Sulfamethoxazole']
    };
    
    // Get antibiotics for selected sample type (or use a default set)
    const antibiotics = antibioticsBySampleType[sampleType] || [
        'Penicillin', 'Ceftriaxone', 'Ciprofloxacin', 'Gentamicin', 'Vancomycin'
    ];
    
    // Update antibiotic fields
    let antibioticHtml = '';
    
    antibiotics.forEach(antibiotic => {
        const fieldId = 'antibiotic_' + antibiotic.toLowerCase().replace(/[^a-z0-9]/g, '_');
        
        antibioticHtml += `
            <div class="col-md-6 mb-3">
                <label for="${fieldId}" class="form-label">${antibiotic}</label>
                <select id="${fieldId}" name="${fieldId}" class="form-select">
                    <option value="">-- Select Result --</option>
                    <option value="S">Susceptible (S)</option>
                    <option value="I">Intermediate (I)</option>
                    <option value="R">Resistant (R)</option>
                </select>
            </div>
        `;
    });
    
    antibioticSection.innerHTML = antibioticHtml;
}

// Show error message for a field
function showFieldError(field, message) {
    // Clear any existing error
    clearFieldError(field);
    
    // Add error class to field
    field.classList.add('is-invalid');
    
    // Create and append error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
}

// Clear error message for a field
function clearFieldError(field) {
    field.classList.remove('is-invalid');
    
    const existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
}

// Show error message for the form
function showFormError(message) {
    const errorContainer = document.getElementById('form-error-container');
    
    if (!errorContainer) return;
    
    errorContainer.innerHTML = `
        <div class="alert alert-danger">
            ${message}
        </div>
    `;
}

// Show error message for file upload
function showUploadError(message) {
    const errorContainer = document.getElementById('upload-error-container');
    
    if (!errorContainer) return;
    
    errorContainer.innerHTML = `
        <div class="alert alert-danger">
            ${message}
        </div>
    `;
}

// Show loading indicator during form submission
function showFormLoading() {
    const submitBtn = document.querySelector('#direct-entry-form button[type="submit"]');
    
    if (!submitBtn) return;
    
    submitBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        Submitting...
    `;
    submitBtn.disabled = true;
}

// Show loading indicator during file upload
function showUploadLoading() {
    const submitBtn = document.querySelector('#upload-form button[type="submit"]');
    
    if (!submitBtn) return;
    
    submitBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        Uploading...
    `;
    submitBtn.disabled = true;
}
