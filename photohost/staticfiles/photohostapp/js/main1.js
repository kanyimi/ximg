// main.js

// ==============================
// CONFIG (must match backend)
// ==============================
const MAX_SECTION_SIZE_MB = 300;
const MAX_SECTION_SIZE = MAX_SECTION_SIZE_MB * 1024 * 1024;

// ==============================
// Elements
// ==============================
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileCount = document.getElementById("fileCount");
const warnings = document.getElementById("fileWarnings");
const previewContainer = document.getElementById("previewContainer");
const uploadForm = document.getElementById("uploadForm");
const submitBtn = document.getElementById("submitBtn");
const uploadStatusContainer = document.getElementById("uploadStatusContainer");
const uploadStatusText = document.getElementById("uploadStatusText");
const uploadProgressBar = document.getElementById("uploadProgressBar");
const uploadProgressText = document.getElementById("uploadProgressText");
const uploadSpeedText = document.getElementById("uploadSpeedText");
const uploadFileList = document.getElementById("uploadFileList");
const cancelUploadBtn = document.getElementById("cancelUploadBtn");

// ==============================
// State
// ==============================
let validFiles = [];
let totalSize = 0;
let xhr = null;
let uploadStartTime = null;
let uploadedBytes = 0;

// ==============================
// Handle file selection
// ==============================
function handleFiles(files) {
    warnings.textContent = "";
    previewContainer.innerHTML = "";
    validFiles = [];
    totalSize = 0;

    if (!files || files.length === 0) {
        fileCount.textContent = "";
        return;
    }

    Array.from(files).forEach(file => {
        totalSize += file.size;
        validFiles.push(file);

        // Image preview
        if (file.type.startsWith("image/")) {
            const reader = new FileReader();
            reader.onload = e => {
                const img = document.createElement("img");
                img.src = e.target.result;
                img.className = "preview-img";
                img.style.width = "100px";
                img.style.height = "100px";
                img.style.objectFit = "cover";
                img.style.borderRadius = "5px";
                previewContainer.appendChild(img);
            };
            reader.readAsDataURL(file);
        }
    });

    // Section size validation
    if (totalSize > MAX_SECTION_SIZE) {
        warnings.innerHTML =
            `❌ Total upload size must not exceed ${MAX_SECTION_SIZE_MB} MB`;
        validFiles = [];
        fileInput.value = "";
        fileCount.textContent = "";
        previewContainer.innerHTML = "";
        return;
    }

    fileCount.textContent =
        `${validFiles.length} file(s) — ${(totalSize / 1024 / 1024).toFixed(2)} MB total`;
}

// ==============================
// Click-to-select
// ==============================
fileInput.addEventListener("change", function () {
    handleFiles(this.files);
});

// ==============================
// Drag-and-drop handlers
// ==============================
["dragenter", "dragover"].forEach(event => {
    dropZone.addEventListener(event, e => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("dragover");
    });
});

["dragleave", "drop"].forEach(event => {
    dropZone.addEventListener(event, e => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("dragover");
    });
});

dropZone.addEventListener("drop", e => {
    const files = e.dataTransfer.files;
    fileInput.files = files;
    handleFiles(files);
});

// ==============================
// Utility Functions
// ==============================
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatSpeed(bytesPerSecond) {
    return formatBytes(bytesPerSecond) + '/s';
}

function calculateSpeed(loaded, startTime) {
    const currentTime = Date.now();
    const elapsedSeconds = (currentTime - startTime) / 1000;
    return elapsedSeconds > 0 ? loaded / elapsedSeconds : 0;
}

function formatTimeRemaining(loaded, total, speed) {
    if (speed === 0) return 'Calculating...';
    const remainingBytes = total - loaded;
    const secondsRemaining = remainingBytes / speed;

    if (secondsRemaining < 60) {
        return `${Math.ceil(secondsRemaining)} seconds`;
    } else if (secondsRemaining < 3600) {
        return `${Math.ceil(secondsRemaining / 60)} minutes`;
    } else {
        return `${Math.ceil(secondsRemaining / 3600)} hours`;
    }
}

