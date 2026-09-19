/* ============================================================================
   PNetLab Main Dashboard — Azam-Features Enterprise Operations Center
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
    if (/\[✔\]|\[PASS\]|success|passed|online|healthy|active/i.test(line)) return '#4ade80';
    if (/\[✘\]|\[FAIL\]|\[!\]|error|fail|critical|fatal/i.test(line))      return '#f87171';
    if (/\[⚠\]|warning|warn|slow|hint/i.test(line))                        return '#fbbf24';
    if (/^===|───|━━━/i.test(line))                                       return '#60a5fa';
    if (/\[\*\]|\[i\]|info/i.test(line))                                  return '#38bdf8';
    return '#94a3b8';
  }

  /* ── Main Render Entry ──────────────────────────────────── */
  function render(view) {
    view.innerHTML = '';

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
        'Azam-Features Enterprise Operations Center' +
      '</div>' +
      '<div style="font-size:13px;color:var(--pnq-text-muted,#94a3b8);margin-top:2px;">' +
        'Exam grader, web Wireshark, cloud transit, image optimizer, diagram exporter & AI copilot' +
      '</div>';

    titleBox.appendChild(iconBox);
    titleBox.appendChild(titleText);

    // Header Actions
    var actions = document.createElement('div');
    actions.style.cssText = 'display:flex;gap:10px;align-items:center;flex-wrap:wrap;';

    var btnToolkit = document.createElement('button');
    btnToolkit.type = 'button';
    btnToolkit.className = 'btn btn-ghost';
    btnToolkit.style.cssText = 'display:inline-flex;align-items:center;gap:6px;color:#a78bfa;border:1px solid rgba(167,139,250,0.3);padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:background 0.15s ease;';
    btnToolkit.innerHTML = '<i class="fa fa-wrench" style="color:#a78bfa;"></i> Client Toolkit';
    btnToolkit.onclick = function () { openClientToolkitModal(); };

    var btnRefresh = document.createElement('button');
    btnRefresh.className = 'btn btn-ghost';
    btnRefresh.innerHTML = '<i class="fa fa-refresh"></i> Refresh All';
    btnRefresh.onclick = function () { loadStats(); loadBackups(); loadMesh(); loadImagesAudit(); App.toast('Metrics refreshed', 'ok'); };

    var btnDoctor = document.createElement('button');
    btnDoctor.className = 'btn btn-primary';
    btnDoctor.style.cssText = 'background:linear-gradient(135deg,#0284c7,#2563eb);border:none;color:#fff;';
    btnDoctor.innerHTML = '<i class="fa fa-stethoscope"></i> Run Doctor';
    btnDoctor.onclick = function () { switchTab('health'); runTool('doctor', {}, null, 'term-doctor'); };

    actions.appendChild(btnToolkit);
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
      createStatCard('az-m-backups', 'Backups Ready', '—', 'fa-archive', '#a78bfa');
    container.appendChild(statsGrid);

    // ── 3. Tab Bar Navigation ─────────────────────────────────
    var navTabs = document.createElement('div');
    navTabs.style.cssText = 'display:flex;gap:6px;border-bottom:2px solid var(--pnq-border,rgba(255,255,255,0.08));padding-bottom:2px;overflow-x:auto;scrollbar-width:thin;';

    var tabs = [
      { id: 'health',    name: 'Cluster Health',          icon: 'fa-heartbeat' },
      { id: 'templates', name: 'Templates Marketplace',   icon: 'fa-th-large' },
      { id: 'grader',    name: 'Exam & Quiz Grader',      icon: 'fa-graduation-cap' },
      { id: 'sniffer',   name: 'Web Wireshark Sniffer',   icon: 'fa-rss' },
      { id: 'bridge',    name: 'Cloud & LAN Transit',     icon: 'fa-globe' },
      { id: 'doc',       name: 'Diagram & Doc Exporter',  icon: 'fa-file-code-o' },
      { id: 'ai',        name: 'AI Lab Copilot',          icon: 'fa-magic' },
      { id: 'diff',      name: 'Config Diff & Rollback',  icon: 'fa-history' },
      { id: 'mesh',      name: 'Ping Mesh & Traffic Gen', icon: 'fa-exchange' },
      { id: 'scheduler', name: 'Idle Saver & Quotas',     icon: 'fa-clock-o' },
      { id: 'cloud',     name: 'Cloud & NAS Backup',      icon: 'fa-cloud-upload' },
      { id: 'security',  name: 'Security & WhatsApp',     icon: 'fa-whatsapp' },
      { id: 'canvas',    name: 'Canvas Accelerators',     icon: 'fa-paint-brush' }
    ];

    tabs.forEach(function (t, idx) {
      var tabBtn = document.createElement('button');
      tabBtn.type = 'button';
      tabBtn.className = 'az-tab-btn' + (idx === 0 ? ' is-active' : '');
      tabBtn.dataset.tab = t.id;
      tabBtn.style.cssText = 'background:none;border:none;padding:8px 12px;font-size:12.5px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;display:flex;align-items:center;gap:6px;transition:all 0.15s ease;white-space:nowrap;';
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
        createToolCard('doctor', 'azam-doctor', 'Cluster Doctor & Self-Healer', 'Deep diagnostic check of file permissions, disk health, orphan QEMU processes, and Apache proxy settings.', 'fa-stethoscope', '#d97706', 'term-doctor') +
        createToolCard('perf', 'azam-perf', 'Performance Benchmark', 'Measures real-time memory throughput, disk I/O latency, and system load stress test.', 'fa-dashboard', '#7c3aed', 'term-perf') +
        createToolCard('watchdog-status', 'azam-watchdog', '24/7 Watchdog Service', 'Autonomous background systemd service that monitors cluster health continuously.', 'fa-eye', '#dc2626', 'term-watchdog', [{ label: 'Reinstall / Enable', param: 'install', tool: 'watchdog-install' }]) +
        createToolCard('console-fix-full', 'azam-console-fix', 'HTML5 Console Auto-Fixer', 'Repairs Guacamole WebSockets, cleans stale pipes, and tests guacd daemon health.', 'fa-terminal', '#10b981', 'term-console-fix') +
      '</div>' +
      '<div class="card" style="margin-top:16px;background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px;">' +
          '<div style="display:flex;align-items:center;gap:10px;">' +
            '<div style="width:36px;height:36px;border-radius:8px;background:rgba(239,68,68,0.15);color:#ef4444;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-fire"></i></div>' +
            '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Live Hot-Node Resource Profiler</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Active QEMU/IOL processes ranked by CPU% and Resident Memory</div></div>' +
          '</div>' +
          '<div style="display:flex;gap:8px;align-items:center;">' +
            '<button type="button" id="btn-perf-refresh" class="btn btn-ghost" style="font-size:12px;"><i class="fa fa-refresh"></i> Refresh Profiler</button>' +
            '<button type="button" id="btn-perf-kill" class="btn btn-danger" style="background:#dc2626;color:#fff;font-size:12px;padding:6px 12px;border:none;border-radius:6px;font-weight:600;"><i class="fa fa-pause-circle"></i> Pause Top Offender (--kill-hot)</button>' +
          '</div>' +
        '</div>' +
        '<div id="perf-nodes-table" style="max-height:260px;overflow-y:auto;background:rgba(0,0,0,0.25);border-radius:8px;border:1px solid var(--pnq-border,rgba(255,255,255,0.06));padding:4px;">' +
          '<div style="padding:10px;color:#64748b;">Click "Refresh Profiler" to view top hot nodes.</div>' +
        '</div>' +
      '</div>' +
      '<div class="card" style="margin-top:16px;background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:12px;">' +
          '<div style="display:flex;align-items:center;gap:10px;">' +
            '<div style="width:36px;height:36px;border-radius:8px;background:rgba(14,165,233,0.15);color:#0ea5e9;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-tachometer"></i></div>' +
            '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">RoCE MTU 9000 & Jumbo Frame Synthetic Benchmark</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">High-speed datapath throughput, MTU 9000 packet validation, and inter-satellite latency probe</div></div>' +
          '</div>' +
          '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">' +
            '<input type="text" id="roce-bench-ip" value="192.168.1.22" placeholder="Satellite IP" style="padding:6px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12.5px;width:140px;">' +
            '<select id="roce-bench-mtu" style="padding:6px 10px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12.5px;">' +
              '<option value="9000">MTU 9000 (Jumbo Frames)</option>' +
              '<option value="1500">MTU 1500 (Standard)</option>' +
            '</select>' +
            '<button type="button" id="btn-run-roce-bench" class="btn btn-primary" style="background:#0ea5e9;border:none;color:#fff;font-weight:600;font-size:12.5px;"><i class="fa fa-bolt"></i> Run Benchmark</button>' +
          '</div>' +
        '</div>' +
        '<div id="term-roce-bench" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;max-height:220px;overflow-y:auto;"></div>' +
      '</div>';
    panesContainer.appendChild(pHealth);

    // ── Pane 1.5: Templates Marketplace ──
    var pTemplates = document.createElement('div');
    pTemplates.id = 'pane-templates';
    pTemplates.style.display = 'none';
    pTemplates.innerHTML = 
      '<div style="display:flex;flex-direction:column;gap:16px;">' +
        '<div style="display:flex;flex-direction:column;gap:12px;background:var(--pnq-surface,#1e293b);padding:16px 20px;border-radius:10px;border:1px solid var(--pnq-border,rgba(255,255,255,0.08));">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#0284c7,#7c3aed);color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 12px rgba(2,132,199,0.3);"><i class="fa fa-th-large"></i></div>' +
              '<div>' +
                '<div style="font-weight:700;font-size:17px;color:#f1f5f9;">Lab Templates & Universal Converter Marketplace</div>' +
                '<div style="font-size:12.5px;color:var(--pnq-text-muted,#94a3b8);">Browse, convert, filter and auto-fix CML2, GNS3, and EVE-NG topologies into native PNetLab v8</div>' +
              '</div>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">' +
              '<div style="position:relative;display:flex;align-items:center;">' +
                '<i class="fa fa-search" style="position:absolute;left:10px;color:#64748b;font-size:12px;"></i>' +
                '<input type="text" id="tmpl-search" placeholder="Search by name, format (cml2, gns3, eve), protocol..." style="padding:7px 12px 7px 30px;background:rgba(0,0,0,0.35);border:1px solid var(--pnq-border,rgba(255,255,255,0.12));border-radius:6px;color:#fff;font-size:12.5px;width:320px;">' +
                '<button type="button" id="btn-tmpl-search-clear" style="position:absolute;right:8px;background:none;border:none;color:#94a3b8;cursor:pointer;font-size:12px;display:none;">✕</button>' +
              '</div>' +
              '<button type="button" id="btn-tmpl-refresh" class="btn btn-ghost" style="font-size:12.5px;"><i class="fa fa-refresh"></i> Refresh</button>' +
            '</div>' +
          '</div>' +
          '<!-- Universal Lab Auto-Fixer Toolbar -->' +
          '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;padding:12px 14px;background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.25);border-radius:8px;">' +
            '<div style="display:flex;align-items:center;gap:8px;">' +
              '<i class="fa fa-wrench" style="color:#10b981;font-size:16px;"></i>' +
              '<span style="font-weight:700;font-size:13px;color:#f1f5f9;">Universal Lab Auto-Fixer:</span>' +
              '<span style="font-size:12px;color:#94a3b8;">Repairs "Network ID is not valid", "Not support device" (iol-l2 → iol), and generates missing XML bridges.</span>' +
            '</div>' +
            '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">' +
              '<input type="text" id="az-fix-lab-path" value="/opt/unetlab/labs/Azam-Templates/ccna/ccna-routing.unl" placeholder="/opt/unetlab/labs/.../lab.unl" style="padding:6px 12px;background:rgba(0,0,0,0.35);border:1px solid var(--pnq-border,rgba(255,255,255,0.12));border-radius:6px;color:#fff;font-size:12px;width:310px;">' +
              '<button type="button" id="btn-fix-lab-run" class="btn btn-primary btn-sm" style="background:#10b981;border:none;color:#fff;font-weight:600;display:inline-flex;align-items:center;gap:6px;"><i class="fa fa-magic"></i> Auto-Fix Lab Now</button>' +
            '</div>' +
          '</div>' +
          '<!-- Repository Selector & Explorer -->' +
          '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding-top:10px;border-top:1px solid rgba(255,255,255,0.06);">' +
            '<span style="font-size:12px;font-weight:700;color:#38bdf8;display:flex;align-items:center;gap:6px;"><i class="fa fa-github"></i> Pull From Repository:</span>' +
            '<select id="az-tmpl-repo-select" style="padding:6px 12px;background:rgba(0,0,0,0.35);border:1px solid var(--pnq-border,rgba(255,255,255,0.12));border-radius:6px;color:#fff;font-size:12.5px;">' +
              '<option value="cml-community">Cisco DevNet CML Community Labs (CML 2.x YAML)</option>' +
              '<option value="cml-labs">Renato CML Enterprise & CCNA Labs (CML 2.x YAML)</option>' +
              '<option value="eve-ng-community">Cisco DevNet & Community EVE-NG Labs (EVE-NG UNL)</option>' +
              '<option value="gns3-community">GNS3 Community Enterprise Labs (GNS3 JSON)</option>' +
              '<option value="local-offline">Azam-Basha Built-in Offline Library (Native UNL)</option>' +
              '<option value="custom">Custom GitHub Repository URL...</option>' +
            '</select>' +
            '<input type="text" id="az-tmpl-custom-url" placeholder="https://github.com/owner/repo" style="display:none;padding:6px 12px;background:rgba(0,0,0,0.35);border:1px solid var(--pnq-border,rgba(255,255,255,0.12));border-radius:6px;color:#fff;font-size:12.5px;width:260px;">' +
            '<button type="button" id="btn-tmpl-browse-repo" class="btn btn-primary btn-sm" style="background:#0284c7;border:none;color:#fff;font-weight:600;display:inline-flex;align-items:center;gap:6px;"><i class="fa fa-search"></i> Browse Repo Labs</button>' +
          '</div>' +
          '<!-- Discovered Repo Labs Drawer -->' +
          '<div id="az-repo-discover-box" style="display:none;background:rgba(0,0,0,0.25);border:1px solid rgba(14,165,233,0.3);border-radius:8px;padding:12px;margin-top:6px;">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
              '<span id="az-repo-discover-title" style="font-weight:700;font-size:13px;color:#38bdf8;">Discovered Repository Labs</span>' +
              '<button type="button" id="btn-close-discover" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:13px;">✕ Close</button>' +
            '</div>' +
            '<div id="az-repo-discover-list" style="display:flex;flex-direction:column;gap:6px;max-height:260px;overflow-y:auto;"></div>' +
          '</div>' +
        '</div>' +
        '<!-- 1. Format Filters (CML2, EVE-NG, GNS3, PNetLab) -->' +
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">' +
          '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' +
            '<span style="font-size:11px;font-weight:800;color:#94a3b8;letter-spacing:0.5px;text-transform:uppercase;">FORMAT FILTER:</span>' +
            '<div id="tmpl-format-chips" style="display:flex;gap:6px;overflow-x:auto;padding-bottom:2px;"></div>' +
          '</div>' +
          '<span id="tmpl-count-badge" style="font-size:11.5px;color:#38bdf8;font-weight:700;padding:3px 10px;background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.25);border-radius:12px;">Topologies</span>' +
        '</div>' +
        '<!-- 2. Track & Category Filters -->' +
        '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' +
          '<span style="font-size:11px;font-weight:800;color:#64748b;letter-spacing:0.5px;text-transform:uppercase;">TRACK FILTER:</span>' +
          '<div id="tmpl-category-chips" style="display:flex;gap:6px;overflow-x:auto;padding-bottom:2px;"></div>' +
        '</div>' +
        '<div id="tmpl-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:16px;"></div>' +
        '<div id="term-templates" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;max-height:260px;overflow-y:auto;"></div>' +
      '</div>';
    panesContainer.appendChild(pTemplates);

    // ── Pane 2: Exam & Quiz Grader ──
    var pGrader = document.createElement('div');
    pGrader.id = 'pane-grader';
    pGrader.style.display = 'none';
    pGrader.innerHTML = 
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:12px;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:36px;height:36px;border-radius:8px;background:rgba(16,185,129,0.15);color:#10b981;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-graduation-cap"></i></div>' +
              '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Automated Lab Exam Grader</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Test checkpoints and generate instant pass/fail scorecards</div></div>' +
            '</div>' +
            '<div id="grader-lab-badge" style="display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:20px;background:rgba(16,185,129,0.1);color:#10b981;font-size:11px;font-weight:700;border:1px solid rgba(16,185,129,0.25);">' +
              '<i class="fa fa-folder-open"></i> <span id="grader-total-count">Loading labs...</span>' +
            '</div>' +
          '</div>' +
          '<div style="position:relative;">' +
            '<input type="text" id="grader-lab-search" placeholder="🔍 Search all labs by name, topic (OSPF, BGP, CCNA)..." style="width:100%;padding:8px 12px;padding-right:32px;background:rgba(0,0,0,0.3);border:1px solid var(--pnq-border,rgba(255,255,255,0.12));border-radius:6px;color:#fff;font-size:12.5px;">' +
            '<button type="button" id="btn-grader-refresh-labs" title="Refresh Labs List" style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;color:#94a3b8;cursor:pointer;font-size:13px;"><i class="fa fa-refresh"></i></button>' +
          '</div>' +
          '<div style="font-size:11px;font-weight:700;color:#94a3b8;letter-spacing:0.5px;text-transform:uppercase;margin-top:2px;">SELECT TARGET LAB (FROM LABS SECTION):</div>' +
          '<div id="grader-lab-tree" style="max-height:220px;overflow-y:auto;background:rgba(5,8,17,0.6);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:8px;display:flex;flex-direction:column;gap:6px;">' +
            '<div style="text-align:center;color:#64748b;padding:16px;font-size:12px;"><i class="fa fa-spinner fa-spin"></i> Loading labs from /opt/unetlab/labs...</div>' +
          '</div>' +
          '<div id="grader-selected-preview" style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.25);border-radius:8px;padding:10px 12px;display:flex;align-items:center;justify-content:space-between;gap:10px;">' +
            '<div style="display:flex;align-items:center;gap:10px;overflow:hidden;">' +
              '<div style="width:28px;height:28px;border-radius:6px;background:rgba(16,185,129,0.2);color:#10b981;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;"><i class="fa fa-check"></i></div>' +
              '<div style="overflow:hidden;">' +
                '<div id="grader-selected-title" style="font-weight:600;font-size:13px;color:#f1f5f9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">No lab selected</div>' +
                '<div id="grader-selected-path" style="font-size:11px;color:#94a3b8;font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Please choose a lab from the list above</div>' +
              '</div>' +
            '</div>' +
            '<div id="grader-selected-nodes" style="padding:2px 8px;border-radius:4px;background:rgba(56,189,248,0.15);color:#38bdf8;font-size:11px;font-weight:700;white-space:nowrap;">- Nodes</div>' +
          '</div>' +
          '<input type="hidden" id="grader-selected-lab-path" value="">' +
          '<button type="button" id="btn-run-grade" class="btn btn-primary" style="background:#10b981;border-color:#10b981;color:#fff;padding:10px 16px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:8px;"><i class="fa fa-check-circle"></i> Grade Selected Lab</button>' +
        '</div>' +
        '<div id="term-grader" style="display:block;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;font-family:monospace;font-size:12.5px;min-height:380px;max-height:520px;overflow-y:auto;color:#38bdf8;">' +
          '<div style="color:#64748b;">// Ready to evaluate lab. Select any lab from the library and click "Grade Selected Lab".</div>' +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pGrader);

    // ── Pane 3: Web Wireshark Sniffer ──
    var pSniffer = document.createElement('div');
    pSniffer.id = 'pane-sniffer';
    pSniffer.style.display = 'none';
    pSniffer.innerHTML = 
      '<div style="display:flex;flex-direction:column;gap:16px;">' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">' +
            '<div style="display:flex;align-items:center;gap:12px;">' +
              '<div style="width:38px;height:38px;border-radius:8px;background:rgba(56,189,248,0.15);color:#38bdf8;display:flex;align-items:center;justify-content:center;font-size:17px;"><i class="fa fa-rss"></i></div>' +
              '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">In-Browser Web Wireshark & Protocol Dissector</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Capture and dissect live packets on physical or virtual bridge interfaces</div></div>' +
            '</div>' +
            '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">' +
              '<select id="sniff-iface" style="padding:7px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12.5px;">' +
                '<option value="eth0">eth0 (Management)</option>' +
                '<option value="pnet0">pnet0 (Bridge)</option>' +
              '</select>' +
              '<button type="button" id="btn-start-sniff" class="btn btn-primary" style="background:#0284c7;border-color:#0284c7;color:#fff;font-weight:600;display:inline-flex;align-items:center;gap:6px;"><i class="fa fa-play"></i> Start Live Capture</button>' +
              '<button type="button" id="btn-stop-sniff" class="btn btn-danger" style="background:#ef4444;border-color:#ef4444;color:#fff;font-weight:600;display:inline-flex;align-items:center;gap:6px;opacity:0.4;cursor:not-allowed;" disabled><i class="fa fa-stop"></i> Stop Capture</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div id="term-sniffer" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;font-family:monospace;font-size:12px;max-height:360px;overflow-y:auto;color:#e2e8f0;"></div>' +
      '</div>';
    panesContainer.appendChild(pSniffer);

    // ── Pane 4: Cloud & LAN Transit ──
    var pBridge = document.createElement('div');
    pBridge.id = 'pane-bridge';
    pBridge.style.display = 'none';
    pBridge.innerHTML = 
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">' +
        createToolCard('bridge-status', 'azam-cloud-bridge', 'Transit Gateway & WireGuard Cloud Status', 'Inspects real-LAN bridging, outbound NAT masquerading, and WireGuard Cloud VPC tunnels.', 'fa-globe', '#0ea5e9', 'term-bridge', [
          { label: 'Enable Outbound NAT', tool: 'bridge-enable-nat' },
          { label: 'Disable NAT', tool: 'bridge-disable-nat' },
          { label: 'WireGuard UP', tool: 'bridge-wireguard-up' }
        ]) +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="font-weight:600;font-size:15px;margin-bottom:10px;"><i class="fa fa-info-circle"></i> Real-LAN Transit Bridging Guide</div>' +
          '<div style="font-size:12.5px;color:var(--pnq-text-muted,#94a3b8);line-height:1.6;">' +
            '• <b>LAN Bridging:</b> Connect any lab node interface to network type <i>Cloud0 (pnet0)</i> to assign IPs directly on your 192.168.1.0/24 subnet.<br>' +
            '• <b>Internet Access:</b> Outbound NAT translates lab subnets (10.0.0.0/8, 172.16.0.0/12) through eth0 so routers can update software and reach internet NTP/DNS.<br>' +
            '• <b>WireGuard:</b> Tunnels lab traffic directly to AWS VPC or Azure VNet over encrypted UDP.' +
          '</div>' +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pBridge);

    // ── Pane 5: Diagram & Doc Exporter ──
    var pDoc = document.createElement('div');
    pDoc.id = 'pane-doc';
    pDoc.style.display = 'none';
    pDoc.innerHTML = 
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">' +
            '<div style="width:36px;height:36px;border-radius:8px;background:rgba(99,102,241,0.15);color:#818cf8;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-file-code-o"></i></div>' +
            '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Topology Documentation & Diagram Exporter</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Export professional diagrams to Draw.io, Mermaid, and Markdown</div></div>' +
          '</div>' +
          '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:14px;">' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Export Format:</label>' +
              '<select id="doc-format-select" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
                '<option value="mermaid">Mermaid.js Diagram (Markdown / GitHub)</option>' +
                '<option value="drawio">Draw.io XML (diagrams.net Import)</option>' +
                '<option value="matrix">Cable Patch & IP Allocation Matrix</option>' +
                '<option value="all">Full Documentation Package (All)</option>' +
              '</select>' +
            '</div>' +
          '</div>' +
          '<button type="button" id="btn-export-doc" class="btn btn-primary" style="background:#6366f1;border-color:#6366f1;color:#fff;"><i class="fa fa-download"></i> Generate & View Documentation</button>' +
        '</div>' +
        '<div id="term-doc" style="display:block;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;font-family:monospace;font-size:12.5px;min-height:300px;max-height:480px;overflow-y:auto;color:#38bdf8;">' +
          '<div style="color:#64748b;">// Select format and click "Generate" to preview diagrams or cabling matrices.</div>' +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pDoc);

    // ── Pane 7: AI Lab Copilot ──
    var pAi = document.createElement('div');
    pAi.id = 'pane-ai';
    pAi.style.display = 'none';
    pAi.innerHTML = 
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
        '<div style="display:flex;flex-direction:column;gap:16px;">' +
          '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">' +
              '<div style="width:36px;height:36px;border-radius:8px;background:rgba(124,58,237,0.15);color:#a78bfa;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-magic"></i></div>' +
              '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Network Config Generator</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Generate production-ready syntax using AI Copilot or built-in templates</div></div>' +
            '</div>' +
            '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:14px;">' +
              '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Built-in Template:</label>' +
                '<select id="ai-tmpl-select" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
                  '<option value="cisco_ospf">Cisco IOS-XE — OSPF Multi-Area + MD5 Auth</option>' +
                  '<option value="cisco_bgp">Cisco IOS-XE — eBGP Dual-Homed + BFD</option>' +
                  '<option value="arista_evpn">Arista EOS — VXLAN EVPN Anycast Gateway</option>' +
                  '<option value="juniper_bgp">Juniper Junos — BGP Peering + Import/Export</option>' +
                  '<option value="frr_ospf">Linux FRRouting — OSPF & BGP Dual-Stack</option>' +
                '</select>' +
              '</div>' +
              '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Or Custom AI Prompt:</label>' +
                '<input type="text" id="ai-custom-prompt" placeholder="e.g. Generate Cisco 8000v BGP EVPN with VXLAN VNI 10010" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
              '</div>' +
            '</div>' +
            '<button type="button" id="btn-ai-gen" class="btn btn-primary" style="background:#7c3aed;border-color:#7c3aed;color:#fff;"><i class="fa fa-code"></i> Generate Configuration</button>' +
          '</div>' +
          '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">' +
              '<div style="width:36px;height:36px;border-radius:8px;background:rgba(234,179,8,0.15);color:#eab308;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-stethoscope"></i></div>' +
              '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Routing Diagnostics Analyzer</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Paste show output or syslog errors for root-cause analysis</div></div>' +
            '</div>' +
            '<textarea id="ai-diag-log" rows="4" placeholder="Paste show ip route, show ip ospf neighbor, or BGP flap logs..." style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12px;font-family:monospace;margin-bottom:12px;"></textarea>' +
            '<button type="button" id="btn-ai-diag" class="btn btn-ghost"><i class="fa fa-search"></i> Diagnose Issue</button>' +
          '</div>' +
        '</div>' +
        '<div id="term-ai" style="display:block;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;font-family:monospace;font-size:12.5px;min-height:360px;max-height:560px;overflow-y:auto;color:#38bdf8;">' +
          '<div style="color:#64748b;">// AI Copilot Output Terminal ready.</div>' +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pAi);

    // ── Pane 8: Config Diff & Rollback ──
    var pDiff = document.createElement('div');
    pDiff.id = 'pane-diff';
    pDiff.style.display = 'none';
    pDiff.innerHTML = 
      '<div style="display:flex;flex-direction:column;gap:16px;">' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">' +
            '<div style="display:flex;align-items:center;gap:12px;">' +
              '<div style="width:38px;height:38px;border-radius:8px;background:rgba(14,165,233,0.15);color:#0ea5e9;display:flex;align-items:center;justify-content:center;font-size:17px;"><i class="fa fa-history"></i></div>' +
              '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Device Configuration History & Visual Diff</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Capture and compare running-configs before and after changes</div></div>' +
            '</div>' +
            '<div style="display:flex;gap:10px;">' +
              '<button type="button" id="btn-diff-snap" class="btn btn-primary" style="background:#0ea5e9;border-color:#0ea5e9;color:#fff;"><i class="fa fa-camera"></i> Snapshot Running-Configs</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div id="term-diff" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;font-family:monospace;font-size:12.5px;max-height:360px;overflow-y:auto;color:#e2e8f0;"></div>' +
      '</div>';
    panesContainer.appendChild(pDiff);

    // ── Pane 9: Ping Mesh & Traffic Generator ──
    var pMesh = document.createElement('div');
    pMesh.id = 'pane-mesh';
    pMesh.style.display = 'none';
    pMesh.innerHTML = 
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">' +
            '<div style="font-weight:600;font-size:15px;"><i class="fa fa-table"></i> Data Plane Reachability Matrix</div>' +
            '<button type="button" id="btn-mesh-sweep" class="btn btn-primary btn-sm"><i class="fa fa-refresh"></i> Run Mesh Sweep</button>' +
          '</div>' +
          '<div id="az-mesh-table" style="font-size:13px;color:var(--pnq-text-muted,#94a3b8);">Click "Run Mesh Sweep" to test IP reachability.</div>' +
        '</div>' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="font-weight:600;font-size:15px;margin-bottom:12px;"><i class="fa fa-bolt"></i> Synthetic Link Traffic Generator</div>' +
          '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:14px;">' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Target Host IP:</label><input type="text" id="traffic-target" value="192.168.1.22" style="width:100%;padding:7px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12.5px;"></div>' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Burst Rate (Mbps):</label><input type="number" id="traffic-rate" value="10" min="1" max="1000" style="width:100%;padding:7px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12.5px;"></div>' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Duration (Seconds):</label><input type="number" id="traffic-dur" value="5" min="1" max="60" style="width:100%;padding:7px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12.5px;"></div>' +
          '</div>' +
          '<button type="button" id="btn-traffic-start" class="btn btn-primary" style="background:#10b981;border-color:#10b981;color:#fff;"><i class="fa fa-play"></i> Inject Traffic Burst</button>' +
          '<div id="term-traffic" style="display:none;margin-top:12px;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;max-height:160px;overflow-y:auto;"></div>' +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pMesh);

    // ── Pane 10: Scheduler & Quotas ──
    var pSched = document.createElement('div');
    pSched.id = 'pane-scheduler';
    pSched.style.display = 'none';
    pSched.innerHTML = 
      '<div style="display:flex;flex-direction:column;gap:16px;">' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">' +
          createToolCard('scheduler-status', 'azam-scheduler', 'Resource Quota & Curfew Watchdog', 'Inspects idle timeout settings, nightly power-saver curfews, and role-based node limits.', 'fa-clock-o', '#f59e0b', 'term-sched', [
            { label: 'Stop Idle Labs Now', tool: 'scheduler-stop-idle' },
            { label: 'Audit Compliance', tool: 'scheduler-check' }
          ]) +
        '</div>' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">' +
            '<div style="width:36px;height:36px;border-radius:8px;background:rgba(245,158,11,0.15);color:#f59e0b;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-sliders"></i></div>' +
            '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Idle Auto-Shutdown & Tenant Capacity Policy</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Configure autonomous lab shutdown timer, max active nodes per student, and nightly power-saver curfew</div></div>' +
          '</div>' +
          '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-bottom:14px;">' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Idle Auto-Shutdown (Minutes):</label>' +
              '<input type="number" id="sched-idle-timeout" value="60" min="15" max="720" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
            '</div>' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Max Active Nodes Per Tenant / Student:</label>' +
              '<input type="number" id="sched-max-nodes" value="12" min="1" max="64" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
            '</div>' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Curfew Start (HH:MM):</label>' +
              '<input type="text" id="sched-curfew-start" value="23:00" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
            '</div>' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Curfew End (HH:MM):</label>' +
              '<input type="text" id="sched-curfew-end" value="07:00" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
            '</div>' +
          '</div>' +
          '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">' +
            '<button type="button" id="btn-sched-save" class="btn btn-primary" style="background:#f59e0b;border-color:#f59e0b;color:#000;font-weight:700;"><i class="fa fa-save"></i> Save & Apply Policy</button>' +
            '<button type="button" id="btn-sched-stop-now" class="btn btn-danger" style="background:#dc2626;border:none;color:#fff;font-weight:600;"><i class="fa fa-power-off"></i> Stop Idle Labs Now</button>' +
          '</div>' +
          '<div id="term-sched-policy" style="display:none;margin-top:12px;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;"></div>' +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pSched);

    // ── Pane 11: Cloud & NAS Backup ──
    var pCloud = document.createElement('div');
    pCloud.id = 'pane-cloud';
    pCloud.style.display = 'none';
    pCloud.innerHTML = 
      '<div style="display:flex;flex-direction:column;gap:16px;">' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">' +
          createToolCard('cloud-sync', 'azam-cloud-backup', 'Offsite Cloud & NAS Sync', 'Synchronizes local snapshots to remote SFTP servers, AWS S3, or Network NAS.', 'fa-cloud-upload', '#0284c7', 'term-cloud', [
            { label: 'Sync Status', tool: 'cloud-status' },
            { label: 'List Remote Files', tool: 'cloud-list' }
          ]) +
          createToolCard('backup', 'azam-backup', 'Instant Local Lab Snapshot', 'Compresses all lab .unl topologies, device startup configs, and database records.', 'fa-archive', '#8b5cf6', 'term-backup', [
            { label: 'List Local Backups', tool: 'backup-list' }
          ]) +
          '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:16px;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:36px;height:36px;border-radius:8px;background:rgba(14,165,233,0.15);color:#0ea5e9;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-cubes"></i></div>' +
              '<div><div style="font-weight:600;font-size:14px;color:#f1f5f9;">100% Offline Air-Gapped Installer Bundle</div><div style="font-size:11.5px;color:var(--pnq-text-muted,#94a3b8);">Packages all deb packages, templates & offline scripts into standalone tarball</div></div>' +
            '</div>' +
            '<div style="margin-top:12px;"><button type="button" class="btn btn-primary btn-sm" style="width:100%;background:linear-gradient(135deg,#0284c7,#2563eb);border:none;color:#fff;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px;" onclick="window.__azGenerateAirgap(this)"><i class="fa fa-archive"></i> Generate Air-Gapped Bundle (azam-airgap-pack)</button></div>' +
          '</div>' +
        '</div>' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:14px;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:36px;height:36px;border-radius:8px;background:rgba(139,92,246,0.15);color:#8b5cf6;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-hdd-o"></i></div>' +
              '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Local Lab Archives & 1-Click Restore</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Saved in /opt/azambasha/backups/ and ready for rollback</div></div>' +
            '</div>' +
            '<button type="button" id="btn-backup-refresh" class="btn btn-ghost" style="font-size:12px;"><i class="fa fa-refresh"></i> Refresh Archives</button>' +
          '</div>' +
          '<div id="az-backups-table" style="font-size:13px;color:var(--pnq-text-muted,#94a3b8);">Reading backup directory…</div>' +
        '</div>' +
      '</div>';
    panesContainer.appendChild(pCloud);

    // ── Pane 12: Security & WhatsApp ──
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
              '<div style="width:36px;height:36px;border-radius:8px;background:rgba(37,211,102,0.15);display:flex;align-items:center;justify-content:center;color:#25d366;font-size:18px;"><i class="fa fa-whatsapp"></i></div>' +
              '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">WhatsApp & Webhook Alert Engine</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Dispatches critical cluster alerts & scan reports straight to your phone</div></div>' +
            '</div>' +
            '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:14px;">' +
              '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">WhatsApp Phone (with country code):</label><input type="text" id="wa-phone" placeholder="e.g. 919876543210" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;"></div>' +
              '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">CallMeBot API Key (Free):</label><input type="password" id="wa-key" placeholder="Enter API key" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;"></div>' +
              '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Custom Alert Message:</label><input type="text" id="wa-msg" value="⚡ Hello Azam! Test alert from PNetLab Master Cluster (192.168.1.23)" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;"></div>' +
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

    // ── Pane 13: Canvas Accelerators ──
    var pCanvas = document.createElement('div');
    pCanvas.id = 'pane-canvas';
    pCanvas.style.display = 'none';
    pCanvas.innerHTML = 
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;">' +
        createFeatureCard('Node Spotlight Search', 'Instant canvas navigation across large topologies with keyboard shortcut.', 'Ctrl + K / ⌘ + K', 'fa-search', '#38bdf8', 'Jump directly to any router, switch, or VM. Auto-focuses and pans viewport.') +
        createFeatureCard('Smart Alignment & Distribution', 'One-click horizontal, vertical, and grid distribution toolbar.', 'Toolbar in Lab', 'fa-align-left', '#818cf8', 'Aligns selected nodes with clean mathematical spacing.') +
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
    loadMesh();
    loadTemplates();
    loadPerf();
    loadGraderLabs();
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

    ['health', 'templates', 'grader', 'sniffer', 'bridge', 'doc', 'ai', 'diff', 'mesh', 'scheduler', 'cloud', 'security', 'canvas'].forEach(function (id) {
      var p = document.getElementById('pane-' + id);
      if (p) p.style.display = id === tabId ? 'block' : 'none';
    });

    if (tabId === 'grader') {
      loadGraderLabs();
    }
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
        }

        runTool(tool, params, btn, term);
      };
    });

    // Exam Grader Run
    var btnGrade = container.querySelector('#btn-run-grade');
    if (btnGrade) {
      btnGrade.onclick = function () {
        var lab = (document.getElementById('grader-selected-lab-path') ? document.getElementById('grader-selected-lab-path').value.trim() : '');
        if (!lab) {
          App.toast('Please select a target lab to grade from the list above', 'warn');
          return;
        }
        runTool('grader-run', { lab: lab }, btnGrade, 'term-grader');
      };
    }

    // Grader Search & Refresh
    var labSearch = container.querySelector('#grader-lab-search');
    if (labSearch) {
      labSearch.oninput = function () {
        if (_graderLabsCache) renderGraderLabs(_graderLabsCache);
      };
    }
    var btnGraderRefresh = container.querySelector('#btn-grader-refresh-labs');
    if (btnGraderRefresh) {
      btnGraderRefresh.onclick = function () {
        loadGraderLabs(true);
      };
    }

    // ── Sniffer Controller (Continuous Live Capture with Start & Stop) ──
    var btnStartSniff = container.querySelector('#btn-start-sniff');
    var btnStopSniff = container.querySelector('#btn-stop-sniff');
    var ifaceSelect = container.querySelector('#sniff-iface');
    var activeSniffAbort = null;
    var isSniffing = false;

    // Dynamically load available interfaces if possible
    fetch(API_BASE + '/sniffer/interfaces')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.interfaces && data.interfaces.length > 0 && ifaceSelect) {
          var currentVal = ifaceSelect.value;
          ifaceSelect.innerHTML = '';
          data.interfaces.forEach(function (item) {
            var opt = document.createElement('option');
            opt.value = item.interface;
            opt.textContent = item.interface + (item.status ? ' (' + item.status + ')' : '');
            ifaceSelect.appendChild(opt);
          });
          if (currentVal) ifaceSelect.value = currentVal;
        }
      })
      .catch(function () {});

    function setSnifferState(capturing) {
      isSniffing = capturing;
      if (capturing) {
        if (btnStartSniff) {
          btnStartSniff.disabled = true;
          btnStartSniff.style.opacity = '0.65';
          btnStartSniff.innerHTML = '<i class="fa fa-circle" style="color:#22c55e;"></i> Capturing...';
        }
        if (btnStopSniff) {
          btnStopSniff.disabled = false;
          btnStopSniff.style.opacity = '1';
          btnStopSniff.style.cursor = 'pointer';
          btnStopSniff.innerHTML = '<i class="fa fa-stop"></i> Stop Capture';
        }
        if (ifaceSelect) ifaceSelect.disabled = true;
      } else {
        if (btnStartSniff) {
          btnStartSniff.disabled = false;
          btnStartSniff.style.opacity = '1';
          btnStartSniff.innerHTML = '<i class="fa fa-play"></i> Start Live Capture';
        }
        if (btnStopSniff) {
          btnStopSniff.disabled = true;
          btnStopSniff.style.opacity = '0.4';
          btnStopSniff.style.cursor = 'not-allowed';
          btnStopSniff.innerHTML = '<i class="fa fa-stop"></i> Stop Capture';
        }
        if (ifaceSelect) ifaceSelect.disabled = false;
      }
    }

    if (btnStartSniff) {
      btnStartSniff.onclick = function () {
        if (isSniffing) return;
        var iface = ifaceSelect ? ifaceSelect.value : 'eth0';
        var term = document.getElementById('term-sniffer');
        if (!term) return;

        setSnifferState(true);
        term.style.display = 'block';
        term.innerHTML = 
          '<div style="display:flex;align-items:center;justify-content:space-between;padding-bottom:8px;margin-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.08);flex-wrap:wrap;gap:8px;">' +
            '<div style="display:flex;align-items:center;gap:8px;">' +
              '<div style="display:flex;gap:6px;">' +
                '<span style="width:10px;height:10px;border-radius:50%;background:#ef4444;display:inline-block;"></span>' +
                '<span style="width:10px;height:10px;border-radius:50%;background:#eab308;display:inline-block;"></span>' +
                '<span style="width:10px;height:10px;border-radius:50%;background:#22c55e;display:inline-block;"></span>' +
              '</div>' +
              '<span style="display:inline-flex;align-items:center;gap:6px;background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);padding:2px 8px;border-radius:12px;font-size:11px;color:#4ade80;font-weight:600;"><i class="fa fa-circle" style="font-size:8px;"></i> LIVE CAPTURE</span>' +
              '<span style="font-size:11px;color:#94a3b8;font-family:monospace;">iface: <b>' + iface + '</b></span>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:12px;">' +
              '<span id="sniff-pkt-badge" style="font-size:11.5px;color:#38bdf8;font-family:monospace;font-weight:600;">0 packets captured</span>' +
              '<span id="sniff-pcap-link"></span>' +
            '</div>' +
          '</div>' +
          '<div id="term-sniffer-lines" style="display:flex;flex-direction:column;gap:2px;"></div>';

        var linesContainer = document.getElementById('term-sniffer-lines');
        var pktBadge = document.getElementById('sniff-pkt-badge');
        var pcapSlot = document.getElementById('sniff-pcap-link');
        var packetCount = 0;
        var savedPcapFile = null;

        activeSniffAbort = new AbortController();

        fetch(API_BASE + '/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: 'sniffer-capture',
            params: { interface: iface, continuous: true }
          }),
          signal: activeSniffAbort.signal
        }).then(function (res) {
          if (!res.body) throw new Error('No response body stream');
          var reader = res.body.getReader();
          var decoder = new TextDecoder();
          var buf = '';

          function pump() {
            reader.read().then(function (r) {
              if (r.done) {
                setSnifferState(false);
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

                    if (txt.includes(' -> ') && (txt.includes('TCP') || txt.includes('UDP') || txt.includes('OSPF') || txt.includes('BGP') || txt.includes('ICMP') || txt.includes('ARP') || txt.includes('ETH'))) {
                      packetCount++;
                      if (pktBadge) pktBadge.textContent = packetCount + ' packets captured';
                    }

                    if (txt.includes('File saved:')) {
                      var m = txt.match(/File saved:\s*(\S+\.pcap)/i);
                      if (m && m[1]) {
                        savedPcapFile = m[1].split('/').pop();
                        if (pcapSlot) {
                          pcapSlot.innerHTML = '<a href="' + API_BASE + '/sniffer/download?file=' + encodeURIComponent(savedPcapFile) + '" target="_blank" download class="btn btn-xs btn-success" style="background:#10b981;border:none;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;text-decoration:none;display:inline-flex;align-items:center;gap:4px;"><i class="fa fa-download"></i> Download PCAP</a>';
                        }
                      }
                    }

                    if (linesContainer) {
                      var row = document.createElement('div');
                      row.style.cssText = 'white-space:pre-wrap;word-break:break-all;line-height:1.45;color:' + getLineColor(txt) + ';';
                      row.textContent = txt;
                      linesContainer.appendChild(row);
                      term.scrollTop = term.scrollHeight;
                    }
                  } else if (obj.type === 'done') {
                    var doneRow = document.createElement('div');
                    doneRow.style.cssText = 'border-top:1px solid rgba(255,255,255,0.08);margin-top:8px;padding-top:6px;font-size:11px;color:#64748b;';
                    doneRow.textContent = '── Capture stopped (status ' + obj.code + ') ──';
                    if (linesContainer) linesContainer.appendChild(doneRow);
                    term.scrollTop = term.scrollHeight;
                    setSnifferState(false);
                    App.toast('✔ Packet capture stopped successfully', 'ok');
                  }
                } catch (e) {}
              });
              pump();
            }).catch(function (err) {
              setSnifferState(false);
            });
          }
          pump();
        }).catch(function (err) {
          setSnifferState(false);
          if (linesContainer) {
            var errDiv = document.createElement('div');
            errDiv.style.color = '#f87171';
            errDiv.textContent = 'Capture error: ' + err.message;
            linesContainer.appendChild(errDiv);
          }
        });
      };
    }

    if (btnStopSniff) {
      btnStopSniff.onclick = function () {
        if (!isSniffing) return;
        btnStopSniff.disabled = true;
        btnStopSniff.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Stopping...';

        fetch(API_BASE + '/sniffer/stop', { method: 'POST' })
          .then(function (r) { return r.json(); })
          .then(function () {
            setTimeout(function () {
              if (isSniffing) {
                setSnifferState(false);
                if (activeSniffAbort) activeSniffAbort.abort();
              }
            }, 2500);
          })
          .catch(function () {
            setSnifferState(false);
            if (activeSniffAbort) activeSniffAbort.abort();
          });
      };
    }

    // Diagram Export
    var btnDoc = container.querySelector('#btn-export-doc');
    if (btnDoc) {
      btnDoc.onclick = function () {
        var fmt = document.getElementById('doc-format-select').value;
        runTool('topology-doc', { format: fmt }, btnDoc, 'term-doc');
      };
    }

    // AI Copilot Generate
    var btnAiGen = container.querySelector('#btn-ai-gen');
    if (btnAiGen) {
      btnAiGen.onclick = function () {
        var tmpl = document.getElementById('ai-tmpl-select').value;
        var custom = document.getElementById('ai-custom-prompt').value.trim();
        runTool('ai-generate', { template: tmpl, prompt: custom }, btnAiGen, 'term-ai');
      };
    }

    // AI Copilot Diagnose
    var btnAiDiag = container.querySelector('#btn-ai-diag');
    if (btnAiDiag) {
      btnAiDiag.onclick = function () {
        var log = document.getElementById('ai-diag-log').value.trim();
        runTool('ai-diagnose', { log: log }, btnAiDiag, 'term-ai');
      };
    }

    // Config Snapshot
    var btnDiffSnap = container.querySelector('#btn-diff-snap');
    if (btnDiffSnap) {
      btnDiffSnap.onclick = function () {
        runTool('config-snapshot', {}, btnDiffSnap, 'term-diff');
      };
    }

    // Ping Mesh Sweep
    var btnMesh = container.querySelector('#btn-mesh-sweep');
    if (btnMesh) {
      btnMesh.onclick = loadMesh;
    }

    // Traffic Generator
    var btnTraffic = container.querySelector('#btn-traffic-start');
    if (btnTraffic) {
      btnTraffic.onclick = function () {
        var tgt = document.getElementById('traffic-target').value.trim();
        var rate = document.getElementById('traffic-rate').value.trim();
        var dur = document.getElementById('traffic-dur').value.trim();
        runTool('mesh-traffic', { target: tgt, rate: rate, duration: dur }, btnTraffic, 'term-traffic');
      };
    }

    // WhatsApp Alert Save
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

    // WhatsApp Quick Test
    var btnWaQuick = container.querySelector('#btn-wa-quick');
    if (btnWaQuick) {
      btnWaQuick.onclick = function () {
        runTool('notify-test', {}, btnWaQuick, 'term-notify');
      };
    }

    // Hot-Node Profiler refresh & kill
    var btnPerfRef = container.querySelector('#btn-perf-refresh');
    if (btnPerfRef) {
      btnPerfRef.onclick = loadPerf;
    }
    var btnPerfKill = container.querySelector('#btn-perf-kill');
    if (btnPerfKill) {
      btnPerfKill.onclick = function () {
        runTool('perf-kill', {}, btnPerfKill, 'term-perf');
      };
    }

    // Templates refresh & search
    var btnTmplRef = container.querySelector('#btn-tmpl-refresh');
    if (btnTmplRef) {
      btnTmplRef.onclick = loadTemplates;
    }

    var searchTmpl = container.querySelector('#tmpl-search');
    var btnClearSearch = container.querySelector('#btn-tmpl-search-clear');

    function onSearchChange() {
      var q = (searchTmpl ? searchTmpl.value : '').toLowerCase().trim();
      activeSearchText = q;
      if (btnClearSearch) {
        btnClearSearch.style.display = q ? 'block' : 'none';
      }
      applyTemplateFilters();
    }

    if (searchTmpl) {
      searchTmpl.oninput = onSearchChange;
      searchTmpl.onkeyup = onSearchChange;
      searchTmpl.onchange = onSearchChange;
      searchTmpl.onpaste = function () {
        setTimeout(onSearchChange, 20);
      };
    }

    if (btnClearSearch && searchTmpl) {
      btnClearSearch.onclick = function () {
        searchTmpl.value = '';
        activeSearchText = '';
        btnClearSearch.style.display = 'none';
        searchTmpl.focus();
        applyTemplateFilters();
      };
    }

    // Universal Lab Auto-Fixer
    var btnFixLab = container.querySelector('#btn-fix-lab-run');
    var inputFixPath = container.querySelector('#az-fix-lab-path');
    if (btnFixLab && inputFixPath) {
      btnFixLab.onclick = function () {
        var filePath = inputFixPath.value.trim();
        if (!filePath) {
          App.toast('Please provide a valid lab .unl file path', 'warn');
          return;
        }
        runTool('templates-fix', { file: filePath }, btnFixLab, 'term-templates');
      };
    }

    // Repository Source Selector & Browse
    var repoSelect = container.querySelector('#az-tmpl-repo-select');
    var customUrlInput = container.querySelector('#az-tmpl-custom-url');
    var btnBrowseRepo = container.querySelector('#btn-tmpl-browse-repo');
    var btnCloseDiscover = container.querySelector('#btn-close-discover');
    var discoverBox = container.querySelector('#az-repo-discover-box');
    var discoverTitle = container.querySelector('#az-repo-discover-title');
    var discoverList = container.querySelector('#az-repo-discover-list');

    if (btnCloseDiscover && discoverBox) {
      btnCloseDiscover.onclick = function () {
        discoverBox.style.display = 'none';
      };
    }

    if (repoSelect && customUrlInput) {
      repoSelect.onchange = function () {
        customUrlInput.style.display = repoSelect.value === 'custom' ? 'inline-block' : 'none';
      };
    }

    if (btnBrowseRepo && repoSelect) {
      btnBrowseRepo.onclick = function () {
        var repoVal = repoSelect.value;
        if (repoVal === 'custom') {
          repoVal = (customUrlInput ? customUrlInput.value : '').trim();
          if (!repoVal) {
            App.toast('Please enter a valid GitHub repository URL', 'warn');
            return;
          }
        }
        if (discoverBox) {
          discoverBox.style.display = 'block';
          if (discoverTitle) discoverTitle.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Browsing repository: ' + repoVal + '…';
          if (discoverList) discoverList.innerHTML = '<div style="padding:16px;color:#94a3b8;text-align:center;"><i class="fa fa-spinner fa-spin" style="font-size:18px;color:#0ea5e9;"></i><br><span style="font-size:12.5px;margin-top:8px;display:inline-block;">Scanning repository for topologies (.yaml, .unl, .gns3project)…</span></div>';
        }
        btnBrowseRepo.disabled = true;

        fetch(API_BASE + '/templates/browse?repo=' + encodeURIComponent(repoVal))
          .then(function (r) { return r.json(); })
          .then(function (res) {
            btnBrowseRepo.disabled = false;
            if (!res.success && res.error) {
              if (discoverTitle) discoverTitle.innerHTML = '<span style="color:#f87171;"><i class="fa fa-exclamation-triangle"></i> Error browsing repository: ' + repoVal + '</span>';
              if (discoverList) discoverList.innerHTML = '<div style="padding:12px;color:#f87171;background:rgba(239,68,68,0.1);border-radius:6px;font-size:12px;">' + res.error + '</div>';
              return;
            }
            var labs = res.labs || [];
            if (discoverTitle) {
              discoverTitle.innerHTML = '<i class="fa fa-check-circle" style="color:#4ade80;"></i> ' + (res.repo_name || res.repo || repoVal) + ' — <span style="color:#fff;font-weight:800;">' + labs.length + ' Topologies Found</span>';
            }
            if (!labs.length) {
              if (discoverList) discoverList.innerHTML = '<div style="padding:16px;color:#94a3b8;text-align:center;font-size:12.5px;">No compatible lab files found in this repository.</div>';
              return;
            }
            // Render interactive cards for discovered labs
            var html = '';
            labs.forEach(function (lab) {
              var fmtColor = '#38bdf8';
              var fmtLabel = 'CML 2.x';
              if (lab.format === 'eve-ng') { fmtColor = '#a78bfa'; fmtLabel = 'EVE-NG'; }
              else if (lab.format === 'gns3') { fmtColor = '#f59e0b'; fmtLabel = 'GNS3'; }
              else if (lab.format === 'pnetlab-v8') { fmtColor = '#4ade80'; fmtLabel = 'PNetLab'; }

              html += '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:6px;">';
              html += '  <div style="flex:1;min-width:0;">';
              html += '    <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;flex-wrap:wrap;">';
              html += '      <span style="font-weight:700;color:#f1f5f9;font-size:13px;">' + (lab.title || lab.name) + '</span>';
              html += '      <span style="font-size:10px;font-weight:800;padding:2px 6px;border-radius:4px;background:' + fmtColor + '22;color:' + fmtColor + ';border:1px solid ' + fmtColor + '44;">' + fmtLabel + '</span>';
              if (lab.nodes) html += '      <span style="font-size:11px;color:#64748b;"><i class="fa fa-server"></i> ' + lab.nodes + ' nodes</span>';
              html += '    </div>';
              html += '    <div style="font-size:11.5px;color:#94a3b8;line-height:1.35;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + (lab.desc || lab.path || '') + '</div>';
              html += '  </div>';
              html += '  <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">';
              if (lab.source_url && lab.source_url !== 'local') {
                html += '    <a href="' + lab.source_url + '" target="_blank" class="btn btn-ghost btn-sm" style="font-size:11px;color:#94a3b8;padding:4px 8px;border:1px solid rgba(255,255,255,0.1);"><i class="fa fa-github"></i> Upstream</a>';
              }
              html += '    <button type="button" class="btn btn-primary btn-sm btn-action-pull-lab" style="background:#0284c7;border:none;color:#fff;font-weight:600;font-size:11.5px;padding:5px 12px;display:inline-flex;align-items:center;gap:6px;" ' +
                'data-repo="' + (res.repo || repoVal) + '" ' +
                'data-lab="' + lab.name + '" ' +
                'data-url="' + (lab.raw_url || '') + '" ' +
                'data-format="' + (lab.format || 'cml2') + '" ' +
                'data-cat="' + (lab.category || 'imported') + '">' +
                '<i class="fa fa-bolt"></i> Pull & Convert</button>';
              html += '  </div>';
              html += '</div>';
            });
            if (discoverList) discoverList.innerHTML = html;

            // Attach Pull & Convert click handlers
            discoverList.querySelectorAll('.btn-action-pull-lab').forEach(function (pBtn) {
              pBtn.onclick = function () {
                var lRepo = pBtn.getAttribute('data-repo');
                var lName = pBtn.getAttribute('data-lab');
                var lUrl = pBtn.getAttribute('data-url');
                var lFmt = pBtn.getAttribute('data-format');
                var lCat = pBtn.getAttribute('data-cat');

                pBtn.disabled = true;
                pBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Pulling…';

                fetch(API_BASE + '/templates/pull', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ repo: lRepo, lab: lName, raw_url: lUrl, format: lFmt, category: lCat })
                }).then(function (r) { return r.json(); }).then(function (pullRes) {
                  if (pullRes.success) {
                    pBtn.style.background = '#15803d';
                    pBtn.innerHTML = '<i class="fa fa-check"></i> Pulled & Deployed!';
                    App.toast('✔ Successfully pulled and deployed ' + lName + ' into PNetLab!', 'ok');
                    var fixInput = container.querySelector('#az-fix-lab-path');
                    if (fixInput && pullRes.unl_path) fixInput.value = pullRes.unl_path;
                    loadTemplates();
                  } else {
                    pBtn.disabled = false;
                    pBtn.style.background = '#b91c1c';
                    pBtn.innerHTML = '<i class="fa fa-times"></i> Failed';
                    App.toast('Pull failed: ' + (pullRes.error || 'Unknown error'), 'err');
                  }
                }).catch(function (err) {
                  pBtn.disabled = false;
                  pBtn.style.background = '#b91c1c';
                  pBtn.innerHTML = '<i class="fa fa-times"></i> Error';
                  App.toast('Network error: ' + err.message, 'err');
                });
              };
            });
          })
          .catch(function (err) {
            btnBrowseRepo.disabled = false;
            if (discoverTitle) discoverTitle.innerHTML = '<span style="color:#f87171;">Failed to browse repository</span>';
            if (discoverList) discoverList.innerHTML = '<div style="padding:12px;color:#f87171;">' + err.message + '</div>';
          });
      };
    }

    // Local Backups refresh
    var btnBackupRef = container.querySelector('#btn-backup-refresh');
    if (btnBackupRef) {
      btnBackupRef.onclick = loadBackups;
    }

    // RoCE MTU 9000 Benchmark
    var btnRoce = container.querySelector('#btn-run-roce-bench');
    if (btnRoce) {
      btnRoce.onclick = function () {
        var ip = (document.getElementById('roce-bench-ip') || {}).value || '';
        var mtu = (document.getElementById('roce-bench-mtu') || {}).value || '9000';
        ip = ip.trim();
        if (!ip) { App.toast('Enter Satellite IP', 'warn'); return; }
        runTool('bench', { satellite_ip: ip, mtu: mtu }, btnRoce, 'term-roce-bench');
      };
    }

    // Scheduler & Curfew Policy Save
    var btnSchedSave = container.querySelector('#btn-sched-save');
    if (btnSchedSave) {
      btnSchedSave.onclick = function () {
        var idleTimeout = parseInt((document.getElementById('sched-idle-timeout') || {}).value, 10) || 60;
        var maxNodes = parseInt((document.getElementById('sched-max-nodes') || {}).value, 10) || 12;
        var curfewStart = ((document.getElementById('sched-curfew-start') || {}).value || '23:00').trim();
        var curfewEnd = ((document.getElementById('sched-curfew-end') || {}).value || '07:00').trim();

        btnSchedSave.disabled = true;
        fetch(API_BASE + '/scheduler/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            idle_timeout_min: idleTimeout,
            max_nodes_per_user: maxNodes,
            curfew_start: curfewStart,
            curfew_end: curfewEnd,
            auto_shutdown_enabled: true
          })
        }).then(function(r) { return r.json(); }).then(function(res) {
          btnSchedSave.disabled = false;
          if (res.success) {
            App.toast('Scheduler & Quota Policy updated successfully', 'ok');
          } else {
            App.toast('Failed: ' + (res.error || 'Server error'), 'err');
          }
        }).catch(function(e) {
          btnSchedSave.disabled = false;
          App.toast('Error: ' + e.message, 'err');
        });
      };
    }

    // Stop Idle Labs Now
    var btnSchedStop = container.querySelector('#btn-sched-stop-now');
    if (btnSchedStop) {
      btnSchedStop.onclick = function () {
        if (!confirm('Halt all idle lab sessions immediately?\n\nNodes in labs with no console interaction for >60min will be gracefully shut down.')) return;
        runTool('scheduler-stop-idle', {}, btnSchedStop, 'term-sched-policy');
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

  /* ── Mesh Loader ────────────────────────────────────────── */
  function loadMesh() {
    var target = document.getElementById('az-mesh-table');
    if (!target) return;
    target.innerHTML = '<div style="padding:10px;"><i class="fa fa-spinner fa-spin"></i> Testing ping reachability across cluster endpoints…</div>';

    fetch(API_BASE + '/mesh/sweep')
      .then(function (r) { return r.json(); })
      .then(function (res) {
        var list = res.mesh || [];
        if (!list.length) {
          target.innerHTML = '<div style="padding:10px;color:#64748b;">No reachability data returned.</div>';
          return;
        }
        var html = '<table class="table" style="width:100%;">';
        html += '<thead><tr><th>Target Endpoint</th><th>IP Address</th><th>Status</th><th>Latency</th></tr></thead><tbody>';
        list.forEach(function (m) {
          var isUp = m.status === 'online';
          var statBadge = isUp 
            ? '<span style="color:#4ade80;font-weight:700;">● ONLINE</span>' 
            : '<span style="color:#f87171;font-weight:700;">○ OFFLINE</span>';
          var lat = m.latency_ms != null ? m.latency_ms + ' ms' : 'Timeout';
          html += '<tr>' +
            '<td style="font-weight:600;color:#f1f5f9;">' + m.name + '</td>' +
            '<td style="font-family:monospace;color:#38bdf8;">' + m.ip + '</td>' +
            '<td>' + statBadge + '</td>' +
            '<td style="font-family:monospace;font-weight:600;">' + lat + '</td>' +
          '</tr>';
        });
        html += '</tbody></table>';
        target.innerHTML = html;
      })
      .catch(function () {
        target.innerHTML = '<div style="padding:10px;color:#ef4444;">Failed to execute ping mesh sweep.</div>';
      });
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

  /* ── Templates Loader & Universal Multi-Format Filter ────── */
  var DEFAULT_CLIENT_TEMPLATES = [
    // CML2 (Cisco Modeling Labs 2.x) Topologies
    { name: "cml2-bgp-enterprise", format: "cml2", category: "bgp", desc: "Cisco DevNet CML2 Enterprise BGP Core: Dual-homed eBGP to dual ISPs with iBGP mesh & Day-0 configs.", nodes: 4, tags: ["cml2","cml","bgp","ospf","cisco","enterprise"], source_url: "https://github.com/CiscoDevNet/cml-community/tree/master/lab-topologies/bgp-enterprise" },
    { name: "cml2-basic-forwarding", format: "cml2", category: "ccna", desc: "CML2 Flexible Forwarding Behavior: Multi-router OSPF area 0 backbone with dual traffic-gen hosts.", nodes: 6, tags: ["cml2","cml","ospf","forwarding","traffic"], source_url: "https://github.com/CiscoDevNet/cml-community/blob/master/lab-topologies/basic-forwarding-behavior.yaml" },
    { name: "ccna-routing", format: "cml2", category: "ccna", desc: "Full CCNA Routing topology: 4x IOSv routers + 2x IOL L2 switches. OSPF, EIGRP, RIP labs ready.", nodes: 6, tags: ["cml2","ccna","ospf","eigrp","rip","routing"], source_url: "https://github.com/CiscoDevNet/cml-community/tree/master/labs/ccna-enterprise-routing" },
    { name: "sdwan-vedge", format: "cml2", category: "sdwan", desc: "SD-WAN vEdge: vManage + vSmart + vBond + 3x vEdge with OMP, TLOCs, and policy templates.", nodes: 6, tags: ["cml2","sdwan","viptela","cisco","vedge"], source_url: "https://github.com/CiscoDevNet/cml-community/tree/master/use-cases/sdwan" },

    // EVE-NG Community Topologies
    { name: "eve-ccie-enterprise", format: "eve-ng", category: "ccie", desc: "EVE-NG Community CCIE Enterprise Infrastructure: Full 10-node core/distribution/access topology.", nodes: 10, tags: ["eve-ng","eve","ccie","enterprise","switching","bgp"], source_url: "https://github.com/Shadow578/eve-ng-labs/tree/master/ccie" },
    { name: "eve-arista-evpn", format: "eve-ng", category: "datacenter", desc: "EVE-NG Arista vEOS BGP EVPN/VXLAN: 2x Spine + 4x Leaf datacenter fabric with auto-vtep.", nodes: 6, tags: ["eve-ng","eve","arista","evpn","vxlan","datacenter"], source_url: "https://github.com/Shadow578/eve-ng-labs/tree/master/arista" },
    { name: "bgp-full-mesh", format: "eve-ng", category: "bgp", desc: "BGP full-mesh: 8x CSR1000v routers, 4 autonomous systems, iBGP/eBGP, communities, route-maps.", nodes: 8, tags: ["eve-ng","bgp","ccie","enterprise","advanced"], source_url: "https://github.com/Shadow578/eve-ng-labs/tree/master/bgp-mesh" },
    { name: "mpls-ldp", format: "eve-ng", category: "mpls", desc: "MPLS/LDP: 6x CSR1000v with MPLS forwarding, LDP neighbors, L3VPN PE-CE, and traffic engineering.", nodes: 6, tags: ["eve-ng","mpls","ldp","l3vpn","te"], source_url: "https://github.com/Shadow578/eve-ng-labs/tree/master/mpls-ldp" },
    { name: "isis-datacenter", format: "eve-ng", category: "isis", desc: "IS-IS spine-leaf datacenter: 2x spine + 4x leaf with IS-IS L2, BFD, and prefix-SID.", nodes: 6, tags: ["eve-ng","isis","datacenter","spine-leaf","bfd"], source_url: "https://github.com/Shadow578/eve-ng-labs/tree/master/isis" },

    // GNS3 Community Topologies
    { name: "gns3-frr-bgp-mesh", format: "gns3", category: "bgp", desc: "GNS3 Open-Source FRRouting BGP Mesh: Containerized Linux routers running high-speed modern FRR.", nodes: 5, tags: ["gns3","frr","bgp","linux","open-source"], source_url: "https://github.com/danehans/gns3-labs/tree/master/bgp-mesh" },
    { name: "gns3-spine-leaf", format: "gns3", category: "datacenter", desc: "GNS3 Datacenter Spine-Leaf: Multi-vendor fabric with automated eBGP unnumbered underlay.", nodes: 6, tags: ["gns3","spine-leaf","datacenter","ebgp","automation"], source_url: "https://github.com/danehans/gns3-labs/tree/master/spine-leaf" },

    // Native PNetLab v8 / Hybrid Topologies
    { name: "ccna-switching", format: "pnetlab-v8", category: "ccna", desc: "CCNA Switching: 6x IOL L2 with STP, VTP, Inter-VLAN, EtherChannel, and HSRP pre-configured.", nodes: 8, tags: ["pnetlab","pnetlab-v8","ccna","switching","stp","vlan","hsrp"], source_url: "https://github.com/JeremyITLab/CCNA-Labs" },
    { name: "ccna-wan", format: "pnetlab-v8", category: "ccna", desc: "CCNA WAN: PPP, HDLC, Frame Relay, DMVPN phase 1 topology with 4 routers.", nodes: 4, tags: ["pnetlab","pnetlab-v8","ccna","wan","ppp","dmvpn"], source_url: "https://github.com/JeremyITLab/CCNA-Labs" },
    { name: "bgp-internet-edge", format: "pnetlab-v8", category: "bgp", desc: "Internet edge: 2x ISP routers + 2x CPE with BGP dual-homing, prefix filtering, AS-path prepend.", nodes: 4, tags: ["pnetlab","pnetlab-v8","bgp","internet","edge","filtering"], source_url: "https://github.com/packetpushers/labs" },
    { name: "ospf-multi-area", format: "pnetlab-v8", category: "ospf", desc: "OSPF multi-area: Areas 0, 1, 2, stub/NSSA, virtual links, redistribution with 6 IOSv routers.", nodes: 6, tags: ["pnetlab","pnetlab-v8","ospf","multiarea","redistribution"], source_url: "https://github.com/CiscoDevNet/cml-community" },
    { name: "mpls-sr", format: "pnetlab-v8", category: "mpls", desc: "Segment Routing: XRv9k or IOSv SR-MPLS with TI-LFA fast reroute, SID allocation, and SR-TE.", nodes: 4, tags: ["pnetlab","pnetlab-v8","mpls","segment-routing","sr-te","xrv"], source_url: "https://github.com/packetpushers/labs" },
    { name: "firewall-perimeter", format: "pnetlab-v8", category: "security", desc: "Perimeter security: ASAv + Cisco ISE + 2x edge routers with ZBF, NAT, VPN, and ACLs.", nodes: 5, tags: ["pnetlab","pnetlab-v8","security","asa","firewall","nat","vpn"], source_url: "https://github.com/Shadow578/eve-ng-labs" },
    { name: "datacenter-vxlan", format: "pnetlab-v8", category: "datacenter", desc: "VXLAN/EVPN BGP: 2x spine + 4x leaf Nexus 9Kv with L2VNI, L3VNI, and VTEP auto-discovery.", nodes: 6, tags: ["pnetlab","pnetlab-v8","vxlan","evpn","bgp","nexus","datacenter"], source_url: "https://github.com/packetpushers/labs" },
    { name: "ccie-rs-lab1", format: "pnetlab-v8", category: "ccie", desc: "CCIE RS mock lab 1: 8-router topology with OSPF, BGP, MPLS, QoS, and redistribution tasks.", nodes: 8, tags: ["pnetlab","pnetlab-v8","ccie","advanced","mock-lab"], source_url: "https://github.com/Shadow578/eve-ng-labs" },
    { name: "ipv6-dual-stack", format: "pnetlab-v8", category: "ccna", desc: "IPv6 dual-stack: 4x routers with OSPFv3, BGP4+, RIPng, SLAAC, DHCPv6, and NAT64.", nodes: 4, tags: ["pnetlab","pnetlab-v8","ipv6","ospfv3","bgp","dual-stack"], source_url: "https://github.com/JeremyITLab/CCNA-Labs" }
  ];

  var allTemplates = DEFAULT_CLIENT_TEMPLATES.slice();
  var activeFormatFilter = 'all';
  var activeCategoryFilter = 'all';
  var activeSearchText = '';

  function applyTemplateFilters() {
    var filtered = allTemplates.filter(function (t) {
      // 1. Format filter
      if (activeFormatFilter !== 'all') {
        var fmt = (t.format || 'pnetlab-v8').toLowerCase();
        if (activeFormatFilter === 'cml2' && !fmt.includes('cml')) return false;
        if (activeFormatFilter === 'eve-ng' && !fmt.includes('eve')) return false;
        if (activeFormatFilter === 'gns3' && !fmt.includes('gns3')) return false;
        if (activeFormatFilter === 'pnetlab-v8' && !fmt.includes('pnet')) return false;
      }
      // 2. Category filter
      if (activeCategoryFilter !== 'all') {
        var cat = (t.category || '').toLowerCase();
        if (cat !== activeCategoryFilter) return false;
      }
      // 3. Search query (tokenized multi-word search)
      if (activeSearchText) {
        var hay = (
          (t.name || '') + ' ' +
          (t.desc || '') + ' ' +
          (t.category || '') + ' ' +
          (t.format || '') + ' ' +
          (t.source_url || '') + ' ' +
          (t.tags || []).join(' ')
        ).toLowerCase();
        var tokens = activeSearchText.split(/\s+/).filter(Boolean);
        for (var i = 0; i < tokens.length; i++) {
          if (!hay.includes(tokens[i])) return false;
        }
      }
      return true;
    });

    var countBadge = document.getElementById('tmpl-count-badge');
    if (countBadge) {
      countBadge.textContent = filtered.length + ' of ' + allTemplates.length + ' Topologies';
    }

    renderTemplateCards(filtered);
  }

  function loadTemplates() {
    renderFormatChips();
    renderCategoryChips();
    applyTemplateFilters();

    fetch(API_BASE + '/templates')
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.templates && res.templates.length) {
          allTemplates = res.templates;
        }
        var sInput = document.getElementById('tmpl-search');
        if (sInput && sInput.value) {
          activeSearchText = sInput.value.toLowerCase().trim();
        }
        renderFormatChips();
        renderCategoryChips();
        applyTemplateFilters();
      })
      .catch(function () {
        renderFormatChips();
        renderCategoryChips();
        applyTemplateFilters();
      });
  }

  function renderFormatChips() {
    var chipsContainer = document.getElementById('tmpl-format-chips');
    if (!chipsContainer) return;
    var formats = [
      { id: 'all',        name: 'All Formats',               icon: 'fa-cubes',  color: '#38bdf8' },
      { id: 'cml2',       name: 'CML 2.x (Cisco DevNet)',    icon: 'fa-globe',  color: '#0284c7' },
      { id: 'eve-ng',     name: 'EVE-NG (Community UNL)',    icon: 'fa-bolt',   color: '#8b5cf6' },
      { id: 'gns3',       name: 'GNS3 (Open-Source JSON)',   icon: 'fa-flask',  color: '#10b981' },
      { id: 'pnetlab-v8', name: 'PNetLab Native (v8 XML)',   icon: 'fa-cube',   color: '#f59e0b' }
    ];
    var html = '';
    formats.forEach(function (f) {
      var isActive = activeFormatFilter === f.id;
      var style = isActive
        ? 'background:' + f.color + ';color:#fff;border-color:' + f.color + ';box-shadow:0 0 12px ' + f.color + '40;'
        : 'background:rgba(255,255,255,0.05);color:#94a3b8;border-color:rgba(255,255,255,0.1);';
      html += '<button type="button" class="tmpl-fmt-btn" data-fmt="' + f.id + '" style="font-size:11.5px;padding:5px 12px;border-radius:14px;border:1px solid;cursor:pointer;font-weight:700;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;transition:all 0.15s ease;' + style + '"><i class="fa ' + f.icon + '"></i> ' + f.name + '</button>';
    });
    chipsContainer.innerHTML = html;

    chipsContainer.querySelectorAll('.tmpl-fmt-btn').forEach(function (btn) {
      btn.onclick = function () {
        activeFormatFilter = btn.dataset.fmt;
        renderFormatChips();
        applyTemplateFilters();
      };
    });
  }

  function renderCategoryChips() {
    var chipsContainer = document.getElementById('tmpl-category-chips');
    if (!chipsContainer) return;
    var categories = ['all', 'ccna', 'bgp', 'mpls', 'isis', 'sdwan', 'datacenter', 'security', 'ccie'];
    var html = '';
    categories.forEach(function (cat) {
      var isActive = activeCategoryFilter === cat;
      var style = isActive 
        ? 'background:#3b82f6;color:#fff;border-color:#3b82f6;' 
        : 'background:rgba(255,255,255,0.05);color:#94a3b8;border-color:rgba(255,255,255,0.1);';
      html += '<button type="button" class="tmpl-cat-btn" data-cat="' + cat + '" style="font-size:11px;padding:3px 10px;border-radius:12px;border:1px solid;cursor:pointer;text-transform:uppercase;font-weight:600;white-space:nowrap;transition:all 0.15s ease;' + style + '">' + (cat === 'all' ? 'All Tracks' : cat) + '</button>';
    });
    chipsContainer.innerHTML = html;

    chipsContainer.querySelectorAll('.tmpl-cat-btn').forEach(function (btn) {
      btn.onclick = function () {
        activeCategoryFilter = btn.dataset.cat;
        renderCategoryChips();
        applyTemplateFilters();
      };
    });
  }

  function renderTemplateCards(list) {
    var target = document.getElementById('tmpl-grid');
    if (!target) return;
    if (!list.length) {
      target.innerHTML = '<div style="padding:40px;color:#64748b;grid-column:1/-1;text-align:center;background:rgba(0,0,0,0.2);border-radius:10px;border:1px dashed rgba(255,255,255,0.1);">' +
        '<i class="fa fa-info-circle" style="font-size:24px;color:#38bdf8;margin-bottom:8px;display:block;"></i>' +
        '<div style="font-weight:600;font-size:14px;color:#f1f5f9;margin-bottom:4px;">No topologies match the active search or format filter</div>' +
        '<div style="font-size:12px;color:#94a3b8;margin-bottom:12px;">Try adjusting your keyword query, choosing "All Formats", or resetting filters.</div>' +
        '<button type="button" class="btn btn-ghost btn-sm" onclick="window.__azClearTemplateFilters()" style="color:#38bdf8;border:1px solid rgba(56,189,248,0.3);"><i class="fa fa-refresh"></i> Reset All Filters</button>' +
      '</div>';
      return;
    }
    var html = '';
    list.forEach(function (t) {
      var catColor = '#3b82f6';
      if (t.category === 'ccie') catColor = '#ef4444';
      else if (t.category === 'bgp') catColor = '#8b5cf6';
      else if (t.category === 'mpls') catColor = '#ec4899';
      else if (t.category === 'security') catColor = '#10b981';
      else if (t.category === 'datacenter') catColor = '#f59e0b';

      var fmt = (t.format || 'pnetlab-v8').toLowerCase();
      var fmtBadge = '<span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.35);"><i class="fa fa-cube"></i> PNetLab v8</span>';
      if (fmt.includes('cml')) {
        fmtBadge = '<span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;background:rgba(14,165,233,0.15);color:#0ea5e9;border:1px solid rgba(14,165,233,0.35);"><i class="fa fa-globe"></i> CML 2.x YAML</span>';
      } else if (fmt.includes('eve')) {
        fmtBadge = '<span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;background:rgba(139,92,246,0.15);color:#a78bfa;border:1px solid rgba(139,92,246,0.35);"><i class="fa fa-bolt"></i> EVE-NG UNL</span>';
      } else if (fmt.includes('gns3')) {
        fmtBadge = '<span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;background:rgba(16,185,129,0.15);color:#34d399;border:1px solid rgba(16,185,129,0.35);"><i class="fa fa-flask"></i> GNS3 JSON</span>';
      }

      var tagsHtml = (t.tags || []).map(function(tag) {
        return '<span style="font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.06);color:#94a3b8;">#' + tag + '</span>';
      }).join(' ');

      var srcUrl = t.source_url || ('https://github.com/CiscoDevNet/cml-community/tree/master/labs/' + t.name);

      html += '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:16px;display:flex;flex-direction:column;justify-content:space-between;transition:transform 0.15s ease, border-color 0.15s ease;" onmouseenter="this.style.borderColor=\'' + catColor + '\'" onmouseleave="this.style.borderColor=\'var(--pnq-border,rgba(255,255,255,0.08))\'">' +
        '<div>' +
          '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;gap:8px;flex-wrap:wrap;">' +
            '<div style="font-weight:700;font-size:15px;color:#f1f5f9;">' + t.name + '</div>' +
            '<div style="display:flex;gap:4px;align-items:center;">' +
              fmtBadge +
              '<span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;background:' + catColor + '20;color:' + catColor + ';border:1px solid ' + catColor + '40;text-transform:uppercase;">' + t.category + '</span>' +
            '</div>' +
          '</div>' +
          '<div style="display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap;">' +
            '<span style="font-size:11px;color:#38bdf8;font-weight:600;"><i class="fa fa-cubes"></i> ' + (t.nodes || 4) + ' Nodes</span>' +
            '<a href="' + srcUrl + '" target="_blank" rel="noopener noreferrer" style="font-size:11px;color:#0ea5e9;text-decoration:none;display:inline-flex;align-items:center;gap:4px;" title="View original lab repository & documentation" onmouseenter="this.style.textDecoration=\'underline\'" onmouseleave="this.style.textDecoration=\'none\'">' +
              '<i class="fa fa-external-link"></i> Upstream Source ↗' +
            '</a>' +
          '</div>' +
          '<div style="font-size:12.5px;color:var(--pnq-text-muted,#94a3b8);line-height:1.4;margin-bottom:12px;">' + t.desc + '</div>' +
        '</div>' +
        '<div>' +
          '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px;">' + tagsHtml + '</div>' +
          '<div style="display:flex;gap:6px;align-items:center;">' +
            '<button type="button" class="btn btn-primary btn-sm" style="flex:1;background:linear-gradient(135deg,' + catColor + ',#2563eb);border:none;color:#fff;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px;" onclick="window.__azDeployTemplate(\'' + t.name + '\', this)">' +
              '<i class="fa fa-cloud-download"></i> Deploy & Auto-Fix' +
            '</button>' +
            '<button type="button" class="btn btn-ghost btn-sm" style="font-size:11.5px;padding:6px 10px;color:#10b981;border:1px solid rgba(16,185,129,0.3);border-radius:6px;" title="Run in-place schema repair for this lab" onclick="window.__azFixSingleTemplate(\'' + t.name + '\', this)">' +
              '<i class="fa fa-wrench"></i> Fix' +
            '</button>' +
            '<a href="' + srcUrl + '" target="_blank" rel="noopener noreferrer" class="btn btn-ghost btn-sm" style="font-size:11px;padding:6px 10px;color:#94a3b8;border:1px solid rgba(255,255,255,0.1);border-radius:6px;display:inline-flex;align-items:center;text-decoration:none;" title="Open original repository in new tab"><i class="fa fa-github"></i></a>' +
          '</div>' +
        '</div>' +
      '</div>';
    });
    target.innerHTML = html;
  }

  window.__azClearTemplateFilters = function () {
    activeFormatFilter = 'all';
    activeCategoryFilter = 'all';
    activeSearchText = '';
    var sInput = document.getElementById('tmpl-search');
    if (sInput) sInput.value = '';
    var sBtn = document.getElementById('btn-tmpl-search-clear');
    if (sBtn) sBtn.style.display = 'none';
    renderFormatChips();
    renderCategoryChips();
    applyTemplateFilters();
  };

  window.__azDeployTemplate = function(name, btn) {
    if (!confirm('Deploy & auto-convert template lab "' + name + '" to your PNetLab repository?\n\nThis automatically converts links, fixes hypervisor device types, injects base configs, and builds the HTML workbook.')) return;
    runTool('templates-deploy', { template: name }, btn, 'term-templates');
  };

  window.__azFixSingleTemplate = function(name, btn) {
    var path = '/opt/unetlab/labs/Azam-Templates/' + name + '.unl';
    runTool('templates-fix', { file: path }, btn, 'term-templates');
  };

  /* ── Perf Loader ────────────────────────────────────────── */
  function loadPerf() {
    var target = document.getElementById('perf-nodes-table');
    if (!target) return;
    target.innerHTML = '<div style="padding:10px;color:#94a3b8;"><i class="fa fa-spinner fa-spin"></i> Profiling active QEMU/IOL processes…</div>';

    fetch(API_BASE + '/perf/top')
      .then(function (r) { return r.json(); })
      .then(function (res) {
        var nodes = res.nodes || [];
        if (!nodes.length) {
          target.innerHTML = '<div style="padding:14px;color:#64748b;text-align:center;">No active node processes detected (0 QEMU/IOL running).</div>';
          return;
        }
        var html = '<table class="table" style="width:100%;font-size:12.5px;">';
        html += '<thead><tr><th>Node Name</th><th>PID</th><th>Type</th><th>CPU%</th><th>RAM (MB)</th><th>State</th><th>Action</th></tr></thead><tbody>';
        var canKill = !window.userRole || window.userRole === '0' || window.userRole === 0 || window.userRole === 'admin';
        nodes.forEach(function (n) {
          var cpuNum = parseFloat(n.cpu_pct) || 0;
          var cpuColor = cpuNum > 80 ? '#f87171' : (cpuNum > 40 ? '#fbbf24' : '#4ade80');
          var actionBtn = canKill
            ? '<button type="button" class="btn btn-ghost btn-sm" style="font-size:11px;padding:2px 8px;color:#f87171;" onclick="window.__azKillNode(' + n.pid + ')"><i class="fa fa-times-circle"></i> Kill</button>'
            : '<span style="font-size:10.5px;color:#64748b;">Admin-Only</span>';
          html += '<tr>' +
            '<td style="font-weight:600;color:#f1f5f9;">' + n.name + '</td>' +
            '<td style="font-family:monospace;color:#94a3b8;">' + n.pid + '</td>' +
            '<td><span style="font-size:11px;padding:1px 6px;border-radius:4px;background:rgba(255,255,255,0.06);color:#38bdf8;">' + n.type + '</span></td>' +
            '<td style="font-family:monospace;font-weight:700;color:' + cpuColor + ';">' + n.cpu_pct + '%</td>' +
            '<td style="font-family:monospace;color:#a78bfa;">' + n.ram_mb + ' MB</td>' +
            '<td><span style="color:#4ade80;">' + n.state + '</span></td>' +
            '<td>' + actionBtn + '</td>' +
          '</tr>';
        });
        html += '</tbody></table>';
        target.innerHTML = html;
      })
      .catch(function () {
        target.innerHTML = '<div style="padding:10px;color:#ef4444;">Failed to retrieve process profiler metrics.</div>';
      });
  }

  window.__azKillNode = function(pid) {
    if (!confirm('Terminate process (PID ' + pid + ') immediately via SIGTERM?\n\nThis will stop the virtual node and release its hypervisor memory.')) return;
    fetch(API_BASE + '/perf-kill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-User-Role': window.userRole || '0' },
      body: JSON.stringify({ pid: pid })
    }).then(function(r) { return r.json(); }).then(function(res) {
      if (res.success) {
        if (window.PnqApp && window.PnqApp.toast) window.PnqApp.toast(res.message, 'ok');
        else alert(res.message);
        setTimeout(loadPerf, 1000);
      } else {
        alert('Action failed: ' + (res.error || 'Permission denied'));
      }
    }).catch(function(e) {
      alert('Request failed: ' + e);
    });
  };

  window.__azGenerateAirgap = function(btn) {
    if (!confirm('Generate 100% Offline Air-Gapped Installation Bundle?\n\nThis will package all local .deb packages, templates, Python wheels, and configuration into a standalone archive.')) return;
    if (btn) btn.disabled = true;
    fetch(API_BASE + '/airgap-pack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-User-Role': window.userRole || '0' },
      body: JSON.stringify({})
    }).then(function(r) { return r.json(); }).then(function(res) {
      if (btn) btn.disabled = false;
      if (res.success) {
        if (window.PnqApp && window.PnqApp.toast) window.PnqApp.toast(res.message, 'ok');
        else alert(res.message);
        setTimeout(loadBackups, 3000);
      } else {
        alert('Error: ' + (res.error || 'Failed to start airgap pack'));
      }
    }).catch(function(e) {
      if (btn) btn.disabled = false;
      alert('Request failed: ' + e);
    });
  };

  window.__azRestore = function (filename) {
    if (!confirm('Are you sure you want to restore cluster backup:\n' + filename + '\n\nThis will restore configurations and labs.')) return;
    runTool('backup-list', { restore_file: filename }, null, 'term-backup');
  };

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
                App.toast(obj.code === 0 ? '✔ Execution finished' : '⚠ Execution exited with code ' + obj.code, obj.code === 0 ? 'ok' : 'err');
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

  /* ── Client Toolkit Modal ───────────────────────────────── */
  function openClientToolkitModal() {
    var modalId = 'az-client-toolkit-modal';
    var modal = document.getElementById(modalId);
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#f8fafc;';
      modal.innerHTML = 
        '<div style="width:680px;max-width:94%;background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:12px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;display:flex;flex-direction:column;max-height:85vh;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
            '<div style="display:flex;align-items:center;gap:12px;">' +
              '<div style="width:36px;height:36px;border-radius:8px;background:rgba(167,139,250,0.2);color:#a78bfa;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-wrench"></i></div>' +
              '<div>' +
                '<div style="font-weight:700;font-size:16px;color:#f1f5f9;">Enterprise Client Connectivity & NetDevOps Toolkit</div>' +
                '<div style="font-size:12px;color:#94a3b8;">Pre-configured client integration packs for 1-click terminal & packet capture</div>' +
              '</div>' +
            '</div>' +
            '<button type="button" id="az-toolkit-close" style="background:none;border:none;color:#94a3b8;font-size:22px;cursor:pointer;line-height:1;">&times;</button>' +
          '</div>' +
          '<div style="padding:20px;overflow-y:auto;display:flex;flex-direction:column;gap:16px;">' +
            '<div class="card" style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;">' +
              '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
                '<div style="font-weight:600;font-size:14px;color:#38bdf8;"><i class="fa fa-windows"></i> Windows 10 / 11 One-Click Setup Pack</div>' +
                '<span style="font-size:11px;color:#94a3b8;">PuTTY, SecureCRT, Wireshark</span>' +
              '</div>' +
              '<div style="font-size:12px;color:#94a3b8;line-height:1.5;margin-bottom:10px;">Associates <code>capture://</code> and <code>telnet://</code> URIs directly with your local Wireshark and PuTTY/SecureCRT executables.</div>' +
              '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
                '<a href="/azam-ops/api/client/toolkit/pnetlab-urischeme-installer.bat" download class="btn btn-primary btn-sm" style="background:#0284c7;border:none;color:#fff;font-size:12px;display:inline-flex;align-items:center;gap:6px;"><i class="fa fa-download"></i> Download URI Scheme Installer (.bat)</a>' +
                '<a href="/azam-ops/api/client/toolkit/setup-windows-ssl-trust.ps1" download class="btn btn-ghost btn-sm" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;"><i class="fa fa-lock"></i> SSL CA Trust (.ps1)</a>' +
                '<a href="/azam-ops/api/client/toolkit/setup-windows-wireshark.ps1" download class="btn btn-ghost btn-sm" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;"><i class="fa fa-rss"></i> Wireshark Pipe (.ps1)</a>' +
              '</div>' +
            '</div>' +
            '<div class="card" style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;">' +
              '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
                '<div style="font-weight:600;font-size:14px;color:#34d399;"><i class="fa fa-apple"></i> macOS & Linux Native Terminal Pack</div>' +
                '<span style="font-size:11px;color:#94a3b8;">iTerm2, GNOME Terminal, Wireshark</span>' +
              '</div>' +
              '<div style="font-size:12px;color:#94a3b8;line-height:1.5;margin-bottom:10px;">Configures default handlers for telnet and Wireshark remote named pipes over SSH.</div>' +
              '<div style="display:flex;gap:8px;">' +
                '<a href="/azam-ops/api/client/toolkit/pnetlab-client-setup.sh" download class="btn btn-primary btn-sm" style="background:#059669;border:none;color:#fff;font-size:12px;display:inline-flex;align-items:center;gap:6px;"><i class="fa fa-download"></i> Download Setup Script (.sh)</a>' +
              '</div>' +
            '</div>' +
            '<div class="card" style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;">' +
              '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
                '<div style="font-weight:600;font-size:14px;color:#a78bfa;"><i class="fa fa-code"></i> Python NetDevOps API Starter Pack</div>' +
                '<span style="font-size:11px;color:#94a3b8;">REST API Automation Client</span>' +
              '</div>' +
              '<div style="font-size:12px;color:#94a3b8;line-height:1.5;margin-bottom:10px;">Standalone Python 3 script with session auth, lab lifecycle methods, topology export, and telemetry queries.</div>' +
              '<div style="display:flex;gap:8px;">' +
                '<a href="/azam-ops/api/client/toolkit/pnetlab-api-client.py" download class="btn btn-primary btn-sm" style="background:#7c3aed;border:none;color:#fff;font-size:12px;display:inline-flex;align-items:center;gap:6px;"><i class="fa fa-download"></i> Download pnetlab-api-client.py</a>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);

      modal.querySelector('#az-toolkit-close').onclick = function () { modal.style.display = 'none'; };
      modal.onclick = function (e) { if (e.target === modal) modal.style.display = 'none'; };
    } else {
      modal.style.display = 'flex';
    }
  }

  /* ── Helper: Escape HTML ────────────────────────────────── */
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /* ── Exam & Quiz Grader Labs Management ─────────────────── */
  var _graderLabsCache = null;

  function loadGraderLabs(force) {
    if (_graderLabsCache && !force) {
      renderGraderLabs(_graderLabsCache);
      return;
    }

    var treeEl = document.getElementById('grader-lab-tree');
    if (treeEl && !treeEl.querySelector('.az-folder-group')) {
      treeEl.innerHTML = '<div style="text-align:center;color:#64748b;padding:16px;font-size:12px;"><i class="fa fa-spinner fa-spin"></i> Loading labs from /opt/unetlab/labs...</div>';
    }

    fetch('/azam-ops/api/labs')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        _graderLabsCache = data;
        renderGraderLabs(data);
      })
      .catch(function (err) {
        if (treeEl) {
          treeEl.innerHTML = '<div style="color:#ef4444;padding:12px;font-size:12px;"><i class="fa fa-exclamation-triangle"></i> Failed to load labs: ' + (err.message || 'API error') + '</div>';
        }
      });
  }

  function renderGraderLabs(data) {
    var treeEl = document.getElementById('grader-lab-tree');
    var badgeCount = document.getElementById('grader-total-count');
    if (!treeEl) return;

    var total = (data && data.total_labs) || 0;
    if (badgeCount) badgeCount.textContent = total + ' Labs in Library';

    if (!data || !data.folders || !data.folders.length) {
      treeEl.innerHTML = '<div style="color:#64748b;padding:14px;text-align:center;font-size:12px;">No labs found under /opt/unetlab/labs</div>';
      return;
    }

    var searchVal = (document.getElementById('grader-lab-search') ? document.getElementById('grader-lab-search').value.toLowerCase().trim() : '');
    var currentSelected = (document.getElementById('grader-selected-lab-path') ? document.getElementById('grader-selected-lab-path').value : '');

    var html = '';
    var matchCount = 0;
    var autoPickFirst = null;

    data.folders.forEach(function (f, fIdx) {
      var filteredLabs = f.labs.filter(function (l) {
        if (!searchVal) return true;
        return l.name.toLowerCase().indexOf(searchVal) !== -1 ||
               l.folder.toLowerCase().indexOf(searchVal) !== -1 ||
               (l.description && l.description.toLowerCase().indexOf(searchVal) !== -1);
      });

      if (!filteredLabs.length) return;
      matchCount += filteredLabs.length;
      if (!autoPickFirst && filteredLabs.length) autoPickFirst = filteredLabs[0];

      var isSearchActive = !!searchVal;
      var showGroup = (isSearchActive || fIdx === 0 || fIdx === 1);
      html += 
        '<div class="az-folder-group" style="margin-bottom:4px;">' +
          '<div class="az-folder-hdr" data-fidx="' + fIdx + '" style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;padding:6px 10px;background:rgba(255,255,255,0.04);border-radius:6px;font-size:12px;font-weight:600;color:#cbd5e1;user-select:none;transition:background 0.15s ease;" onmouseenter="this.style.background=\'rgba(255,255,255,0.07)\'" onmouseleave="this.style.background=\'rgba(255,255,255,0.04)\'">' +
            '<div style="display:flex;align-items:center;gap:7px;overflow:hidden;">' +
              '<i class="fa ' + (showGroup ? 'fa-folder-open' : 'fa-folder') + '" style="color:#f59e0b;font-size:13px;"></i>' +
              '<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(f.name) + '</span>' +
            '</div>' +
            '<span style="font-size:10px;color:#94a3b8;background:rgba(255,255,255,0.06);padding:2px 7px;border-radius:10px;font-weight:700;">' + filteredLabs.length + '</span>' +
          '</div>' +
          '<div class="az-folder-labs" id="az-flabs-' + fIdx + '" style="display:' + (showGroup ? 'flex' : 'none') + ';flex-direction:column;gap:3px;margin-top:3px;padding-left:14px;">';

      filteredLabs.forEach(function (lab) {
        var isSel = (currentSelected && currentSelected === lab.path);
        var borderStyle = isSel ? 'border:1px solid #10b981;background:rgba(16,185,129,0.15);' : 'border:1px solid rgba(255,255,255,0.05);background:rgba(0,0,0,0.2);';
        html += 
          '<div class="az-grader-lab-item" data-path="' + escapeHtml(lab.path) + '" data-name="' + escapeHtml(lab.name) + '" data-nodes="' + lab.nodes + '" data-folder="' + escapeHtml(lab.folder) + '" style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;padding:7px 10px;border-radius:6px;' + borderStyle + 'font-size:12px;transition:all 0.15s ease;">' +
            '<div style="display:flex;align-items:center;gap:8px;overflow:hidden;">' +
              '<i class="fa fa-cube" style="color:' + (isSel ? '#10b981' : '#38bdf8') + ';font-size:11px;"></i>' +
              '<span style="color:' + (isSel ? '#34d399' : '#f1f5f9') + ';font-weight:' + (isSel ? '700' : '500') + ';white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(lab.name) + '</span>' +
            '</div>' +
            '<span style="padding:1px 6px;border-radius:4px;background:rgba(56,189,248,0.12);color:#38bdf8;font-size:10.5px;font-weight:700;white-space:nowrap;">' + lab.nodes + ' Nodes</span>' +
          '</div>';
      });

      html += '</div></div>';
    });

    if (matchCount === 0) {
      treeEl.innerHTML = '<div style="color:#64748b;padding:14px;text-align:center;font-size:12px;">No labs match "<b>' + escapeHtml(searchVal) + '</b>"</div>';
      return;
    }

    treeEl.innerHTML = html;

    // Attach folder collapse/expand toggles
    treeEl.querySelectorAll('.az-folder-hdr').forEach(function (hdr) {
      hdr.onclick = function () {
        var fIdx = hdr.dataset.fidx;
        var labsList = document.getElementById('az-flabs-' + fIdx);
        var icon = hdr.querySelector('.fa');
        if (labsList) {
          var isHidden = labsList.style.display === 'none';
          labsList.style.display = isHidden ? 'flex' : 'none';
          if (icon) {
            icon.className = isHidden ? 'fa fa-folder-open' : 'fa fa-folder';
          }
        }
      };
    });

    // Attach click handlers to lab items
    treeEl.querySelectorAll('.az-grader-lab-item').forEach(function (item) {
      item.onclick = function () {
        selectGraderLab({
          path: item.dataset.path,
          name: item.dataset.name,
          nodes: item.dataset.nodes,
          folder: item.dataset.folder
        });
      };
    });

    // If nothing currently selected and we have an autoPick, select it
    if (!currentSelected && autoPickFirst) {
      selectGraderLab(autoPickFirst);
    }
  }

  function selectGraderLab(lab) {
    if (!lab) return;
    var pathInput = document.getElementById('grader-selected-lab-path');
    var titleEl = document.getElementById('grader-selected-title');
    var pathEl = document.getElementById('grader-selected-path');
    var nodesEl = document.getElementById('grader-selected-nodes');

    if (pathInput) pathInput.value = lab.path;
    if (titleEl) titleEl.textContent = lab.name;
    if (pathEl) pathEl.textContent = lab.path;
    if (nodesEl) nodesEl.textContent = (lab.nodes || '-') + ' Nodes';

    // Highlight selected item in tree
    var treeEl = document.getElementById('grader-lab-tree');
    if (treeEl) {
      treeEl.querySelectorAll('.az-grader-lab-item').forEach(function (item) {
        var isMatch = item.dataset.path === lab.path;
        item.style.borderColor = isMatch ? '#10b981' : 'rgba(255,255,255,0.05)';
        item.style.background = isMatch ? 'rgba(16,185,129,0.15)' : 'rgba(0,0,0,0.2)';
        var icon = item.querySelector('.fa-cube');
        if (icon) icon.style.color = isMatch ? '#10b981' : '#38bdf8';
        var nameSpan = item.querySelector('span');
        if (nameSpan) {
          nameSpan.style.color = isMatch ? '#34d399' : '#f1f5f9';
          nameSpan.style.fontWeight = isMatch ? '700' : '500';
        }
      });
    }
  }

  /* ── Register with App Router ───────────────────────────── */
  App.register('azam-features', {
    title: 'Azam-Features',
    icon: 'fa-bolt',
    admin: false,
    render: render
  });

})();
