/* ============================================================================
   PNetLab Main Dashboard — Azam-Features Operations Center View
   Integrated into /main/ as the primary "Azam-Features" navigation tab.
   Communicates with the backend API service on /azam-ops/api/
   ============================================================================ */
(function () {
  'use strict';

  var App = window.PnqApp;
  if (!App) return;

  var API_BASE = '/azam-ops/api';

  /* ── ANSI Color helper ──────────────────────────────────── */
  function stripAnsi(str) {
    return str.replace(/\x1b\[[0-9;]*[mGKH]/g, '');
  }

  function getLineColor(line) {
    if (/\[✔\]|success|passed|online|healthy|active/i.test(line)) return '#4ade80';
    if (/\[✘\]|\[!\]|error|fail|critical|fatal/i.test(line))      return '#f87171';
    if (/\[⚠\]|warning|warn|slow/i.test(line))                   return '#fbbf24';
    if (/^===|───|━━━/i.test(line))                               return '#60a5fa';
    if (/\[\*\]|\[i\]|info/i.test(line))                         return '#38bdf8';
    return '#94a3b8';
  }

  /* ── Main Render Entry ──────────────────────────────────── */
  function render(view) {
    view.innerHTML = '';

    // Container with modern dark styling & spacing
    var container = document.createElement('div');
    container.className = 'azam-features-container';
    container.style.cssText = 'display:flex;flex-direction:column;gap:20px;max-width:1440px;margin:0 auto;color:var(--pnq-text,#f1f5f9);';

    // ── 1. Top Header ─────────────────────────────────────────
    var head = document.createElement('div');
    head.className = 'view-head';
    head.style.cssText = 'display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;padding-bottom:16px;border-bottom:1px solid var(--pnq-border,rgba(255,255,255,0.08));';

    var titleBox = document.createElement('div');
    titleBox.style.cssText = 'display:flex;align-items:center;gap:14px;';

    var iconBox = document.createElement('div');
    iconBox.style.cssText = 'width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#0284c7,#7c3aed);display:flex;align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(2,132,199,0.35);';
    iconBox.innerHTML = '<i class="fa fa-bolt" style="font-size:22px;color:#fff;"></i>';

    var titleText = document.createElement('div');
    titleText.innerHTML = 
      '<div style="font-size:22px;font-weight:700;letter-spacing:-0.02em;background:linear-gradient(90deg,#38bdf8,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">' +
        'Azam-Features Operations Center' +
      '</div>' +
      '<div style="font-size:13px;color:var(--pnq-text-muted,#94a3b8);margin-top:2px;">' +
        'Unified cluster intelligence, real-time diagnostic suite, automated backup & canvas accelerators' +
      '</div>';

    titleBox.appendChild(iconBox);
    titleBox.appendChild(titleText);

    // Header Actions
    var actions = document.createElement('div');
    actions.style.cssText = 'display:flex;gap:10px;align-items:center;flex-wrap:wrap;';

    var btnRefresh = document.createElement('button');
    btnRefresh.className = 'btn btn-ghost';
    btnRefresh.innerHTML = '<i class="fa fa-refresh"></i> Refresh';
    btnRefresh.onclick = function () { loadStats(); loadBackups(); App.toast('Metrics refreshed', 'ok'); };

    var btnDoctor = document.createElement('button');
    btnDoctor.className = 'btn btn-primary';
    btnDoctor.style.cssText = 'background:linear-gradient(135deg,#0284c7,#2563eb);border:none;color:#fff;';
    btnDoctor.innerHTML = '<i class="fa fa-stethoscope"></i> Run Doctor';
    btnDoctor.onclick = function () { switchTab('health'); runTool('doctor', {}, null, 'term-doctor'); };

    actions.appendChild(btnRefresh);
    actions.appendChild(btnDoctor);

    head.appendChild(titleBox);
    head.appendChild(actions);
    container.appendChild(head);

    // ── 2. Vital Metrics Cards (Top HUD) ──────────────────────
    var statsGrid = document.createElement('div');
    statsGrid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:14px;';
    statsGrid.innerHTML = 
      createStatCard('az-m-ram', 'Memory (RAM)', '—', 'fa-microchip', '#38bdf8') +
      createStatCard('az-m-cpu', 'CPU Load (1m)', '—', 'fa-tachometer', '#818cf8') +
      createStatCard('az-m-nodes', 'Active QEMU Nodes', '—', 'fa-cubes', '#34d399') +
      createStatCard('az-m-watchdog', '24/7 Watchdog', '—', 'fa-shield', '#fbbf24') +
      createStatCard('az-m-disk', 'Storage (/)', '—', 'fa-hdd-o', '#f472b6') +
      createStatCard('az-m-backups', 'Backups Count', '—', 'fa-archive', '#a78bfa');
    container.appendChild(statsGrid);

    // ── 3. Tab Bar Navigation ─────────────────────────────────
    var navTabs = document.createElement('div');
    navTabs.style.cssText = 'display:flex;gap:8px;border-bottom:2px solid var(--pnq-border,rgba(255,255,255,0.08));padding-bottom:2px;overflow-x:auto;';

    var tabs = [
      { id: 'health',   name: 'Cluster Health & Diagnostic', icon: 'fa-heartbeat' },
      { id: 'backups',  name: 'Backups & Git VCS',          icon: 'fa-archive' },
      { id: 'network',  name: 'Consoles & Dataplane',       icon: 'fa-sitemap' },
      { id: 'security', name: 'Security & WhatsApp Alerts', icon: 'fa-shield' },
      { id: 'canvas',   name: 'Canvas Accelerators',        icon: 'fa-paint-brush' }
    ];

    tabs.forEach(function (t, idx) {
      var tabBtn = document.createElement('button');
      tabBtn.type = 'button';
      tabBtn.className = 'az-tab-btn' + (idx === 0 ? ' is-active' : '');
      tabBtn.dataset.tab = t.id;
      tabBtn.style.cssText = 'background:none;border:none;padding:10px 16px;font-size:13.5px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;display:flex;align-items:center;gap:8px;transition:all 0.15s ease;white-space:nowrap;';
      if (idx === 0) {
        tabBtn.style.color = '#38bdf8';
        tabBtn.style.borderBottomColor = '#38bdf8';
      }
      tabBtn.innerHTML = '<i class="fa ' + t.icon + '"></i> ' + t.name;
      tabBtn.onclick = function () { switchTab(t.id); };
      navTabs.appendChild(tabBtn);
    });
    container.appendChild(navTabs);

    // ── 4. Tab Panes Container ────────────────────────────────
    var panesContainer = document.createElement('div');
    panesContainer.id = 'az-panes';

    // ── Pane 1: Health & Diagnostics ──
    var pHealth = document.createElement('div');
    pHealth.id = 'pane-health';
    pHealth.style.display = 'block';
    pHealth.innerHTML = 
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">' +
        createToolCard('fleet', 'azam-fleet', 'Cluster Fleet & Satellite Monitor', 'Pings Master & Satellites (192.168.1.22, 192.168.1.23, 192.168.1.24), checks WireGuard/GRE tunnels and node distribution.', 'fa-server', '#0284c7', 'term-fleet') +
        createToolCard('capacity', 'azam-capacity', 'Resource Capacity Planner', 'Live calculation of remaining RAM, vCPU cores, and maximum additional QEMU/IOL node slots before saturation.', 'fa-bar-chart', '#059669', 'term-capacity') +
        createToolCard('doctor', 'azam-doctor', 'Cluster Doctor & Self-Healer', 'Deep diagnostic check of file permissions, disk health, orphan QEMU processes, and Apache proxy settings.', 'fa-stethoscope', '#d97706', 'term-doctor', [{ label: 'Reclaim Disk (--compress)', param: 'compress', tool: 'doctor-compress' }]) +
        createToolCard('perf', 'azam-perf', 'Performance Benchmark', 'Measures real-time memory throughput, disk I/O latency, and system response times under active load.', 'fa-dashboard', '#7c3aed', 'term-perf') +
        createToolCard('watchdog-status', 'azam-watchdog', '24/7 Watchdog Service', 'Inspect or configure the autonomous background systemd service that monitors cluster health continuously.', 'fa-eye', '#dc2626', 'term-watchdog', [{ label: 'Reinstall / Enable', param: 'install', tool: 'watchdog-install' }]) +
      '</div>';
    panesContainer.appendChild(pHealth);

    // ── Pane 2: Backups & Git VCS ──
    var pBackups = document.createElement('div');
    pBackups.id = 'pane-backups';
    pBackups.style.display = 'none';
    pBackups.innerHTML = 
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
        '<div style="display:flex;flex-direction:column;gap:16px;">' +
          createToolCard('backup', 'azam-backup', 'Create Cluster Snapshot', 'Creates an automated, compressed tar.gz archive of all lab files, configs, and SQLite user database.', 'fa-cloud-upload', '#0284c7', 'term-backup') +
          '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">' +
              '<div style="font-weight:600;font-size:15px;"><i class="fa fa-list"></i> Backup Archives</div>' +
              '<button type="button" class="btn btn-ghost btn-sm" id="btn-refresh-backups"><i class="fa fa-refresh"></i></button>' +
            '</div>' +
            '<div id="az-backups-table" style="max-height:260px;overflow-y:auto;font-size:13px;color:var(--pnq-text-muted,#94a3b8);">' +
              'Loading backups list…' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div style="display:flex;flex-direction:column;gap:16px;">' +
          createToolCard('topology-snapshot', 'azam-topology-git', 'Git Lab Topology VCS', 'Version-control active lab topologies. Commits live device positions and connections directly to Git.', 'fa-code-fork', '#7c3aed', 'term-vcs', [], [
            { id: 'vcs-lab', placeholder: 'Lab path or name (optional)' },
            { id: 'vcs-msg', placeholder: 'Commit message (e.g. Added OSPF area 0)' }
          ]) +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pBackups);

    // ── Pane 3: Consoles & Dataplane ──
    var pNetwork = document.createElement('div');
    pNetwork.id = 'pane-network';
    pNetwork.style.display = 'none';
    pNetwork.innerHTML = 
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">' +
        createToolCard('console-fix', 'azam-console-fix', 'Console Port Collision Cleaner', 'Repairs broken HTML5, VNC, and Telnet console bindings, kills zombie listeners, and resets Guacamole.', 'fa-terminal', '#0284c7', 'term-console') +
        createToolCard('bench', 'azam-bench', 'Satellite Dataplane Benchmark', 'Tests inter-cluster tunnel latency, MTU discovery, and packet loss between Master and specified Satellite.', 'fa-exchange', '#059669', 'term-bench', [], [
          { id: 'bench-ip', placeholder: 'Satellite IP (e.g. 192.168.1.22)' }
        ]) +
      '</div>';
    panesContainer.appendChild(pNetwork);

    // ── Pane 4: Security & WhatsApp Alerts ──
    var pSecurity = document.createElement('div');
    pSecurity.id = 'pane-security';
    pSecurity.style.display = 'none';
    pSecurity.innerHTML = 
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
        '<div style="display:flex;flex-direction:column;gap:16px;">' +
          createToolCard('ssl-status', 'azam-ssl', 'SSL / TLS Certificate Engine', 'Inspect active HTTPS certificate expiration, renew SAN multi-domain certificates, or generate new root CA.', 'fa-lock', '#059669', 'term-ssl', [{ label: 'Regenerate Cert', tool: 'ssl-generate' }]) +
          createToolCard('scanner', 'azambasha-scanner', 'Weekly Codeberg Intelligence', 'Scans upstream Codeberg & PNetLab repositories for updates, bugfixes, and security advisories.', 'fa-search', '#6366f1', 'term-scanner') +
        '</div>' +
        '<div style="display:flex;flex-direction:column;gap:16px;">' +
          '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">' +
              '<div style="width:36px;height:36px;border-radius:8px;background:rgba(37,211,102,0.15);display:flex;align-items:center;justify-content:center;color:#25d366;font-size:18px;">' +
                '<i class="fa fa-whatsapp"></i>' +
              '</div>' +
              '<div>' +
                '<div style="font-weight:600;font-size:15px;color:#f1f5f9;">WhatsApp & Webhook Alert Engine</div>' +
                '<div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Dispatches critical cluster alerts & scan reports straight to your phone</div>' +
              '</div>' +
            '</div>' +
            '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:14px;">' +
              '<div>' +
                '<label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">WhatsApp Phone (with country code):</label>' +
                '<input type="text" id="wa-phone" class="input" placeholder="e.g. 919876543210" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
              '</div>' +
              '<div>' +
                '<label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">CallMeBot API Key (Free):</label>' +
                '<input type="password" id="wa-key" class="input" placeholder="Enter API key" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
              '</div>' +
              '<div>' +
                '<label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Custom Alert Message:</label>' +
                '<input type="text" id="wa-msg" class="input" value="⚡ Hello Azam! Test alert from PNetLab Master Cluster (192.168.1.23)" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
              '</div>' +
            '</div>' +
            '<div style="display:flex;gap:10px;align-items:center;">' +
              '<button type="button" id="btn-wa-save" class="btn btn-primary" style="background:#25d366;border-color:#25d366;color:#052e16;font-weight:700;"><i class="fa fa-paper-plane"></i> Save & Send Test Alert</button>' +
              '<button type="button" id="btn-wa-quick" class="btn btn-ghost"><i class="fa fa-bell"></i> Quick Test (--test)</button>' +
            '</div>' +
            '<div id="term-notify" style="display:none;margin-top:14px;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;max-height:180px;overflow-y:auto;"></div>' +
          '</div>' +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pSecurity);

    // ── Pane 5: Canvas Accelerators ──
    var pCanvas = document.createElement('div');
    pCanvas.id = 'pane-canvas';
    pCanvas.style.display = 'none';
    pCanvas.innerHTML = 
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;">' +
        createFeatureCard('Node Spotlight Search', 'Instant canvas navigation across large topologies with keyboard shortcut.', 'Ctrl + K / ⌘ + K', 'fa-search', '#38bdf8', 'Jump directly to any router, switch, or VM. Auto-focuses and pans the viewport.') +
        createFeatureCard('Smart Alignment & Distribution', 'One-click horizontal, vertical, and grid distribution toolbar.', 'Toolbar in Lab', 'fa-align-left', '#818cf8', 'Aligns selected nodes with clean mathematical spacing. Keeps diagrams pristine.') +
        createFeatureCard('Interactive Radar Minimap', 'Floating high-density canvas radar showing the entire topology overview.', 'Minimap Button', 'fa-map-o', '#34d399', 'Interactive viewport box can be dragged to pan across large networks instantly.') +
        createFeatureCard('QuadTree Viewport Culling', 'High-performance spatial indexing engine for 100+ node topologies.', 'Automatic 60 FPS', 'fa-bolt', '#f472b6', 'Culls off-screen node SVG renders, cutting GPU and browser memory by up to 70%.') +
        createFeatureCard('Live Telemetry Heatmap', 'Real-time interface packet load heatmap and animated link flow inspector.', 'Link Stats Layer', 'fa-rss', '#fbbf24', 'Color-codes links by traffic density and visualizes simulated packet flow paths.') +
      '</div>';
    panesContainer.appendChild(pCanvas);

    container.appendChild(panesContainer);
    view.appendChild(container);

    // ── Wire Event Handlers ──
    wirePanes(container);
    loadStats();
    loadBackups();
    loadNotifyConfig();
  }

  /* ── Tab Switching Helper ───────────────────────────────── */
  function switchTab(tabId) {
    var btns = document.querySelectorAll('.az-tab-btn');
    btns.forEach(function (b) {
      var isActive = b.dataset.tab === tabId;
      b.classList.toggle('is-active', isActive);
      b.style.color = isActive ? '#38bdf8' : 'var(--pnq-text-muted,#94a3b8)';
      b.style.borderBottomColor = isActive ? '#38bdf8' : 'transparent';
    });

    ['health', 'backups', 'network', 'security', 'canvas'].forEach(function (id) {
      var p = document.getElementById('pane-' + id);
      if (p) p.style.display = id === tabId ? 'block' : 'none';
    });
  }

  /* ── Wire Dynamic Buttons ───────────────────────────────── */
  function wirePanes(container) {
    container.querySelectorAll('[data-az-tool]').forEach(function (btn) {
      btn.onclick = function () {
        var tool = btn.dataset.azTool;
        var term = btn.dataset.azTerm;
        var params = {};

        if (tool === 'bench') {
          var ipInput = document.getElementById('bench-ip');
          params.satellite_ip = ipInput ? ipInput.value.trim() : '';
          if (!params.satellite_ip) { App.toast('Please enter Satellite IP', 'warn'); return; }
        } else if (tool === 'topology-snapshot') {
          var labInput = document.getElementById('vcs-lab');
          var msgInput = document.getElementById('vcs-msg');
          params.lab = labInput ? labInput.value.trim() : '';
          params.message = msgInput ? msgInput.value.trim() : 'Lab topology snapshot';
        }

        runTool(tool, params, btn, term);
      };
    });

    var btnRefreshBackups = container.querySelector('#btn-refresh-backups');
    if (btnRefreshBackups) btnRefreshBackups.onclick = loadBackups;

    var btnWaSave = container.querySelector('#btn-wa-save');
    if (btnWaSave) {
      btnWaSave.onclick = function () {
        var phone = document.getElementById('wa-phone').value.trim();
        var key = document.getElementById('wa-key').value.trim();
        var msg = document.getElementById('wa-msg').value.trim();
        if (!phone) { App.toast('Enter your WhatsApp phone number', 'warn'); return; }
        runTool('notify-send', { phone: phone, apikey: key, message: msg, save: true }, btnWaSave, 'term-notify');
      };
    }

    var btnWaQuick = container.querySelector('#btn-wa-quick');
    if (btnWaQuick) {
      btnWaQuick.onclick = function () {
        runTool('notify-test', {}, btnWaQuick, 'term-notify');
      };
    }
  }

  /* ── Stats Loader ───────────────────────────────────────── */
  function loadStats() {
    fetch(API_BASE + '/stats')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        setStat('az-m-ram', (d.ram_used_gb || 0) + ' / ' + (d.ram_total_gb || 0) + ' GB', (d.ram_pct || 0) + '% used');
        setStat('az-m-cpu', (d.load1 != null ? d.load1 : '—'), (d.cpus || 1) + ' vCPU cores');
        setStat('az-m-nodes', d.active_nodes || 0, 'Active QEMU/IOL');
        setStat('az-m-watchdog', d.watchdog === 'active' ? 'Active' : 'Stopped', d.watchdog === 'active' ? 'Self-healing ON' : 'Service idle', d.watchdog === 'active' ? '#4ade80' : '#f87171');
        setStat('az-m-disk', (d.disk_used_gb || 0) + ' / ' + (d.disk_total_gb || 0) + ' GB', (d.disk_pct || 0) + '% used');
        setStat('az-m-backups', (d.backup_count || 0) + ' archives', 'Ready to restore');
      })
      .catch(function () {});
  }

  function setStat(id, val, sub, customColor) {
    var card = document.getElementById(id);
    if (!card) return;
    var vEl = card.querySelector('.stat-val');
    var sEl = card.querySelector('.stat-sub');
    if (vEl) {
      vEl.textContent = val;
      if (customColor) vEl.style.color = customColor;
    }
    if (sEl && sub) sEl.textContent = sub;
  }

  /* ── Backups Loader ─────────────────────────────────────── */
  function loadBackups() {
    var target = document.getElementById('az-backups-table');
    if (!target) return;
    target.innerHTML = '<div style="padding:10px;"><i class="fa fa-spinner fa-spin"></i> Reading backup directory…</div>';

    fetch(API_BASE + '/backups')
      .then(function (r) { return r.json(); })
      .then(function (res) {
        var list = res.backups || [];
        if (!list.length) {
          target.innerHTML = '<div style="padding:10px;color:#64748b;">No backups found in /opt/azambasha/backups/</div>';
          return;
        }
        var html = '<table class="table" style="width:100%;">';
        html += '<thead><tr><th>Archive File</th><th>Size</th><th>Created</th><th>Action</th></tr></thead><tbody>';
        list.forEach(function (b) {
          var date = new Date(b.mtime * 1000).toLocaleString();
          html += '<tr>' +
            '<td style="font-family:monospace;font-size:12px;color:#38bdf8;">' + b.name + '</td>' +
            '<td>' + (b.size_kb > 1024 ? (b.size_kb / 1024).toFixed(1) + ' MB' : b.size_kb + ' KB') + '</td>' +
            '<td style="color:#94a3b8;font-size:11.5px;">' + date + '</td>' +
            '<td><button type="button" class="btn btn-ghost btn-sm" onclick="window.__azRestore(\'' + b.name + '\')"><i class="fa fa-undo"></i> Restore</button></td>' +
          '</tr>';
        });
        html += '</tbody></table>';
        target.innerHTML = html;
      })
      .catch(function () {
        target.innerHTML = '<div style="padding:10px;color:#ef4444;">Failed to load backup archives</div>';
      });
  }

  window.__azRestore = function (filename) {
    if (!confirm('Are you sure you want to restore cluster backup:\n' + filename + '\n\nThis will restore configurations and labs.')) return;
    runTool('backup-list', { restore_file: filename }, null, 'term-backup');
  };

  /* ── WhatsApp Config Loader ─────────────────────────────── */
  function loadNotifyConfig() {
    fetch(API_BASE + '/notify-config')
      .then(function (r) { return r.json(); })
      .then(function (conf) {
        if (conf.whatsapp_phone) {
          var pInput = document.getElementById('wa-phone');
          if (pInput && !pInput.value) pInput.value = conf.whatsapp_phone;
        }
        if (conf.whatsapp_apikey) {
          var kInput = document.getElementById('wa-key');
          if (kInput && !kInput.value) kInput.placeholder = 'Configured (' + conf.whatsapp_apikey + ')';
        }
      })
      .catch(function () {});
  }

  /* ── Tool Runner with Live Stream ───────────────────────── */
  function runTool(tool, params, btn, termId) {
    var term = document.getElementById(termId);
    if (!term) return;

    term.style.display = 'block';
    term.innerHTML = 
      '<div style="display:flex;align-items:center;justify-content:space-between;padding-bottom:8px;margin-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.08);">' +
        '<div style="display:flex;gap:6px;">' +
          '<span style="width:10px;height:10px;border-radius:50%;background:#ef4444;display:inline-block;"></span>' +
          '<span style="width:10px;height:10px;border-radius:50%;background:#eab308;display:inline-block;"></span>' +
          '<span style="width:10px;height:10px;border-radius:50%;background:#22c55e;display:inline-block;"></span>' +
        '</div>' +
        '<div style="font-size:11px;color:#64748b;font-family:monospace;">executing: ' + tool + '</div>' +
      '</div>';

    if (btn) btn.disabled = true;

    fetch(API_BASE + '/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: tool, params: params || {} })
    }).then(function (res) {
      if (!res.body) throw new Error('No response body stream');
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buf = '';

      function pump() {
        reader.read().then(function (r) {
          if (r.done) {
            if (btn) btn.disabled = false;
            loadStats();
            return;
          }
          buf += decoder.decode(r.value, { stream: true });
          var lines = buf.split('\n');
          buf = lines.pop();

          lines.forEach(function (line) {
            if (!line.startsWith('data:')) return;
            try {
              var obj = JSON.parse(line.slice(5).trim());
              if (obj.type === 'line') {
                var txt = stripAnsi(obj.data);
                if (!txt.trim()) return;
                var row = document.createElement('div');
                row.style.cssText = 'white-space:pre-wrap;word-break:break-all;line-height:1.45;color:' + getLineColor(txt) + ';';
                row.textContent = txt;
                term.appendChild(row);
                term.scrollTop = term.scrollHeight;
              } else if (obj.type === 'done') {
                var doneRow = document.createElement('div');
                doneRow.style.cssText = 'border-top:1px solid rgba(255,255,255,0.08);margin-top:8px;padding-top:6px;font-size:11px;color:#64748b;';
                doneRow.textContent = '── Process exited with status ' + obj.code + ' ──';
                term.appendChild(doneRow);
                term.scrollTop = term.scrollHeight;
                if (btn) btn.disabled = false;
                App.toast(obj.code === 0 ? '✔ Execution finished successfully' : '⚠ Execution exited with code ' + obj.code, obj.code === 0 ? 'ok' : 'err');
                loadStats();
              }
            } catch (e) {}
          });
          pump();
        }).catch(function (err) {
          if (btn) btn.disabled = false;
        });
      }
      pump();
    }).catch(function (err) {
      if (btn) btn.disabled = false;
      var errDiv = document.createElement('div');
      errDiv.style.color = '#f87171';
      errDiv.textContent = 'Failed to execute tool: ' + err.message;
      term.appendChild(errDiv);
    });
  }

  /* ── HTML UI Template Builders ─────────────────────────── */
  function createStatCard(id, title, val, icon, color) {
    return (
      '<div id="' + id + '" class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:14px 16px;display:flex;align-items:center;gap:14px;box-shadow:0 2px 8px rgba(0,0,0,0.2);">' +
        '<div style="width:42px;height:42px;border-radius:10px;background:' + color + '15;border:1px solid ' + color + '30;display:flex;align-items:center;justify-content:center;color:' + color + ';font-size:18px;flex-shrink:0;">' +
          '<i class="fa ' + icon + '"></i>' +
        '</div>' +
        '<div style="overflow:hidden;flex:1;">' +
          '<div style="font-size:11.5px;text-transform:uppercase;letter-spacing:0.04em;color:var(--pnq-text-muted,#94a3b8);font-weight:600;">' + title + '</div>' +
          '<div class="stat-val" style="font-size:17px;font-weight:700;color:var(--pnq-text,#f1f5f9);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + val + '</div>' +
          '<div class="stat-sub" style="font-size:11px;color:#64748b;margin-top:2px;">Loading…</div>' +
        '</div>' +
      '</div>'
    );
  }

  function createToolCard(tool, cmd, title, desc, icon, color, termId, extraBtns, inputs) {
    var html = 
      '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:14px;box-shadow:0 2px 8px rgba(0,0,0,0.2);">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">' +
          '<div style="display:flex;gap:12px;align-items:center;">' +
            '<div style="width:38px;height:38px;border-radius:8px;background:' + color + '18;color:' + color + ';display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0;">' +
              '<i class="fa ' + icon + '"></i>' +
            '</div>' +
            '<div>' +
              '<div style="font-weight:600;font-size:15px;color:#f1f5f9;">' + title + '</div>' +
              '<div style="font-family:monospace;font-size:11.5px;color:#38bdf8;margin-top:2px;">' + cmd + '</div>' +
            '</div>' +
          '</div>' +
          '<span style="padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;background:rgba(56,189,248,0.15);color:#38bdf8;">CLI & GUI</span>' +
        '</div>' +
        '<div style="font-size:12.5px;color:var(--pnq-text-muted,#94a3b8);line-height:1.5;">' + desc + '</div>';

    if (inputs && inputs.length) {
      html += '<div style="display:flex;flex-direction:column;gap:8px;">';
      inputs.forEach(function (inp) {
        html += '<input type="text" id="' + inp.id + '" placeholder="' + inp.placeholder + '" style="padding:7px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12.5px;">';
      });
      html += '</div>';
    }

    html += '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">';
    html += '<button type="button" class="btn btn-primary" data-az-tool="' + tool + '" data-az-term="' + termId + '" style="background:' + color + ';border-color:' + color + ';color:#fff;"><i class="fa fa-play"></i> Run ' + cmd + '</button>';

    if (extraBtns && extraBtns.length) {
      extraBtns.forEach(function (eb) {
        html += '<button type="button" class="btn btn-ghost btn-sm" data-az-tool="' + (eb.tool || tool) + '" data-az-term="' + termId + '">' + eb.label + '</button>';
      });
    }
    html += '</div>';

    html += '<div id="' + termId + '" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;max-height:220px;overflow-y:auto;box-shadow:inset 0 2px 6px rgba(0,0,0,0.4);"></div>';
    html += '</div>';
    return html;
  }

  function createFeatureCard(name, desc, trigger, icon, color, detail) {
    return (
      '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:12px;box-shadow:0 2px 8px rgba(0,0,0,0.2);">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;">' +
          '<div style="display:flex;gap:10px;align-items:center;">' +
            '<div style="width:36px;height:36px;border-radius:8px;background:' + color + '20;color:' + color + ';display:flex;align-items:center;justify-content:center;font-size:16px;">' +
              '<i class="fa ' + icon + '"></i>' +
            '</div>' +
            '<div style="font-weight:600;font-size:14.5px;color:#f1f5f9;">' + name + '</div>' +
          '</div>' +
          '<span style="padding:3px 8px;border-radius:6px;font-size:11px;font-weight:700;font-family:monospace;background:rgba(255,255,255,0.08);color:#38bdf8;">' + trigger + '</span>' +
        '</div>' +
        '<div style="font-size:12.5px;color:var(--pnq-text-muted,#94a3b8);line-height:1.5;">' + desc + '</div>' +
        '<div style="font-size:12px;color:#64748b;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;margin-top:auto;">' + detail + '</div>' +
      '</div>'
    );
  }

  /* ── Register with App Router ───────────────────────────── */
  App.register('azam-features', {
    title: 'Azam-Features',
    icon: 'fa-bolt',
    admin: false,
    render: render
  });

})();
