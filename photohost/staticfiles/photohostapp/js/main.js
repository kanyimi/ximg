// main.js

// ==============================
// CONFIG (must match backend)
// ==============================
const MAX_SECTION_SIZE_MB = 150;
const MAX_SECTION_SIZE = MAX_SECTION_SIZE_MB * 1024 * 1024;

// ==============================
// Elements
// ==============================
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileCount = document.getElementById("fileCount");
const warnings = document.getElementById("fileWarnings");
const previewContainer = document.getElementById("previewContainer");
const form = document.querySelector("form");

// ==============================
// State
// ==============================
let validFiles = [];
let totalSize = 0;

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
// Final form validation
// ==============================
form.addEventListener("submit", function (e) {
    if (validFiles.length === 0) {
        warnings.textContent = "❌ Please select at least one file.";
        e.preventDefault();
        return;
    }

    if (totalSize > MAX_SECTION_SIZE) {
        warnings.textContent =
            `❌ Total upload size must not exceed ${MAX_SECTION_SIZE_MB} MB`;
        e.preventDefault();
    }

    // Otherwise: allow normal form submit
});
