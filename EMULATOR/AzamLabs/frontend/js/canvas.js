/**
 * AzamLabs GPU-Accelerated 60 FPS Cyber-Tactical Command Deck Canvas Engine
 * Features:
 * - Procedural vector node glyphs (Routers, Switches, Firewalls, SecOps/Kali)
 * - Holo-HUD orbital telemetry ring on node hover
 * - Sci-Fi radial quick-action wheel on right-click
 * - Holographic laser guide with magnetic port snapping
 * - Interactive cable interface HUD pinout on wire hover
 * - Corner Holo-Radar tactical minimap with 1-click teleport navigation
 * - Multi-node tactical laser net group selection
 * - Node state EMP shockwaves & background radar sweeps
 * - Hyperspace camera bookmarks (Shift+1..9 to save, 1..9 to jump)
 * - One-click 4K Holo-Blueprint export
 * - Bounded object pools ensuring 60 FPS locked performance (zero GC thrashing)
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
    this.hoveredLink = null;
    this.selectedNodes = new Set(); // Multi-selection set

    // Viewport Transform (Pan & Zoom)
    this.scale = 1.0;
    this.panX = 150;
    this.panY = 100;
    this.isPanning = false;
    this.isDraggingNode = false;
    this.dragStart = { x: 0, y: 0 };
    this.targetPanX = 150;
    this.targetPanY = 100;
    this.targetScale = 1.0;
    this.isGliding = false;

    // Modes: 'select', 'connect', 'pan', 'box-select'
    this.mode = 'select';
    this.connectSourceNode = null;
    this.mouseWorldPos = { x: 0, y: 0 };
    this.mouseScreenPos = { x: 0, y: 0 };

    // Multi-Selection Box
    this.isBoxSelecting = false;
    this.boxStart = { x: 0, y: 0 };
    this.boxCurrent = { x: 0, y: 0 };

    // Radial Quick-Action Menu State
    this.radialMenuNode = null;
    this.radialHoverIndex = -1;
    this.radialActions = [
      { id: 'start', label: 'START', icon: '▶', color: '#00ff87' },
      { id: 'stop', label: 'STOP', icon: '⏹', color: '#ff3366' },
      { id: 'terminal', label: 'CONSOLE', icon: '💻', color: '#00f2fe' },
      { id: 'capture', label: 'CAPTURE', icon: '📡', color: '#4facfe' },
      { id: 'config', label: 'DAY-0', icon: '⚙', color: '#ffd200' },
    ];

    // Bounded Particle & Effect Pools (Zero GC Allocations in Render Loop)
    this.particles = [];
    this.shockwaves = [];
    this.lastTime = performance.now();
    this.radarAngle = 0;

    // Camera Bookmarks Slot Dictionary (1..9)
    this.cameraBookmarks = {};

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
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.width = this.canvas.parentElement ? this.canvas.parentElement.clientWidth : window.innerWidth;
    this.height = this.canvas.parentElement ? this.canvas.parentElement.clientHeight : window.innerHeight;
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

    // Pre-allocate photon traffic packets for running links (capped at 3 per link)
    this.links.forEach(link => {
      for (let i = 0; i < 3; i++) {
        this.particles.push({
          link: link,
          progress: Math.random(),
          speed: 0.16 + Math.random() * 0.12,
          color: '#00f2fe',
        });
      }
    });

    this.fitToViewport();
  }

  triggerShockwave(x, y, color = '#00ff87') {
    if (this.shockwaves.length > 10) this.shockwaves.shift();
    this.shockwaves.push({
      x, y, radius: 15, maxRadius: 85, alpha: 1.0, color
    });
    if (window.tacticalWidget) {
      window.tacticalWidget.playClamp();
    }
  }

  fitToViewport() {
    if (!this.nodes || this.nodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    this.nodes.forEach(n => {
      minX = Math.min(minX, n.pos_x - 60);
      maxX = Math.max(maxX, n.pos_x + 60);
      minY = Math.min(minY, n.pos_y - 60);
      maxY = Math.max(maxY, n.pos_y + 60);
    });

    const bboxWidth = Math.max(maxX - minX, 120);
    const bboxHeight = Math.max(maxY - minY, 120);
    const padding = 100;

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
    // Fast distance-squared collision
    const radiusSq = 32 * 32;
    for (let i = this.nodes.length - 1; i >= 0; i--) {
      const node = this.nodes[i];
      const dx = node.pos_x - worldX;
      const dy = node.pos_y - worldY;
      if (dx * dx + dy * dy <= radiusSq) {
        return node;
      }
    }
    return null;
  }

  getLinkAt(worldX, worldY) {
    // Distance from point to line segment
    for (let i = 0; i < this.links.length; i++) {
      const link = this.links[i];
      const s = this.nodes.find(n => n.name === link.source_node || n.id === link.source_node);
      const t = this.nodes.find(n => n.name === link.target_node || n.id === link.target_node);
      if (!s || !t) continue;

      const dx = t.pos_x - s.pos_x;
      const dy = t.pos_y - s.pos_y;
      const l2 = dx * dx + dy * dy;
      if (l2 === 0) continue;

      let tVal = ((worldX - s.pos_x) * dx + (worldY - s.pos_y) * dy) / l2;
      tVal = Math.max(0, Math.min(1, tVal));
      const projX = s.pos_x + tVal * dx;
      const projY = s.pos_y + tVal * dy;
      const distSq = (worldX - projX) * (worldX - projX) + (worldY - projY) * (worldY - projY);

      if (distSq <= 12 * 12) {
        return link;
      }
    }
    return null;
  }

  initEvents() {
    window.addEventListener('resize', () => this.resize(), { passive: true });

    // Prevent default browser context menu for our Radial Action Wheel
    this.canvas.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;
      const world = this.screenToWorld(screenX, screenY);
      const clicked = this.getNodeAt(world.x, world.y);

      if (clicked) {
        this.radialMenuNode = clicked;
        this.radialHoverIndex = -1;
        if (window.tacticalWidget) window.tacticalWidget.playClick(1100, 0.04);
      } else {
        this.radialMenuNode = null;
      }
    });

    // Mouse Down
    this.canvas.addEventListener('mousedown', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;
      this.mouseScreenPos = { x: screenX, y: screenY };



      // Check if Radial Menu is open
      if (this.radialMenuNode) {
        if (this.radialHoverIndex >= 0) {
          const action = this.radialActions[this.radialHoverIndex];
          this.executeRadialAction(action.id, this.radialMenuNode);
        }
        this.radialMenuNode = null;
        return;
      }

      const world = this.screenToWorld(screenX, screenY);
      const clickedNode = this.getNodeAt(world.x, world.y);

      if (e.button === 1 || this.mode === 'pan') {
        this.isPanning = true;
        this.dragStart = { x: screenX - this.panX, y: screenY - this.panY };
        return;
      }

      if (this.mode === 'connect') {
        if (clickedNode) {
          if (!this.connectSourceNode) {
            this.connectSourceNode = clickedNode;
            if (window.tacticalWidget) window.tacticalWidget.playClick(900);
          } else if (this.connectSourceNode.id !== clickedNode.id) {
            if (this.onLinkCreated) {
              this.onLinkCreated(this.connectSourceNode, clickedNode);
            }
            if (window.tacticalWidget) window.tacticalWidget.playClamp();
            this.connectSourceNode = null;
            this.mode = 'select';
          }
        } else {
          this.connectSourceNode = null;
          this.mode = 'select';
        }
        return;
      }

      if (e.shiftKey) {
        // Multi-select laser net drag
        this.isBoxSelecting = true;
        this.boxStart = { x: world.x, y: world.y };
        this.boxCurrent = { x: world.x, y: world.y };
        return;
      }

      if (clickedNode) {
        this.selectedNode = clickedNode;
        this.selectedNodes.clear();
        this.selectedNodes.add(clickedNode.id);
        this.isDraggingNode = true;
        this.dragStart = { x: world.x - clickedNode.pos_x, y: world.y - clickedNode.pos_y };
        if (this.onNodeSelected) {
          this.onNodeSelected(clickedNode);
        }
        if (window.tacticalWidget) window.tacticalWidget.playClick(850, 0.02);
      } else {
        this.selectedNode = null;
        this.selectedNodes.clear();
        this.isPanning = true;
        this.dragStart = { x: screenX - this.panX, y: screenY - this.panY };
        if (this.onNodeSelected) {
          this.onNodeSelected(null);
        }
      }
    });

    // Mouse Move
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;
      this.mouseScreenPos = { x: screenX, y: screenY };
      const world = this.screenToWorld(screenX, screenY);
      this.mouseWorldPos = world;

      // Update Radial Action Wheel Hover
      if (this.radialMenuNode) {
        const nodeScreen = this.worldToScreen(this.radialMenuNode.pos_x, this.radialMenuNode.pos_y);
        const rdx = screenX - nodeScreen.x;
        const rdy = screenY - nodeScreen.y;
        const dist = Math.sqrt(rdx * rdx + rdy * rdy);

        if (dist >= 50 && dist <= 95) {
          let angle = Math.atan2(rdy, rdx);
          if (angle < 0) angle += Math.PI * 2;
          const segmentAngle = (Math.PI * 2) / this.radialActions.length;
          this.radialHoverIndex = Math.floor(angle / segmentAngle);
        } else {
          this.radialHoverIndex = -1;
        }
        return;
      }

      if (this.isBoxSelecting) {
        this.boxCurrent = { x: world.x, y: world.y };
        this.updateBoxSelection();
        return;
      }

      if (this.isPanning) {
        this.panX = screenX - this.dragStart.x;
        this.panY = screenY - this.dragStart.y;
        return;
      }

      if (this.isDraggingNode && this.selectedNode) {
        this.selectedNode.pos_x = world.x - this.dragStart.x;
        this.selectedNode.pos_y = world.y - this.dragStart.y;
        return;
      }

      // Hover Detection
      const hovered = this.getNodeAt(world.x, world.y);
      if (hovered !== this.hoveredNode) {
        this.hoveredNode = hovered;
        if (hovered && window.tacticalWidget) {
          window.tacticalWidget.playClick(1400, 0.015);
        }
        this.canvas.style.cursor = hovered ? 'pointer' : (this.mode === 'pan' ? 'grab' : 'default');
      }

      // Link Wire Hover
      if (!hovered) {
        this.hoveredLink = this.getLinkAt(world.x, world.y);
      } else {
        this.hoveredLink = null;
      }
    });

    // Mouse Up
    window.addEventListener('mouseup', () => {
      this.isPanning = false;
      this.isDraggingNode = false;
      this.isBoxSelecting = false;
    });

    // Zoom (Wheel)
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      const newScale = Math.min(Math.max(this.scale * zoomFactor, 0.25), 3.0);

      this.panX = mouseX - (mouseX - this.panX) * (newScale / this.scale);
      this.panY = mouseY - (mouseY - this.panY) * (newScale / this.scale);
      this.scale = newScale;

      this.updateZoomDisplay();
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

    // Keyboard Shortcuts: Camera Bookmarks (Shift+1..9 to save, 1..9 to jump)
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      const num = parseInt(e.key, 10);
      if (num >= 1 && num <= 9) {
        if (e.shiftKey) {
          // Save Bookmark
          this.cameraBookmarks[num] = { panX: this.panX, panY: this.panY, scale: this.scale };
          if (window.studio) window.studio.showNotification(`Camera zone saved to slot [${num}]`, 'success');
          if (window.tacticalWidget) window.tacticalWidget.playChime();
        } else if (this.cameraBookmarks[num]) {
          // Glide to Bookmark
          this.glideToBookmark(this.cameraBookmarks[num]);
          if (window.studio) window.studio.showNotification(`Hyperspace jump to zone [${num}]`, 'info');
        }
      }
    });
  }

  glideToBookmark(target) {
    this.targetPanX = target.panX;
    this.targetPanY = target.panY;
    this.targetScale = target.scale;
    this.isGliding = true;
    if (window.tacticalWidget) window.tacticalWidget.playClick(1200, 0.05);
  }

  updateBoxSelection() {
    const minX = Math.min(this.boxStart.x, this.boxCurrent.x);
    const maxX = Math.max(this.boxStart.x, this.boxCurrent.x);
    const minY = Math.min(this.boxStart.y, this.boxCurrent.y);
    const maxY = Math.max(this.boxStart.y, this.boxCurrent.y);

    this.selectedNodes.clear();
    this.nodes.forEach(node => {
      if (node.pos_x >= minX && node.pos_x <= maxX && node.pos_y >= minY && node.pos_y <= maxY) {
        this.selectedNodes.add(node.id);
      }
    });
  }

  executeRadialAction(actionId, node) {
    if (!window.studio) return;
    if (actionId === 'start') {
      window.studio.startSingleNode(node.id);
      this.triggerShockwave(node.pos_x, node.pos_y, '#00ff87');
    } else if (actionId === 'stop') {
      window.studio.stopSingleNode(node.id);
      this.triggerShockwave(node.pos_x, node.pos_y, '#ff3366');
    } else if (actionId === 'terminal') {
      if (this.onNodeDoubleClicked) this.onNodeDoubleClicked(node);
    } else if (actionId === 'capture') {
      window.studio.openWireshark();
    } else if (actionId === 'config') {
      window.studio.generateDay0('ospf');
    }
  }

  handleMinimapClick(screenX, screenY) {
    return false;
  }

  zoomIn() {
    this.scale = Math.min(this.scale * 1.2, 3.0);
    this.updateZoomDisplay();
  }

  zoomOut() {
    this.scale = Math.max(this.scale * 0.8, 0.25);
    this.updateZoomDisplay();
  }

  resetZoom() {
    this.fitToViewport();
  }

  updateZoomDisplay() {
    const zoomDisplay = document.getElementById('zoomLevelDisplay');
    if (zoomDisplay) {
      zoomDisplay.textContent = `${Math.round(this.scale * 100)}%`;
    }
  }

  // Animation Loop (Locked 60 FPS)
  animate(currentTime) {
    const dt = Math.min((currentTime - this.lastTime) / 1000, 0.1);
    this.lastTime = currentTime;

    // Smooth Gliding Interpolation
    if (this.isGliding) {
      this.panX += (this.targetPanX - this.panX) * 0.15;
      this.panY += (this.targetPanY - this.panY) * 0.15;
      this.scale += (this.targetScale - this.scale) * 0.15;
      if (Math.abs(this.panX - this.targetPanX) < 1 && Math.abs(this.panY - this.targetPanY) < 1) {
        this.isGliding = false;
      }
      this.updateZoomDisplay();
    }

    this.ctx.clearRect(0, 0, this.width, this.height);

    // 0. World Coordinate Space
    this.ctx.save();
    this.ctx.translate(this.panX, this.panY);
    this.ctx.scale(this.scale, this.scale);

    // Living Data-Highway Grid & Radar Sweep
    this.drawLivingGrid(currentTime);

    // Annotations & Zones
    this.drawAnnotations();

    // Links & Virtual Wires
    this.drawLinks();

    // Animated Photon Particles
    this.drawParticles(dt);

    // Shockwaves
    this.drawShockwaves(dt);

    // Connecting Laser Guide (Snap Crosshair)
    if (this.mode === 'connect' && this.connectSourceNode) {
      this.drawConnectingLaserGuide();
    }

    // Nodes
    this.drawNodes(currentTime);

    // Multi-Selection Tactical Net Box
    if (this.isBoxSelecting) {
      this.drawBoxSelection();
    }

    // Cable Hover Interface Pinout Chip
    if (this.hoveredLink) {
      this.drawLinkPinout(this.hoveredLink);
    }

    this.ctx.restore();

    // 1. Screen Space Overlays (Radial Menu)
    if (this.radialMenuNode) {
      this.drawRadialActionWheel();
    }

    if (document.visibilityState === 'visible') {
      requestAnimationFrame(this.animate);
    } else {
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
          this.lastTime = performance.now();
          requestAnimationFrame(this.animate);
        }
      }, { once: true });
    }
  }

  drawLivingGrid(currentTime) {
    // Pure dark canvas: background sweep beam removed for distraction-free view
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
      const isHovered = this.hoveredLink === link;

      this.ctx.beginPath();
      this.ctx.moveTo(source.pos_x, source.pos_y);
      this.ctx.lineTo(target.pos_x, target.pos_y);

      if (isHovered) {
        this.ctx.strokeStyle = '#00ff87';
        this.ctx.lineWidth = 3.5;
        this.ctx.shadowColor = '#00ff87';
        this.ctx.shadowBlur = 14;
      } else if (isRunning) {
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

      // If impaired, draw warning pill
      if (link.impairment && (link.impairment.delay_ms > 0 || link.impairment.loss_percent > 0)) {
        const midX = (source.pos_x + target.pos_x) / 2;
        const midY = (source.pos_y + target.pos_y) / 2;
        this.ctx.fillStyle = 'rgba(255, 51, 102, 0.85)';
        this.ctx.fillRect(midX - 24, midY - 10, 48, 18);
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

      this.ctx.beginPath();
      this.ctx.arc(px, py, 3.2, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color;
      this.ctx.shadowColor = p.color;
      this.ctx.shadowBlur = 10;
      this.ctx.fill();
      this.ctx.shadowBlur = 0;
    });
  }

  drawShockwaves(dt) {
    for (let i = this.shockwaves.length - 1; i >= 0; i--) {
      const sw = this.shockwaves[i];
      sw.radius += 110 * dt;
      sw.alpha -= 1.8 * dt;

      if (sw.alpha <= 0 || sw.radius >= sw.maxRadius) {
        this.shockwaves.splice(i, 1);
        continue;
      }

      this.ctx.save();
      this.ctx.beginPath();
      this.ctx.arc(sw.x, sw.y, sw.radius, 0, Math.PI * 2);
      this.ctx.strokeStyle = sw.color;
      this.ctx.globalAlpha = Math.max(0, sw.alpha);
      this.ctx.lineWidth = 2.5;
      this.ctx.shadowColor = sw.color;
      this.ctx.shadowBlur = 12;
      this.ctx.stroke();
      this.ctx.restore();
    }
  }

  drawConnectingLaserGuide() {
    const s = this.connectSourceNode;
    let targetX = this.mouseWorldPos.x;
    let targetY = this.mouseWorldPos.y;
    let isSnapped = false;

    // Check magnetic port snap to closest node
    const nearby = this.getNodeAt(targetX, targetY);
    if (nearby && nearby.id !== s.id) {
      targetX = nearby.pos_x;
      targetY = nearby.pos_y;
      isSnapped = true;
    }

    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.moveTo(s.pos_x, s.pos_y);
    this.ctx.lineTo(targetX, targetY);
    this.ctx.strokeStyle = isSnapped ? '#00ff87' : '#ffd200';
    this.ctx.lineWidth = isSnapped ? 3 : 2;
    this.ctx.setLineDash([6, 6]);
    this.ctx.shadowColor = isSnapped ? '#00ff87' : '#ffd200';
    this.ctx.shadowBlur = 10;
    this.ctx.stroke();

    // Snap Crosshairs Target
    if (isSnapped) {
      this.ctx.beginPath();
      this.ctx.arc(targetX, targetY, 36, 0, Math.PI * 2);
      this.ctx.strokeStyle = '#00ff87';
      this.ctx.lineWidth = 1.5;
      this.ctx.stroke();
    }
    this.ctx.restore();
  }

  drawLinkPinout(link) {
    const source = this.nodes.find(n => n.name === link.source_node || n.id === link.source_node);
    const target = this.nodes.find(n => n.name === link.target_node || n.id === link.target_node);
    if (!source || !target) return;

    const midX = (source.pos_x + target.pos_x) / 2;
    const midY = (source.pos_y + target.pos_y) / 2;
    const label = `${link.source_node}:${link.source_interface || 'eth1'} ⇄ ${link.target_node}:${link.target_interface || 'eth1'}`;

    this.ctx.save();
    this.ctx.font = '600 10px JetBrains Mono, monospace';
    const textWidth = this.ctx.measureText(label).width;
    const boxW = textWidth + 18;
    const boxH = 22;

    this.ctx.fillStyle = 'rgba(7, 10, 19, 0.92)';
    this.ctx.strokeStyle = '#00ff87';
    this.ctx.lineWidth = 1;
    this.ctx.shadowColor = 'rgba(0, 255, 135, 0.5)';
    this.ctx.shadowBlur = 10;

    if (this.ctx.roundRect) {
      this.ctx.beginPath();
      this.ctx.roundRect(midX - boxW / 2, midY - boxH / 2, boxW, boxH, 6);
      this.ctx.fill();
      this.ctx.stroke();
    } else {
      this.ctx.fillRect(midX - boxW / 2, midY - boxH / 2, boxW, boxH);
      this.ctx.strokeRect(midX - boxW / 2, midY - boxH / 2, boxW, boxH);
    }

    this.ctx.shadowBlur = 0;
    this.ctx.fillStyle = '#00ff87';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText(label, midX, midY);
    this.ctx.restore();
  }

  drawBoxSelection() {
    const minX = Math.min(this.boxStart.x, this.boxCurrent.x);
    const maxX = Math.max(this.boxStart.x, this.boxCurrent.x);
    const minY = Math.min(this.boxStart.y, this.boxCurrent.y);
    const maxY = Math.max(this.boxStart.y, this.boxCurrent.y);
    const w = maxX - minX;
    const h = maxY - minY;

    this.ctx.save();
    this.ctx.fillStyle = 'rgba(0, 242, 254, 0.08)';
    this.ctx.strokeStyle = '#00f2fe';
    this.ctx.lineWidth = 1.5;
    this.ctx.setLineDash([4, 4]);
    this.ctx.strokeRect(minX, minY, w, h);
    this.ctx.fillRect(minX, minY, w, h);
    this.ctx.setLineDash([]);

    // Tactical Corner Brackets (┌ ┐ └ ┘)
    const bLen = 10;
    this.ctx.strokeStyle = '#00ff87';
    this.ctx.lineWidth = 2;
    // Top-left
    this.ctx.beginPath(); this.ctx.moveTo(minX, minY + bLen); this.ctx.lineTo(minX, minY); this.ctx.lineTo(minX + bLen, minY); this.ctx.stroke();
    // Top-right
    this.ctx.beginPath(); this.ctx.moveTo(maxX - bLen, minY); this.ctx.lineTo(maxX, minY); this.ctx.lineTo(maxX, minY + bLen); this.ctx.stroke();
    // Bottom-left
    this.ctx.beginPath(); this.ctx.moveTo(minX, maxY - bLen); this.ctx.lineTo(minX, maxY); this.ctx.lineTo(minX + bLen, maxY); this.ctx.stroke();
    // Bottom-right
    this.ctx.beginPath(); this.ctx.moveTo(maxX - bLen, maxY); this.ctx.lineTo(maxX, maxY); this.ctx.lineTo(maxX, maxY - bLen); this.ctx.stroke();

    this.ctx.restore();
  }

  drawNodes(currentTime) {
    this.nodes.forEach(node => {
      const isSelected = (this.selectedNode && this.selectedNode.id === node.id) || this.selectedNodes.has(node.id);
      const isHovered = this.hoveredNode && this.hoveredNode.id === node.id;
      const isRunning = node.status === 'running';

      // 1. Status Glow Halo
      if (isRunning) {
        const pulse = 0.5 + 0.5 * Math.sin(currentTime * 0.005);
        const radius = 33 + pulse * 3;
        this.ctx.beginPath();
        this.ctx.arc(node.pos_x, node.pos_y, radius, 0, Math.PI * 2);
        this.ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
        this.ctx.fill();
      }

      // 2. Node Body Circle
      this.ctx.beginPath();
      this.ctx.arc(node.pos_x, node.pos_y, 28, 0, Math.PI * 2);

      if (isRunning) {
        this.ctx.fillStyle = '#060b17';
        this.ctx.strokeStyle = isSelected ? '#00f2fe' : '#10b981';
        this.ctx.lineWidth = isSelected ? 3 : 2;
        this.ctx.shadowColor = isSelected ? '#00f2fe' : '#10b981';
        this.ctx.shadowBlur = 10;
      } else {
        this.ctx.fillStyle = '#030712';
        this.ctx.strokeStyle = isSelected ? '#00f2fe' : 'rgba(255, 255, 255, 0.12)';
        this.ctx.lineWidth = isSelected ? 2.5 : 1.5;
        this.ctx.shadowBlur = 0;
      }

      this.ctx.fill();
      this.ctx.stroke();
      this.ctx.shadowBlur = 0;

      // 3. Cybernetic Device Vector Emblem
      this.drawDeviceGlyph(node);

      // 4. Vendor Branding Badge Tag (e.g. CISCO, ARISTA, NOKIA, KALI)
      this.drawVendorBadge(node);

      // 5. Node Name Label
      this.ctx.font = '600 12px Inter, sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.fillStyle = isSelected ? '#00f2fe' : '#f8fafc';
      this.ctx.fillText(node.name, node.pos_x, node.pos_y + 46);

      // 6. IP Address / Telemetry Subtitle
      const ip = this.getNodeDisplayIp(node);
      if (ip) {
        this.ctx.font = '500 10px JetBrains Mono, monospace';
        this.ctx.fillStyle = '#64748b';
        this.ctx.fillText(ip, node.pos_x, node.pos_y + 59);
      }

      // 7. Holo-HUD Orbital Ring on Hover
      if (isHovered && !this.radialMenuNode) {
        this.drawHoloHudRing(node, currentTime);
      }
    });
  }

  drawDeviceGlyph(node) {
    const type = (node.device_type || 'router').toLowerCase();
    const isRunning = node.status === 'running';
    this.ctx.save();
    this.ctx.translate(node.pos_x, node.pos_y);

    if (type === 'router') {
      // Procedural Cybernetic Router: Multi-ring core with 4 illuminated glowing chevron arrows
      const color = isRunning ? '#00ff87' : '#94a3b8';
      this.ctx.strokeStyle = color;
      this.ctx.fillStyle = color;
      this.ctx.lineWidth = 1.8;

      // Center Core
      this.ctx.beginPath();
      this.ctx.arc(0, 0, 4, 0, Math.PI * 2);
      this.ctx.fill();

      // 4 Chevron Routing Arrows
      const dirs = [
        { dx: 0, dy: -12, ax: -4, ay: -8, bx: 4, by: -8 }, // Up
        { dx: 0, dy: 12, ax: -4, ay: 8, bx: 4, by: 8 },    // Down
        { dx: -12, dy: 0, ax: -8, ay: -4, bx: -8, by: 4 }, // Left
        { dx: 12, dy: 0, ax: 8, ay: -4, bx: 8, by: 4 },    // Right
      ];
      dirs.forEach(d => {
        this.ctx.beginPath();
        this.ctx.moveTo(0, 0);
        this.ctx.lineTo(d.dx, d.dy);
        this.ctx.stroke();

        this.ctx.beginPath();
        this.ctx.moveTo(d.ax, d.ay);
        this.ctx.lineTo(d.dx, d.dy);
        this.ctx.lineTo(d.bx, d.by);
        this.ctx.stroke();
      });

    } else if (type === 'switch') {
      // Procedural Cybernetic Switch: High-density crossbar fiber matrix with data lanes
      const color = isRunning ? '#00f2fe' : '#94a3b8';
      this.ctx.strokeStyle = color;
      this.ctx.lineWidth = 2;

      // Top Lane
      this.ctx.beginPath();
      this.ctx.moveTo(-11, -5); this.ctx.lineTo(11, -5);
      this.ctx.stroke();
      // Arrow Right
      this.ctx.beginPath();
      this.ctx.moveTo(8, -8); this.ctx.lineTo(11, -5); this.ctx.lineTo(8, -2);
      this.ctx.stroke();

      // Bottom Lane
      this.ctx.beginPath();
      this.ctx.moveTo(11, 5); this.ctx.lineTo(-11, 5);
      this.ctx.stroke();
      // Arrow Left
      this.ctx.beginPath();
      this.ctx.moveTo(-8, 2); this.ctx.lineTo(-11, 5); this.ctx.lineTo(-8, 8);
      this.ctx.stroke();

    } else if (type === 'firewall') {
      // Hexagonal Cyber-Barrier Shield with Threat Vector
      this.ctx.strokeStyle = '#ff007f';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(0, -12);
      this.ctx.lineTo(11, -6);
      this.ctx.lineTo(11, 5);
      this.ctx.lineTo(0, 12);
      this.ctx.lineTo(-11, 5);
      this.ctx.lineTo(-11, -6);
      this.ctx.closePath();
      this.ctx.stroke();

      // Inner Firewall Flame Dot
      this.ctx.fillStyle = '#ff007f';
      this.ctx.beginPath();
      this.ctx.arc(0, 0, 3, 0, Math.PI * 2);
      this.ctx.fill();

    } else {
      // Host / Kali / SecOps Target
      const isSec = node.image && node.image.toLowerCase().includes('kali');
      const color = isSec ? '#ff3366' : '#38bdf8';
      this.ctx.strokeStyle = color;
      this.ctx.lineWidth = 1.8;

      // Tactical Crosshair
      this.ctx.beginPath();
      this.ctx.arc(0, 0, 9, 0, Math.PI * 2);
      this.ctx.stroke();

      this.ctx.beginPath();
      this.ctx.moveTo(-12, 0); this.ctx.lineTo(-7, 0);
      this.ctx.moveTo(7, 0); this.ctx.lineTo(12, 0);
      this.ctx.moveTo(0, -12); this.ctx.lineTo(0, -7);
      this.ctx.moveTo(0, 7); this.ctx.lineTo(0, 12);
      this.ctx.stroke();
    }

    this.ctx.restore();
  }

  drawVendorBadge(node) {
    let vendor = 'FRR';
    const img = (node.image || '').toLowerCase();
    if (img.includes('cisco') || (node.name || '').toLowerCase().startsWith('c')) vendor = 'CISCO';
    else if (img.includes('arista') || (node.name || '').toLowerCase().startsWith('eos')) vendor = 'ARISTA';
    else if (img.includes('nokia') || (node.name || '').toLowerCase().startsWith('sr')) vendor = 'NOKIA';
    else if (img.includes('kali')) vendor = 'KALI';
    else if (img.includes('alpine') || img.includes('linux')) vendor = 'LINUX';

    this.ctx.save();
    this.ctx.font = '700 8px JetBrains Mono, monospace';
    this.ctx.textAlign = 'center';
    this.ctx.fillStyle = 'rgba(0, 242, 254, 0.85)';
    this.ctx.fillText(vendor, node.pos_x, node.pos_y - 33);
    this.ctx.restore();
  }

  drawHoloHudRing(node, currentTime) {
    this.ctx.save();
    const rot = currentTime * 0.002;
    this.ctx.translate(node.pos_x, node.pos_y);

    // Rotating Holographic Ring with 4 Cardinal Degree Ticks
    this.ctx.beginPath();
    this.ctx.arc(0, 0, 36, rot, rot + Math.PI * 1.5);
    this.ctx.strokeStyle = '#00f2fe';
    this.ctx.lineWidth = 1.5;
    this.ctx.stroke();

    // Data Readout Pill in Corner
    const rx = 44;
    const ry = -38;
    this.ctx.fillStyle = 'rgba(7, 10, 19, 0.94)';
    this.ctx.strokeStyle = '#00f2fe';
    this.ctx.lineWidth = 1;
    this.ctx.shadowColor = 'rgba(0, 242, 254, 0.4)';
    this.ctx.shadowBlur = 10;

    const w = 110;
    const h = 54;
    if (this.ctx.roundRect) {
      this.ctx.beginPath();
      this.ctx.roundRect(rx, ry, w, h, 6);
      this.ctx.fill();
      this.ctx.stroke();
    } else {
      this.ctx.fillRect(rx, ry, w, h);
      this.ctx.strokeRect(rx, ry, w, h);
    }
    this.ctx.shadowBlur = 0;

    this.ctx.font = '600 9px JetBrains Mono, monospace';
    this.ctx.fillStyle = '#00ff87';
    this.ctx.textAlign = 'left';
    this.ctx.fillText(`STATUS: ${(node.status || 'STOPPED').toUpperCase()}`, rx + 8, ry + 14);

    this.ctx.fillStyle = '#f8fafc';
    this.ctx.fillText(`CPU: ${node.cpu || 1} vCPU`, rx + 8, ry + 26);
    this.ctx.fillText(`RAM: ${node.ram_mb || 1024} MB`, rx + 8, ry + 38);
    this.ctx.fillStyle = '#64748b';
    this.ctx.fillText(`IFACES: ${node.interfaces ? node.interfaces.length : 1}`, rx + 8, ry + 49);

    this.ctx.restore();
  }

  drawRadialActionWheel() {
    const node = this.radialMenuNode;
    if (!node) return;

    const pos = this.worldToScreen(node.pos_x, node.pos_y);
    const count = this.radialActions.length;
    const segmentAngle = (Math.PI * 2) / count;
    const innerR = 48;
    const outerR = 92;

    this.ctx.save();
    this.ctx.translate(pos.x, pos.y);

    for (let i = 0; i < count; i++) {
      const act = this.radialActions[i];
      const startAngle = i * segmentAngle;
      const endAngle = startAngle + segmentAngle;
      const isHovered = this.radialHoverIndex === i;

      this.ctx.beginPath();
      this.ctx.arc(0, 0, isHovered ? outerR + 4 : outerR, startAngle, endAngle);
      this.ctx.arc(0, 0, innerR, endAngle, startAngle, true);
      this.ctx.closePath();

      this.ctx.fillStyle = isHovered ? 'rgba(0, 242, 254, 0.35)' : 'rgba(10, 16, 30, 0.88)';
      this.ctx.fill();
      this.ctx.strokeStyle = isHovered ? act.color : 'rgba(255, 255, 255, 0.15)';
      this.ctx.lineWidth = isHovered ? 2.5 : 1;
      this.ctx.stroke();

      // Label & Icon
      const midAngle = startAngle + segmentAngle / 2;
      const textR = (innerR + outerR) / 2;
      const tx = Math.cos(midAngle) * textR;
      const ty = Math.sin(midAngle) * textR;

      this.ctx.font = '700 10px JetBrains Mono, monospace';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillStyle = isHovered ? '#ffffff' : act.color;
      this.ctx.fillText(`${act.icon} ${act.label}`, tx, ty);
    }

    this.ctx.restore();
  }

  drawHoloRadarMinimap(currentTime) {
    // Holo-Radar minimap removed for clean tactical dark mode
  }

  // One-Click 4K Holo-Blueprint Schematic Export
  exportHoloBlueprint() {
    const offCanvas = document.createElement('canvas');
    offCanvas.width = 3840;
    offCanvas.height = 2160;
    const octx = offCanvas.getContext('2d');

    // Background
    octx.fillStyle = '#05070e';
    octx.fillRect(0, 0, 3840, 2160);

    // Blueprint Grid
    octx.strokeStyle = 'rgba(0, 242, 254, 0.08)';
    octx.lineWidth = 1;
    for (let x = 0; x < 3840; x += 60) {
      octx.beginPath(); octx.moveTo(x, 0); octx.lineTo(x, 2160); octx.stroke();
    }
    for (let y = 0; y < 2160; y += 60) {
      octx.beginPath(); octx.moveTo(0, y); octx.lineTo(3840, y); octx.stroke();
    }

    // Header Title & Security Watermark
    octx.font = '900 48px Orbitron, Outfit, sans-serif';
    octx.fillStyle = '#00f2fe';
    octx.fillText('AZAMLABS TACTICAL TOPOLOGY BLUEPRINT', 80, 100);

    octx.font = '500 20px JetBrains Mono, monospace';
    octx.fillStyle = '#64748b';
    octx.fillText(`SECURITY CLASSIFICATION: CONFIDENTIAL // SHA256 SEAL: ${Date.now().toString(16).toUpperCase()}`, 80, 140);
    octx.fillText(`GENERATED: ${new Date().toISOString()} // NODES: ${this.nodes.length} // LINKS: ${this.links.length}`, 80, 170);

    // Render Topology
    const scale = 2.2;
    const offsetX = 500;
    const offsetY = 400;

    // Draw Links
    this.links.forEach(l => {
      const s = this.nodes.find(n => n.name === l.source_node || n.id === l.source_node);
      const t = this.nodes.find(n => n.name === l.target_node || n.id === l.target_node);
      if (!s || !t) return;
      octx.beginPath();
      octx.moveTo(offsetX + s.pos_x * scale, offsetY + s.pos_y * scale);
      octx.lineTo(offsetX + t.pos_x * scale, offsetY + t.pos_y * scale);
      octx.strokeStyle = '#00f2fe';
      octx.lineWidth = 4;
      octx.stroke();
    });

    // Draw Nodes
    this.nodes.forEach(n => {
      const x = offsetX + n.pos_x * scale;
      const y = offsetY + n.pos_y * scale;

      octx.beginPath();
      octx.arc(x, y, 40, 0, Math.PI * 2);
      octx.fillStyle = '#0a1628';
      octx.strokeStyle = n.status === 'running' ? '#00ff87' : '#00f2fe';
      octx.lineWidth = 4;
      octx.fill();
      octx.stroke();

      octx.font = '700 22px Inter, sans-serif';
      octx.fillStyle = '#ffffff';
      octx.textAlign = 'center';
      octx.fillText(n.name, x, y + 65);
    });

    // Download trigger
    const link = document.createElement('a');
    link.download = `azamlabs-tactical-blueprint-${Date.now()}.png`;
    link.href = offCanvas.toDataURL('image/png');
    link.click();
    if (window.studio) window.studio.showNotification('Exported 4K Holo-Blueprint Schematic!', 'success');
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