// ==============================
// Progress Functions
// ==============================
function updateProgress(loaded, total) {
    const percent = Math.round((loaded / total) * 100);
    uploadProgressBar.style.width = `${percent}%`;
    uploadProgressBar.textContent = `${percent}%`;
    uploadProgressBar.setAttribute('aria-valuenow', percent);

    // Calculate upload speed
    const speed = calculateSpeed(loaded, uploadStartTime);
    const speedFormatted = formatSpeed(speed);
    const timeRemaining = formatTimeRemaining(loaded, total, speed);

    uploadSpeedText.textContent = `${speedFormatted} - ${timeRemaining} remaining`;
    uploadProgressText.textContent = `${formatBytes(loaded)} of ${formatBytes(total)}`;
}

function createFileList() {
    uploadFileList.innerHTML = '';

    validFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'upload-file-item';
        fileItem.innerHTML = `
            <div class="d-flex align-items-center" style="flex: 1;">
                <div class="file-status pending"></div>
                <div style="flex: 1;">
                    <div class="text-truncate" style="max-width: 200px;" title="${file.name}">
                        ${file.name}
                    </div>
                    <small class="text-muted">${formatBytes(file.size)}</small>
                </div>
            </div>
            <div class="progress" style="width: 80px; height: 20px;">
                <div class="file-progress progress-bar" role="progressbar" style="width: 0%;">0%</div>
            </div>
        `;
        uploadFileList.appendChild(fileItem);
    });
}

function updateFileListStatus(currentFileIndex, totalFiles, percent) {
    const fileItems = uploadFileList.querySelectorAll('.upload-file-item');

    // Mark previous files as completed
    for (let i = 0; i < currentFileIndex; i++) {
        if (fileItems[i]) {
            const status = fileItems[i].querySelector('.file-status');
            const progress = fileItems[i].querySelector('.file-progress');
            if (status) {
                status.className = 'file-status completed';
                status.innerHTML = '✓';
            }
            if (progress) {
                progress.style.width = '100%';
                progress.textContent = '100%';
                progress.className = 'file-progress progress-bar bg-success';
            }
        }
    }

    // Update current file
    if (fileItems[currentFileIndex]) {
        const status = fileItems[currentFileIndex].querySelector('.file-status');
        const progress = fileItems[currentFileIndex].querySelector('.file-progress');
        if (status) {
            status.className = 'file-status uploading';
            status.innerHTML = '';
        }
        if (progress) {
            progress.style.width = `${percent}%`;
            progress.textContent = `${percent}%`;
            progress.className = 'file-progress progress-bar progress-bar-striped progress-bar-animated';
        }
    }
}

// ==============================
// Cancel Upload Function
// ==============================
cancelUploadBtn.addEventListener('click', function() {
    if (xhr) {
        xhr.abort();
        uploadStatusText.textContent = 'Upload cancelled';
        uploadStatusText.parentElement.parentElement.className = 'alert alert-warning';

        // Hide upload status after 2 seconds
        setTimeout(() => {
            resetUploadForm();
        }, 2000);
    }
});

function resetUploadForm() {
    uploadStatusContainer.style.display = 'none';
    uploadForm.style.display = 'block';
    xhr = null;
    uploadStartTime = null;
    uploadedBytes = 0;
}

