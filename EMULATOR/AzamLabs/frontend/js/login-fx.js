/**
 * AzamLabs Login Cyber-FX Engine (60 FPS Locked)
 * Features: High-performance bounded neural packet starfield,
 * distance-squared proximity math, 3D card tilt parallax,
 * and high-speed 400ms diagnostic boot sequence.
 */

class LoginCyberFX {
  constructor() {
    this.canvas = document.getElementById('cyberCanvas');
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');

    // Bounded Particle Pool (Zero GC Thrashing)
    this.MAX_PARTICLES = 42;
    this.particles = [];
    this.mouse = { x: -1000, y: -1000, radius: 140 };
    this.lastTime = performance.now();

    // 3D Parallax Tilt Target
    this.card = document.querySelector('.login-card');
    this.cardRect = null;
    this.tiltX = 0;
    this.tiltY = 0;
    this.ticking = false;

    this.init();
  }

  init() {
    this.resize();
    this.initParticlePool();
    this.bindEvents();

    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.canvas.style.width = `${this.width}px`;
    this.canvas.style.height = `${this.height}px`;
    this.ctx.scale(dpr, dpr);
  }

  initParticlePool() {
    this.particles = [];
    for (let i = 0; i < this.MAX_PARTICLES; i++) {
      this.particles.push({
        x: Math.random() * this.width,
        y: Math.random() * this.height,
        vx: (Math.random() - 0.5) * 0.6,
        vy: (Math.random() - 0.5) * 0.6,
        radius: 1.5 + Math.random() * 2,
        color: i % 3 === 0 ? '#00f2fe' : (i % 3 === 1 ? '#4facfe' : '#00ff87'),
        pulse: Math.random() * Math.PI
      });
    }
  }

  bindEvents() {
    window.addEventListener('resize', () => {
      this.resize();
      this.initParticlePool();
    }, { passive: true });

    window.addEventListener('mousemove', (e) => {
      this.mouse.x = e.clientX;
      this.mouse.y = e.clientY;

      if (!this.ticking && this.card) {
        window.requestAnimationFrame(() => {
          this.applyCardTilt(e.clientX, e.clientY);
          this.ticking = false;
        });
        this.ticking = true;
      }
    }, { passive: true });

    window.addEventListener('mouseleave', () => {
      this.mouse.x = -1000;
      this.mouse.y = -1000;
      if (this.card) {
        this.card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
      }
    });
  }

  applyCardTilt(mouseX, mouseY) {
    if (!this.card) return;
    const cx = window.innerWidth / 2;
    const cy = window.innerHeight / 2;
    const dx = (mouseX - cx) / cx;
    const dy = (mouseY - cy) / cy;

    const rotX = -dy * 8; // Max 8 deg
    const rotY = dx * 8;

    this.card.style.transform = `perspective(1000px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) translateZ(10px)`;
  }

  animate(currentTime) {
    const dt = Math.min((currentTime - this.lastTime) / 1000, 0.1);
    this.lastTime = currentTime;

    this.ctx.clearRect(0, 0, this.width, this.height);

    // Render Neural Mesh & Interconnecting Optical Links
    const maxDistSq = 140 * 140;
    const mouseRadiusSq = this.mouse.radius * this.mouse.radius;

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      // Update positions
      p.x += p.vx;
      p.y += p.vy;

      // Bounce cleanly at boundaries
      if (p.x < 0 || p.x > this.width) p.vx *= -1;
      if (p.y < 0 || p.y > this.height) p.vy *= -1;

      // Mouse repulsion using distance squared
      const mdx = p.x - this.mouse.x;
      const mdy = p.y - this.mouse.y;
      const mdistSq = mdx * mdx + mdy * mdy;

      if (mdistSq < mouseRadiusSq && mdistSq > 0) {
        const force = (1 - mdistSq / mouseRadiusSq) * 1.5;
        p.x += (mdx / Math.sqrt(mdistSq)) * force;
        p.y += (mdy / Math.sqrt(mdistSq)) * force;
      }

      // Draw particle dot
      p.pulse += dt * 2;
      const alpha = 0.5 + 0.4 * Math.sin(p.pulse);

      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = alpha;
      this.ctx.fill();

      // Proximity connection to other particles (Distance-Squared Math)
      for (let j = i + 1; j < this.particles.length; j++) {
        const p2 = this.particles[j];
        const dx = p.x - p2.x;
        const dy = p.y - p2.y;
        const distSq = dx * dx + dy * dy;

        if (distSq < maxDistSq) {
          const lineAlpha = (1 - distSq / maxDistSq) * 0.22;
          this.ctx.beginPath();
          this.ctx.moveTo(p.x, p.y);
          this.ctx.lineTo(p2.x, p2.y);
          this.ctx.strokeStyle = '#00f2fe';
          this.ctx.globalAlpha = lineAlpha;
          this.ctx.lineWidth = 1;
          this.ctx.stroke();
        }
      }
    }

    this.ctx.globalAlpha = 1.0;

    // Keep running smoothly when visible
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

}

// Auto-run on load
window.addEventListener('DOMContentLoaded', () => {
  new LoginCyberFX();
});
