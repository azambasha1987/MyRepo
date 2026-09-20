/**
 * AzamLabs Tactical Core — Holographic Draggable Companion Widget
 * Features: High-performance pointer physics with magnetic edge snapping,
 * Web Audio API synthesizer, 60 FPS real-time telemetry, and 4-palette theme switcher.
 */

class AzamTacticalWidget {
  constructor() {
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;
    this.posX = window.innerWidth - 80;
    this.posY = 110;
    this.isExpanded = false;
    this.audioEnabled = localStorage.getItem('azam_audio_enabled') !== 'false';
    this.voiceEnabled = localStorage.getItem('azam_voice_enabled') === 'true';
    this.currentTheme = localStorage.getItem('azam_theme') || 'cyan';

    // FPS Telemetry
    this.fps = 60;
    this.frameTime = 16.6;
    this.frameCount = 0;
    this.lastFpsUpdate = performance.now();
    this.lastFrameTime = performance.now();

    // Audio Context
    this.audioCtx = null;

    this.init();
  }

  init() {
    this.applyTheme(this.currentTheme);
    this.restorePosition();
    this.mountWidget();
    this.bindEvents();
    this.startFpsLoop();

    // Expose globally for interaction by other modules
    window.tacticalWidget = this;
  }

  getAudioContext() {
    if (!this.audioCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.audioCtx = new AudioCtx();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  // Synthesized Web Audio API Sound Effects (Zero Audio Files)
  playClick(freq = 880, duration = 0.03) {
    if (!this.audioEnabled) return;
    try {
      const ctx = this.getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (_) {}
  }

  playClamp() {
    if (!this.audioEnabled) return;
    try {
      const ctx = this.getAudioContext();
      if (!ctx) return;
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();
      osc1.type = 'triangle';
      osc2.type = 'sine';
      osc1.frequency.setValueAtTime(220, ctx.currentTime);
      osc1.frequency.exponentialRampToValueAtTime(110, ctx.currentTime + 0.08);
      osc2.frequency.setValueAtTime(440, ctx.currentTime);
      osc2.frequency.exponentialRampToValueAtTime(220, ctx.currentTime + 0.08);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.09);
      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);
      osc1.start();
      osc2.start();
      osc1.stop(ctx.currentTime + 0.09);
      osc2.stop(ctx.currentTime + 0.09);
    } catch (_) {}
  }

  playChime() {
    if (!this.audioEnabled) return;
    try {
      const ctx = this.getAudioContext();
      if (!ctx) return;
      [523.25, 659.25, 783.99, 1046.5].forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.05);
        gain.gain.setValueAtTime(0.06, ctx.currentTime + idx * 0.05);
        gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + idx * 0.05 + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + idx * 0.05);
        osc.stop(ctx.currentTime + idx * 0.05 + 0.25);
      });
    } catch (_) {}
  }

  playEmp() {
    if (!this.audioEnabled) return;
    try {
      const ctx = this.getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(600, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.22);
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.24);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.24);
    } catch (_) {}
  }

  speak(text) {
    if (!this.voiceEnabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.1;
      utterance.pitch = 1.0;
      utterance.volume = 0.5;
      window.speechSynthesis.speak(utterance);
    } catch (_) {}
  }

  mountWidget() {
    if (document.getElementById('tacticalCoreWidget')) return;

    const container = document.createElement('div');
    container.id = 'tacticalCoreWidget';
    container.style.transform = `translate3d(${this.posX}px, ${this.posY}px, 0)`;

    container.innerHTML = `
      <div class="tactical-orb-button" id="tacticalOrbBtn" title="AzamLabs Tactical Core (Drag or Click)">
        <div class="orb-ring-outer"></div>
        <div class="orb-ring-inner"></div>
        <div class="orb-reactor-core">
          <img src="/assets/logo-icon.png" alt="AzamLabs Core">
        </div>
        <div class="orb-beacon"></div>
      </div>

      <div class="tactical-dock-panel dock-hidden" id="tacticalDockPanel">
        <div class="dock-header">
          <div class="dock-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
            Tactical Telemetry
          </div>
          <button class="dock-close-btn" id="dockCloseBtn" title="Collapse Deck">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <div class="dock-stats-grid">
          <div class="dock-stat-box">
            <span class="dock-stat-label">Framerate</span>
            <span class="dock-stat-val fps-good" id="dockFpsVal">60 <span style="font-size:0.65rem; color:#64748b;">FPS</span></span>
          </div>
          <div class="dock-stat-box">
            <span class="dock-stat-label">Latency</span>
            <span class="dock-stat-val" id="dockMsVal">16.6 <span style="font-size:0.65rem; color:#64748b;">MS</span></span>
          </div>
        </div>

        <div class="dock-toggles-row">
          <button class="dock-toggle-btn ${this.audioEnabled ? 'active' : ''}" id="btnToggleAudio" title="Toggle Synthesized Audio Feedback">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
            <span>Audio FX</span>
          </button>
          <button class="dock-toggle-btn ${this.voiceEnabled ? 'active' : ''}" id="btnToggleVoice" title="Toggle AI Voice Telemetry">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
            <span>Voice</span>
          </button>
        </div>

        <div class="dock-theme-section">
          <span class="dock-theme-label">Cyber Theme Palette</span>
          <div class="dock-theme-chips">
            <div class="theme-chip theme-chip-cyan ${this.currentTheme === 'cyan' ? 'active' : ''}" data-set-theme="cyan" title="Cyber Cyan"></div>
            <div class="theme-chip theme-chip-violet ${this.currentTheme === 'violet' ? 'active' : ''}" data-set-theme="violet" title="Quantum Violet"></div>
            <div class="theme-chip theme-chip-amber ${this.currentTheme === 'amber' ? 'active' : ''}" data-set-theme="amber" title="Tactical Amber"></div>
            <div class="theme-chip theme-chip-emerald ${this.currentTheme === 'emerald' ? 'active' : ''}" data-set-theme="emerald" title="Matrix Emerald"></div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(container);
  }

  bindEvents() {
    const orb = document.getElementById('tacticalOrbBtn');
    const container = document.getElementById('tacticalCoreWidget');
    const dock = document.getElementById('tacticalDockPanel');
    const closeBtn = document.getElementById('dockCloseBtn');
    const toggleAudio = document.getElementById('btnToggleAudio');
    const toggleVoice = document.getElementById('btnToggleVoice');
    const themeChips = document.querySelectorAll('.theme-chip');

    let hasMoved = false;

    // Pointer Dragging with Hardware Acceleration (translate3d)
    orb.addEventListener('pointerdown', (e) => {
      this.isDragging = true;
      hasMoved = false;
      this.dragStartX = e.clientX - this.posX;
      this.dragStartY = e.clientY - this.posY;
      orb.setPointerCapture(e.pointerId);
      this.playClick(950, 0.02);
    });

    orb.addEventListener('pointermove', (e) => {
      if (!this.isDragging) return;
      hasMoved = true;
      let nextX = e.clientX - this.dragStartX;
      let nextY = e.clientY - this.dragStartY;

      // Bound to window
      const maxX = window.innerWidth - 60;
      const maxY = window.innerHeight - 60;
      this.posX = Math.max(10, Math.min(nextX, maxX));
      this.posY = Math.max(10, Math.min(nextY, maxY));

      container.style.transform = `translate3d(${this.posX}px, ${this.posY}px, 0)`;
    });

    orb.addEventListener('pointerup', (e) => {
      if (!this.isDragging) return;
      this.isDragging = false;
      try { orb.releasePointerCapture(e.pointerId); } catch (_) {}

      // If user merely clicked without moving, toggle dock
      if (!hasMoved) {
        this.toggleDock();
        return;
      }

      // Magnetic Edge Snapping (Smooth spring to left or right screen border)
      const snapThreshold = window.innerWidth / 2;
      const targetX = this.posX > snapThreshold ? (window.innerWidth - 70) : 18;
      
      container.style.transition = 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
      this.posX = targetX;
      container.style.transform = `translate3d(${this.posX}px, ${this.posY}px, 0)`;
      setTimeout(() => {
        container.style.transition = '';
        this.savePosition();
      }, 300);
      this.playClamp();
    });

    closeBtn.addEventListener('click', () => this.toggleDock(false));

    // Audio & Voice toggles
    toggleAudio.addEventListener('click', () => {
      this.audioEnabled = !this.audioEnabled;
      toggleAudio.classList.toggle('active', this.audioEnabled);
      localStorage.setItem('azam_audio_enabled', this.audioEnabled);
      if (this.audioEnabled) this.playClick(1000);
    });

    toggleVoice.addEventListener('click', () => {
      this.voiceEnabled = !this.voiceEnabled;
      toggleVoice.classList.toggle('active', this.voiceEnabled);
      localStorage.setItem('azam_voice_enabled', this.voiceEnabled);
      if (this.voiceEnabled) this.speak("Tactical voice telemetry online");
    });

    // Theme Picker
    themeChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const theme = chip.getAttribute('data-set-theme');
        this.applyTheme(theme);
        themeChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        this.playClick(1200);
      });
    });

    // Reposition on window resize if outside bounds
    window.addEventListener('resize', () => {
      if (this.posX > window.innerWidth - 70) {
        this.posX = window.innerWidth - 70;
        container.style.transform = `translate3d(${this.posX}px, ${this.posY}px, 0)`;
      }
    }, { passive: true });
  }

  toggleDock(forceState) {
    const dock = document.getElementById('tacticalDockPanel');
    if (!dock) return;
    this.isExpanded = forceState !== undefined ? forceState : !this.isExpanded;
    dock.classList.toggle('dock-hidden', !this.isExpanded);
    if (this.isExpanded) {
      this.playClick(1100, 0.04);
    }
  }

  applyTheme(theme) {
    this.currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('azam_theme', theme);
  }

  restorePosition() {
    try {
      const saved = localStorage.getItem('azam_tactical_widget_pos');
      if (saved) {
        const pos = JSON.parse(saved);
        if (pos.x && pos.y && pos.x < window.innerWidth && pos.y < window.innerHeight) {
          this.posX = pos.x;
          this.posY = pos.y;
        }
      }
    } catch (_) {}
  }

  savePosition() {
    try {
      localStorage.setItem('azam_tactical_widget_pos', JSON.stringify({ x: this.posX, y: this.posY }));
    } catch (_) {}
  }

  startFpsLoop() {
    const fpsVal = document.getElementById('dockFpsVal');
    const msVal = document.getElementById('dockMsVal');

    const updateFrame = (timestamp) => {
      const delta = timestamp - this.lastFrameTime;
      this.lastFrameTime = timestamp;
      this.frameCount++;

      if (timestamp - this.lastFpsUpdate >= 400) {
        this.fps = Math.round((this.frameCount * 1000) / (timestamp - this.lastFpsUpdate));
        this.frameTime = (delta).toFixed(1);
        this.frameCount = 0;
        this.lastFpsUpdate = timestamp;

        if (fpsVal && this.isExpanded) {
          fpsVal.innerHTML = `${this.fps} <span style="font-size:0.65rem; color:#64748b;">FPS</span>`;
          fpsVal.className = `dock-stat-val ${this.fps >= 55 ? 'fps-good' : 'fps-warn'}`;
        }
        if (msVal && this.isExpanded) {
          msVal.innerHTML = `${this.frameTime} <span style="font-size:0.65rem; color:#64748b;">MS</span>`;
        }
      }

      // Keep running only when tab visible to conserve GPU cycles
      if (document.visibilityState === 'visible') {
        requestAnimationFrame(updateFrame);
      } else {
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'visible') {
            this.lastFrameTime = performance.now();
            requestAnimationFrame(updateFrame);
          }
        }, { once: true });
      }
    };

    requestAnimationFrame(updateFrame);
  }
}

// Auto-initialize once DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new AzamTacticalWidget());
} else {
  new AzamTacticalWidget();
}
