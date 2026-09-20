/**
 * AzamLabs Left-Side Folder-Wise Lab Explorer
 * Inspired by Azam-Pnet / Enterprise Emulators.
 * Provides hierarchical folder tree, deep search, cascading deletion, folder export, and lab switching.
 */

class LabExplorer {
  constructor(studioContext) {
    this.studio = studioContext;
    this.drawer = document.getElementById('labExplorerDrawer');
    this.treeContainer = document.getElementById('explorerTree');
    this.searchInput = document.getElementById('explorerSearch');
    this.currentSelectedFolder = '/';
    this.folderData = [];
    this.isOpen = false;

    this.initEvents();
  }

  initEvents() {
    // Left Toolbar Toggle Button
    const toggleBtn = document.getElementById('toolToggleExplorer');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => this.toggleDrawer());
    }

    // Close Button in Explorer Header
    const closeBtn = document.getElementById('btnCloseExplorer');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.toggleDrawer(false));
    }

    // Create New Folder Button
    const btnNewFolder = document.getElementById('btnNewFolder');
    if (btnNewFolder) {
      btnNewFolder.addEventListener('click', () => this.promptCreateFolder());
    }

    // Search Filter
    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => this.filterTree(e.target.value));
    }

    // Quick Import Button in Explorer
    const btnQuickImport = document.getElementById('btnExplorerImport');
    if (btnQuickImport) {
      btnQuickImport.addEventListener('click', () => {
        this.studio.openImporter();
      });
    }
  }

  toggleDrawer(forceState = null) {
    this.isOpen = forceState !== null ? forceState : !this.isOpen;
    if (this.drawer) {
      this.drawer.classList.toggle('open', this.isOpen);
    }
    const toggleBtn = document.getElementById('toolToggleExplorer');
    if (toggleBtn) {
      toggleBtn.classList.toggle('active', this.isOpen);
    }
    if (this.isOpen) {
      this.refresh();
    }
  }

  async refresh() {
    try {
      const resp = await fetch('/api/v1/folders');
      if (resp.ok) {
        this.folderData = await resp.json();
        this.renderTree(this.folderData, this.searchInput ? this.searchInput.value : '');
      }
    } catch (e) {
      console.warn('Error loading folders:', e);
    }
  }

  renderTree(folders, filterQuery = '') {
    if (!this.treeContainer) return;
    this.treeContainer.innerHTML = '';

    const query = (filterQuery || '').toLowerCase().trim();

    folders.forEach(folder => {
      const filteredLabs = folder.labs.filter(l =>
        !query ||
        l.name.toLowerCase().includes(query) ||
        (l.description || '').toLowerCase().includes(query) ||
        (l.author || '').toLowerCase().includes(query) ||
        (folder.name || '').toLowerCase().includes(query)
      );

      // If filtering and no matches in this folder, skip unless folder name matches
      if (query && filteredLabs.length === 0 && !folder.name.toLowerCase().includes(query)) {
        return;
      }

      const folderEl = document.createElement('div');
      folderEl.className = 'folder-node';
      folderEl.dataset.folderPath = folder.path;

      // Folder Header Bar
      const headerEl = document.createElement('div');
      headerEl.className = `folder-header ${this.currentSelectedFolder === folder.path ? 'selected' : ''}`;
      headerEl.innerHTML = `
        <div class="folder-header-left">
          <span class="folder-chevron">▾</span>
          <svg class="folder-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--neon-cyan)" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          <span class="folder-name">${folder.name}</span>
        </div>
        <div class="folder-header-right">
          <span class="folder-badge">${folder.labs.length}</span>
          ${folder.id !== 'root' ? `
            <button class="folder-exp-btn" title="Export Folder as ZIP" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:12px; margin-right:4px;">📦</button>
            <button class="folder-del-btn" title="Delete Folder (Cascading Delete)">&times;</button>
          ` : ''}
        </div>
      `;

      // Click to select / toggle folder
      headerEl.querySelector('.folder-header-left').addEventListener('click', () => {
        this.currentSelectedFolder = folder.path;
        itemsEl.classList.toggle('collapsed');
        headerEl.querySelector('.folder-chevron').textContent = itemsEl.classList.contains('collapsed') ? '▸' : '▾';
      });

      // Export folder ZIP action
      const expBtn = headerEl.querySelector('.folder-exp-btn');
      if (expBtn) {
        expBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          window.location.href = `/api/v1/folders/${folder.id}/export`;
        });
      }

      // Delete folder action (Cascading Deletion)
      const delBtn = headerEl.querySelector('.folder-del-btn');
      if (delBtn) {
        delBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const count = folder.labs.length;
          const msg = count > 0
            ? `Delete folder '${folder.name}' and ALL ${count} labs inside it permanently?\n\n• Click OK for Cascading Delete (Deletes Folder + all ${count} nested labs).\n• Click Cancel to abort.`
            : `Delete empty folder '${folder.name}'?`;

          if (confirm(msg)) {
            await fetch(`/api/v1/folders/${folder.id}?delete_contents=true`, { method: 'DELETE' });
            this.studio.showNotification(`Deleted folder '${folder.name}' and all contained labs.`, 'info');
            this.refresh();
          }
        });
      }

      // Folder Labs List Container
      const itemsEl = document.createElement('div');
      itemsEl.className = 'folder-items';

      if (filteredLabs.length === 0) {
        const emptyEl = document.createElement('div');
        emptyEl.className = 'empty-folder-hint';
        emptyEl.textContent = 'No labs in this folder';
        itemsEl.appendChild(emptyEl);
      } else {
        filteredLabs.forEach(lab => {
          const labEl = document.createElement('div');
          const isCurrentActive = this.studio.activeLabId === lab.id;
          labEl.className = `lab-item-row ${isCurrentActive ? 'active-lab' : ''}`;

          const isRunning = (lab.running_nodes || 0) > 0;
          const statusDot = isRunning ? '<span class="status-dot dot-running" title="Running"></span>' : '<span class="status-dot dot-stopped" title="Stopped"></span>';

          labEl.title = `${lab.name}\nNodes: ${lab.total_nodes || 0} (${lab.running_nodes || 0} running)\nFolder: ${lab.folder_path || '/'}\nAuthor: ${lab.author || 'AzamLabs'}`;

          labEl.innerHTML = `
            <div class="lab-row-left">
              ${statusDot}
              <span class="lab-row-name">${lab.name}</span>
            </div>
            <div class="lab-row-right">
              <span class="lab-nodes-badge">${lab.total_nodes || 0}N</span>
              <button class="lab-row-action-btn" title="Lab Actions">⋮</button>
            </div>
          `;

          // Click on lab to load it into Studio Canvas
          labEl.querySelector('.lab-row-left').addEventListener('click', async () => {
            await this.loadLabIntoStudio(lab.id);
          });

          // Lab Context Menu Action
          labEl.querySelector('.lab-row-action-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.showLabContextMenu(lab, e.clientX, e.clientY);
          });

          itemsEl.appendChild(labEl);
        });
      }

      folderEl.appendChild(headerEl);
      folderEl.appendChild(itemsEl);
      this.treeContainer.appendChild(folderEl);
    });
  }

  filterTree(query) {
    this.renderTree(this.folderData, query);
  }

  async loadLabIntoStudio(labId) {
    try {
      const resp = await fetch(`/api/v1/labs/${labId}`);
      if (resp.ok) {
        const labData = await resp.json();
        this.studio.loadTopology(labData);
        this.studio.showNotification(`Loaded lab '${labData.name}'`, 'success');
        this.refresh(); // updates active highlight
      }
    } catch (e) {
      this.studio.showNotification(`Failed to load lab: ${e}`, 'error');
    }
  }

  async promptCreateFolder() {
    const name = prompt('Enter new folder name (e.g. Cisco CCIE, Data Center EVPN):');
    if (!name || !name.trim()) return;

    try {
      const resp = await fetch('/api/v1/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), parent_id: 'root' })
      });
      if (resp.ok) {
        this.studio.showNotification(`Folder '${name}' created!`, 'success');
        this.refresh();
      }
    } catch (e) {
      this.studio.showNotification(`Error creating folder: ${e}`, 'error');
    }
  }

  showLabContextMenu(lab, x, y) {
    const existing = document.getElementById('labContextMenu');
    if (existing) existing.remove();

    const menu = document.createElement('div');
    menu.id = 'labContextMenu';
    menu.className = 'lab-context-menu';
    menu.style.left = `${Math.min(x, window.innerWidth - 220)}px`;
    menu.style.top = `${Math.min(y, window.innerHeight - 240)}px`;

    menu.innerHTML = `
      <div class="ctx-item" data-action="start">▶ Start All Nodes</div>
      <div class="ctx-item" data-action="stop">⏹ Stop All Nodes</div>
      <div class="ctx-item" data-action="wipe">🧹 Wipe to Day-0</div>
      <div class="ctx-divider"></div>
      <div class="ctx-item" data-action="clone">📑 Duplicate / Clone Lab</div>
      <div class="ctx-item" data-action="move">📁 Move to Folder...</div>
      <div class="ctx-item" data-action="export">📦 Export Lab...</div>
      <div class="ctx-divider"></div>
      <div class="ctx-item ctx-danger" data-action="delete">🗑 Delete Lab</div>
    `;

    document.body.appendChild(menu);

    const closeHandler = () => {
      menu.remove();
      document.removeEventListener('click', closeHandler);
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 50);

    menu.addEventListener('click', async (e) => {
      const action = e.target.dataset.action;
      if (!action) return;

      if (action === 'start') {
        await fetch(`/api/v1/labs/${lab.id}/start`, { method: 'POST' });
        this.studio.showNotification(`Started lab '${lab.name}'`, 'success');
        this.refresh();
      } else if (action === 'stop') {
        await fetch(`/api/v1/labs/${lab.id}/stop`, { method: 'POST' });
        this.studio.showNotification(`Stopped lab '${lab.name}'`, 'info');
        this.refresh();
      } else if (action === 'wipe') {
        if (confirm(`Wipe lab '${lab.name}' back to Day-0?`)) {
          await fetch(`/api/v1/labs/${lab.id}/wipe`, { method: 'POST' });
          this.studio.showNotification(`Wiped lab '${lab.name}'`, 'success');
        }
      } else if (action === 'clone') {
        const cloneResp = await fetch(`/api/v1/labs/${lab.id}/clone`, { method: 'POST' });
        if (cloneResp.ok) {
          const cloned = await cloneResp.json();
          this.studio.showNotification(`Cloned lab '${cloned.name}'`, 'success');
          this.refresh();
        } else {
          this.studio.showNotification(`Failed to clone lab`, 'error');
        }
      } else if (action === 'move') {
        const target = prompt('Enter destination folder path (e.g. /Enterprise Networks):', lab.folder_path || '/');
        if (target && target !== lab.folder_path) {
          await fetch(`/api/v1/labs/${lab.id}/move`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder_path: target })
          });
          this.studio.showNotification(`Moved lab to '${target}'`, 'success');
          this.refresh();
        }
      } else if (action === 'export') {
        this.studio.exportLab('azaml');
      } else if (action === 'delete') {
        if (confirm(`Permanently delete lab '${lab.name}'?`)) {
          await fetch(`/api/v1/labs/${lab.id}`, { method: 'DELETE' });
          this.studio.showNotification(`Deleted lab '${lab.name}'`, 'info');
          this.refresh();
        }
      }
    });
  }
}

window.LabExplorer = LabExplorer;
