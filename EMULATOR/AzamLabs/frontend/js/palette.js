/**
 * AzamLabs Command Palette (Ctrl+K) Controller
 */

class CommandPalette {
  constructor(appContext) {
    this.app = appContext;
    this.modal = document.getElementById('paletteModal');
    this.input = document.getElementById('paletteInput');
    this.resultsContainer = document.getElementById('paletteResults');
    this.selectedIndex = 0;
    this.filteredActions = [];

    this.actions = [
      { id: 'start_all', title: 'Start All Nodes', badge: 'Lifecycle', action: () => this.app.startAllNodes() },
      { id: 'stop_all', title: 'Stop All Nodes', badge: 'Lifecycle', action: () => this.app.stopAllNodes() },
      { id: 'wipe_all', title: 'Wipe Lab (Day-0 Reset)', badge: 'Lifecycle', action: () => this.app.wipeAllNodes() },
      { id: 'day0_ospf', title: 'Auto Day-0 Provisioning (OSPF Area 0)', badge: 'Automation', action: () => this.app.generateDay0('ospf') },
      { id: 'day0_bgp', title: 'Auto Day-0 Provisioning (BGP Mesh)', badge: 'Automation', action: () => this.app.generateDay0('bgp') },
      { id: 'open_wireshark', title: 'Launch In-Browser Web Wireshark', badge: 'Sniffer', action: () => this.app.openWireshark() },
      { id: 'open_terminal', title: 'Toggle Web Terminal Drawer', badge: 'Terminal', action: () => this.app.terminal.toggleDrawer() },
      { id: 'import_modal', title: 'Import Lab (CLAB / CML / EVE / GNS3 / P2V)', badge: 'Universal Importer', action: () => this.app.openImporter() },
      { id: 'export_clab', title: 'Export Lab to Containerlab (.clab.yml)', badge: 'Export', action: () => this.app.exportLab('clab') },
      { id: 'export_cml', title: 'Export Lab to Cisco CML 2.x (.yaml)', badge: 'Export', action: () => this.app.exportLab('cml') },
      { id: 'export_eve', title: 'Export Lab to EVE-NG / PNETLab (.unl)', badge: 'Export', action: () => this.app.exportLab('eve') },
      { id: 'export_gns3', title: 'Export Lab to GNS3 (.gns3)', badge: 'Export', action: () => this.app.exportLab('gns3') },
      { id: 'export_azaml', title: 'Export Portable .azaml Bundle Archive', badge: 'Export', action: () => this.app.exportLab('azaml') },
      { id: 'download_wt', title: 'Download Windows Terminal (wt.exe) 1-Click Launcher', badge: 'Desktop', action: () => this.app.downloadLauncher('wt') },
      { id: 'download_crt', title: 'Download SecureCRT 1-Click Multi-Tab Launcher', badge: 'Desktop', action: () => this.app.downloadLauncher('securecrt') },
      { id: 'zoom_reset', title: 'Reset Viewport Zoom to 100%', badge: 'View', action: () => this.app.canvas.resetZoom() },
    ];

    this.initEvents();
  }

  initEvents() {
    // Global Ctrl+K / Cmd+K listener
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        this.toggle();
      } else if (e.key === 'Escape' && this.isOpen()) {
        this.close();
      }
    });

    if (this.input) {
      this.input.addEventListener('input', () => this.renderResults());
      this.input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this.selectedIndex = Math.min(this.selectedIndex + 1, this.filteredActions.length - 1);
          this.updateSelectionHighlight();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
          this.updateSelectionHighlight();
        } else if (e.key === 'Enter') {
          e.preventDefault();
          this.executeSelected();
        }
      });
    }

    // Backdrop click
    if (this.modal) {
      this.modal.addEventListener('click', (e) => {
        if (e.target === this.modal) this.close();
      });
    }
  }

  isOpen() {
    return this.modal && this.modal.classList.contains('open');
  }

  toggle() {
    if (this.isOpen()) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    if (this.modal) this.modal.classList.add('open');
    if (this.input) {
      this.input.value = '';
      this.input.focus();
    }
    this.selectedIndex = 0;
    this.renderResults();
  }

  close() {
    if (this.modal) this.modal.classList.remove('open');
  }

  renderResults() {
    if (!this.resultsContainer) return;
    const query = (this.input ? this.input.value : '').toLowerCase().trim();

    this.filteredActions = this.actions.filter(a =>
      !query || a.title.toLowerCase().includes(query) || a.badge.toLowerCase().includes(query)
    );

    this.resultsContainer.innerHTML = '';

    if (this.filteredActions.length === 0) {
      this.resultsContainer.innerHTML = `
        <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 0.9rem;">
          No matching commands found.
        </div>
      `;
      return;
    }

    if (this.selectedIndex >= this.filteredActions.length) {
      this.selectedIndex = 0;
    }

    this.filteredActions.forEach((item, idx) => {
      const el = document.createElement('div');
      el.className = `palette-item ${idx === this.selectedIndex ? 'selected' : ''}`;
      el.innerHTML = `
        <div class="palette-item-left">
          <span>${item.title}</span>
        </div>
        <span class="palette-badge">${item.badge}</span>
      `;

      el.addEventListener('click', () => {
        this.selectedIndex = idx;
        this.executeSelected();
      });

      this.resultsContainer.appendChild(el);
    });
  }

  updateSelectionHighlight() {
    const items = this.resultsContainer.querySelectorAll('.palette-item');
    items.forEach((el, idx) => {
      el.classList.toggle('selected', idx === this.selectedIndex);
      if (idx === this.selectedIndex) {
        el.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  executeSelected() {
    if (this.filteredActions[this.selectedIndex]) {
      const selected = this.filteredActions[this.selectedIndex];
      this.close();
      selected.action();
    }
  }
}

window.CommandPalette = CommandPalette;
