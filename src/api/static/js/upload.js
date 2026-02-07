// DOM Elements
const dropArea = document.getElementById('dropArea');
const fileInput = document.getElementById('fileInput');
const selectedFile = document.getElementById('selectedFile');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFileBtn = document.getElementById('removeFile');
const submitBtn = document.getElementById('submitBtn');
const uploadForm = document.getElementById('uploadForm');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultContainer = document.getElementById('resultContainer');
const resultTitle = document.getElementById('resultTitle');
const resultContent = document.getElementById('resultContent');
const resultActions = document.getElementById('resultActions');

// Current file
let currentFile = null;
let isOpeningFileDialog = false;

// Event Listeners
dropArea.addEventListener('click', handleDropAreaClick);
dropArea.addEventListener('dragover', handleDragOver);
dropArea.addEventListener('dragleave', handleDragLeave);
dropArea.addEventListener('drop', handleDrop);
fileInput.addEventListener('change', handleFileSelect);
removeFileBtn.addEventListener('click', removeFile);
uploadForm.addEventListener('submit', handleSubmit);

// Functions
function handleDropAreaClick(e) {
    // Prevent the click from bubbling to parent elements
    e.stopPropagation();
    
    // Only trigger file input if we're not already opening a dialog
    if (!isOpeningFileDialog) {
        isOpeningFileDialog = true;
        
        // Trigger file input click
        fileInput.click();
        
        // Reset flag after a short delay
        setTimeout(() => {
            isOpeningFileDialog = false;
        }, 100);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    dropArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    dropArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dropArea.classList.remove('dragover');
    
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleFileSelect({ target: fileInput });
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file type
    const validTypes = ['application/pdf', 
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'text/plain'];
    
    const validExtensions = ['.pdf', '.doc', '.docx', '.txt'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!validTypes.includes(file.type) && 
        !validExtensions.includes(fileExtension)) {
        alert('Please select a valid file (PDF, DOC, DOCX, or TXT)');
        fileInput.value = ''; // Clear the input
        return;
    }
    
    // Validate file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
        alert('File size must be less than 50MB');
        fileInput.value = ''; // Clear the input
        return;
    }
    
    currentFile = file;
    showSelectedFile(file);
    updateSubmitButton();
}

function showSelectedFile(file) {
    const size = formatFileSize(file.size);
    fileName.textContent = file.name;
    fileSize.textContent = `${size} • ${getFileType(file.name)}`;
    selectedFile.classList.add('show');
}

function getFileType(filename) {
    const extension = filename.substring(filename.lastIndexOf('.')).toLowerCase();
    switch(extension) {
        case '.pdf': return 'PDF Document';
        case '.doc': return 'Word Document';
        case '.docx': return 'Word Document';
        case '.txt': return 'Text File';
        default: return 'Unknown File';
    }
}

function removeFile() {
    fileInput.value = '';
    currentFile = null;
    selectedFile.classList.remove('show');
    updateSubmitButton();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function updateSubmitButton() {
    const isFormValid = currentFile !== null;
    submitBtn.disabled = !isFormValid;
    
    // Update button text based on state
    if (isFormValid) {
        submitBtn.textContent = `Upload and Analyze "${currentFile.name}"`;
    } else {
        submitBtn.textContent = 'Upload and Analyze Document';
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    
    if (!currentFile) {
        alert('Please select a file');
        return;
    }
    
    // Disable submit button during upload
    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading...';
    
    // Show progress
    uploadForm.style.display = 'none';
    progressContainer.classList.add('show');
    progressFill.style.width = '10%';
    progressText.textContent = 'Preparing upload...';
    
    try {
        // Create FormData
        const formData = new FormData();
        formData.append('file', currentFile);
        
        // Simulate progress for better UX
        const progressInterval = simulateProgress();
        
        // Make API request
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        // Clear progress simulation
        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = 'Processing complete!';
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess(result);
        } else {
            throw new Error(result.detail || result.message || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message);
    }
}

function simulateProgress() {
    let progress = 10;
    const interval = setInterval(() => {
        if (progress >= 90) {
            clearInterval(interval);
            return;
        }
        progress += Math.random() * 10;
        progressFill.style.width = Math.min(progress, 90) + '%';
        
        if (progress < 30) {
            progressText.textContent = 'Uploading file...';
        } else if (progress < 60) {
            progressText.textContent = 'Processing document...';
        } else {
            progressText.textContent = 'Running NLP analysis...';
        }
    }, 300);
    
    return interval; // Return interval ID so we can clear it later
}

function showSuccess(result) {
    resultContainer.classList.add('show');
    resultContainer.classList.remove('result-error');
    resultContainer.classList.add('result-success');
    
    resultTitle.textContent = '✅ Document Uploaded Successfully!';
    resultContent.innerHTML = `
        <p><strong>Document ID:</strong> ${result.document_id || 'N/A'}</p>
        <p><strong>Status:</strong> ${result.status || 'Processing'}</p>
        <p><strong>Message:</strong> ${result.message || 'Document is being analyzed'}</p>
        <p>The document is now being processed. You can:</p>
        <ul>
            <li>Check processing status</li>
            <li>View analysis results when complete</li>
            <li>Track progress via the API</li>
        </ul>
    `;
    
    const documentId = result.document_id || result.id;
    if (documentId) {
        resultActions.innerHTML = `
            <button onclick="window.location.href='/'" class="btn">🏠 Back to Home</button>
            <button onclick="checkStatus('${documentId}')" class="btn btn-secondary">🔍 Check Status</button>
            <button onclick="viewAPI()" class="btn">📚 View in API Docs</button>
        `;
    } else {
        resultActions.innerHTML = `
            <button onclick="window.location.href='/'" class="btn">🏠 Back to Home</button>
            <button onclick="window.location.href='/docs'" class="btn btn-secondary">📚 API Documentation</button>
        `;
    }
}

function showError(message) {
    resultContainer.classList.add('show');
    resultContainer.classList.add('result-error');
    
    resultTitle.textContent = '❌ Upload Failed';
    resultContent.innerHTML = `
        <p><strong>Error:</strong> ${message}</p>
        <p>Please try again or contact support if the problem persists.</p>
    `;
    
    resultActions.innerHTML = `
        <button onclick="window.location.reload()" class="btn">🔄 Try Again</button>
        <button onclick="window.location.href='/'" class="btn btn-secondary">🏠 Back to Home</button>
    `;
    
    // Show form again for retry
    uploadForm.style.display = 'block';
    submitBtn.disabled = false;
    submitBtn.textContent = 'Upload and Analyze Document';
}

// Helper functions for success actions
window.checkStatus = function(documentId) {
    window.location.href = `/documents/status/${documentId}`;
};

window.viewAPI = function() {
    window.location.href = '/docs#/documents/get_status_documents_status__document_id__get';
};

// Initialize
updateSubmitButton();

// Prevent file input from being triggered multiple times
fileInput.addEventListener('click', function(e) {
    e.stopPropagation();
});

// Add event listener to the document to handle any bubbling clicks
document.addEventListener('click', function(e) {
    // If user clicks outside the drop area while file dialog is open, reset flag
    if (isOpeningFileDialog && !dropArea.contains(e.target) && e.target !== fileInput) {
        isOpeningFileDialog = false;
    }
});