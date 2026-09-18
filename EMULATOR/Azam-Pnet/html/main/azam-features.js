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

    var btnRefresh = document.createElement('button');
    btnRefresh.className = 'btn btn-ghost';
    btnRefresh.innerHTML = '<i class="fa fa-refresh"></i> Refresh All';
    btnRefresh.onclick = function () { loadStats(); loadBackups(); loadMesh(); loadImagesAudit(); App.toast('Metrics refreshed', 'ok'); };

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
      createStatCard('az-m-backups', 'Backups Ready', '—', 'fa-archive', '#a78bfa');
    container.appendChild(statsGrid);

    // ── 3. Tab Bar Navigation ─────────────────────────────────
    var navTabs = document.createElement('div');
    navTabs.style.cssText = 'display:flex;gap:6px;border-bottom:2px solid var(--pnq-border,rgba(255,255,255,0.08));padding-bottom:2px;overflow-x:auto;scrollbar-width:thin;';

    var tabs = [
      { id: 'health',    name: 'Cluster Health',          icon: 'fa-heartbeat' },
      { id: 'grader',    name: 'Exam & Quiz Grader',      icon: 'fa-graduation-cap' },
      { id: 'sniffer',   name: 'Web Wireshark Sniffer',   icon: 'fa-rss' },
      { id: 'bridge',    name: 'Cloud & LAN Transit',     icon: 'fa-globe' },
      { id: 'shrink',    name: 'Golden Disk Shrinker',    icon: 'fa-compress' },
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
        createToolCard('doctor', 'azam-doctor', 'Cluster Doctor & Self-Healer', 'Deep diagnostic check of file permissions, disk health, orphan QEMU processes, and Apache proxy settings.', 'fa-stethoscope', '#d97706', 'term-doctor', [{ label: 'Reclaim Disk (--compress)', param: 'compress', tool: 'doctor-compress' }]) +
        createToolCard('perf', 'azam-perf', 'Performance Benchmark', 'Measures real-time memory throughput, disk I/O latency, and system load stress test.', 'fa-dashboard', '#7c3aed', 'term-perf') +
        createToolCard('watchdog-status', 'azam-watchdog', '24/7 Watchdog Service', 'Autonomous background systemd service that monitors cluster health continuously.', 'fa-eye', '#dc2626', 'term-watchdog', [{ label: 'Reinstall / Enable', param: 'install', tool: 'watchdog-install' }]) +
      '</div>';
    panesContainer.appendChild(pHealth);

    // ── Pane 2: Exam & Quiz Grader ──
    var pGrader = document.createElement('div');
    pGrader.id = 'pane-grader';
    pGrader.style.display = 'none';
    pGrader.innerHTML = 
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">' +
            '<div style="width:36px;height:36px;border-radius:8px;background:rgba(16,185,129,0.15);color:#10b981;display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa fa-graduation-cap"></i></div>' +
            '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Automated Lab Exam Grader</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Test checkpoints and generate instant pass/fail scorecards</div></div>' +
          '</div>' +
          '<div style="display:flex;flex-direction:column;gap:12px;margin-bottom:14px;">' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Select Certification Quiz:</label>' +
              '<select id="grader-quiz-select" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
                '<option value="ccna_ospf_basics">CCNA 200-301 — Multi-Area OSPF & Gateway Routing</option>' +
                '<option value="ccnp_bgp_enterprise">CCNP ENCOR 350-401 — Enterprise Dual-Homed BGP</option>' +
              '</select>' +
            '</div>' +
            '<div><label style="font-size:12px;font-weight:600;color:var(--pnq-text-muted,#94a3b8);display:block;margin-bottom:4px;">Target Lab ID:</label>' +
              '<input type="text" id="grader-lab-id" value="default_lab" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:13px;">' +
            '</div>' +
          '</div>' +
          '<button type="button" id="btn-run-grade" class="btn btn-primary" style="background:#10b981;border-color:#10b981;color:#fff;"><i class="fa fa-check-circle"></i> Grade My Lab</button>' +
        '</div>' +
        '<div id="term-grader" style="display:block;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;font-family:monospace;font-size:12.5px;min-height:300px;max-height:450px;overflow-y:auto;color:#38bdf8;">' +
          '<div style="color:#64748b;">// Ready to evaluate lab. Click "Grade My Lab" to audit checkpoints.</div>' +
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
            '<div style="display:flex;gap:10px;align-items:center;">' +
              '<select id="sniff-iface" style="padding:7px 12px;background:rgba(0,0,0,0.25);border:1px solid var(--pnq-border,rgba(255,255,255,0.1));border-radius:6px;color:#fff;font-size:12.5px;">' +
                '<option value="eth0">eth0 (Management)</option>' +
                '<option value="pnet0">pnet0 (Bridge)</option>' +
              '</select>' +
              '<button type="button" id="btn-start-sniff" class="btn btn-primary"><i class="fa fa-play"></i> Start Live Capture</button>' +
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

    // ── Pane 5: Golden Disk Shrinker ──
    var pShrink = document.createElement('div');
    pShrink.id = 'pane-shrink';
    pShrink.style.display = 'none';
    pShrink.innerHTML = 
      '<div style="display:flex;flex-direction:column;gap:16px;">' +
        '<div class="card" style="background:var(--pnq-surface,#1e293b);border:1px solid var(--pnq-border,rgba(255,255,255,0.08));border-radius:10px;padding:18px;">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">' +
            '<div style="display:flex;align-items:center;gap:12px;">' +
              '<div style="width:38px;height:38px;border-radius:8px;background:rgba(244,63,94,0.15);color:#f43f5e;display:flex;align-items:center;justify-content:center;font-size:17px;"><i class="fa fa-compress"></i></div>' +
              '<div><div style="font-weight:600;font-size:15px;color:#f1f5f9;">Golden Image Optimizer & QCOW2 Disk Shrinker</div><div style="font-size:12px;color:var(--pnq-text-muted,#94a3b8);">Compress oversized appliance images non-destructively, saving 50%–70% disk space</div></div>' +
            '</div>' +
            '<div style="display:flex;gap:10px;">' +
              '<button type="button" class="btn btn-ghost" data-az-tool="image-audit" data-az-term="term-shrink"><i class="fa fa-search"></i> Audit Bloat</button>' +
              '<button type="button" class="btn btn-primary" data-az-tool="image-shrink-all" data-az-term="term-shrink" style="background:#f43f5e;border-color:#f43f5e;color:#fff;"><i class="fa fa-compress"></i> Compress All Disks</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div id="term-shrink" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;font-family:monospace;font-size:12.5px;max-height:360px;overflow-y:auto;color:#e2e8f0;"></div>' +
      '</div>';
    panesContainer.appendChild(pShrink);

    // ── Pane 6: Diagram & Doc Exporter ──
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
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">' +
        createToolCard('scheduler-status', 'azam-scheduler', 'Resource Quota & Curfew Watchdog', 'Inspects idle timeout settings, nightly power-saver curfews, and role-based node limits.', 'fa-clock-o', '#f59e0b', 'term-sched', [
          { label: 'Stop Idle Labs Now', tool: 'scheduler-stop-idle' },
          { label: 'Audit Compliance', tool: 'scheduler-check' }
        ]) +
      '</div>';
    panesContainer.appendChild(pSched);

    // ── Pane 11: Cloud & NAS Backup ──
    var pCloud = document.createElement('div');
    pCloud.id = 'pane-cloud';
    pCloud.style.display = 'none';
    pCloud.innerHTML = 
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">' +
        createToolCard('cloud-sync', 'azam-cloud-backup', 'Offsite Cloud & NAS Sync', 'Synchronizes local snapshots to remote SFTP servers, AWS S3, or Network NAS.', 'fa-cloud-upload', '#0284c7', 'term-cloud', [
          { label: 'Sync Status', tool: 'cloud-status' },
          { label: 'List Remote Files', tool: 'cloud-list' }
        ]) +
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

    ['health', 'grader', 'sniffer', 'bridge', 'shrink', 'doc', 'ai', 'diff', 'mesh', 'scheduler', 'cloud', 'security', 'canvas'].forEach(function (id) {
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
        }

        runTool(tool, params, btn, term);
      };
    });

    // Exam Grader Run
    var btnGrade = container.querySelector('#btn-run-grade');
    if (btnGrade) {
      btnGrade.onclick = function () {
        var quiz = document.getElementById('grader-quiz-select').value;
        var lab = document.getElementById('grader-lab-id').value.trim();
        runTool('grader-run', { quiz: quiz, lab: lab }, btnGrade, 'term-grader');
      };
    }

    // Sniffer Start
    var btnSniff = container.querySelector('#btn-start-sniff');
    if (btnSniff) {
      btnSniff.onclick = function () {
        var iface = document.getElementById('sniff-iface').value;
        runTool('sniffer-capture', { interface: iface, count: 15 }, btnSniff, 'term-sniffer');
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

  function loadImagesAudit() {
    fetch(API_BASE + '/images/audit')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        // Can optionally populate an image table
      })
      .catch(function () {});
  }

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

  /* ── Register with App Router ───────────────────────────── */
  App.register('azam-features', {
    title: 'Azam-Features',
    icon: 'fa-bolt',
    admin: false,
    render: render
  });

})();
