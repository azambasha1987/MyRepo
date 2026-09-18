/**
 * pnetlab-azam-features.js
 * ─────────────────────────────────────────────────────────────
 * Injects the "⚡ Azam-Features" entry into the PNetLab left
 * sidebar (#lab-sidebar) and mounts the full operations
 * dashboard panel when the user clicks it.
 *
 * Follows the same pattern as pnetlab-sidebar-tools.js:
 *   - waits for #lab-sidebar to appear (MutationObserver + poll)
 *   - appends a single <li> with id="pnq-azam-features"
 *   - creates the full-screen dashboard modal in-DOM
 *   - manages open/close state
 * ─────────────────────────────────────────────────────────────
 */
(function () {
  'use strict';

  var PANEL_ID   = 'azam-features-panel';
  var TRIGGER_ID = 'pnq-azam-features';
  var API_BASE   = '/azam-ops/api';

  /* ── Sidebar entry ──────────────────────────────────────── */
  function injectSidebarEntry(sidebar) {
    if (document.getElementById(TRIGGER_ID)) return; // already present

    var li = document.createElement('li');
    li.id = TRIGGER_ID;
    li.innerHTML =
      '<a href="#" id="pnq-azam-features-link" title="Azam-Features Operations Center" style="display:flex;align-items:center;gap:8px;">' +
        '<i class="fa fa-bolt" style="color:#3b82f6;width:16px;text-align:center"></i>' +
        '<span style="font-weight:600;background:linear-gradient(90deg,#3b82f6,#8b5cf6);' +
              '-webkit-background-clip:text;-webkit-text-fill-color:transparent;">' +
          'Azam-Features' +
        '</span>' +
        '<span style="font-size:9px;padding:1px 5px;border-radius:8px;background:rgba(59,130,246,0.2);' +
              'color:#3b82f6;font-weight:700;-webkit-text-fill-color:#3b82f6;margin-left:auto">NEW</span>' +
      '</a>';

    li.querySelector('a').addEventListener('click', function (e) {
      e.preventDefault();
      openPanel();
    });

    // Insert before the first <hr> divider or at the end of <ul>
    var ul = sidebar.tagName === 'UL' ? sidebar : sidebar.querySelector('ul');
    if (!ul) { sidebar.appendChild(li); return; }
    var hr = ul.querySelector('li > hr, li.divider, hr');
    if (hr && hr.parentNode === ul) {
      ul.insertBefore(li, hr);
    } else {
      ul.appendChild(li);
    }
  }

  /* ── Wait for sidebar ───────────────────────────────────── */
  function waitForSidebar() {
    var sidebar = document.getElementById('lab-sidebar');
    if (sidebar) { injectSidebarEntry(sidebar); return; }

    var obs = new MutationObserver(function () {
      sidebar = document.getElementById('lab-sidebar');
      if (sidebar) { obs.disconnect(); injectSidebarEntry(sidebar); }
    });
    obs.observe(document.body, { childList: true, subtree: true });

    // Fallback poll (some PNetLab builds render sidebar late)
    var attempts = 0;
    var poll = setInterval(function () {
      sidebar = document.getElementById('lab-sidebar');
      if (sidebar || ++attempts > 60) {
        clearInterval(poll);
        if (sidebar) injectSidebarEntry(sidebar);
      }
    }, 500);
  }

  /* ═══════════════════════════════════════════════════════════
     Full-Screen Operations Panel
  ═══════════════════════════════════════════════════════════ */
  function buildPanel() {
    if (document.getElementById(PANEL_ID)) return;

    var overlay = document.createElement('div');
    overlay.id = PANEL_ID;
    overlay.style.cssText = [
      'position:fixed;inset:0;z-index:99999',
      'background:#080c18',
      'display:none',
      'flex-direction:column',
      'font-family:Inter,system-ui,sans-serif',
      'font-size:14px',
      'color:#e2e8f0',
      'overflow:hidden'
    ].join(';');

    overlay.innerHTML = getPanelHTML();
    document.body.appendChild(overlay);

    // Wire up all tab buttons
    overlay.querySelectorAll('[data-az-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () { azSwitchTab(btn.dataset.azTab); });
    });

    // Wire close button
    overlay.querySelector('#az-close').addEventListener('click', closePanel);

    // Wire tool run buttons
    overlay.querySelectorAll('[data-az-tool]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var tool = btn.dataset.azTool;
        var termId = btn.dataset.azTerm;
        azRunTool(tool, {}, btn, termId);
      });
    });

    // Wire bench
    var benchBtn = overlay.querySelector('#az-bench-run');
    if (benchBtn) benchBtn.addEventListener('click', function () {
      var ip = overlay.querySelector('#az-bench-ip').value.trim();
      if (!ip) { azToast('Enter Satellite IP', 'err'); return; }
      azRunTool('bench', { satellite_ip: ip }, benchBtn, 'az-term-bench');
    });

    // Wire SSL
    var sslBtn = overlay.querySelector('#az-ssl-gen');
    if (sslBtn) sslBtn.addEventListener('click', function () {
      var ip = overlay.querySelector('#az-ssl-ip').value.trim() || '192.168.1.23';
      azRunTool('ssl-generate', { ip: ip }, sslBtn, 'az-term-ssl-gen');
    });

    // Wire templates
    overlay.querySelector('#az-tmpl-refresh').addEventListener('click', azLoadTemplates);

    // Wire backup list
    overlay.querySelector('#az-backup-refresh').addEventListener('click', azLoadBackups);

    // Wire topology log
    overlay.querySelector('#az-vcs-log-btn').addEventListener('click', function () {
      var lab = overlay.querySelector('#az-vcs-lab').value.trim();
      if (!lab) { azToast('Enter lab name', 'err'); return; }
      azFetchLog(lab);
    });

    // Load initial data
    azLoadStats();
    setInterval(azLoadStats, 20000);
    azLoadTemplates();
    azLoadBackups();

    // Open to overview tab
    azSwitchTab('overview');
  }

  function openPanel() {
    buildPanel();
    document.getElementById(PANEL_ID).style.display = 'flex';
    document.body.style.overflow = 'hidden';
    azLoadStats();
  }

  function closePanel() {
    var p = document.getElementById(PANEL_ID);
    if (p) p.style.display = 'none';
    document.body.style.overflow = '';
  }

  /* ── Tab Switching ──────────────────────────────────────── */
  function azSwitchTab(name) {
    var panel = document.getElementById(PANEL_ID);
    panel.querySelectorAll('[data-az-tab]').forEach(function (b) {
      b.classList.toggle('az-tab-active', b.dataset.azTab === name);
    });
    panel.querySelectorAll('[data-az-section]').forEach(function (s) {
      s.style.display = s.dataset.azSection === name ? 'block' : 'none';
    });
  }

  /* ── Stats ──────────────────────────────────────────────── */
  function azLoadStats() {
    fetch(API_BASE + '/stats')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        azSet('az-s-ram', (d.ram_used_gb || 0) + ' GB / ' + (d.ram_total_gb || 0) + ' GB (' + (d.ram_pct || 0) + '%)');
        azSet('az-s-nodes', d.active_nodes || 0);
        azSet('az-s-watchdog', d.watchdog === 'active' ? '● Active' : '○ Inactive');
        azSet('az-s-cert', d.cert_expiry || '—');
        azSet('az-s-disk', (d.disk_used_gb || 0) + ' GB / ' + (d.disk_total_gb || 0) + ' GB (' + (d.disk_pct || 0) + '%)');
        azSet('az-s-backups', (d.backup_count || 0) + ' archive(s)');
      })
      .catch(function () {});
  }

  function azSet(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  /* ── Run Tool (SSE streaming) ───────────────────────────── */
  function azRunTool(tool, params, btn, termId) {
    var term = document.getElementById(termId);
    if (!term) return;

    term.style.display = 'block';
    term.innerHTML =
      '<div style="display:flex;gap:6px;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.06)">' +
        '<div style="width:10px;height:10px;border-radius:50%;background:#ef4444"></div>' +
        '<div style="width:10px;height:10px;border-radius:50%;background:#eab308"></div>' +
        '<div style="width:10px;height:10px;border-radius:50%;background:#22c55e"></div>' +
        '<span style="margin-left:6px;color:#475569;font-size:11px">' + tool + '</span>' +
      '</div>';

    if (btn) btn.disabled = true;

    fetch(API_BASE + '/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: tool, params: params })
    }).then(function (res) {
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buf = '';

      function pump() {
        reader.read().then(function (r) {
          if (r.done) { if (btn) btn.disabled = false; return; }
          buf += decoder.decode(r.value, { stream: true });
          var lines = buf.split('\n'); buf = lines.pop();
          lines.forEach(function (line) {
            if (!line.startsWith('data:')) return;
            try {
              var obj = JSON.parse(line.slice(5).trim());
              if (obj.type === 'line') {
                var txt = azStripAnsi(obj.data);
                if (!txt.trim()) return;
                var d = document.createElement('div');
                d.style.cssText = 'white-space:pre-wrap;word-break:break-all;padding:1px 0';
                d.style.color = azLineColor(txt);
                d.textContent = txt;
                term.appendChild(d);
                term.scrollTop = term.scrollHeight;
              } else if (obj.type === 'done') {
                var done = document.createElement('div');
                done.style.cssText = 'border-top:1px solid rgba(255,255,255,0.06);margin-top:6px;padding-top:6px;color:#475569;font-size:11px';
                done.textContent = '── Exited (code ' + obj.code + ') ──';
                term.appendChild(done);
                term.scrollTop = term.scrollHeight;
                if (btn) btn.disabled = false;
                azToast(obj.code === 0 ? '✔ Done' : '⚠ Finished with errors', obj.code === 0 ? 'ok' : 'err');
                azLoadStats();
                return;
              }
            } catch (e) {}
          });
          pump();
        }).catch(function () { if (btn) btn.disabled = false; });
      }
      pump();
    }).catch(function (e) {
      term.innerHTML += '<div style="color:#ef4444">API error: ' + e.message + '</div>';
      if (btn) btn.disabled = false;
      azToast('Cannot reach Azam-Ops API', 'err');
    });
  }

  function azStripAnsi(s) {
    return s.replace(/\x1B\[[0-9;]*[mGKHF]/g, '');
  }

  function azLineColor(s) {
    var l = s.toLowerCase();
    if (l.includes('[✔]') || l.includes('pass') || l.includes('success') || l.includes('done') || l.includes('installed') || l.includes('ok]')) return '#22c55e';
    if (l.includes('[!]') || l.includes('warn') || l.includes('fixing') || l.includes('missing')) return '#eab308';
    if (l.includes('[✘]') || l.includes('fail') || l.includes('error') || l.includes('critical')) return '#ef4444';
    if (l.includes('===') || l.includes('[*]') || l.includes('[1/') || l.includes('[2/') || l.includes('[3/') || l.includes('[4/') || l.includes('[5/') || l.includes('[6/')) return '#60a5fa';
    return '#94a3b8';
  }

  /* ── Templates ──────────────────────────────────────────── */
  function azLoadTemplates() {
    fetch(API_BASE + '/templates')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var grid = document.getElementById('az-tmpl-grid');
        if (!grid || !d.templates) return;
        var CAT_COLORS = {
          ccna:'#22c55e', bgp:'#f59e0b', mpls:'#06b6d4', ospf:'#a855f7',
          isis:'#ec4899', sdwan:'#3b82f6', datacenter:'#ef4444',
          security:'#f97316', ccie:'#dc2626', custom:'#94a3b8'
        };
        grid.innerHTML = d.templates.map(function (t) {
          var col = CAT_COLORS[t.category] || '#94a3b8';
          return '<div onclick="azDeployTemplate(\'' + t.name + '\')" style="' +
            'background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);' +
            'border-radius:10px;padding:14px;cursor:pointer;transition:all .2s;' +
            'display:flex;flex-direction:column;gap:6px" ' +
            'onmouseover="this.style.borderColor=\'rgba(99,179,237,0.3)\';this.style.background=\'rgba(255,255,255,0.07)\'" ' +
            'onmouseout="this.style.borderColor=\'rgba(255,255,255,0.08)\';this.style.background=\'rgba(255,255,255,0.04)\'">' +
              '<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:' + col + '">' + t.category + '</div>' +
              '<div style="font-size:13px;font-weight:600">' + t.name + '</div>' +
              '<div style="font-size:11px;color:#64748b;line-height:1.5">' + t.desc + '</div>' +
              '<div style="font-size:11px;color:#475569;margin-top:4px">⬡ ' + t.nodes + ' nodes</div>' +
          '</div>';
        }).join('');
        window.azDeployTemplate = function (name) {
          if (!confirm('Deploy "' + name + '" to PNetLab?')) return;
          var term = document.getElementById('az-term-deploy');
          if (term) {
            term.style.display = 'block';
            term.innerHTML = '<div style="color:#60a5fa">Deploying ' + name + '…</div>';
          }
          fetch(API_BASE + '/run', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool: 'templates-list', params: { deploy: name } })
          }).then(function (res) {
            var reader = res.body.getReader(); var dec = new TextDecoder(); var buf = '';
            function pump() {
              reader.read().then(function (r) {
                if (r.done) return;
                buf += dec.decode(r.value, { stream: true });
                var lines = buf.split('\n'); buf = lines.pop();
                lines.forEach(function (line) {
                  if (!line.startsWith('data:')) return;
                  try {
                    var obj = JSON.parse(line.slice(5).trim());
                    if (obj.type === 'line' && term) {
                      var d = document.createElement('div');
                      d.style.color = azLineColor(azStripAnsi(obj.data));
                      d.textContent = azStripAnsi(obj.data);
                      term.appendChild(d);
                    } else if (obj.type === 'done') {
                      azToast(obj.code === 0 ? '"' + name + '" deployed!' : 'Deploy had issues',
                              obj.code === 0 ? 'ok' : 'err');
                    }
                  } catch (e) {}
                });
                pump();
              });
            }
            pump();
          });
        };
      }).catch(function () {});
  }

  /* ── Backups ────────────────────────────────────────────── */
  function azLoadBackups() {
    fetch(API_BASE + '/backups')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var tbody = document.getElementById('az-backup-tbody');
        if (!tbody) return;
        if (!d.backups || d.backups.length === 0) {
          tbody.innerHTML = '<tr><td colspan="3" style="color:#475569;text-align:center;padding:16px">No backups yet — create one below.</td></tr>';
          return;
        }
        tbody.innerHTML = d.backups.map(function (b) {
          var dt = new Date(b.mtime * 1000).toLocaleString();
          return '<tr style="border-bottom:1px solid rgba(255,255,255,0.04)">' +
            '<td style="padding:8px 12px;font-family:monospace;font-size:11px;color:#94a3b8">' + b.name + '</td>' +
            '<td style="padding:8px 12px;font-size:12px">' + b.size_kb + ' KB</td>' +
            '<td style="padding:8px 12px">' +
              '<button onclick="azRestoreBackup(\'' + b.name + '\',this)" ' +
                'style="padding:4px 10px;font-size:11px;background:rgba(239,68,68,0.15);color:#ef4444;' +
                       'border:1px solid rgba(239,68,68,0.25);border-radius:6px;cursor:pointer">⏪ Restore</button>' +
            '</td>' +
          '</tr>';
        }).join('');
        window.azRestoreBackup = function (filename, btn) {
          if (!confirm('Restore ' + filename + '? Current lab data will be overwritten.')) return;
          btn.disabled = true;
          var term = document.getElementById('az-term-restore');
          if (term) term.style.display = 'block';
          fetch(API_BASE + '/restore', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
          }).then(function (res) {
            var reader = res.body.getReader(); var dec = new TextDecoder(); var buf = '';
            function pump() {
              reader.read().then(function (r) {
                if (r.done) { btn.disabled = false; return; }
                buf += dec.decode(r.value, { stream: true });
                var lines = buf.split('\n'); buf = lines.pop();
                lines.forEach(function (line) {
                  if (!line.startsWith('data:')) return;
                  try {
                    var obj = JSON.parse(line.slice(5).trim());
                    if (obj.type === 'line' && term) {
                      var d = document.createElement('div'); d.style.color = azLineColor(azStripAnsi(obj.data));
                      d.textContent = azStripAnsi(obj.data); term.appendChild(d);
                    } else if (obj.type === 'done') { btn.disabled = false; azToast(obj.code === 0 ? 'Restored!' : 'Restore failed', obj.code === 0 ? 'ok' : 'err'); }
                  } catch (e) {}
                });
                pump();
              }).catch(function () { btn.disabled = false; });
            }
            pump();
          });
        };
      }).catch(function () {});
  }

  /* ── Topology log ───────────────────────────────────────── */
  function azFetchLog(lab) {
    fetch(API_BASE + '/topology-log?lab=' + encodeURIComponent(lab))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var term = document.getElementById('az-term-vcs-log');
        if (!term) return;
        term.style.display = 'block';
        term.innerHTML = '';
        (d.output || d.error || 'No history found.').split('\n').forEach(function (line) {
          if (!line.trim()) return;
          var el = document.createElement('div');
          el.style.color = azLineColor(line);
          el.textContent = line;
          term.appendChild(el);
        });
      }).catch(function () {});
  }

  /* ── Toast ──────────────────────────────────────────────── */
  function azToast(msg, type) {
    var t = document.createElement('div');
    t.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:999999;' +
      'background:#1e293b;border:1px solid rgba(255,255,255,0.1);border-radius:10px;' +
      'padding:12px 18px;font-size:13px;color:#e2e8f0;box-shadow:0 8px 32px rgba(0,0,0,.5);' +
      'animation:az-slide-in .3s ease;font-family:Inter,system-ui,sans-serif;' +
      'border-left:3px solid ' + (type === 'ok' ? '#22c55e' : type === 'err' ? '#ef4444' : '#3b82f6');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 4000);
  }

  /* ══════════════════════════════════════════════════════════
     Panel HTML
  ══════════════════════════════════════════════════════════ */
  function getPanelHTML() {
    var TERM_STYLE = 'display:none;background:#010409;border:1px solid rgba(255,255,255,0.06);' +
      'border-radius:8px;padding:14px;font-family:"JetBrains Mono",monospace;font-size:11px;' +
      'line-height:1.7;max-height:280px;overflow-y:auto;margin-top:10px;color:#94a3b8';
    var CARD_STYLE = 'background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);' +
      'border-radius:12px;padding:20px;transition:border-color .2s';
    var INPUT_STYLE = 'width:100%;padding:8px 12px;background:rgba(0,0,0,0.3);' +
      'border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#e2e8f0;' +
      'font-family:monospace;font-size:12px;outline:none;box-sizing:border-box';
    var BTN_PRI = 'padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:500;' +
      'background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;box-shadow:0 0 20px rgba(59,130,246,.25);transition:all .2s';
    var BTN_SEC = 'padding:8px 16px;border-radius:8px;border:1px solid rgba(255,255,255,.08);cursor:pointer;' +
      'font-size:13px;font-weight:500;background:rgba(255,255,255,.06);color:#e2e8f0;transition:all .2s';
    var BTN_SM  = 'padding:5px 10px;border-radius:6px;border:none;cursor:pointer;font-size:11px;font-weight:500;' +
      'background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff';

    function statCard(id, label, icon, color) {
      return '<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);' +
        'border-radius:12px;padding:16px">' +
          '<div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;color:#475569;font-weight:500;margin-bottom:6px">' + label + '</div>' +
          '<div id="' + id + '" style="font-size:16px;font-weight:700;color:' + color + '">' + icon + ' —</div>' +
      '</div>';
    }

    function toolCard(icon, iconCol, name, cli, desc, body) {
      return '<div style="' + CARD_STYLE + '">' +
        '<div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:14px">' +
          '<div style="width:40px;height:40px;border-radius:10px;background:rgba(255,255,255,.06);' +
            'display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">' + icon + '</div>' +
          '<div>' +
            '<div style="font-size:14px;font-weight:600;margin-bottom:4px">' + name + '</div>' +
            '<div style="font-family:monospace;font-size:10px;color:' + iconCol + ';background:rgba(59,130,246,.1);' +
              'padding:1px 6px;border-radius:4px;display:inline-block">' + cli + '</div>' +
            '<div style="font-size:12px;color:#64748b;margin-top:6px;line-height:1.5">' + desc + '</div>' +
          '</div>' +
        '</div>' +
        body +
      '</div>';
    }

    var TOOL_DEFS = [
      // [icon, color, name, cli, desc, tool_id, term_id]
      ['📊','#3b82f6','Fleet Dashboard','azam-fleet','Live cluster health: RAM, KSM savings, active nodes, satellite links.','fleet','az-term-fleet'],
      ['🐕','#22c55e','Node Watchdog Status','azam-watchdog --status','Auto-recovery daemon monitoring all QEMU/IOL processes for silent crashes.','watchdog-status','az-term-watchdog'],
      ['🔥','#8b5cf6','Hot-Node Profiler','azam-perf --once','CPU/RAM/IO snapshot — instantly spots the resource-hogging node.','perf','az-term-perf'],
      ['📐','#eab308','Capacity Estimator','azam-capacity','Max node ceiling calculation with Ultra-KSM deduplication factor.','capacity','az-term-capacity'],
      ['🩺','#22c55e','Image Doctor Check','azam-doctor --check','Validates QEMU templates, IOL license, and image disk usage.','doctor','az-term-doctor'],
      ['💾','#ef4444','Create Backup Snapshot','azam-backup --backup','Snapshot all .unl files, startup configs, and MySQL DB to timestamped archive.','backup','az-term-backup'],
      ['🖥️','#06b6d4','HTML5 Console Auto-Fix','azam-console-fix --fix','Repairs WebSocket tunnel, guacd, stale pipes, generates Windows .reg handlers.','console-fix','az-term-console'],
      ['📸','#8b5cf6','Topology Git Snapshot','azam-topology-git --snapshot','Commit all changed .unl topology files to the local Git version history.','topology-snapshot','az-term-topo'],
      ['📱','#22c55e','Send WhatsApp Test Alert','azam-notify --test','Verify the WhatsApp (CallMeBot) + webhook notification pipeline is working.','notify-test','az-term-notify'],
      ['🔍','#3b82f6','Run Weekly Intelligence Scan','azam-weekly-scanner','Pull issues/commits from Codeberg, regenerate weekly plan, send WhatsApp digest.','scanner','az-term-scanner'],
    ];

    var allToolCards = TOOL_DEFS.map(function (t) {
      return toolCard(t[0], t[1], t[2], t[3], t[4],
        '<button style="' + BTN_PRI + '" data-az-tool="' + t[5] + '" data-az-term="' + t[6] + '">▶ Run</button>' +
        '<div id="' + t[6] + '" style="' + TERM_STYLE + '"></div>'
      );
    }).join('');

    return '' +
    /* ── Header bar ── */
    '<div style="display:flex;align-items:center;gap:16px;padding:14px 24px;' +
      'background:rgba(8,12,24,.9);border-bottom:1px solid rgba(255,255,255,.08);flex-shrink:0">' +
      '<div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);' +
        'display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 0 20px rgba(59,130,246,.3)">⚡</div>' +
      '<div>' +
        '<div style="font-size:16px;font-weight:700;background:linear-gradient(135deg,#3b82f6,#8b5cf6);' +
          '-webkit-background-clip:text;-webkit-text-fill-color:transparent">Azam-Features</div>' +
        '<div style="font-size:10px;color:#475569;font-weight:500;text-transform:uppercase;letter-spacing:.5px">Operations Center — ' + window.location.hostname + '</div>' +
      '</div>' +
      '<div style="flex:1"></div>' +
      /* Stats pills */
      '<div id="az-s-nodes" style="background:rgba(34,197,94,.1);color:#22c55e;padding:4px 12px;border-radius:20px;font-size:12px">— nodes</div>' +
      '<div id="az-s-watchdog" style="background:rgba(59,130,246,.1);color:#3b82f6;padding:4px 12px;border-radius:20px;font-size:12px">watchdog —</div>' +
      '<button id="az-close" style="width:32px;height:32px;border-radius:8px;border:1px solid rgba(255,255,255,.1);' +
        'background:rgba(255,255,255,.06);color:#94a3b8;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center">✕</button>' +
    '</div>' +

    /* ── Tab bar ── */
    '<div style="display:flex;gap:2px;padding:0 24px;background:rgba(8,12,24,.6);border-bottom:1px solid rgba(255,255,255,.06);flex-shrink:0;overflow-x:auto">' +
      [['overview','🏠 Overview'],['health','📊 Health'],['backup','💾 Backup & Restore'],
       ['network','🌐 Network'],['security','🔒 SSL & Security'],
       ['templates','📦 Templates'],['vcs','🕰️ Topology VCS'],['alerts','🔔 Alerts']
      ].map(function (t) {
        return '<button data-az-tab="' + t[0] + '" style="' +
          'display:flex;align-items:center;gap:6px;padding:12px 16px;border:none;background:none;' +
          'color:#64748b;cursor:pointer;font-family:inherit;font-size:13px;font-weight:500;' +
          'border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap;transition:color .2s">' +
          t[1] + '</button>';
      }).join('') +
    '</div>' +

    /* ── Body (scrollable) ── */
    '<div style="flex:1;overflow-y:auto;padding:24px">' +

      /* Stats row (always visible) */
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:24px">' +
        statCard('az-s-ram',    'RAM Usage',        '🧠', '#3b82f6') +
        statCard('az-s-cert',   'SSL Cert Expiry',  '🔒', '#8b5cf6') +
        statCard('az-s-disk',   'Disk Usage',       '💿', '#eab308') +
        statCard('az-s-backups','Lab Backups',      '💾', '#22c55e') +
      '</div>' +

      /* ─ OVERVIEW ─ */
      '<div data-az-section="overview">' +
        '<div style="font-size:16px;font-weight:700;margin-bottom:16px">⚡ Quick Actions</div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px">' +
          allToolCards +
        '</div>' +
      '</div>' +

      /* ─ HEALTH ─ */
      '<div data-az-section="health" style="display:none">' +
        '<div style="font-size:16px;font-weight:700;margin-bottom:16px">📊 Cluster Health Tools</div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px">' +
          toolCard('📊','#3b82f6','Fleet Dashboard','azam-fleet','Full multi-node health dashboard.','<button style="'+BTN_PRI+'" data-az-tool="fleet" data-az-term="az-term-fleet-h">▶ Run</button><div id="az-term-fleet-h" style="'+TERM_STYLE+'"></div>') +
          toolCard('🔥','#8b5cf6','Hot-Node Profiler','azam-perf --once','CPU/RAM/IO snapshot for all active nodes.','<button style="'+BTN_PRI+'" data-az-tool="perf" data-az-term="az-term-perf-h">▶ Snapshot</button><div id="az-term-perf-h" style="'+TERM_STYLE+'"></div>') +
          toolCard('📐','#eab308','Capacity Estimator','azam-capacity','Node ceiling with Ultra-KSM factor.','<button style="'+BTN_PRI+'" data-az-tool="capacity" data-az-term="az-term-cap-h">▶ Run</button><div id="az-term-cap-h" style="'+TERM_STYLE+'"></div>') +
          toolCard('🩺','#22c55e','Image Doctor','azam-doctor','QEMU template audit + disk compression.','<button style="'+BTN_PRI+'" data-az-tool="doctor" data-az-term="az-term-doc-h">▶ Check</button><button style="'+BTN_SEC+';margin-left:8px" data-az-tool="doctor-compress" data-az-term="az-term-doc-h">🗜 Compress</button><div id="az-term-doc-h" style="'+TERM_STYLE+'"></div>') +
          toolCard('🐕','#06b6d4','Node Watchdog','azam-watchdog','Systemd daemon — detect crashes, auto-recover.','<button style="'+BTN_PRI+'" data-az-tool="watchdog-status" data-az-term="az-term-wd-h">▶ Status</button><button style="'+BTN_SEC+';margin-left:8px" data-az-tool="watchdog-install" data-az-term="az-term-wd-h">⚙ Install</button><div id="az-term-wd-h" style="'+TERM_STYLE+'"></div>') +
        '</div>' +
      '</div>' +

      /* ─ BACKUP ─ */
      '<div data-az-section="backup" style="display:none">' +
        '<div style="font-size:16px;font-weight:700;margin-bottom:16px">💾 Backup & Restore Engine</div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px">' +
          toolCard('📸','#22c55e','Create Backup','azam-backup --backup','Snapshot all .unl + configs + MySQL.','<button style="'+BTN_PRI+'" data-az-tool="backup" data-az-term="az-term-bk2">💾 Backup Now</button><div id="az-term-bk2" style="'+TERM_STYLE+'"></div>') +
          '<div style="'+CARD_STYLE+'">' +
            '<div style="font-size:14px;font-weight:600;margin-bottom:10px">📋 Browse & Restore Backups</div>' +
            '<div style="display:flex;gap:8px;margin-bottom:12px">' +
              '<button id="az-backup-refresh" style="'+BTN_SM+'">🔄 Refresh</button>' +
            '</div>' +
            '<table style="width:100%;border-collapse:collapse">' +
              '<thead><tr>' +
                '<th style="text-align:left;font-size:10px;text-transform:uppercase;color:#475569;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,.06)">Archive</th>' +
                '<th style="text-align:left;font-size:10px;text-transform:uppercase;color:#475569;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,.06)">Size</th>' +
                '<th style="text-align:left;font-size:10px;text-transform:uppercase;color:#475569;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,.06)">Action</th>' +
              '</tr></thead>' +
              '<tbody id="az-backup-tbody"><tr><td colspan="3" style="color:#475569;text-align:center;padding:16px">Click Refresh</td></tr></tbody>' +
            '</table>' +
            '<div id="az-term-restore" style="'+TERM_STYLE+'"></div>' +
          '</div>' +
          toolCard('🕰️','#8b5cf6','Topology Git Snapshot','azam-topology-git --snapshot','Commit changed .unl files to version history.','<button style="'+BTN_PRI+'" data-az-tool="topology-snapshot" data-az-term="az-term-topo-bk">▶ Snapshot</button><div id="az-term-topo-bk" style="'+TERM_STYLE+'"></div>') +
        '</div>' +
      '</div>' +

      /* ─ NETWORK ─ */
      '<div data-az-section="network" style="display:none">' +
        '<div style="font-size:16px;font-weight:700;margin-bottom:16px">🌐 Network & Console Tools</div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px">' +
          '<div style="'+CARD_STYLE+'">' +
            '<div style="font-size:14px;font-weight:600;margin-bottom:4px">📡 MTU 9000 & RoCE Benchmark</div>' +
            '<div style="font-family:monospace;font-size:10px;color:#06b6d4;background:rgba(6,182,212,.1);padding:1px 6px;border-radius:4px;display:inline-block;margin-bottom:8px">azam-bench &lt;SAT_IP&gt;</div>' +
            '<div style="font-size:12px;color:#64748b;margin-bottom:12px">5-probe fabric check: ICMP RTT, MTU 9000 jumbo frames, Soft-RoCE counters, iperf3 throughput.</div>' +
            '<input id="az-bench-ip" style="'+INPUT_STYLE+';margin-bottom:10px" type="text" placeholder="Satellite IP (e.g. 192.168.1.50)">' +
            '<button id="az-bench-run" style="'+BTN_PRI+'">▶ Run Benchmark</button>' +
            '<div id="az-term-bench" style="'+TERM_STYLE+'"></div>' +
          '</div>' +
          '<div style="'+CARD_STYLE+'">' +
            '<div style="font-size:14px;font-weight:600;margin-bottom:4px">⚡ Anti-Bootstorm Engine</div>' +
            '<div style="font-family:monospace;font-size:10px;color:#3b82f6;background:rgba(59,130,246,.1);padding:1px 6px;border-radius:4px;display:inline-block;margin-bottom:8px">azam-bootstorm --lab &lt;PATH&gt;</div>' +
            '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Staggered boot: heavy→medium→light with configurable batch sizes and delays.</div>' +
            '<input id="az-boot-lab" style="'+INPUT_STYLE+';margin-bottom:10px" type="text" placeholder="Lab path (e.g. /Admin/my-lab.unl)">' +
            '<button onclick="azBoostorm(false)" style="'+BTN_PRI+'">▶ Start</button>&nbsp;' +
            '<button onclick="azBoostorm(true)" style="'+BTN_SEC+'">👁 Dry Run</button>' +
            '<div id="az-term-boot" style="'+TERM_STYLE+'">'+
              '<div style="color:#60a5fa;padding:10px">Enter the lab path above and click Start. Or SSH and run: azam-bootstorm --lab /Admin/mylab.unl</div>' +
            '</div>' +
          '</div>' +
          toolCard('🖥️','#22c55e','HTML5 Console Auto-Fixer','azam-console-fix','WebSocket tunnel, guacd, stale pipes + Windows .reg URL handlers.','<button style="'+BTN_PRI+'" data-az-tool="console-fix" data-az-term="az-term-con-n">🔧 Fix Now</button>&nbsp;<button style="'+BTN_SEC+'" data-az-tool="console-check" data-az-term="az-term-con-n">▶ Check</button><div id="az-term-con-n" style="'+TERM_STYLE+'"></div>') +
        '</div>' +
      '</div>' +

      /* ─ SECURITY ─ */
      '<div data-az-section="security" style="display:none">' +
        '<div style="font-size:16px;font-weight:700;margin-bottom:16px">🔒 SSL & Security</div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px">' +
          toolCard('📜','#22c55e','Certificate Status','azam-ssl --status','Check current cert subject, SANs, and expiry.','<button style="'+BTN_PRI+'" data-az-tool="ssl-status" data-az-term="az-term-ssl-s">▶ Check</button><div id="az-term-ssl-s" style="'+TERM_STYLE+'"></div>') +
          '<div style="'+CARD_STYLE+'">' +
            '<div style="font-size:14px;font-weight:600;margin-bottom:4px">🔑 Generate 5-Year SSL Certificate</div>' +
            '<div style="font-family:monospace;font-size:10px;color:#3b82f6;background:rgba(59,130,246,.1);padding:1px 6px;border-radius:4px;display:inline-block;margin-bottom:8px">azam-ssl --generate</div>' +
            '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Creates a 5-year SAN TLS certificate. Exports a Windows CA trust package to eliminate all browser security warnings.</div>' +
            '<input id="az-ssl-ip" style="'+INPUT_STYLE+';margin-bottom:10px" type="text" placeholder="Master IP (default: 192.168.1.23)">' +
            '<button id="az-ssl-gen" style="'+BTN_PRI+'">🔑 Generate</button>' +
            '<div id="az-term-ssl-gen" style="'+TERM_STYLE+'"></div>' +
            '<div style="font-size:11px;color:#475569;margin-top:10px">After generation, install <code style="color:#06b6d4">/opt/azambasha/azam-pnet-ca.crt</code> into Windows Trusted Root CA.</div>' +
          '</div>' +
        '</div>' +
      '</div>' +

      /* ─ TEMPLATES ─ */
      '<div data-az-section="templates" style="display:none">' +
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">' +
          '<div style="font-size:16px;font-weight:700">📦 Lab Template Marketplace</div>' +
          '<button id="az-tmpl-refresh" style="'+BTN_SM+'">🔄 Refresh</button>' +
          '<span style="font-size:12px;color:#475569">Click any card to deploy instantly</span>' +
        '</div>' +
        '<div id="az-tmpl-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px">Loading…</div>' +
        '<div id="az-term-deploy" style="'+TERM_STYLE+';margin-top:16px"></div>' +
      '</div>' +

      /* ─ VCS ─ */
      '<div data-az-section="vcs" style="display:none">' +
        '<div style="font-size:16px;font-weight:700;margin-bottom:16px">🕰️ Topology Version Control</div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px">' +
          toolCard('📸','#8b5cf6','Snapshot All Topologies','azam-topology-git --snapshot','Commit changed .unl files to Git. Runs automatically every 5 min via cron.','<button style="'+BTN_PRI+'" data-az-tool="topology-snapshot" data-az-term="az-term-vcs-sn">▶ Snapshot Now</button><div id="az-term-vcs-sn" style="'+TERM_STYLE+'"></div>') +
          '<div style="'+CARD_STYLE+'">' +
            '<div style="font-size:14px;font-weight:600;margin-bottom:4px">📖 View Topology History</div>' +
            '<div style="font-family:monospace;font-size:10px;color:#3b82f6;background:rgba(59,130,246,.1);padding:1px 6px;border-radius:4px;display:inline-block;margin-bottom:8px">azam-topology-git --log &lt;lab&gt;</div>' +
            '<div style="font-size:12px;color:#64748b;margin-bottom:10px">Every .unl save is committed with a timestamp. View the full diff history for any topology.</div>' +
            '<input id="az-vcs-lab" style="'+INPUT_STYLE+';margin-bottom:10px" type="text" placeholder="Lab name (e.g. ccna-routing)">' +
            '<button id="az-vcs-log-btn" style="'+BTN_PRI+'">▶ Show History</button>' +
            '<div id="az-term-vcs-log" style="'+TERM_STYLE+'"></div>' +
          '</div>' +
        '</div>' +
      '</div>' +

      /* ─ ALERTS ─ */
      '<div data-az-section="alerts" style="display:none">' +
        '<div style="font-size:16px;font-weight:700;margin-bottom:16px">🔔 Alerts & Weekly Intelligence</div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px">' +
          toolCard('📱','#22c55e','Send WhatsApp Test Alert','azam-notify --test','Verify the CallMeBot WhatsApp + webhook pipeline.','<button style="'+BTN_PRI+'" data-az-tool="notify-test" data-az-term="az-term-ntfy">📱 Send Test</button><div id="az-term-ntfy" style="'+TERM_STYLE+'"></div>') +
          toolCard('🔍','#3b82f6','Run Weekly Intelligence Scan','azambasha-weekly-codeberg-scanner.py','Pull issues + commits from Codeberg, regenerate weekly plan, send WhatsApp digest.','<button style="'+BTN_PRI+'" data-az-tool="scanner" data-az-term="az-term-scan2">▶ Run Scan</button><div id="az-term-scan2" style="'+TERM_STYLE+'"></div>') +
        '</div>' +
      '</div>' +

    '</div>'; /* end body */
  }

  /* ── Bootstorm helper (client-side) ──────────────────────── */
  window.azBoostorm = function (dryRun) {
    var lab = document.getElementById('az-boot-lab').value.trim();
    var term = document.getElementById('az-term-boot');
    if (!lab) { azToast('Enter lab path first', 'err'); return; }
    if (term) {
      term.style.display = 'block';
      term.innerHTML = '<div style="color:#60a5fa">SSH to ' + window.location.hostname + ' and run:<br>' +
        '<span style="color:#22c55e">azam-bootstorm --lab ' + lab + (dryRun ? ' --dry-run' : '') + '</span></div>';
    }
    azToast('Bootstorm: connect via SSH and run the command shown.', 'info');
  };

  /* ── CSS for active tab ──────────────────────────────────── */
  function injectStyles() {
    if (document.getElementById('az-feat-style')) return;
    var s = document.createElement('style');
    s.id = 'az-feat-style';
    s.textContent = '' +
      '@import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap");' +
      '#' + PANEL_ID + ' [data-az-tab].az-tab-active{color:#3b82f6!important;border-bottom-color:#3b82f6!important}' +
      '#' + PANEL_ID + ' [data-az-tab]:hover{color:#e2e8f0!important}' +
      '#' + PANEL_ID + ' button:disabled{opacity:.5;cursor:not-allowed}' +
      '@keyframes az-slide-in{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:none}}' +
      '#pnq-azam-features:hover a{opacity:.85}' +
      '#pnq-azam-features a{transition:opacity .2s}';
    document.head.appendChild(s);
  }

  /* ── Init ───────────────────────────────────────────────── */
  injectStyles();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitForSidebar);
  } else {
    waitForSidebar();
  }

})();
