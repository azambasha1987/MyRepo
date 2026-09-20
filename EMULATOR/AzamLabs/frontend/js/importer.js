/**
 * AzamLabs Drag & Drop Universal Lab Importer Controller
 */

class UniversalImporter {
  constructor(appContext) {
    this.app = appContext;
    this.modal = document.getElementById('importerModal');
    this.dropzone = document.getElementById('importerDropzone');
    this.fileInput = document.getElementById('importerFileInput');
    this.detectedBadge = document.getElementById('importerDetectedBadge');
    this.btnConfirm = document.getElementById('btnConfirmImport');

    this.pendingContent = null;
    this.pendingFilename = null;
    this.detectedFormat = 'unknown';

    this.initEvents();
  }

  initEvents() {
    const closeBtn = document.getElementById('btnCloseImporter');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.close());
    }

    if (this.dropzone) {
      this.dropzone.addEventListener('click', () => {
        if (this.fileInput) this.fileInput.click();
      });

      this.dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        this.dropzone.classList.add('dragover');
      });

      this.dropzone.addEventListener('dragleave', () => {
        this.dropzone.classList.remove('dragover');
      });

      this.dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        this.dropzone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          this.handleFile(e.dataTransfer.files[0]);
        }
      });
    }

    if (this.fileInput) {
      this.fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          this.handleFile(e.target.files[0]);
        }
      });
    }

    if (this.btnConfirm) {
      this.btnConfirm.addEventListener('click', () => this.executeImport());
    }
  }

  open() {
    if (this.modal) this.modal.classList.add('open');
    this.resetState();
  }

  close() {
    if (this.modal) this.modal.classList.remove('open');
    this.resetState();
  }

  resetState() {
    this.pendingContent = null;
    this.pendingFilename = null;
    this.detectedFormat = 'unknown';
    if (this.detectedBadge) {
      this.detectedBadge.style.display = 'none';
      this.detectedBadge.textContent = '';
    }
    if (this.btnConfirm) {
      this.btnConfirm.disabled = true;
    }
  }

  handleFile(file) {
    this.pendingFilename = file.name;
    const reader = new FileReader();

    reader.onload = (e) => {
      this.pendingContent = e.target.result;
      this.detectFormat(this.pendingContent, this.pendingFilename);
    };

    // If text or binary
    if (file.name.endsWith('.azaml') || file.name.endsWith('.tar.gz')) {
      reader.readAsArrayBuffer(file);
    } else {
      reader.readAsText(file);
    }
  }

  detectFormat(content, filename) {
    const fn = (filename || '').toLowerCase();
    let fmt = 'Unknown Format';

    if (fn.endsWith('.azaml')) {
      fmt = 'Universal .azaml Bundle';
      this.detectedFormat = 'azaml';
    } else if (fn.endsWith('.unl')) {
      fmt = 'EVE-NG / PNETLab XML (.unl)';
      this.detectedFormat = 'eve';
    } else if (fn.endsWith('.gns3')) {
      fmt = 'GNS3 Project JSON (.gns3)';
      this.detectedFormat = 'gns3';
    } else if (fn.endsWith('.clab.yml') || fn.endsWith('.clab.yaml')) {
      fmt = 'Containerlab YAML (.clab.yml)';
      this.detectedFormat = 'clab';
    } else if (typeof content === 'string') {
      const trimmed = content.trim();
      if (trimmed.startsWith('<') || trimmed.includes('<lab ')) {
        fmt = 'EVE-NG / PNETLab XML (.unl)';
        this.detectedFormat = 'eve';
      } else if (trimmed.startsWith('{') && trimmed.includes('topology')) {
        fmt = 'GNS3 Project JSON (.gns3)';
        this.detectedFormat = 'gns3';
      } else if (trimmed.includes('kinds:') || trimmed.includes('mgmt:')) {
        fmt = 'Containerlab YAML (.clab.yml)';
        this.detectedFormat = 'clab';
      } else if (trimmed.includes('lab:') && trimmed.includes('nodes:')) {
        fmt = 'Cisco CML 2.x YAML (.yaml)';
        this.detectedFormat = 'cml';
      } else if (trimmed.toLowerCase().includes('hostname ') || trimmed.toLowerCase().includes('interface ')) {
        fmt = 'P2V Production Running-Config';
        this.detectedFormat = 'p2v';
      }
    }

    if (this.detectedBadge) {
      this.detectedBadge.style.display = 'inline-block';
      this.detectedBadge.textContent = `Auto-Detected: ${fmt}`;
    }

    if (this.btnConfirm) {
      this.btnConfirm.disabled = false;
    }
  }

  async executeImport() {
    if (!this.pendingContent) return;

    if (this.btnConfirm) {
      this.btnConfirm.textContent = 'Importing...';
      this.btnConfirm.disabled = true;
    }

    try {
      let resp;
      if (this.pendingContent instanceof ArrayBuffer) {
        // Upload binary as FormData
        const formData = new FormData();
        const blob = new Blob([this.pendingContent]);
        formData.append('file', blob, this.pendingFilename || 'imported.azaml');
        resp = await fetch('/api/v1/convert/upload', {
          method: 'POST',
          body: formData,
        });
      } else {
        // Post string payload
        resp = await fetch('/api/v1/convert/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: this.pendingContent,
            filename: this.pendingFilename,
            format_hint: this.detectedFormat !== 'unknown' ? this.detectedFormat : null,
          }),
        });
      }

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Import failed');
      }

      const newTopology = await resp.json();
      this.app.loadTopology(newTopology);
      this.close();
      this.app.showNotification(`Successfully imported lab: ${newTopology.name}`, 'success');
    } catch (e) {
      alert(`Import Error: ${e.message}`);
    } finally {
      if (this.btnConfirm) {
        this.btnConfirm.textContent = 'Import to Canvas';
        this.btnConfirm.disabled = false;
      }
    }
  }
}

window.UniversalImporter = UniversalImporter;
