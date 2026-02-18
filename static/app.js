const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const fileInfo = document.getElementById("file-info");
const fileName = document.getElementById("file-name");
const voiceSelect = document.getElementById("voice-select");
const convertBtn = document.getElementById("convert-btn");
const progressSection = document.getElementById("progress-section");
const progressFill = document.getElementById("progress-fill");
const progressPct = document.getElementById("progress-pct");
const progressNote = document.getElementById("progress-note");
const downloadSection = document.getElementById("download-section");
const downloadBtn = document.getElementById("download-btn");
const downloadNote = document.getElementById("download-note");
const errorSection = document.getElementById("error-section");
const errorMessage = document.getElementById("error-message");

let selectedFile = null;
let pollInterval = null;

// ── Load voices ──
async function loadVoices() {
  try {
    const res = await fetch("/api/voices");
    const data = await res.json();
    voiceSelect.innerHTML = data.voices
      .map((v) => `<option value="${v.id}">${v.label}</option>`)
      .join("");
  } catch {
    voiceSelect.innerHTML = '<option value="en-US-AriaNeural">Aria (US Female)</option>';
  }
}

loadVoices();

// ── File selection ──
function handleFile(file) {
  if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
    alert("Please select a PDF file.");
    return;
  }
  selectedFile = file;
  fileName.textContent = file.name;
  fileInfo.classList.remove("hidden");
  convertBtn.disabled = false;
}

fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));

// Drag and drop
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  handleFile(e.dataTransfer.files[0]);
});

// Tap on drop zone (mobile)
dropZone.addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") {
    fileInput.click();
  }
});

// ── Convert ──
convertBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  convertBtn.disabled = true;
  showProgress();

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("voice", voiceSelect.value);

  try {
    const res = await fetch("/api/convert", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json();
      showError(err.detail || "Upload failed.");
      return;
    }
    const { job_id } = await res.json();
    startPolling(job_id);
  } catch (e) {
    showError("Could not connect to server.");
  }
});

// ── Polling ──
function startPolling(jobId) {
  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${jobId}`);
      const job = await res.json();

      if (job.status === "processing") {
        const total = job.total || 1;
        const done = job.progress || 0;
        const pct = total ? Math.round((done / total) * 100) : 0;

        progressFill.style.width = pct + "%";
        progressPct.textContent = pct + "%";

        if (done === 0) {
          progressNote.textContent = "Extracting text from PDF...";
        } else {
          progressNote.textContent = `Converting chunk ${done} of ${total}...`;
        }
      } else if (job.status === "done") {
        clearInterval(pollInterval);
        progressFill.style.width = "100%";
        progressPct.textContent = "100%";
        progressNote.textContent = "Finalizing audiobook...";

        setTimeout(() => showDownload(jobId, job.filename), 600);
      } else if (job.status === "error") {
        clearInterval(pollInterval);
        showError(job.error || "An error occurred during conversion.");
      }
    } catch {
      clearInterval(pollInterval);
      showError("Lost connection to server.");
    }
  }, 1500);
}

// ── UI helpers ──
function showProgress() {
  hide(downloadSection);
  hide(errorSection);
  progressFill.style.width = "0%";
  progressPct.textContent = "0%";
  progressNote.textContent = "Starting conversion...";
  show(progressSection);
}

function showDownload(jobId, originalName) {
  hide(progressSection);
  const stem = originalName.replace(/\.pdf$/i, "");
  downloadNote.textContent = `"${stem}.mp3" is ready to download.`;
  downloadBtn.href = `/api/download/${jobId}`;
  downloadBtn.download = `${stem}.mp3`;
  show(downloadSection);
}

function showError(msg) {
  hide(progressSection);
  errorMessage.textContent = msg;
  show(errorSection);
  convertBtn.disabled = false;
}

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

// ── Reset buttons ──
document.getElementById("reset-btn").addEventListener("click", resetApp);
document.getElementById("error-reset-btn").addEventListener("click", resetApp);

function resetApp() {
  selectedFile = null;
  fileInput.value = "";
  fileName.textContent = "";
  fileInfo.classList.add("hidden");
  convertBtn.disabled = true;
  hide(downloadSection);
  hide(errorSection);
  hide(progressSection);
  if (pollInterval) clearInterval(pollInterval);
}
