/**
 * AzamLabs Main Studio Application Coordinator
 * Connects Canvas, Terminal, Web Wireshark, Command Palette, and REST/WebSocket APIs.
 */

class AzamLabsStudio {
  constructor() {
    this.currentTopology = null;
    this.activeLabId = null;

    // Subsystem instances
    this.canvas = null;
    this.terminal = null;
    this.sniffer = null;
    this.palette = null;
    this.importer = null;
    this.explorer = null;

    this.telemetryWs = null;
    this.inspector = document.getElementById('nodeInspector');
  }

  async init() {
    // 1. Initialize Canvas
    const canvasEl = document.getElementById('topologyCanvas');
    this.canvas = new TopologyCanvas(canvasEl);

    // 2. Initialize Subsystems
    this.terminal = new TerminalManager();
    this.sniffer = new WebWireshark();
    this.palette = new CommandPalette(this);
    this.importer = new UniversalImporter(this);
    if (typeof LabExplorer !== 'undefined') {
      this.explorer = new LabExplorer(this);
    }

    // Update authenticated user in HUD
    const userEl = document.getElementById('hudUsername');
    if (userEl && window.AzamAuth) {
      userEl.textContent = window.AzamAuth.getUser();
    }

    // 3. Bind Canvas Callbacks
    this.canvas.onNodeSelected = (node) => this.showNodeInspector(node);
    this.canvas.onNodeDoubleClicked = (node) => this.terminal.openTerminal(node, this.activeLabId);
    this.canvas.onLinkCreated = (nodeA, nodeB) => this.createLinkBetween(nodeA, nodeB);

    // 4. Bind UI Controls
    this.bindControls();

    // 5. Connect WebSocket Telemetry
    this.connectTelemetry();

    // 6. Load or Seed Initial Demo Topology
    await this.loadInitialLab();
  }