// ==============================
// Form Submission with Progress (using XMLHttpRequest)
// ==============================
uploadForm.addEventListener("submit", function (e) {
    e.preventDefault();

    if (validFiles.length === 0) {
        warnings.textContent = "❌ Please select at least one file.";
        return;
    }

    if (totalSize > MAX_SECTION_SIZE) {
        warnings.textContent =
            `❌ Total upload size must not exceed ${MAX_SECTION_SIZE_MB} MB`;
        return;
    }

    // Get form data
    const formData = new FormData(uploadForm);

    // Reset progress
    uploadStartTime = Date.now();
    uploadedBytes = 0;

    // Show upload status
    uploadStatusContainer.style.display = 'block';
    uploadForm.style.display = 'none';
    uploadStatusText.textContent = 'Preparing upload...';
    uploadStatusText.parentElement.parentElement.className = 'alert alert-info';
    uploadProgressBar.style.width = '0%';
    uploadProgressBar.textContent = '0%';
    uploadSpeedText.textContent = '';
    uploadProgressText.textContent = 'Starting upload...';

    // Create file list
    createFileList();

    // Create XMLHttpRequest for progress tracking
    xhr = new XMLHttpRequest();

    // Progress event
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            updateProgress(e.loaded, e.total);

            // Estimate which file is being uploaded
            const avgFileSize = totalSize / validFiles.length;
            const currentFileIndex = Math.min(
                Math.floor(e.loaded / avgFileSize),
                validFiles.length - 1
            );
            const filePercent = Math.min(
                Math.round(((e.loaded % avgFileSize) / avgFileSize) * 100),
                100
            );

            updateFileListStatus(currentFileIndex, validFiles.length, filePercent);
        }
    });

    // Load event (when upload completes)
    xhr.addEventListener('load', function() {
        if (xhr.status >= 200 && xhr.status < 300) {
            // Success
            uploadStatusText.textContent = 'Upload complete! Processing files...';
            uploadStatusText.parentElement.parentElement.className = 'alert alert-success';
            uploadProgressBar.style.width = '100%';
            uploadProgressBar.textContent = '100%';
            uploadProgressBar.className = 'progress-bar progress-bar-striped bg-success';

            // Mark all files as completed
            const fileItems = uploadFileList.querySelectorAll('.upload-file-item');
            fileItems.forEach(item => {
                const status = item.querySelector('.file-status');
                const progress = item.querySelector('.file-progress');
                if (status) {
                    status.className = 'file-status completed';
                    status.innerHTML = '✓';
                }
                if (progress) {
                    progress.style.width = '100%';
                    progress.textContent = '100%';
                    progress.className = 'file-progress progress-bar bg-success';
                }
            });

            // Try to parse response as JSON for redirect
            try {
                const response = JSON.parse(xhr.responseText);
                if (response.redirect_url) {
                    setTimeout(() => {
                        window.location.href = response.redirect_url;
                    }, 1500);
                } else {
                    // If no redirect in JSON, check if response is HTML
                    if (xhr.responseText.includes('<html')) {
                        // It's an HTML page, reload the form
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else {
                        // Fallback: submit the form normally
                        setTimeout(() => {
                            uploadForm.submit();
                        }, 1500);
                    }
                }
            } catch (error) {
                // If response is not JSON, it's probably HTML
                // Submit the form normally
                setTimeout(() => {
                    uploadForm.submit();
                }, 1500);
            }
        } else {
            // Server error
            uploadStatusText.textContent = `Upload failed (${xhr.status}). Please try again.`;
            uploadStatusText.parentElement.parentElement.className = 'alert alert-danger';

            // Show retry button
            setTimeout(() => {
                resetUploadForm();
            }, 3000);
        }
    });

    // Error event
    xhr.addEventListener('error', function() {
        uploadStatusText.textContent = 'Network error. Please check your connection.';
        uploadStatusText.parentElement.parentElement.className = 'alert alert-danger';

        setTimeout(() => {
            resetUploadForm();
        }, 3000);
    });

    // Abort event
    xhr.addEventListener('abort', function() {
        uploadStatusText.textContent = 'Upload cancelled';
        uploadStatusText.parentElement.parentElement.className = 'alert alert-warning';

        setTimeout(() => {
            resetUploadForm();
        }, 2000);
    });

    // Set CSRF token header
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    xhr.open('POST', uploadForm.action);
    xhr.setRequestHeader('X-CSRFToken', csrfToken);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    // Send the request
    xhr.send(formData);
});

// ==============================
// Initial validation
// ==============================
uploadForm.addEventListener("submit", function (e) {
    // This validation is now handled in the async submit handler above
});