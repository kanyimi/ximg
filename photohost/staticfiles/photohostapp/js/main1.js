
"use strict";

// ==========================================
// CONFIGURATION
// ==========================================

const MAX_SECTION_SIZE_MB = 300;
const MAX_SECTION_SIZE = MAX_SECTION_SIZE_MB * 1024 * 1024;

// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // ELEMENTS
    // ==========================================

    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const fileCount = document.getElementById("fileCount");
    const warnings = document.getElementById("fileWarnings");
    const previewContainer = document.getElementById("previewContainer");

    const uploadForm = document.getElementById("uploadForm");
    const submitBtn = document.getElementById("submitBtn");

    const uploadStatusContainer =
        document.getElementById("uploadStatusContainer");

    const uploadStatusText =
        document.getElementById("uploadStatusText");

    const uploadProgressBar =
        document.getElementById("uploadProgressBar");

    const uploadProgressText =
        document.getElementById("uploadProgressText");

    const uploadSpeedText =
        document.getElementById("uploadSpeedText");

    const uploadFileList =
        document.getElementById("uploadFileList");

    const cancelUploadBtn =
        document.getElementById("cancelUploadBtn");

    // Checkboxes from upload.html
    const multiUploadOption =
        document.getElementById("multiUploadOption");

    const multiUploadCheckbox =
        document.getElementById("id_multi_upload");

    const passwordOption =
        document.getElementById("passwordOption");

    const passwordCheckbox =
        document.getElementById("id_set_password");

    const passwordContainer =
        document.getElementById("passwordInputContainer");

    const passwordInput =
        document.getElementById("sectionPassword");

    if (
        !dropZone ||
        !fileInput ||
        !fileCount ||
        !warnings ||
        !previewContainer ||
        !uploadForm ||
        !submitBtn ||
        !uploadStatusContainer ||
        !uploadStatusText ||
        !uploadProgressBar ||
        !uploadProgressText ||
        !uploadSpeedText ||
        !uploadFileList ||
        !cancelUploadBtn
    ) {
        console.error(
            "main1.js: One or more required upload elements are missing."
        );
        return;
    }

    // ==========================================
    // STATE
    // ==========================================

    let validFiles = [];
    let totalSize = 0;
    let xhr = null;
    let uploadStartTime = null;
    let isUploading = false;
    let previewURLs = [];

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================

    function formatBytes(bytes) {
        if (!bytes || bytes <= 0) {
            return "0 Bytes";
        }

        const units = ["Bytes", "KB", "MB", "GB"];
        const index = Math.min(
            Math.floor(Math.log(bytes) / Math.log(1024)),
            units.length - 1
        );

        return (
            parseFloat(
                (bytes / Math.pow(1024, index)).toFixed(2)
            ) +
            " " +
            units[index]
        );
    }

    function formatSpeed(bytesPerSecond) {
        return formatBytes(bytesPerSecond) + "/s";
    }

    function calculateSpeed(loaded, startTime) {
        if (!startTime) return 0;

        const elapsedSeconds =
            (Date.now() - startTime) / 1000;

        return elapsedSeconds > 0
            ? loaded / elapsedSeconds
            : 0;
    }

    function formatTimeRemaining(loaded, total, speed) {
        if (speed <= 0) {
            return "Calculating...";
        }

        const remainingBytes = Math.max(
            0,
            total - loaded
        );

        const secondsRemaining =
            remainingBytes / speed;

        if (secondsRemaining < 60) {
            return `${Math.ceil(secondsRemaining)} seconds`;
        }

        if (secondsRemaining < 3600) {
            return `${Math.ceil(secondsRemaining / 60)} minutes`;
        }

        return `${Math.ceil(secondsRemaining / 3600)} hours`;
    }

    // ==========================================
    // UPDATE MULTI-UPLOAD CHECKBOX
    // ==========================================

    function updateMultiUploadOption() {
        if (!multiUploadOption || !multiUploadCheckbox) {
            return;
        }

        const show = validFiles.length > 1;

        multiUploadOption.style.display =
            show ? "block" : "none";

        if (!show) {
            multiUploadCheckbox.checked = false;
        }
    }

    // ==========================================
    // UPDATE PASSWORD CHECKBOX
    // ==========================================

    function updatePasswordField() {
        if (
            !passwordCheckbox ||
            !passwordContainer ||
            !passwordInput
        ) {
            return;
        }

        const enabled = passwordCheckbox.checked;

        passwordContainer.style.display =
            enabled ? "block" : "none";

        passwordInput.required = enabled;
        passwordInput.disabled = !enabled;

        if (!enabled) {
            passwordInput.value = "";
        }
    }

    function updatePasswordOption() {
        if (!passwordOption || !passwordCheckbox) {
            return;
        }

        const hasFiles = validFiles.length > 0;

        passwordOption.style.display =
            hasFiles ? "block" : "none";

        if (!hasFiles) {
            passwordCheckbox.checked = false;
        }

        updatePasswordField();
    }

    function updateUploadOptions() {
        updateMultiUploadOption();
        updatePasswordOption();
    }

    if (passwordCheckbox) {
        passwordCheckbox.addEventListener("change", () => {
            updatePasswordField();

            if (
                passwordCheckbox.checked &&
                passwordInput
            ) {
                passwordInput.focus();
            }
        });
    }

    // ==========================================
    // CLEAR IMAGE PREVIEWS
    // ==========================================

    function clearPreviews() {
        previewURLs.forEach(url => {
            URL.revokeObjectURL(url);
        });

        previewURLs = [];
        previewContainer.innerHTML = "";
    }

    // ==========================================
    // HANDLE FILES
    // ==========================================

    function handleFiles(files) {
        if (isUploading) {
            return;
        }

        warnings.textContent = "";
        clearPreviews();

        validFiles = [];
        totalSize = 0;

        if (!files || files.length === 0) {
            fileCount.textContent = "";
            updateUploadOptions();
            return;
        }

        const selectedFiles = Array.from(files);

        selectedFiles.forEach(file => {
            totalSize += file.size;
            validFiles.push(file);
        });

        // Validate total size before creating previews.
        if (totalSize > MAX_SECTION_SIZE) {
            warnings.textContent =
                `❌ Total upload size must not exceed ${MAX_SECTION_SIZE_MB} MB.`;

            validFiles = [];
            totalSize = 0;

            fileInput.value = "";
            fileCount.textContent = "";

            updateUploadOptions();
            return;
        }

        // ==========================================
        // IMAGE PREVIEWS
        // ==========================================

        validFiles.forEach(file => {
            if (!file.type.startsWith("image/")) {
                return;
            }

            const imageURL = URL.createObjectURL(file);
            previewURLs.push(imageURL);

            const img = document.createElement("img");

            img.src = imageURL;
            img.alt = file.name;
            img.className = "preview-img";

            img.style.width = "100px";
            img.style.height = "100px";
            img.style.objectFit = "cover";
            img.style.borderRadius = "5px";

            previewContainer.appendChild(img);
        });

        // ==========================================
        // FILE COUNTER
        // ==========================================

        fileCount.textContent =
            `${validFiles.length} file(s) — ${formatBytes(totalSize)} total`;

        // Update checkboxes.
        updateUploadOptions();
    }

    // ==========================================
    // FILE PICKER
    // ==========================================

    // IMPORTANT FIX:
    // Previously, the file picker updated the
    // checkboxes but did not call handleFiles().
    //
    // Now both file picker and drag-and-drop
    // use this one change listener.

    fileInput.addEventListener("change", () => {
        handleFiles(fileInput.files);
    });

    // ==========================================
    // DRAG-AND-DROP HANDLERS
    // ==========================================

    ["dragenter", "dragover"].forEach(eventName => {
        dropZone.addEventListener(eventName, event => {
            event.preventDefault();
            event.stopPropagation();

            if (!isUploading) {
                dropZone.classList.add("dragover");
            }
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropZone.addEventListener(eventName, event => {
            event.preventDefault();
            event.stopPropagation();

            dropZone.classList.remove("dragover");
        });
    });

    dropZone.addEventListener("drop", event => {
        if (isUploading) {
            return;
        }

        const droppedFiles = event.dataTransfer.files;

        if (!droppedFiles || droppedFiles.length === 0) {
            return;
        }

        // Assign dropped files to the real input.
        fileInput.files = droppedFiles;

        // Trigger the same processing used by
        // normal file selection.
        //
        // This also notifies upload.html listeners.
        fileInput.dispatchEvent(
            new Event("change", { bubbles: true })
        );

        // Do NOT call handleFiles() again here.
        // The change listener already handles it.
    });

    // ==========================================
    // INITIAL STATE
    // ==========================================

    handleFiles(fileInput.files);

    // ==========================================
    // UPLOAD PROGRESS
    // ==========================================

    function updateProgress(loaded, total) {
        const percent = total > 0
            ? Math.min(
                100,
                Math.round((loaded / total) * 100)
            )
            : 0;

        uploadProgressBar.style.width = `${percent}%`;
        uploadProgressBar.textContent = `${percent}%`;

        uploadProgressBar.setAttribute(
            "aria-valuenow",
            percent
        );

        const speed = calculateSpeed(
            loaded,
            uploadStartTime
        );

        const timeRemaining = formatTimeRemaining(
            loaded,
            total,
            speed
        );

        uploadSpeedText.textContent =
            `${formatSpeed(speed)} - ${timeRemaining} remaining`;

        uploadProgressText.textContent =
            `${formatBytes(loaded)} of ${formatBytes(total)}`;
    }

    // ==========================================
    // CREATE UPLOAD FILE LIST
    // ==========================================

    function createFileList() {
        uploadFileList.innerHTML = "";

        validFiles.forEach(file => {
            const fileItem = document.createElement("div");

            fileItem.className = "upload-file-item";

            const info = document.createElement("div");
            info.className = "d-flex align-items-center";
            info.style.flex = "1";
            info.style.minWidth = "0";

            const status = document.createElement("div");
            status.className = "file-status pending";

            const details = document.createElement("div");
            details.style.flex = "1";
            details.style.minWidth = "0";

            const name = document.createElement("div");
            name.className = "text-truncate";
            name.style.maxWidth = "200px";
            name.title = file.name;
            name.textContent = file.name;

            const size = document.createElement("small");
            size.className = "text-muted";
            size.textContent = formatBytes(file.size);

            details.appendChild(name);
            details.appendChild(size);

            info.appendChild(status);
            info.appendChild(details);

            const progressWrapper =
                document.createElement("div");

            progressWrapper.className = "progress";
            progressWrapper.style.width = "80px";
            progressWrapper.style.height = "20px";

            const progress = document.createElement("div");

            progress.className =
                "file-progress progress-bar";

            progress.setAttribute(
                "role",
                "progressbar"
            );

            progress.style.width = "0%";
            progress.textContent = "0%";

            progressWrapper.appendChild(progress);

            fileItem.appendChild(info);
            fileItem.appendChild(progressWrapper);

            uploadFileList.appendChild(fileItem);
        });
    }

    // ==========================================
    // UPDATE FILE LIST PROGRESS
    // ==========================================

    function updateFileListStatus(
        currentFileIndex,
        totalFiles,
        percent
    ) {
        const fileItems = uploadFileList.querySelectorAll(
            ".upload-file-item"
        );

        // Mark previous files as complete.
        for (let i = 0; i < currentFileIndex; i++) {
            const item = fileItems[i];

            if (!item) continue;

            const status =
                item.querySelector(".file-status");

            const progress =
                item.querySelector(".file-progress");

            if (status) {
                status.className =
                    "file-status completed";

                status.textContent = "✓";
            }

            if (progress) {
                progress.style.width = "100%";
                progress.textContent = "100%";
                progress.className =
                    "file-progress progress-bar bg-success";
            }
        }

        // Update current file.
        const currentItem = fileItems[currentFileIndex];

        if (!currentItem) return;

        const status =
            currentItem.querySelector(".file-status");

        const progress =
            currentItem.querySelector(".file-progress");

        if (status) {
            status.className = "file-status uploading";
            status.textContent = "";
        }

        if (progress) {
            progress.style.width = `${percent}%`;
            progress.textContent = `${percent}%`;

            progress.className =
                "file-progress progress-bar " +
                "progress-bar-striped progress-bar-animated";
        }
    }

    // ==========================================
    // MARK ALL FILES COMPLETE
    // ==========================================

    function markAllFilesCompleted() {
        const fileItems = uploadFileList.querySelectorAll(
            ".upload-file-item"
        );

        fileItems.forEach(item => {
            const status =
                item.querySelector(".file-status");

            const progress =
                item.querySelector(".file-progress");

            if (status) {
                status.className =
                    "file-status completed";

                status.textContent = "✓";
            }

            if (progress) {
                progress.style.width = "100%";
                progress.textContent = "100%";
                progress.className =
                    "file-progress progress-bar bg-success";
            }
        });
    }

    // ==========================================
    // UPLOAD STATUS HELPERS
    // ==========================================

    function setUploadAlert(type, message) {
        uploadStatusText.textContent = message;

        const alert = uploadStatusText.closest(".alert");

        if (alert) {
            alert.className = `alert alert-${type}`;
        }
    }

    function resetUploadForm() {
        uploadStatusContainer.style.display = "none";
        uploadForm.style.display = "block";

        xhr = null;
        uploadStartTime = null;
        isUploading = false;

        submitBtn.disabled = false;
        fileInput.disabled = false;

        uploadProgressBar.className =
            "progress-bar progress-bar-striped " +
            "progress-bar-animated";
    }

    function showUploadError(message) {
        setUploadAlert("danger", message);

        uploadProgressBar.classList.remove(
            "progress-bar-animated"
        );

        isUploading = false;

        // Keep the selected files so users can retry.
        setTimeout(() => {
            resetUploadForm();
            warnings.textContent = message;
        }, 2500);
    }

    // ==========================================
    // CANCEL UPLOAD
    // ==========================================

    cancelUploadBtn.addEventListener("click", () => {
        if (!xhr || !isUploading) {
            return;
        }

        cancelUploadBtn.disabled = true;
        xhr.abort();
    });

    // ==========================================
    // FORM SUBMISSION
    // ==========================================

    uploadForm.addEventListener("submit", event => {
        event.preventDefault();

        if (isUploading) {
            return;
        }

        warnings.textContent = "";

        // Synchronize the selected files.
        // This also catches any changes made by
        // another file-selection script.
        handleFiles(fileInput.files);

        if (validFiles.length === 0) {
            warnings.textContent =
                "❌ Please select at least one file.";
            return;
        }

        if (totalSize > MAX_SECTION_SIZE) {
            warnings.textContent =
                `❌ Total upload size must not exceed ${MAX_SECTION_SIZE_MB} MB.`;
            return;
        }

        // Validate password before uploading.
        if (
            passwordCheckbox &&
            passwordCheckbox.checked &&
            passwordInput
        ) {
            if (passwordInput.value.length < 8) {
                warnings.textContent =
                    "❌ Section password must contain at least 8 characters.";

                passwordInput.focus();
                return;
            }
        }

        // ==========================================
        // FORM DATA
        // ==========================================

        const formData = new FormData(uploadForm);

        // Make sure the submitted files match
        // the files shown in the preview.
        formData.delete("files");

        validFiles.forEach(file => {
            formData.append(
                "files",
                file,
                file.name
            );
        });

        // ==========================================
        // INITIALIZE UPLOAD
        // ==========================================

        isUploading = true;
        uploadStartTime = Date.now();

        submitBtn.disabled = true;
        fileInput.disabled = true;
        cancelUploadBtn.disabled = false;

        uploadStatusContainer.style.display = "block";
        uploadForm.style.display = "none";

        setUploadAlert("info", "Preparing upload...");

        uploadProgressBar.className =
            "progress-bar progress-bar-striped " +
            "progress-bar-animated";

        uploadProgressBar.style.width = "0%";
        uploadProgressBar.textContent = "0%";
        uploadProgressBar.setAttribute(
            "aria-valuenow",
            "0"
        );

        uploadSpeedText.textContent = "";
        uploadProgressText.textContent =
            "Starting upload...";

        createFileList();

        // ==========================================
        // CREATE XHR
        // ==========================================

        const request = new XMLHttpRequest();
        xhr = request;

        // ==========================================
        // PROGRESS EVENT
        // ==========================================

        request.upload.addEventListener(
            "progress",
            event => {
                if (!event.lengthComputable) {
                    return;
                }

                updateProgress(
                    event.loaded,
                    event.total
                );

                // Approximate per-file progress.
                // The browser sends multipart data
                // in one request, so this is an estimate.
                const avgFileSize =
                    event.total / validFiles.length;

                const currentFileIndex = Math.min(
                    Math.floor(
                        event.loaded / avgFileSize
                    ),
                    validFiles.length - 1
                );

                const filePercent = Math.min(
                    100,
                    Math.round(
                        (
                            (event.loaded -
                                currentFileIndex * avgFileSize)
                            / avgFileSize
                        ) * 100
                    )
                );

                updateFileListStatus(
                    currentFileIndex,
                    validFiles.length,
                    filePercent
                );
            }
        );

        // ==========================================
        // SUCCESS / SERVER RESPONSE
        // ==========================================

        request.addEventListener("load", () => {
            let response = null;

            try {
                response = JSON.parse(
                    request.responseText
                );
            } catch (error) {
                response = null;
            }

            if (
                request.status >= 200 &&
                request.status < 300 &&
                response &&
                response.status === "success" &&
                response.redirect_url
            ) {
                setUploadAlert(
                    "success",
                    "Upload complete! Processing files..."
                );

                uploadProgressBar.style.width = "100%";
                uploadProgressBar.textContent = "100%";

                uploadProgressBar.setAttribute(
                    "aria-valuenow",
                    "100"
                );

                uploadProgressBar.className =
                    "progress-bar progress-bar-striped bg-success";

                markAllFilesCompleted();

                // Supports both normal sections and
                // Multi-upload batch results pages.
                window.location.assign(
                    response.redirect_url
                );

                return;
            }

            let errorMessage =
                `Upload failed (${request.status}). Please try again.`;

            if (response) {
                if (response.message) {
                    errorMessage = response.message;
                }

                if (response.errors) {
                    const errorDetails = Object.entries(
                        response.errors
                    ).map(([field, errors]) => {
                        const messages = Array.isArray(errors)
                            ? errors.join(", ")
                            : String(errors);

                        return `${field}: ${messages}`;
                    });

                    if (errorDetails.length > 0) {
                        errorMessage +=
                            " " + errorDetails.join(" | ");
                    }
                }
            }

            showUploadError(errorMessage);
        });

        // ==========================================
        // NETWORK ERROR
        // ==========================================

        request.addEventListener("error", () => {
            showUploadError(
                "Network error. Please check your connection."
            );
        });

        // ==========================================
        // UPLOAD CANCELLED
        // ==========================================

        request.addEventListener("abort", () => {
            setUploadAlert(
                "warning",
                "Upload cancelled."
            );

            isUploading = false;

            setTimeout(() => {
                resetUploadForm();
            }, 1500);
        });

        // ==========================================
        // SEND REQUEST
        // ==========================================

        const csrfInput = uploadForm.querySelector(
            '[name="csrfmiddlewaretoken"]'
        );

        const csrfToken = csrfInput
            ? csrfInput.value
            : "";

        request.open(
            "POST",
            uploadForm.action || window.location.href
        );

        request.setRequestHeader(
            "X-Requested-With",
            "XMLHttpRequest"
        );

        if (csrfToken) {
            request.setRequestHeader(
                "X-CSRFToken",
                csrfToken
            );
        }

        request.send(formData);
    });

});