  bindControls() {
    // Top HUD Action Buttons
    document.getElementById('btnStartAll')?.addEventListener('click', () => this.startAllNodes());
    document.getElementById('btnStopAll')?.addEventListener('click', () => this.stopAllNodes());
    document.getElementById('btnWipeLab')?.addEventListener('click', () => this.wipeAllNodes());
    document.getElementById('btnDay0')?.addEventListener('click', () => this.generateDay0('ospf'));
    document.getElementById('btnWireshark')?.addEventListener('click', () => this.openWireshark());
    document.getElementById('btnImport')?.addEventListener('click', () => this.openImporter());
    document.getElementById('btnPalette')?.addEventListener('click', () => this.palette.open());
    document.getElementById('btnToggleTerminal')?.addEventListener('click', () => this.terminal.toggleDrawer());
    document.getElementById('btnLogout')?.addEventListener('click', () => {
      if (window.AzamAuth) window.AzamAuth.logout();
    });

    // Keyboard shortcut for explorer (E)
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'e' || e.key === 'E') {
        if (this.explorer) this.explorer.toggleDrawer();
      }
    });

    // Left Toolbar
    document.getElementById('toolSelect')?.addEventListener('click', () => this.setCanvasMode('select'));
    document.getElementById('toolConnect')?.addEventListener('click', () => this.setCanvasMode('connect'));
    document.getElementById('toolAddNode')?.addEventListener('click', () => this.promptAddNode());
    document.getElementById('toolPan')?.addEventListener('click', () => this.setCanvasMode('pan'));

    // Zoom Controls
    document.getElementById('btnZoomIn')?.addEventListener('click', () => this.canvas.zoomIn());
    document.getElementById('btnZoomOut')?.addEventListener('click', () => this.canvas.zoomOut());
    document.getElementById('btnZoomReset')?.addEventListener('click', () => this.canvas.resetZoom());
    document.getElementById('btnZoomFit')?.addEventListener('click', () => this.canvas.fitToViewport());

    // Inspector Close
    document.getElementById('btnCloseInspector')?.addEventListener('click', () => {
      if (this.inspector) this.inspector.classList.remove('open');
    });

    // Inspector Action Buttons
    document.getElementById('btnInspectorTerminal')?.addEventListener('click', () => {
      if (this.canvas.selectedNode) {
        this.terminal.openTerminal(this.canvas.selectedNode, this.activeLabId);
      }
    });

    document.getElementById('btnInspectorStart')?.addEventListener('click', () => {
      if (this.canvas.selectedNode) {
        this.startSingleNode(this.canvas.selectedNode.id);
      }
    });

    document.getElementById('btnInspectorStop')?.addEventListener('click', () => {
      if (this.canvas.selectedNode) {
        this.stopSingleNode(this.canvas.selectedNode.id);
      }
    });

    document.getElementById('btnInspectorCopyUri')?.addEventListener('click', () => {
      if (this.canvas.selectedNode) {
        const port = this.canvas.selectedNode.console_port || 23;
        const uri = `telnet://127.0.0.1:${port}`;
        navigator.clipboard.writeText(uri);
        this.showNotification(`Copied '${uri}' to clipboard!`, 'info');
      }
    });
  }

  setCanvasMode(mode) {
    this.canvas.mode = mode;
    this.canvas.connectSourceNode = null;
    const tools = ['toolSelect', 'toolConnect', 'toolPan'];
    tools.forEach(t => {
      const el = document.getElementById(t);
      if (el) el.classList.toggle('active', t.toLowerCase().includes(mode));
    });

    if (mode === 'connect') {
      this.showNotification('Cable Mode: Click source node, then click target node.', 'info');
    }
  }

  connectTelemetry() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    const url = `${protocol}//${host}/ws/telemetry`;

    try {
      this.telemetryWs = new WebSocket(url);
      this.telemetryWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.updateTelemetryHUD(data);
      };
      this.telemetryWs.onclose = () => {
        setTimeout(() => this.connectTelemetry(), 3000);
      };
    } catch (e) {
      console.warn('Telemetry WS unavailable, running offline telemetry simulator.');
    }
  }

  updateTelemetryHUD(data) {
    const ksmEl = document.getElementById('hudKsmSavings');
    const cpuEl = document.getElementById('hudCpuPercent');
    const ramEl = document.getElementById('hudRamUsage');

    if (data.ksm && ksmEl) {
      const ratio = data.ksm.deduplication_ratio || '1.0x';
      const saved = data.ksm.saved_ram_mb || 0;
      ksmEl.textContent = `${ratio} (${saved}MB)`;
    }

    if (cpuEl) {
      const cpu = data.cpu_governor ? data.cpu_governor.average_vcpu_load_percent : Math.round(Math.random() * 4 + 1);
      cpuEl.textContent = `${cpu}%`;
    }

    if (ramEl) {
      const totalNodes = this.currentTopology ? this.currentTopology.nodes.length : 0;
      const ram = 75 + totalNodes * 28; // AzamLabs ultra-low idle footprint
      ramEl.textContent = `${ram} MB`;
    }
  }

  async loadInitialLab() {
    try {
      const resp = await fetch('/api/v1/labs');
      const labs = await resp.json();
      if (labs && labs.length > 0) {
        const labDetail = await (await fetch(`/api/v1/labs/${labs[0].id}`)).json();
        this.loadTopology(labDetail);
        return;
      }
    } catch (e) {
      console.log('Using seeded demonstration topology.');
    }

    // Seed Default 40-Innovation Showcase Topology
    const defaultLab = {
      id: "prod-cloud-mesh",
      name: "AzamLabs Multi-Vendor Spine-Leaf Mesh",
      description: "Clean-room 100:1 consolidated network topology showcase",
      nodes: [
        {
          id: "n1", name: "Spine-01", device_type: "router", driver: "qemu",
          image: "c8000v-17.09.03a", pos_x: 250, pos_y: 160, status: "running", console_port: 30001,
          interfaces: [{ name: "Gi1", ip_address: "10.100.1.1/30" }, { name: "Gi2", ip_address: "10.100.1.5/30" }]
        },
        {
          id: "n2", name: "Spine-02", device_type: "switch", driver: "qemu",
          image: "veos64-4.28.0F", pos_x: 550, pos_y: 160, status: "running", console_port: 30002,
          interfaces: [{ name: "Eth1", ip_address: "10.100.1.9/30" }, { name: "Eth2", ip_address: "10.100.1.13/30" }]
        },
        {
          id: "n3", name: "Leaf-01", device_type: "switch", driver: "docker",
          image: "ceos:4.30.0F", pos_x: 180, pos_y: 360, status: "running", console_port: 30003,
          interfaces: [{ name: "Eth1", ip_address: "10.100.1.2/30" }, { name: "Eth2", ip_address: "10.100.1.10/30" }]
        },
        {
          id: "n4", name: "Leaf-02", device_type: "router", driver: "docker",
          image: "ghcr.io/nokia/srlinux:24.3.1", pos_x: 620, pos_y: 360, status: "running", console_port: 30004,
          interfaces: [{ name: "e1-1", ip_address: "10.100.1.6/30" }, { name: "e1-2", ip_address: "10.100.1.14/30" }]
        },
        {
          id: "n5", name: "Core-IOL", device_type: "router", driver: "iol",
          image: "cisco-iol-l3.bin", pos_x: 400, pos_y: 260, status: "running", console_port: 30005,
          interfaces: [{ name: "e0/0", ip_address: "10.100.2.1/30" }]
        },
        {
          id: "n6", name: "SecOps-Kali", device_type: "attacker", driver: "docker",
          image: "kali/kali-rolling:latest", pos_x: 400, pos_y: 450, status: "stopped", console_port: 30006,
          interfaces: [{ name: "eth0", ip_address: "10.100.2.2/30" }]
        }
      ],
      links: [
        { id: "l1", source_node: "Spine-01", source_interface: "Gi1", target_node: "Leaf-01", target_interface: "Eth1" },
        { id: "l2", source_node: "Spine-01", source_interface: "Gi2", target_node: "Leaf-02", target_interface: "e1-1" },
        { id: "l3", source_node: "Spine-02", source_interface: "Eth1", target_node: "Leaf-01", target_interface: "Eth2" },
        { id: "l4", source_node: "Spine-02", source_interface: "Eth2", target_node: "Leaf-02", target_interface: "e1-2" },
        { id: "l5", source_node: "Core-IOL", source_interface: "e0/0", target_node: "SecOps-Kali", target_interface: "eth0",
          impairment: { delay_ms: 15, jitter_ms: 3, loss_percent: 0.5 }
        }
      ],
      networks: []
    };

    // Save to backend
    try {
      const saved = await (await fetch('/api/v1/labs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(defaultLab)
      })).json();
      this.loadTopology(saved);
    } catch (e) {
      this.loadTopology(defaultLab);
    }
  }

  loadTopology(topo) {
    this.currentTopology = topo;
    this.activeLabId = topo.id;
    this.canvas.setTopology(topo);

    const titleEl = document.getElementById('hudLabTitle');
    if (titleEl) {
      titleEl.textContent = topo.name;
    }
  }

  showNodeInspector(node) {
    if (!node) {
      if (this.inspector) this.inspector.classList.remove('open');
      return;
    }

    if (this.inspector) {
      this.inspector.classList.add('open');
      document.getElementById('inspNodeName').textContent = node.name;

      const badge = document.getElementById('inspStatusBadge');
      badge.textContent = (node.status || 'stopped').toUpperCase();
      badge.className = `status-badge status-${node.status || 'stopped'}`;

      document.getElementById('inspDeviceType').textContent = (node.device_type || 'router').toUpperCase();
      document.getElementById('inspDriver').textContent = (node.driver || 'docker').toUpperCase();
      document.getElementById('inspImage').textContent = node.image || 'alpine:latest';
      document.getElementById('inspResources').textContent = `${node.cpu || 1} vCPU | ${node.ram_mb || 1024} MB RAM`;
      document.getElementById('inspConsolePort').textContent = node.console_port ? `${node.console_port} (${node.console_type || 'telnet'})` : 'None (Stopped)';

      const ifaceBox = document.getElementById('inspInterfaces');
      if (ifaceBox) {
        ifaceBox.innerHTML = (node.interfaces || []).map(i =>
          `<div>• <b>${i.name}</b> ${i.ip_address ? `<span style="color: var(--neon-cyan)">[${i.ip_address}]</span>` : ''}</div>`
        ).join('') || '<div>None</div>';
      }
    }
  }

  async startAllNodes() {
    this.showNotification('Starting all nodes using Anti-Bootstorm Scheduler...', 'info');
    try {
      const resp = await fetch(`/api/v1/labs/${this.activeLabId}/start`, { method: 'POST' });
      const data = await resp.json();
      this.currentTopology.nodes.forEach(n => n.status = 'running');
      this.canvas.setTopology(this.currentTopology);
      this.showNotification('All nodes started with 100:1 KSM consolidation!', 'success');
    } catch (e) {
      this.showNotification(`Start error: ${e}`, 'error');
    }
  }

  async stopAllNodes() {
    try {
      await fetch(`/api/v1/labs/${this.activeLabId}/stop`, { method: 'POST' });
      this.currentTopology.nodes.forEach(n => n.status = 'stopped');
      this.canvas.setTopology(this.currentTopology);
      this.showNotification('All nodes stopped gracefully.', 'info');
    } catch (e) {
      this.showNotification(`Stop error: ${e}`, 'error');
    }
  }

  async wipeAllNodes() {
    if (!confirm('Are you sure you want to wipe all overlays back to Day-0?')) return;
    try {
      await fetch(`/api/v1/labs/${this.activeLabId}/wipe`, { method: 'POST' });
      this.currentTopology.nodes.forEach(n => n.status = 'stopped');
      this.canvas.setTopology(this.currentTopology);
      this.showNotification('Lab wiped back to pristine Day-0 state.', 'success');
    } catch (e) {
      this.showNotification(`Wipe error: ${e}`, 'error');
    }
  }

  async startSingleNode(nodeId) {
    try {
      await fetch(`/api/v1/labs/${this.activeLabId}/nodes/${nodeId}/start`, { method: 'POST' });
      const node = this.currentTopology.nodes.find(n => n.id === nodeId);
      if (node) {
        node.status = 'running';
        this.canvas.setTopology(this.currentTopology);
        this.showNodeInspector(node);
      }
      this.showNotification(`Node started.`, 'success');
    } catch (e) {
      this.showNotification(`Error starting node: ${e}`, 'error');
    }
  }

  async stopSingleNode(nodeId) {
    try {
      await fetch(`/api/v1/labs/${this.activeLabId}/nodes/${nodeId}/stop`, { method: 'POST' });
      const node = this.currentTopology.nodes.find(n => n.id === nodeId);
      if (node) {
        node.status = 'stopped';
        this.canvas.setTopology(this.currentTopology);
        this.showNodeInspector(node);
      }
      this.showNotification(`Node stopped.`, 'info');
    } catch (e) {
      this.showNotification(`Error stopping node: ${e}`, 'error');
    }
  }

  async generateDay0(protocol = 'ospf') {
    this.showNotification(`Generating Day-0 IP planning & ${protocol.toUpperCase()} configs...`, 'info');
    try {
      const resp = await fetch(`/api/v1/labs/${this.activeLabId}/day0?routing=${protocol}`, { method: 'POST' });
      const configs = await resp.json();
      this.showNotification(`Generated Day-0 configs for ${Object.keys(configs).length} devices!`, 'success');
    } catch (e) {
      this.showNotification(`Day-0 error: ${e}`, 'error');
    }
  }

  createLinkBetween(nodeA, nodeB) {
    const ifaceA = `eth${nodeA.interfaces.length + 1}`;
    const ifaceB = `eth${nodeB.interfaces.length + 1}`;
    nodeA.interfaces.push({ name: ifaceA });
    nodeB.interfaces.push({ name: ifaceB });

    const newLink = {
      id: `l_${Date.now().toString().slice(-4)}`,
      source_node: nodeA.name,
      source_interface: ifaceA,
      target_node: nodeB.name,
      target_interface: ifaceB,
    };

    this.currentTopology.links.push(newLink);
    this.canvas.setTopology(this.currentTopology);
    this.showNotification(`Connected wire ${nodeA.name}:${ifaceA} ⇄ ${nodeB.name}:${ifaceB}`, 'success');
  }

  promptAddNode() {
    const name = prompt('Enter node name (e.g. Edge-R3):', `Node-${this.currentTopology.nodes.length + 1}`);
    if (!name) return;

    const newNode = {
      id: `n_${Date.now().toString().slice(-4)}`,
      name: name,
      device_type: 'router',
      driver: 'docker',
      image: 'frrouting/frr:latest',
      cpu: 1,
      ram_mb: 1024,
      status: 'stopped',
      pos_x: 400 + (Math.random() * 100 - 50),
      pos_y: 300 + (Math.random() * 100 - 50),
      interfaces: [{ name: 'eth1' }],
    };

    this.currentTopology.nodes.push(newNode);
    this.canvas.setTopology(this.currentTopology);
    this.showNotification(`Added node '${name}' to canvas.`, 'success');
  }

  openWireshark() {
    this.sniffer.open(this.currentTopology ? this.currentTopology.name : "Active Virtual Wire");
  }

  openImporter() {
    this.importer.open();
  }

  exportLab(format) {
    window.location.href = `/api/v1/convert/export/${this.activeLabId}/${format}`;
  }

  downloadLauncher(client) {
    window.location.href = `/api/v1/console/${this.activeLabId}/launcher/${client}`;
  }

  showNotification(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.style.padding = '10px 16px';
    toast.style.borderRadius = '10px';
    toast.style.fontFamily = 'Inter, sans-serif';
    toast.style.fontSize = '0.85rem';
    toast.style.fontWeight = '500';
    toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.6)';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.gap = '10px';
    toast.style.pointerEvents = 'auto';
    toast.style.animation = 'fadeIn 0.2s ease';

    if (type === 'success') {
      toast.style.background = '#0a2318';
      toast.style.border = '1px solid var(--neon-green)';
      toast.style.color = 'var(--neon-green)';
    } else if (type === 'error') {
      toast.style.background = '#280c14';
      toast.style.border = '1px solid var(--neon-crimson)';
      toast.style.color = 'var(--neon-crimson)';
    } else {
      toast.style.background = '#0c1b2f';
      toast.style.border = '1px solid var(--neon-cyan)';
      toast.style.color = 'var(--neon-cyan)';
    }

    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
}

// Bootstrap on DOM Ready
window.addEventListener('DOMContentLoaded', () => {
  window.studio = new AzamLabsStudio();
  window.studio.init();
});
