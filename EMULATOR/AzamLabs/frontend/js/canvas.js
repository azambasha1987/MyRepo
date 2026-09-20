/**
 * AzamLabs GPU-Accelerated 60 FPS Topology Canvas Engine
 * Features cyber-tactical node rendering, status halos, smooth pan/zoom,
 * and animated glowing photon traffic particles traveling along virtual wires.
 */

class TopologyCanvas {
  constructor(canvasElement) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext('2d');

    // Topology Data
    this.nodes = [];
    this.links = [];
    this.annotations = [];
    this.selectedNode = null;
    this.hoveredNode = null;

    // Viewport Transform (Pan & Zoom)
    this.scale = 1.0;
    this.panX = 150;
    this.panY = 100;
    this.isPanning = false;
    this.isDraggingNode = false;
    this.dragStart = { x: 0, y: 0 };

    // Modes: 'select', 'connect', 'pan'
    this.mode = 'select';
    this.connectSourceNode = null;

    // Photon Particle Animation State
    this.particles = [];
    this.lastTime = performance.now();

    // Callbacks
    this.onNodeSelected = null;
    this.onNodeDoubleClicked = null;
    this.onLinkCreated = null;

    this.initEvents();
    this.resize();
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    this.width = this.canvas.parentElement.clientWidth;
    this.height = this.canvas.parentElement.clientHeight;
    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.canvas.style.width = `${this.width}px`;
    this.canvas.style.height = `${this.height}px`;
    this.ctx.scale(dpr, dpr);
  }

  setTopology(topology) {
    this.nodes = topology.nodes || [];
    this.links = topology.links || [];
    this.annotations = topology.annotations || [];
    this.particles = [];

    // Initialize photon traffic particles for running links
    this.links.forEach(link => {
      for (let i = 0; i < 3; i++) {
        this.particles.push({
          link: link,
          progress: Math.random(),
          speed: 0.15 + Math.random() * 0.1,
          color: '#00f2fe',
        });
      }
    });

    // Auto-center and fit topology comfortably in canvas viewport
    this.fitToViewport();
  }

  fitToViewport() {
    if (!this.nodes || this.nodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    this.nodes.forEach(n => {
      minX = Math.min(minX, n.pos_x - 50);
      maxX = Math.max(maxX, n.pos_x + 50);
      minY = Math.min(minY, n.pos_y - 50);
      maxY = Math.max(maxY, n.pos_y + 50);
    });

    if (this.annotations && this.annotations.length > 0) {
      this.annotations.forEach(a => {
        minX = Math.min(minX, a.pos_x);
        maxX = Math.max(maxX, a.pos_x + (a.width || 200));
        minY = Math.min(minY, a.pos_y);
        maxY = Math.max(maxY, a.pos_y + (a.height || 150));
      });
    }

    const bboxWidth = Math.max(maxX - minX, 100);
    const bboxHeight = Math.max(maxY - minY, 100);
    const padding = 80;

    const availableWidth = Math.max(this.width - padding * 2, 200);
    const availableHeight = Math.max(this.height - padding * 2, 200);

    const scaleX = availableWidth / bboxWidth;
    const scaleY = availableHeight / bboxHeight;
    this.scale = Math.min(Math.max(Math.min(scaleX, scaleY), 0.25), 1.5);

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    this.panX = this.width / 2 - centerX * this.scale;
    this.panY = this.height / 2 - centerY * this.scale;
    this.updateZoomDisplay();
  }

  screenToWorld(screenX, screenY) {
    return {
      x: (screenX - this.panX) / this.scale,
      y: (screenY - this.panY) / this.scale,
    };
  }

  worldToScreen(worldX, worldY) {
    return {
      x: worldX * this.scale + this.panX,
      y: worldY * this.scale + this.panY,
    };
  }

  getNodeAt(worldX, worldY) {
    for (let i = this.nodes.length - 1; i >= 0; i--) {
      const node = this.nodes[i];
      const dx = node.pos_x - worldX;
      const dy = node.pos_y - worldY;
      if (Math.sqrt(dx * dx + dy * dy) <= 32) {
        return node;
      }
    }
    return null;
  }

  initEvents() {
    window.addEventListener('resize', () => this.resize());

    // Mouse Down
    this.canvas.addEventListener('mousedown', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const world = this.screenToWorld(mouseX, mouseY);
      const clickedNode = this.getNodeAt(world.x, world.y);

      if (e.button === 1 || e.shiftKey || this.mode === 'pan') {
        // Middle click or Pan mode
        this.isPanning = true;
        this.dragStart = { x: mouseX - this.panX, y: mouseY - this.panY };
        return;
      }

      if (this.mode === 'connect') {
        if (clickedNode) {
          if (!this.connectSourceNode) {
            this.connectSourceNode = clickedNode;
          } else if (this.connectSourceNode.id !== clickedNode.id) {
            if (this.onLinkCreated) {
              this.onLinkCreated(this.connectSourceNode, clickedNode);
            }
            this.connectSourceNode = null;
            this.mode = 'select';
          }
        }
        return;
      }

      if (clickedNode) {
        this.selectedNode = clickedNode;
        this.isDraggingNode = true;
        this.dragStart = { x: world.x - clickedNode.pos_x, y: world.y - clickedNode.pos_y };
        if (this.onNodeSelected) {
          this.onNodeSelected(clickedNode);
        }
      } else {
        this.selectedNode = null;
        this.isPanning = true;
        this.dragStart = { x: mouseX - this.panX, y: mouseY - this.panY };
        if (this.onNodeSelected) {
          this.onNodeSelected(null);
        }
      }
    });

    // Mouse Move
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (this.isPanning) {
        this.panX = mouseX - this.dragStart.x;
        this.panY = mouseY - this.dragStart.y;
        return;
      }

      const world = this.screenToWorld(mouseX, mouseY);

      if (this.isDraggingNode && this.selectedNode) {
        this.selectedNode.pos_x = world.x - this.dragStart.x;
        this.selectedNode.pos_y = world.y - this.dragStart.y;
        return;
      }

      const hovered = this.getNodeAt(world.x, world.y);
      if (hovered !== this.hoveredNode) {
        this.hoveredNode = hovered;
        this.canvas.style.cursor = hovered ? 'pointer' : (this.mode === 'pan' ? 'grab' : 'default');
      }
    });

    // Mouse Up
    window.addEventListener('mouseup', () => {
      this.isPanning = false;
      this.isDraggingNode = false;
    });

    // Zoom (Wheel)
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      const newScale = Math.min(Math.max(this.scale * zoomFactor, 0.3), 3.0);

      this.panX = mouseX - (mouseX - this.panX) * (newScale / this.scale);
      this.panY = mouseY - (mouseY - this.panY) * (newScale / this.scale);
      this.scale = newScale;

      const zoomDisplay = document.getElementById('zoomLevelDisplay');
      if (zoomDisplay) {
        zoomDisplay.textContent = `${Math.round(this.scale * 100)}%`;
      }
    }, { passive: false });

    // Double Click (Open Terminal)
    this.canvas.addEventListener('dblclick', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const world = this.screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
      const clicked = this.getNodeAt(world.x, world.y);
      if (clicked && this.onNodeDoubleClicked) {
        this.onNodeDoubleClicked(clicked);
      }
    });
  }

  zoomIn() {
    this.scale = Math.min(this.scale * 1.2, 3.0);
    this.updateZoomDisplay();
  }

  zoomOut() {
    this.scale = Math.max(this.scale * 0.8, 0.3);
    this.updateZoomDisplay();
  }

  resetZoom() {
    this.scale = 1.0;
    this.panX = 150;
    this.panY = 100;
    this.updateZoomDisplay();
  }

  updateZoomDisplay() {
    const zoomDisplay = document.getElementById('zoomLevelDisplay');
    if (zoomDisplay) {
      zoomDisplay.textContent = `${Math.round(this.scale * 100)}%`;
    }
  }

  // Animation Loop (60 FPS)
  animate(currentTime) {
    const dt = (currentTime - this.lastTime) / 1000;
    this.lastTime = currentTime;

    this.ctx.clearRect(0, 0, this.width, this.height);
    this.ctx.save();
    this.ctx.translate(this.panX, this.panY);
    this.ctx.scale(this.scale, this.scale);

    // 0. Draw Visual Architectural Annotations & Zones
    this.drawAnnotations();

    // 1. Draw Links & Virtual Wires
    this.drawLinks();

    // 2. Draw Animated Photon Particles
    this.drawParticles(dt);

    // 3. Draw Connecting Cable Line if in Connect Mode
    if (this.mode === 'connect' && this.connectSourceNode) {
      this.drawConnectingLine();
    }

    // 4. Draw Nodes
    this.drawNodes(currentTime);

    this.ctx.restore();
    requestAnimationFrame(this.animate);
  }

  drawAnnotations() {
    if (!this.annotations || this.annotations.length === 0) return;

    this.annotations.forEach(ann => {
      const x = ann.pos_x || 0;
      const y = ann.pos_y || 0;
      const w = ann.width || 220;
      const h = ann.height || 140;
      const color = ann.color || '#00f2fe';
      const bg = ann.background_color || 'rgba(0, 242, 254, 0.06)';

      this.ctx.save();
      this.ctx.fillStyle = bg;
      this.ctx.strokeStyle = color;
      this.ctx.lineWidth = 1.5;
      this.ctx.setLineDash([4, 4]);

      this.ctx.beginPath();
      if (this.ctx.roundRect) {
        this.ctx.roundRect(x, y, w, h, 8);
      } else {
        this.ctx.rect(x, y, w, h);
      }
      this.ctx.fill();
      this.ctx.stroke();
      this.ctx.setLineDash([]);

      if (ann.label) {
        this.ctx.fillStyle = color;
        this.ctx.font = '600 12px Inter, sans-serif';
        this.ctx.textAlign = 'left';
        this.ctx.fillText(ann.label, x + 12, y + 22);
      }
      this.ctx.restore();
    });
  }

  drawLinks() {
    this.links.forEach(link => {
      const source = this.nodes.find(n => n.name === link.source_node || n.id === link.source_node);
      const target = this.nodes.find(n => n.name === link.target_node || n.id === link.target_node);
      if (!source || !target) return;

      const isRunning = source.status === 'running' && target.status === 'running';

      this.ctx.beginPath();
      this.ctx.moveTo(source.pos_x, source.pos_y);
      this.ctx.lineTo(target.pos_x, target.pos_y);

      if (isRunning) {
        this.ctx.strokeStyle = 'rgba(0, 242, 254, 0.45)';
        this.ctx.lineWidth = 2.5;
        this.ctx.shadowColor = 'rgba(0, 242, 254, 0.6)';
        this.ctx.shadowBlur = 8;
      } else {
        this.ctx.strokeStyle = 'rgba(100, 116, 139, 0.3)';
        this.ctx.lineWidth = 1.8;
        this.ctx.shadowBlur = 0;
      }

      this.ctx.stroke();
      this.ctx.shadowBlur = 0;

      // Draw link endpoints label
      const midX = (source.pos_x + target.pos_x) / 2;
      const midY = (source.pos_y + target.pos_y) / 2;

      // If impaired, draw warning pill
      if (link.impairment && (link.impairment.delay_ms > 0 || link.impairment.loss_percent > 0)) {
        this.ctx.fillStyle = 'rgba(255, 51, 102, 0.8)';
        this.ctx.fillRect(midX - 22, midY - 10, 44, 18);
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '10px JetBrains Mono';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(`${link.impairment.delay_ms}ms`, midX, midY + 3);
      }
    });
  }

  drawParticles(dt) {
    this.particles.forEach(p => {
      const source = this.nodes.find(n => n.name === p.link.source_node || n.id === p.link.source_node);
      const target = this.nodes.find(n => n.name === p.link.target_node || n.id === p.link.target_node);
      if (!source || !target || source.status !== 'running' || target.status !== 'running') return;

      p.progress += p.speed * dt;
      if (p.progress > 1.0) p.progress = 0;

      const px = source.pos_x + (target.pos_x - source.pos_x) * p.progress;
      const py = source.pos_y + (target.pos_y - source.pos_y) * p.progress;

      // Glow packet
      this.ctx.beginPath();
      this.ctx.arc(px, py, 3, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color;
      this.ctx.shadowColor = p.color;
      this.ctx.shadowBlur = 10;
      this.ctx.fill();
      this.ctx.shadowBlur = 0;
    });
  }

  drawConnectingLine() {
    this.ctx.beginPath();
    this.ctx.moveTo(this.connectSourceNode.pos_x, this.connectSourceNode.pos_y);
    // Draw dashed yellow line to mouse
    this.ctx.setLineDash([6, 6]);
    this.ctx.strokeStyle = '#ffd200';
    this.ctx.lineWidth = 2;
    // Mouse world pos approximate
    this.ctx.stroke();
    this.ctx.setLineDash([]);
  }

  drawNodes(currentTime) {
    this.nodes.forEach(node => {
      const isSelected = this.selectedNode && this.selectedNode.id === node.id;
      const isHovered = this.hoveredNode && this.hoveredNode.id === node.id;
      const isRunning = node.status === 'running';

      // 1. Status Glow Halo
      if (isRunning) {
        const pulse = 0.5 + 0.5 * Math.sin(currentTime * 0.004);
        const radius = 32 + pulse * 4;
        this.ctx.beginPath();
        this.ctx.arc(node.pos_x, node.pos_y, radius, 0, Math.PI * 2);
        this.ctx.fillStyle = 'rgba(0, 255, 135, 0.08)';
        this.ctx.fill();
      }

      // 2. Node Body Circle
      this.ctx.beginPath();
      this.ctx.arc(node.pos_x, node.pos_y, 28, 0, Math.PI * 2);

      if (isRunning) {
        this.ctx.fillStyle = '#0a1628';
        this.ctx.strokeStyle = isSelected ? '#00f2fe' : '#00ff87';
        this.ctx.lineWidth = isSelected ? 3 : 2;
        this.ctx.shadowColor = isSelected ? '#00f2fe' : '#00ff87';
        this.ctx.shadowBlur = 12;
      } else {
        this.ctx.fillStyle = '#090e1a';
        this.ctx.strokeStyle = isSelected ? '#00f2fe' : 'rgba(255, 255, 255, 0.15)';
        this.ctx.lineWidth = isSelected ? 2.5 : 1.5;
        this.ctx.shadowBlur = 0;
      }

      this.ctx.fill();
      this.ctx.stroke();
      this.ctx.shadowBlur = 0;

      // 3. Render Device Glyph (Router / Switch / Firewall / Host)
      this.drawDeviceGlyph(node);

      // 4. Node Name Label
      this.ctx.font = '600 12px Inter, sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.fillStyle = isSelected ? '#00f2fe' : '#f8fafc';
      this.ctx.fillText(node.name, node.pos_x, node.pos_y + 46);

      // 5. IP Address Badge
      const ip = this.getNodeDisplayIp(node);
      if (ip) {
        this.ctx.font = '500 10px JetBrains Mono, monospace';
        this.ctx.fillStyle = '#64748b';
        this.ctx.fillText(ip, node.pos_x, node.pos_y + 60);
      }
    });
  }

  drawDeviceGlyph(node) {
    const type = (node.device_type || 'router').toLowerCase();
    this.ctx.save();
    this.ctx.translate(node.pos_x, node.pos_y);

    if (type === 'router') {
      // 4 cross routing arrows
      this.ctx.strokeStyle = node.status === 'running' ? '#00ff87' : '#94a3b8';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(-10, 0); this.ctx.lineTo(10, 0);
      this.ctx.moveTo(0, -10); this.ctx.lineTo(0, 10);
      this.ctx.stroke();
    } else if (type === 'switch') {
      // 2 horizontal parallel cross-switch arrows
      this.ctx.strokeStyle = node.status === 'running' ? '#00f2fe' : '#94a3b8';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(-10, -5); this.ctx.lineTo(10, -5);
      this.ctx.moveTo(10, 5); this.ctx.lineTo(-10, 5);
      this.ctx.stroke();
    } else if (type === 'firewall') {
      // Shield
      this.ctx.strokeStyle = '#ff007f';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(-9, -8); this.ctx.lineTo(9, -8);
      this.ctx.lineTo(9, 2); this.ctx.lineTo(0, 10); this.ctx.lineTo(-9, 2);
      this.ctx.closePath();
      this.ctx.stroke();
    } else {
      // Host / Terminal PC
      this.ctx.strokeStyle = '#38bdf8';
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(-9, -7, 18, 14);
    }
    this.ctx.restore();
  }

  getNodeDisplayIp(node) {
    for (const iface of node.interfaces || []) {
      if (iface.ip_address) {
        return iface.ip_address.split('/')[0];
      }
    }
    return null;
  }
}

window.TopologyCanvas = TopologyCanvas;
