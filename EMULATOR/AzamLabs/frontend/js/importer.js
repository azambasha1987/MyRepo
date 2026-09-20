/**
 * AzamLabs Drag & Drop Universal Lab Importer Controller
 * Supports dual-mode ingestion:
 *   1. Client-side Drag & Drop (supports single lab files & bulk .zip archives)
 *   2. Host Filesystem Batch Scanning (processes directories and archives directly on server)
 */

class UniversalImporter {
  constructor(appContext) {
    this.app = appContext;
    this.modal = document.getElementById('importerModal');
    this.dropzone = document.getElementById('importerDropzone');
    this.fileInput = document.getElementById('importerFileInput');
    this.detectedBadge = document.getElementById('importerDetectedBadge');
    this.btnConfirm = document.getElementById('btnConfirmImport');

    // Tab buttons & panes
    this.tabUpload = document.getElementById('tabImportUpload');
    this.tabHost = document.getElementById('tabImportHost');
    this.paneUpload = document.getElementById('importerUploadPane');
    this.paneHost = document.getElementById('importerHostPane');
    this.inputHostPath = document.getElementById('inputHostPath');
    this.inputHostTargetFolder = document.getElementById('inputHostTargetFolder');
    this.btnHostBatchImport = document.getElementById('btnHostBatchImport');

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

    // Tab Switching
    if (this.tabUpload && this.tabHost) {
      this.tabUpload.addEventListener('click', () => this.switchTab('upload'));
      this.tabHost.addEventListener('click', () => this.switchTab('host'));
    }

    // Host Batch Import
    if (this.btnHostBatchImport) {
      this.btnHostBatchImport.addEventListener('click', () => this.executeHostBatchImport());
    }

    // Dropzone Events
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

  switchTab(tab) {
    if (tab === 'upload') {
      this.tabUpload.className = 'btn btn-primary';
      this.tabHost.className = 'btn btn-ghost';
      if (this.paneUpload) this.paneUpload.style.display = 'block';
      if (this.paneHost) this.paneHost.style.display = 'none';
    } else {
      this.tabUpload.className = 'btn btn-ghost';
      this.tabHost.className = 'btn btn-primary';
      if (this.paneUpload) this.paneUpload.style.display = 'none';
      if (this.paneHost) this.paneHost.style.display = 'flex';
    }
  }

  open() {
    if (this.modal) this.modal.classList.add('open');
    this.resetState();
    this.switchTab('upload');
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
      this.btnConfirm.textContent = 'Convert & Import Lab';
    }
    if (this.fileInput) {
      this.fileInput.value = '';
    }
  }

  handleFile(file) {
    this.pendingFilename = file.name;
    const fn = file.name.toLowerCase();
    const reader = new FileReader();

    reader.onload = (e) => {
      this.pendingContent = e.target.result;
      this.detectFormat(this.pendingContent, this.pendingFilename);
    };

    // Correctly distinguish binary archives vs UTF-8 text formats
    if (fn.endsWith('.azaml') || fn.endsWith('.tar.gz') || fn.endsWith('.zip') || fn.endsWith('.gns3project')) {
      reader.readAsArrayBuffer(file);
    } else {
      reader.readAsText(file);
    }
  }

  detectFormat(content, filename) {
    const fn = (filename || '').toLowerCase();
    let fmt = 'Unknown Format';

    if (fn.endsWith('.azaml') || fn.endsWith('.bundle')) {
      fmt = 'Universal .azaml Bundle';
      this.detectedFormat = 'azaml';
    } else if (fn.endsWith('.gns3project')) {
      fmt = 'GNS3 Portable Project Archive (.gns3project)';
      this.detectedFormat = 'gns3project';
    } else if (fn.endsWith('.zip')) {
      fmt = 'Batch Multi-Lab Archive (.zip)';
      this.detectedFormat = 'zip';
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
      this.btnConfirm.textContent = this.detectedFormat === 'zip' ? 'Batch Extract & Import' : 'Convert & Import Lab';
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
        // Upload binary archive as FormData
        const formData = new FormData();
        const blob = new Blob([this.pendingContent]);
        formData.append('file', blob, this.pendingFilename || 'imported.bin');
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

      const result = await resp.json();

      // Check if this was a bulk archive import
      if (result && result.imported_count !== undefined) {
        this.app.showNotification(`Batch imported ${result.imported_count} labs successfully!`, 'success');
        if (this.app.explorer) {
          await this.app.explorer.refresh();
        }
        if (result.imported_labs && result.imported_labs.length > 0) {
          const firstLabResp = await fetch(`/api/v1/labs/${result.imported_labs[0].id}`);
          if (firstLabResp.ok) {
            const firstLab = await firstLabResp.json();
            this.app.loadTopology(firstLab);
          }
        }
      } else {
        // Single topology imported
        this.app.loadTopology(result);
        if (this.app.explorer) {
          await this.app.explorer.refresh();
        }
        this.app.showNotification(`Successfully imported lab: ${result.name}`, 'success');
      }

      this.close();
    } catch (e) {
      alert(`Import Error: ${e.message}`);
    } finally {
      if (this.btnConfirm) {
        this.btnConfirm.textContent = 'Convert & Import Lab';
        this.btnConfirm.disabled = false;
      }
    }
  }

  async executeHostBatchImport() {
    const hostPath = this.inputHostPath ? this.inputHostPath.value.trim() : '';
    const targetFolder = this.inputHostTargetFolder ? this.inputHostTargetFolder.value.trim() : '';

    if (!hostPath) {
      alert('Please enter a host directory path or .zip file path.');
      return;
    }

    if (this.btnHostBatchImport) {
      this.btnHostBatchImport.textContent = 'Scanning & Importing...';
      this.btnHostBatchImport.disabled = true;
    }

    try {
      this.app.showNotification(`Scanning host path '${hostPath}'...`, 'info');
      const resp = await fetch('/api/v1/convert/batch-import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: hostPath,
          target_folder: targetFolder || null,
          dry_run: false,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Batch import failed');
      }

      const res = await resp.json();
      this.app.showNotification(`Batch imported ${res.imported_count} labs (${res.failed_count} failed)`, 'success');

      if (this.app.explorer) {
        await this.app.explorer.refresh();
      }

      if (res.imported_labs && res.imported_labs.length > 0) {
        const firstLab = await (await fetch(`/api/v1/labs/${res.imported_labs[0].id}`)).json();
        this.app.loadTopology(firstLab);
      }

      this.close();
    } catch (e) {
      alert(`Host Batch Import Error: ${e.message}`);
    } finally {
      if (this.btnHostBatchImport) {
        this.btnHostBatchImport.textContent = 'Run Batch Import';
        this.btnHostBatchImport.disabled = false;
      }
    }
  }
}

window.UniversalImporter = UniversalImporter;
