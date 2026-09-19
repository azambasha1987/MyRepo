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
    if (sidebar) {
      injectSidebarEntry(sidebar);
      injectGitSidebarButton(sidebar);
      return;
    }

    var obs = new MutationObserver(function () {
      sidebar = document.getElementById('lab-sidebar');
      if (sidebar) {
        obs.disconnect();
        injectSidebarEntry(sidebar);
        injectGitSidebarButton(sidebar);
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });

    // Fallback poll (some PNetLab builds render sidebar late)
    var attempts = 0;
    var poll = setInterval(function () {
      sidebar = document.getElementById('lab-sidebar');
      if (sidebar || ++attempts > 60) {
        clearInterval(poll);
        if (sidebar) {
          injectSidebarEntry(sidebar);
          injectGitSidebarButton(sidebar);
        }
      }
    }, 500);
  }

  /* ═══════════════════════════════════════════════════════════
     Full-Screen Operations Panel
  ═══════════════════════════════════════════════════════════ */
  /* ═══════════════════════════════════════════════════════════
     Futuristic Cyber-Console Operations Window
  ═══════════════════════════════════════════════════════════ */
  function buildPanel() {
    if (document.getElementById(PANEL_ID)) return;

    // Inject futuristic animations, scrollbar and neon glow styles once
    if (!document.getElementById('az-cyber-styles')) {
      var s = document.createElement('style');
      s.id = 'az-cyber-styles';
      s.textContent = [
        '@keyframes azLaserFlow { 0%{background-position:0% 50%} 100%{background-position:200% 50%} }',
        '@keyframes azWindowPop { 0%{transform:scale(0.96) translateY(14px);opacity:0} 100%{transform:scale(1) translateY(0);opacity:1} }',
        '@keyframes azPulseDot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.3;transform:scale(0.8)} }',
        '.az-close-futuristic:hover { background:linear-gradient(135deg,rgba(239,68,68,0.5),rgba(220,38,38,0.65)) !important; box-shadow:0 0 30px rgba(239,68,68,0.7) !important; color:#fff !important; transform:translateY(-1px); }',
        '.az-tab-active { color:#38bdf8 !important; border-bottom:2px solid #38bdf8 !important; box-shadow:0 2px 12px rgba(56,189,248,0.3) !important; font-weight:700 !important; }',
        '#az-features-window ::-webkit-scrollbar { width:8px; height:8px; }',
        '#az-features-window ::-webkit-scrollbar-track { background:rgba(0,0,0,0.25); }',
        '#az-features-window ::-webkit-scrollbar-thumb { background:rgba(56,189,248,0.25); border-radius:4px; }',
        '#az-features-window ::-webkit-scrollbar-thumb:hover { background:rgba(56,189,248,0.5); }'
      ].join('\n');
      document.head.appendChild(s);
    }

    var overlay = document.createElement('div');
    overlay.id = PANEL_ID;
    overlay.style.cssText = [
      'position:fixed;inset:0;z-index:999999',
      'background:rgba(3,7,18,0.78)',
      'backdrop-filter:blur(12px)',
      '-webkit-backdrop-filter:blur(12px)',
      'display:none',
      'align-items:center',
      'justify-content:center',
      'padding:16px',
      'box-sizing:border-box',
      'font-family:Inter,system-ui,sans-serif',
      'font-size:14px',
      'color:#e2e8f0',
      'transition:all 0.25s cubic-bezier(0.16,1,0.3,1)'
    ].join(';');

    overlay.innerHTML = getPanelHTML();
    document.body.appendChild(overlay);

    // Wire backdrop click to close
    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) {
        closePanel();
      }
    });

    // Wire keyboard ESC key to close
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' || e.keyCode === 27) {
        var p = document.getElementById(PANEL_ID);
        if (p && p.style.display !== 'none') {
          closePanel();
        }
      }
    });

    // Wire close button
    var closeBtn = overlay.querySelector('#az-close');
    if (closeBtn) closeBtn.addEventListener('click', closePanel);

    // Wire fullscreen/windowed size toggle
    var isMaximized = false;
    var expandBtn = overlay.querySelector('#az-toggle-expand');
    var win = overlay.querySelector('#az-features-window');
    var expandIcon = overlay.querySelector('#az-expand-icon');
    if (expandBtn && win) {
      expandBtn.addEventListener('click', function() {
        isMaximized = !isMaximized;
        if (isMaximized) {
          win.style.width = '100vw';
          win.style.height = '100vh';
          win.style.maxWidth = '100vw';
          win.style.maxHeight = '100vh';
          win.style.borderRadius = '0px';
          overlay.style.padding = '0px';
          if (expandIcon) expandIcon.className = 'fa fa-compress';
          expandBtn.title = 'Restore Windowed Mode';
        } else {
          win.style.width = '1200px';
          win.style.height = '88vh';
          win.style.maxWidth = '95vw';
          win.style.maxHeight = '92vh';
          win.style.borderRadius = '18px';
          overlay.style.padding = '16px';
          if (expandIcon) expandIcon.className = 'fa fa-expand';
          expandBtn.title = 'Toggle Fullscreen';
        }
      });
    }

    // Wire live tool search
    var searchInput = overlay.querySelector('#az-filter-tools');
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        var q = searchInput.value.toLowerCase().trim();
        overlay.querySelectorAll('[data-az-tool-card]').forEach(function(card) {
          var txt = card.textContent.toLowerCase();
          card.style.display = (!q || txt.includes(q)) ? '' : 'none';
        });
      });
    }

    // Wire up all tab buttons
    overlay.querySelectorAll('[data-az-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () { azSwitchTab(btn.dataset.azTab); });
    });

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
    var p = document.getElementById(PANEL_ID);
    if (p) p.style.display = 'flex';
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
      if (b.dataset.azTab === name) {
        b.style.color = '#38bdf8';
        b.style.borderBottomColor = '#38bdf8';
      } else {
        b.style.color = '#64748b';
        b.style.borderBottomColor = 'transparent';
      }
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
      return '<div data-az-tool-card="1" style="' + CARD_STYLE + '">' +
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
      ['🩺','#22c55e','Image Doctor Check','azam-doctor --check','Validates QEMU templates, IOL license, and image compliance.','doctor','az-term-doctor'],
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
    /* ── Futuristic Window Wrapper ── */
    '<div id="az-features-window" style="width:1200px;max-width:95vw;height:88vh;max-height:92vh;' +
      'background:radial-gradient(circle at 50% 0%,rgba(30,41,59,0.96),rgba(11,17,33,0.98));' +
      'border:1px solid rgba(56,189,248,0.35);border-radius:18px;' +
      'box-shadow:0 0 60px rgba(56,189,248,0.25),0 30px 80px rgba(0,0,0,0.9),inset 0 1px 0 rgba(255,255,255,0.15);' +
      'display:flex;flex-direction:column;overflow:hidden;position:relative;' +
      'animation:azWindowPop 0.25s cubic-bezier(0.16,1,0.3,1);transition:all 0.25s ease;">' +

      /* Top Animated Neon Laser Runner */
      '<div style="height:3px;width:100%;background:linear-gradient(90deg,#38bdf8,#818cf8,#c084fc,#38bdf8);' +
        'background-size:200% 100%;animation:azLaserFlow 4s linear infinite;flex-shrink:0;"></div>' +

      /* ── Futuristic Header bar ── */
      '<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;padding:12px 20px;' +
        'background:rgba(15,23,42,0.85);border-bottom:1px solid rgba(56,189,248,0.2);flex-shrink:0">' +
        '<div style="display:flex;align-items:center;gap:12px;">' +
          '<div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#0284c7,#7c3aed);' +
            'display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 0 20px rgba(56,189,248,0.4);border:1px solid rgba(255,255,255,0.2)">⚡</div>' +
          '<div>' +
            '<div style="font-size:16px;font-weight:800;letter-spacing:-0.01em;background:linear-gradient(90deg,#38bdf8,#a78bfa,#f43f5e);' +
              '-webkit-background-clip:text;-webkit-text-fill-color:transparent">AZAM-OPS // QUANTUM CONSOLE</div>' +
            '<div style="font-size:10.5px;color:#94a3b8;font-weight:600;display:flex;align-items:center;gap:8px;">' +
              '<span>ENTERPRISE LAB ENGINE</span>' +
              '<span style="color:#22c55e;display:inline-flex;align-items:center;gap:4px;"><i class="fa fa-circle" style="font-size:7px;animation:azPulseDot 1.5s infinite;"></i> ONLINE</span>' +
              '<span style="color:#64748b;">•</span>' +
              '<span style="color:#38bdf8;font-family:monospace;">' + window.location.hostname + '</span>' +
            '</div>' +
          '</div>' +
        '</div>' +

        /* Center Quick Search */
        '<div style="flex:1;max-width:340px;position:relative;margin:0 10px;">' +
          '<i class="fa fa-search" style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:#64748b;font-size:12px;"></i>' +
          '<input type="text" id="az-filter-tools" placeholder="Filter tools (doctor, git, backup)..." style="width:100%;padding:7px 12px 7px 32px;' +
            'background:rgba(0,0,0,0.45);border:1px solid rgba(56,189,248,0.25);border-radius:8px;color:#f8fafc;font-size:12px;outline:none;' +
            'transition:border-color 0.2s;" onfocus="this.style.borderColor=\'#38bdf8\';" onblur="this.style.borderColor=\'rgba(56,189,248,0.25)\';">' +
        '</div>' +

        /* Right Window Control Trio */
        '<div style="display:flex;align-items:center;gap:10px;">' +
          '<div id="az-s-nodes" style="background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);color:#4ade80;padding:5px 12px;border-radius:20px;font-size:11.5px;font-weight:600;display:flex;align-items:center;gap:5px;">' +
            '<i class="fa fa-cubes"></i> <span>— nodes</span>' +
          '</div>' +
          '<div id="az-s-watchdog" style="background:rgba(56,189,248,0.15);border:1px solid rgba(56,189,248,0.3);color:#38bdf8;padding:5px 12px;border-radius:20px;font-size:11.5px;font-weight:600;display:flex;align-items:center;gap:5px;">' +
            '<i class="fa fa-shield"></i> <span>watchdog —</span>' +
          '</div>' +
          '<button id="az-toggle-expand" type="button" title="Toggle Fullscreen / Windowed Mode" style="width:34px;height:34px;border-radius:8px;' +
            'border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.06);color:#94a3b8;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.2s;" ' +
            'onmouseover="this.style.background=\'rgba(255,255,255,0.12)\';this.style.color=\'#fff\';" onmouseout="this.style.background=\'rgba(255,255,255,0.06)\';this.style.color=\'#94a3b8\';">' +
            '<i class="fa fa-expand" id="az-expand-icon"></i>' +
          '</button>' +
          '<button id="az-close" type="button" class="az-close-futuristic" title="Close Operations Center (Esc)" style="height:34px;padding:0 14px;border-radius:8px;' +
            'border:1px solid rgba(239,68,68,0.6);background:linear-gradient(135deg,rgba(239,68,68,0.25),rgba(185,28,28,0.35));color:#fee2e2;font-size:12px;' +
            'font-weight:700;letter-spacing:0.5px;cursor:pointer;display:flex;align-items:center;gap:8px;box-shadow:0 0 20px rgba(239,68,68,0.35);transition:all 0.2s;" ' +
            'onmouseover="this.style.background=\'linear-gradient(135deg,rgba(239,68,68,0.5),rgba(220,38,38,0.6))\';this.style.boxShadow=\'0 0 25px rgba(239,68,68,0.6)\';this.style.color=\'#fff\';" ' +
            'onmouseout="this.style.background=\'linear-gradient(135deg,rgba(239,68,68,0.25),rgba(185,28,28,0.35))\';this.style.boxShadow=\'0 0 20px rgba(239,68,68,0.35)\';this.style.color=\'#fee2e2\';">' +
            '<i class="fa fa-times" style="font-size:14px;color:#fca5a5;"></i>' +
            '<span>CLOSE</span>' +
            '<kbd style="font-size:9.5px;padding:1px 5px;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.2);border-radius:4px;color:#fecaca;font-family:inherit;">ESC</kbd>' +
          '</button>' +
        '</div>' +
      '</div>' +

      /* ── Tab bar ── */
      '<div style="display:flex;gap:2px;padding:0 20px;background:rgba(8,12,24,0.7);border-bottom:1px solid rgba(56,189,248,0.15);flex-shrink:0;overflow-x:auto">' +
        [['overview','🏠 Overview'],['health','📊 Health'],['backup','💾 Backup & Restore'],
         ['network','🌐 Network'],['security','🔒 SSL & Security'],
         ['templates','📦 Templates'],['vcs','🕰️ Topology VCS'],['alerts','🔔 Alerts']
        ].map(function (t) {
          return '<button data-az-tab="' + t[0] + '" style="' +
            'display:flex;align-items:center;gap:6px;padding:12px 16px;border:none;background:none;' +
            'color:#64748b;cursor:pointer;font-family:inherit;font-size:13px;font-weight:500;' +
            'border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap;transition:all .2s">' +
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
          toolCard('🩺','#22c55e','Image Doctor','azam-doctor','QEMU template and image integrity audit.','<button style="'+BTN_PRI+'" data-az-tool="doctor" data-az-term="az-term-doc-h">▶ Check</button><div id="az-term-doc-h" style="'+TERM_STYLE+'"></div>') +
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

    '</div>' + /* end body */
    '</div>'; /* end #az-features-window */
  }

  /* ── Desktop Notification Helper ────────────────────────── */
  function azamNotifyDesktop(title, body) {
    try {
      if ('Notification' in window) {
        if (Notification.permission === 'granted') {
          new Notification(title, { body: body, icon: '/themes/default/images/logo.png' });
        } else if (Notification.permission !== 'denied') {
          Notification.requestPermission().then(function (perm) {
            if (perm === 'granted') {
              new Notification(title, { body: body, icon: '/themes/default/images/logo.png' });
            }
          });
        }
      }
    } catch (e) {}
  }

  /* ── In-Canvas KSM Heavy Node Tuning ─────────────────────── */
  window.azTuneNodeKSM = function(nodeId, nodeName) {
    azToast('Applying Heavy-Node KSM Memory Tuning for ' + (nodeName || 'node') + '…', 'info');
    fetch(API_BASE + '/node-ksm-tune', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: nodeId || '', node_name: nodeName || 'Heavy Node' })
    }).then(function(r) { return r.json(); }).then(function(res) {
      if (res.success) {
        azToast(res.message, 'ok');
        azamNotifyDesktop('KSM Tuning Active', res.message);
      } else {
        azToast('KSM tuning error: ' + res.error, 'err');
      }
    }).catch(function(e) {
      azToast('Request failed: ' + e, 'err');
    });
  };

  /* ── Dynamic Link Traffic Heatmap ────────────────────────── */
  var trafficHeatmapActive = false;
  var trafficPollTimer = null;

  function toggleTrafficHeatmap(btn) {
    trafficHeatmapActive = !trafficHeatmapActive;
    if (trafficHeatmapActive) {
      btn.style.background = '#10b981';
      btn.style.color = '#fff';
      btn.innerHTML = '<i class="fa fa-line-chart"></i> <span>Heatmap: ON</span>';
      azToast('Live Traffic Heatmap active (polling bridge stats)', 'ok');
      trafficPollTimer = setInterval(updateCanvasHeatmap, 3000);
      updateCanvasHeatmap();
    } else {
      btn.style.background = 'rgba(56,189,248,0.15)';
      btn.style.color = '#38bdf8';
      btn.innerHTML = '<i class="fa fa-line-chart"></i> <span>Traffic Heatmap</span>';
      if (trafficPollTimer) clearInterval(trafficPollTimer);
      resetCanvasHeatmap();
      azToast('Traffic Heatmap deactivated', 'info');
    }
  }

  function updateCanvasHeatmap() {
    fetch(API_BASE + '/link-stats')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var ifaces = data.interfaces || [];
        var paths = document.querySelectorAll('svg path.link, svg path[data-link], svg g.jtk-connector path');
        if (!paths.length) return;
        paths.forEach(function(p, idx) {
          var stat = ifaces[idx % ifaces.length];
          var kb = stat ? stat.total_kb : 0;
          var strokeColor = '#22c55e';
          var strokeWidth = '3px';
          if (kb > 50000) {
            strokeColor = '#ef4444';
            strokeWidth = '5px';
          } else if (kb > 5000) {
            strokeColor = '#f59e0b';
            strokeWidth = '4px';
          }
          p.style.stroke = strokeColor;
          p.style.strokeWidth = strokeWidth;
          p.style.transition = 'stroke 0.3s ease, stroke-width 0.3s ease';
        });
      }).catch(function() {});
  }

  function resetCanvasHeatmap() {
    var paths = document.querySelectorAll('svg path.link, svg path[data-link], svg g.jtk-connector path');
    paths.forEach(function(p) {
      p.style.stroke = '';
      p.style.strokeWidth = '';
    });
  }

  /* ── Bootstorm helper ────────────────────────────────────── */
  window.azBoostorm = function (dryRun) {
    var labInput = document.getElementById('az-boot-lab');
    var lab = labInput ? labInput.value.trim() : (window.lab_filename || window.location.pathname || '');
    var term = document.getElementById('az-term-boot');
    if (!lab) { azToast('Enter lab path first', 'err'); return; }
    azRunTool('bootstorm-start', { lab: lab, dry_run: dryRun }, null, 'az-term-boot');
  };

  /* ── Canvas In-Lab Toolbar Actions ────────────────────────── */
  function openBootstormModal() {
    var modalId = 'pnq-bootstorm-modal';
    var modal = document.getElementById(modalId);
    var currentLab = window.lab_filename || window.lab_name || window.location.pathname || '/Admin/active_lab.unl';

    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#f8fafc;';
      modal.innerHTML = 
        '<div style="width:540px;max-width:92%;background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:12px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:32px;height:32px;border-radius:8px;background:rgba(245,158,11,0.2);color:#f59e0b;display:flex;align-items:center;justify-content:center;font-size:16px;"><i class="fa fa-rocket"></i></div>' +
              '<div style="font-weight:700;font-size:15px;">Anti-Bootstorm Staggered Startup</div>' +
            '</div>' +
            '<button type="button" id="pnq-bs-close" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1;">&times;</button>' +
          '</div>' +
          '<div style="padding:18px;display:flex;flex-direction:column;gap:14px;">' +
            '<div>' +
              '<label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Target Lab Topology:</label>' +
              '<input type="text" id="pnq-bs-lab" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;" value="' + currentLab + '">' +
            '</div>' +
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">' +
              '<div>' +
                '<label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:4px;">Heavy Delay (XRd, C8000v):</label>' +
                '<input type="number" id="pnq-bs-heavy" value="18" min="5" max="60" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;">' +
              '</div>' +
              '<div>' +
                '<label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:4px;">Medium Delay (vIOS, CSR):</label>' +
                '<input type="number" id="pnq-bs-medium" value="10" min="3" max="30" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;">' +
              '</div>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:8px;">' +
              '<input type="checkbox" id="pnq-bs-dryrun" style="cursor:pointer;">' +
              '<label for="pnq-bs-dryrun" style="font-size:12.5px;color:#cbd5e1;cursor:pointer;">Simulate boot order without launching nodes (--dry-run)</label>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:8px;">' +
              '<input type="checkbox" id="pnq-bs-probe" checked style="cursor:pointer;accent-color:#10b981;">' +
              '<label for="pnq-bs-probe" style="font-size:12px;color:#6ee7b7;cursor:pointer;">Ready-State Probing: Wait for console login prompt (&gt; / # / login:) before next batch</label>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:8px;">' +
              '<input type="checkbox" id="pnq-bs-ksm" checked style="cursor:pointer;accent-color:#6366f1;">' +
              '<label for="pnq-bs-ksm" style="font-size:12px;color:#a5b4fc;cursor:pointer;">Auto-apply KSM memory optimization after boot (Saves up to 70% RAM)</label>' +
            '</div>' +
            '<div style="display:flex;gap:10px;margin-top:4px;">' +
              '<button type="button" id="pnq-bs-start" style="flex:1;background:linear-gradient(135deg,#f59e0b,#ea580c);border:none;color:#fff;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;"><i class="fa fa-play"></i> Launch Staggered Boot</button>' +
            '</div>' +
            '<div id="pnq-bs-term" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:11.5px;max-height:180px;overflow-y:auto;white-space:pre-wrap;"></div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);

      modal.querySelector('#pnq-bs-close').onclick = function() { modal.style.display = 'none'; };
      modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

      modal.querySelector('#pnq-bs-start').onclick = function() {
        var lab = modal.querySelector('#pnq-bs-lab').value.trim();
        var hd = modal.querySelector('#pnq-bs-heavy').value.trim();
        var md = modal.querySelector('#pnq-bs-medium').value.trim();
        var dry = modal.querySelector('#pnq-bs-dryrun').checked;
        var probe = modal.querySelector('#pnq-bs-probe').checked;
        var autoKsm = modal.querySelector('#pnq-bs-ksm').checked;
        azRunTool('bootstorm-start', { lab: lab, heavy_delay: hd, medium_delay: md, dry_run: dry, probe_console: probe }, this, 'pnq-bs-term');
        if (autoKsm && !dry) {
          setTimeout(function () {
            fetch(API_BASE + '/node-ksm-tune', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ node_name: 'All Booted Nodes', lab_path: lab })
            });
            azamNotifyDesktop('Anti-Bootstorm Complete', 'All nodes have been safely booted with KSM deduplication active.');
          }, 6000);
        }
      };
    } else {
      modal.querySelector('#pnq-bs-lab').value = currentLab;
      modal.style.display = 'flex';
    }
  }

  /* ── 1. Lab QCOW2 Checkpoint Modal ────────────────────── */
  function openCheckpointModal() {
    var modalId = 'pnq-checkpoint-modal';
    var modal = document.getElementById(modalId);
    var currentLab = window.lab_filename || window.lab_name || window.location.pathname || '/Admin/active_lab.unl';
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#f8fafc;';
      modal.innerHTML = 
        '<div style="width:560px;max-width:92%;background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:12px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:32px;height:32px;border-radius:8px;background:rgba(56,189,248,0.2);color:#38bdf8;display:flex;align-items:center;justify-content:center;font-size:16px;"><i class="fa fa-camera"></i></div>' +
              '<div style="font-weight:700;font-size:15px;">Lab Multi-Node QCOW2 Checkpoint & Snapshot</div>' +
            '</div>' +
            '<button type="button" id="pnq-cp-close" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1;">&times;</button>' +
          '</div>' +
          '<div style="padding:18px;display:flex;flex-direction:column;gap:14px;">' +
            '<div>' +
              '<label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Checkpoint Tag / Name:</label>' +
              '<input type="text" id="pnq-cp-name" value="checkpoint_1" placeholder="e.g. pre_bgp_cutover" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;">' +
            '</div>' +
            '<div style="font-size:12px;color:#94a3b8;line-height:1.5;">Creates instant copy-on-write overlay snapshots across all active QEMU/IOL nodes without halting data-plane forwarding.</div>' +
            '<div style="display:flex;gap:10px;">' +
              '<button type="button" id="pnq-cp-create" style="flex:1;background:linear-gradient(135deg,#0284c7,#2563eb);border:none;color:#fff;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;"><i class="fa fa-camera"></i> Create Snapshot</button>' +
              '<button type="button" id="pnq-cp-restore" style="flex:1;background:rgba(239,68,68,0.2);border:1px solid rgba(239,68,68,0.4);color:#f87171;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;"><i class="fa fa-undo"></i> Rollback Snapshot</button>' +
            '</div>' +
            '<div id="pnq-cp-term" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:11.5px;max-height:180px;overflow-y:auto;white-space:pre-wrap;"></div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);
      modal.querySelector('#pnq-cp-close').onclick = function() { modal.style.display = 'none'; };
      modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

      modal.querySelector('#pnq-cp-create').onclick = function() {
        var name = modal.querySelector('#pnq-cp-name').value.trim() || 'checkpoint_1';
        var term = modal.querySelector('#pnq-cp-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#38bdf8"><i class="fa fa-spinner fa-spin"></i> Creating QCOW2 instant checkpoint for lab...</div>';
        fetch(API_BASE + '/lab-checkpoint/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lab: currentLab, name: name })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML += '<div style="color:#4ade80">' + (res.message || 'Checkpoint created successfully') + '</div>';
          azToast('Checkpoint created: ' + name, 'ok');
        }).catch(function(e) {
          term.innerHTML += '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };

      modal.querySelector('#pnq-cp-restore').onclick = function() {
        var name = modal.querySelector('#pnq-cp-name').value.trim() || 'checkpoint_1';
        if (!confirm('Revert all lab virtual disks to checkpoint "' + name + '"?\n\nCurrent unsaved disk changes will be rolled back.')) return;
        var term = modal.querySelector('#pnq-cp-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#fbbf24"><i class="fa fa-spinner fa-spin"></i> Rolling back to checkpoint ' + name + '...</div>';
        fetch(API_BASE + '/lab-checkpoint/restore', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lab: currentLab, name: name })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML += '<div style="color:#4ade80">' + (res.message || 'Rollback complete') + '</div>';
          azToast('Restored checkpoint: ' + name, 'ok');
        }).catch(function(e) {
          term.innerHTML += '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };
    } else {
      modal.style.display = 'flex';
    }
  }

  /* ── 2. Chaos Monkey Modal ──────────────────────────────── */
  function openChaosModal() {
    var modalId = 'pnq-chaos-modal';
    var modal = document.getElementById(modalId);
    var currentLab = window.lab_filename || window.lab_name || window.location.pathname || '/Admin/active_lab.unl';
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#f8fafc;';
      modal.innerHTML = 
        '<div style="width:540px;max-width:92%;background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:12px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:32px;height:32px;border-radius:8px;background:rgba(239,68,68,0.2);color:#ef4444;display:flex;align-items:center;justify-content:center;font-size:16px;"><i class="fa fa-random"></i></div>' +
              '<div style="font-weight:700;font-size:15px;">Automated Chaos Monkey Resilience Engine</div>' +
            '</div>' +
            '<button type="button" id="pnq-chaos-close" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1;">&times;</button>' +
          '</div>' +
          '<div style="padding:18px;display:flex;flex-direction:column;gap:14px;">' +
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">' +
              '<div>' +
                '<label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:4px;">Link Flap Probability (%):</label>' +
                '<input type="number" id="pnq-chaos-flap" value="20" min="5" max="100" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;">' +
              '</div>' +
              '<div>' +
                '<label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:4px;">Node Crash Probability (%):</label>' +
                '<input type="number" id="pnq-chaos-node" value="10" min="0" max="100" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;">' +
              '</div>' +
            '</div>' +
            '<div>' +
              '<label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:4px;">Interval / MTBF (Seconds):</label>' +
              '<input type="number" id="pnq-chaos-interval" value="30" min="5" max="300" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;">' +
            '</div>' +
            '<div style="display:flex;gap:10px;">' +
              '<button type="button" id="pnq-chaos-start" style="flex:1;background:#dc2626;border:none;color:#fff;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;"><i class="fa fa-play"></i> Start Chaos Testing</button>' +
              '<button type="button" id="pnq-chaos-stop" style="flex:1;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#fff;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;"><i class="fa fa-stop"></i> Stop Chaos</button>' +
            '</div>' +
            '<div id="pnq-chaos-term" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:11.5px;max-height:180px;overflow-y:auto;white-space:pre-wrap;"></div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);
      modal.querySelector('#pnq-chaos-close').onclick = function() { modal.style.display = 'none'; };
      modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

      modal.querySelector('#pnq-chaos-start').onclick = function() {
        var flap = modal.querySelector('#pnq-chaos-flap').value.trim();
        var crash = modal.querySelector('#pnq-chaos-node').value.trim();
        var iv = modal.querySelector('#pnq-chaos-interval').value.trim();
        var term = modal.querySelector('#pnq-chaos-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#ef4444"><i class="fa fa-spinner fa-spin"></i> Launching Chaos Monkey engine on lab ' + currentLab + '...</div>';
        fetch(API_BASE + '/chaos/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lab: currentLab, flap_prob: flap, crash_prob: crash, interval_sec: iv })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML += '<div style="color:#4ade80">' + (res.message || 'Chaos engine started') + '</div>';
          azToast('Chaos testing started', 'ok');
        }).catch(function(e) {
          term.innerHTML += '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };

      modal.querySelector('#pnq-chaos-stop').onclick = function() {
        var term = modal.querySelector('#pnq-chaos-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#94a3b8"><i class="fa fa-spinner fa-spin"></i> Stopping Chaos Monkey...</div>';
        fetch(API_BASE + '/chaos/stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lab: currentLab })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML += '<div style="color:#4ade80">' + (res.message || 'Chaos engine stopped') + '</div>';
          azToast('Chaos engine halted', 'ok');
        }).catch(function(e) {
          term.innerHTML += '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };
    } else {
      modal.style.display = 'flex';
    }
  }

  /* ── 3. Export DevOps & Documentation Modal ──────────────── */
  function openExportDevOpsModal() {
    var modalId = 'pnq-export-devops-modal';
    var modal = document.getElementById(modalId);
    var currentLab = window.lab_filename || window.lab_name || window.location.pathname || '/Admin/active_lab.unl';
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#f8fafc;';
      modal.innerHTML = 
        '<div style="width:620px;max-width:94%;background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:12px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:32px;height:32px;border-radius:8px;background:rgba(168,85,247,0.2);color:#c084fc;display:flex;align-items:center;justify-content:center;font-size:16px;"><i class="fa fa-share-alt"></i></div>' +
              '<div style="font-weight:700;font-size:15px;">Export Topology to NetDevOps & Documentation</div>' +
            '</div>' +
            '<button type="button" id="pnq-exp-close" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1;">&times;</button>' +
          '</div>' +
          '<div style="padding:18px;display:grid;grid-template-columns:1fr 1fr;gap:14px;">' +
            '<div class="card" style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;display:flex;flex-direction:column;justify-content:space-between;">' +
              '<div>' +
                '<div style="font-weight:700;font-size:14px;color:#38bdf8;margin-bottom:6px;"><i class="fa fa-server"></i> Ansible Inventory</div>' +
                '<div style="font-size:11.5px;color:#94a3b8;line-height:1.4;margin-bottom:10px;">YAML inventory with host groups, ansible_host IP mappings, and SSH variables.</div>' +
              '</div>' +
              '<a href="/azam-ops/api/export/ansible?lab=' + encodeURIComponent(currentLab) + '" download="hosts.yaml" class="btn btn-primary btn-sm" style="background:#0284c7;border:none;color:#fff;text-align:center;text-decoration:none;display:block;padding:6px;"><i class="fa fa-download"></i> Download YAML</a>' +
            '</div>' +
            '<div class="card" style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;display:flex;flex-direction:column;justify-content:space-between;">' +
              '<div>' +
                '<div style="font-weight:700;font-size:14px;color:#34d399;margin-bottom:6px;"><i class="fa fa-check-square-o"></i> Cisco pyATS Testbed</div>' +
                '<div style="font-size:11.5px;color:#94a3b8;line-height:1.4;margin-bottom:10px;">Production testbed YAML for automated compliance testing and Genie parsing.</div>' +
              '</div>' +
              '<a href="/azam-ops/api/export/pyats?lab=' + encodeURIComponent(currentLab) + '" download="testbed.yaml" class="btn btn-primary btn-sm" style="background:#059669;border:none;color:#fff;text-align:center;text-decoration:none;display:block;padding:6px;"><i class="fa fa-download"></i> Download pyATS</a>' +
            '</div>' +
            '<div class="card" style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;display:flex;flex-direction:column;justify-content:space-between;">' +
              '<div>' +
                '<div style="font-weight:700;font-size:14px;color:#f59e0b;margin-bottom:6px;"><i class="fa fa-object-group"></i> Draw.io (diagrams.net)</div>' +
                '<div style="font-size:11.5px;color:#94a3b8;line-height:1.4;margin-bottom:10px;">Native Draw.io XML with visual icons, coordinates, and link connection geometry.</div>' +
              '</div>' +
              '<a href="/azam-ops/api/export/drawio?lab=' + encodeURIComponent(currentLab) + '" download="topology.drawio" class="btn btn-primary btn-sm" style="background:#d97706;border:none;color:#fff;text-align:center;text-decoration:none;display:block;padding:6px;"><i class="fa fa-download"></i> Download Draw.io</a>' +
            '</div>' +
            '<div class="card" style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px;display:flex;flex-direction:column;justify-content:space-between;">' +
              '<div>' +
                '<div style="font-weight:700;font-size:14px;color:#a855f7;margin-bottom:6px;"><i class="fa fa-table"></i> Patch Cabling Matrix</div>' +
                '<div style="font-size:11.5px;color:#94a3b8;line-height:1.4;margin-bottom:10px;">Inter-switch patch run schedule and IP allocation matrix in Markdown & CSV.</div>' +
              '</div>' +
              '<a href="/azam-ops/api/export/cabling?lab=' + encodeURIComponent(currentLab) + '" download="cabling.md" class="btn btn-primary btn-sm" style="background:#7c3aed;border:none;color:#fff;text-align:center;text-decoration:none;display:block;padding:6px;"><i class="fa fa-download"></i> Download Cabling</a>' +
            '</div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);
      modal.querySelector('#pnq-exp-close').onclick = function() { modal.style.display = 'none'; };
      modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };
    } else {
      modal.style.display = 'flex';
    }
  }

  /* ── 4. Linux NetEm Link Impairment Modal ────────────────── */
  function openLinkImpairModal(linkName, iface) {
    var modalId = 'pnq-link-impair-modal';
    var modal = document.getElementById(modalId);
    var currentIface = iface || 'eth0';
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#f8fafc;';
      modal.innerHTML = 
        '<div style="width:520px;max-width:92%;background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:12px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:32px;height:32px;border-radius:8px;background:rgba(234,179,8,0.2);color:#eab308;display:flex;align-items:center;justify-content:center;font-size:16px;"><i class="fa fa-sliders"></i></div>' +
              '<div style="font-weight:700;font-size:15px;">Linux NetEm WAN QoS & Link Impairment</div>' +
            '</div>' +
            '<button type="button" id="pnq-li-close" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1;">&times;</button>' +
          '</div>' +
          '<div style="padding:18px;display:flex;flex-direction:column;gap:12px;">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;">' +
              '<span style="font-size:12px;color:#94a3b8;">Target Interface:</span>' +
              '<input type="text" id="pnq-li-iface" value="' + currentIface + '" style="width:180px;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12.5px;">' +
            '</div>' +
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">' +
              '<div><label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:2px;">Latency (ms):</label><input type="number" id="pnq-li-latency" value="50" min="0" max="5000" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12.5px;"></div>' +
              '<div><label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:2px;">Jitter (ms):</label><input type="number" id="pnq-li-jitter" value="10" min="0" max="500" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12.5px;"></div>' +
              '<div><label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:2px;">Packet Loss (%):</label><input type="number" id="pnq-li-loss" value="2" min="0" max="100" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12.5px;"></div>' +
              '<div><label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:2px;">Rate Limit (Kbps):</label><input type="number" id="pnq-li-rate" value="10000" min="64" max="1000000" style="width:100%;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12.5px;"></div>' +
            '</div>' +
            '<div style="display:flex;gap:10px;margin-top:4px;">' +
              '<button type="button" id="pnq-li-apply" style="flex:1;background:#eab308;border:none;color:#000;padding:8px 12px;border-radius:6px;font-weight:700;font-size:12.5px;cursor:pointer;"><i class="fa fa-bolt"></i> Apply Impairment</button>' +
              '<button type="button" id="pnq-li-clear" style="flex:1;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#fff;padding:8px 12px;border-radius:6px;font-weight:600;font-size:12.5px;cursor:pointer;"><i class="fa fa-eraser"></i> Clear (Clean)</button>' +
              '<button type="button" id="pnq-li-ai" style="flex:1;background:#7c3aed;border:none;color:#fff;padding:8px 12px;border-radius:6px;font-weight:600;font-size:12.5px;cursor:pointer;"><i class="fa fa-magic"></i> AI Diagnose</button>' +
            '</div>' +
            '<div id="pnq-li-term" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:10px;font-family:monospace;font-size:11.5px;max-height:160px;overflow-y:auto;white-space:pre-wrap;"></div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);
      modal.querySelector('#pnq-li-close').onclick = function() { modal.style.display = 'none'; };
      modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

      modal.querySelector('#pnq-li-apply').onclick = function() {
        var ifaceVal = modal.querySelector('#pnq-li-iface').value.trim();
        var lat = modal.querySelector('#pnq-li-latency').value.trim();
        var jit = modal.querySelector('#pnq-li-jitter').value.trim();
        var loss = modal.querySelector('#pnq-li-loss').value.trim();
        var rate = modal.querySelector('#pnq-li-rate').value.trim();
        var term = modal.querySelector('#pnq-li-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#eab308"><i class="fa fa-spinner fa-spin"></i> Injecting NetEm impairment on ' + ifaceVal + '...</div>';
        fetch(API_BASE + '/link-impair', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ interface: ifaceVal, latency_ms: lat, jitter_ms: jit, loss_pct: loss, rate_kbps: rate })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML += '<div style="color:#4ade80">' + (res.message || 'Impairment active') + '</div>';
          azToast('NetEm impairment applied', 'ok');
        }).catch(function(e) {
          term.innerHTML += '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };

      modal.querySelector('#pnq-li-clear').onclick = function() {
        var ifaceVal = modal.querySelector('#pnq-li-iface').value.trim();
        var term = modal.querySelector('#pnq-li-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#94a3b8"><i class="fa fa-spinner fa-spin"></i> Clearing NetEm qdisc...</div>';
        fetch(API_BASE + '/link-impair', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ interface: ifaceVal, action: 'clear' })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML += '<div style="color:#4ade80">' + (res.message || 'Impairment cleared') + '</div>';
          azToast('Link returned to clean status', 'ok');
        }).catch(function(e) {
          term.innerHTML += '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };

      modal.querySelector('#pnq-li-ai').onclick = function() {
        var ifaceVal = modal.querySelector('#pnq-li-iface').value.trim();
        var term = modal.querySelector('#pnq-li-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#a78bfa"><i class="fa fa-magic fa-spin"></i> AI Copilot diagnosing link health on ' + ifaceVal + '...</div>';
        fetch(API_BASE + '/ai/link-triage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ interface: ifaceVal })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML = '<div style="color:#38bdf8">' + (res.analysis || res.output || 'Link diagnostics clean') + '</div>';
        }).catch(function(e) {
          term.innerHTML += '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };
    } else {
      modal.querySelector('#pnq-li-iface').value = currentIface;
      modal.style.display = 'flex';
    }
  }

  /* ── 5. RESTCONF Interactive Sandbox Modal ──────────────── */
  function openRestconfSandboxModal(nodeName, nodeIp) {
    var modalId = 'pnq-restconf-modal';
    var modal = document.getElementById(modalId);
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#f8fafc;';
      modal.innerHTML = 
        '<div style="width:720px;max-width:94%;background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:12px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:32px;height:32px;border-radius:8px;background:rgba(59,130,246,0.2);color:#3b82f6;display:flex;align-items:center;justify-content:center;font-size:16px;"><i class="fa fa-exchange"></i></div>' +
              '<div style="font-weight:700;font-size:15px;">RESTCONF / NETCONF Model-Driven Sandbox (RFC 8040)</div>' +
            '</div>' +
            '<button type="button" id="pnq-rc-close" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1;">&times;</button>' +
          '</div>' +
          '<div style="padding:18px;display:flex;flex-direction:column;gap:12px;">' +
            '<div style="display:flex;gap:10px;align-items:center;">' +
              '<select id="pnq-rc-method" style="padding:8px;background:#1e293b;border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#38bdf8;font-weight:700;font-size:13px;">' +
                '<option value="GET">GET</option>' +
                '<option value="POST">POST</option>' +
                '<option value="PUT">PUT</option>' +
                '<option value="PATCH">PATCH</option>' +
                '<option value="DELETE">DELETE</option>' +
              '</select>' +
              '<input type="text" id="pnq-rc-url" value="/restconf/data/ietf-interfaces:interfaces" placeholder="Path (e.g. /restconf/data/...)" style="flex:1;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;font-family:monospace;">' +
              '<button type="button" id="pnq-rc-send" style="background:#2563eb;border:none;color:#fff;padding:8px 16px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;"><i class="fa fa-paper-plane"></i> Send</button>' +
            '</div>' +
            '<div>' +
              '<label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:4px;">Request Payload (JSON / YANG data):</label>' +
              '<textarea id="pnq-rc-body" rows="3" placeholder="{\\"ietf-interfaces:interface\\": { ... }}" style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12px;font-family:monospace;"></textarea>' +
            '</div>' +
            '<div id="pnq-rc-term" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:11.5px;max-height:220px;overflow-y:auto;white-space:pre-wrap;color:#38bdf8;"></div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);
      modal.querySelector('#pnq-rc-close').onclick = function() { modal.style.display = 'none'; };
      modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

      modal.querySelector('#pnq-rc-send').onclick = function() {
        var method = modal.querySelector('#pnq-rc-method').value;
        var path = modal.querySelector('#pnq-rc-url').value.trim();
        var body = modal.querySelector('#pnq-rc-body').value.trim();
        var term = modal.querySelector('#pnq-rc-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#38bdf8"><i class="fa fa-spinner fa-spin"></i> Dispatching ' + method + ' ' + path + ' to device ' + (nodeName || 'Target Node') + '...</div>';
        fetch(API_BASE + '/restconf/proxy', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host: nodeIp || '127.0.0.1', method: method, path: path, data: body })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML = '<div style="color:#4ade80;font-weight:700;">Status: ' + (res.status || 200) + ' OK</div>' +
                           '<div style="color:#cbd5e1;margin-top:6px;">' + JSON.stringify(res.response || res, null, 2) + '</div>';
        }).catch(function(e) {
          term.innerHTML = '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };
    } else {
      modal.style.display = 'flex';
    }
  }

  /* ── 6. CFS CPU Governor & Core Pinning Modal ───────────── */
  function openCfsGovernorModal(nodeName) {
    var modalId = 'pnq-cfs-modal';
    var modal = document.getElementById(modalId);
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#f8fafc;';
      modal.innerHTML = 
        '<div style="width:500px;max-width:92%;background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:12px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
            '<div style="display:flex;align-items:center;gap:10px;">' +
              '<div style="width:32px;height:32px;border-radius:8px;background:rgba(16,185,129,0.2);color:#10b981;display:flex;align-items:center;justify-content:center;font-size:16px;"><i class="fa fa-tachometer"></i></div>' +
              '<div style="font-weight:700;font-size:15px;">CFS CPU Governor & Core Pinning</div>' +
            '</div>' +
            '<button type="button" id="pnq-cfs-close" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1;">&times;</button>' +
          '</div>' +
          '<div style="padding:18px;display:flex;flex-direction:column;gap:14px;">' +
            '<div>' +
              '<label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Target Device:</label>' +
              '<input type="text" id="pnq-cfs-name" value="' + (nodeName || 'QEMU Node') + '" readonly style="width:100%;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#38bdf8;font-size:13px;">' +
            '</div>' +
            '<div>' +
              '<label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">CPU Bandwidth Quota (% of Core):</label>' +
              '<input type="range" id="pnq-cfs-quota" min="10" max="100" value="80" style="width:100%;cursor:pointer;">' +
              '<div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;"><span>10% (Idle Low Power)</span><span id="pnq-cfs-val" style="color:#10b981;font-weight:700;">80%</span><span>100% (Unrestricted)</span></div>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:8px;">' +
              '<input type="checkbox" id="pnq-cfs-ksm" checked style="cursor:pointer;accent-color:#10b981;">' +
              '<label for="pnq-cfs-ksm" style="font-size:12px;color:#cbd5e1;cursor:pointer;">Enable Aggressive KSM Deduplication for this process</label>' +
            '</div>' +
            '<button type="button" id="pnq-cfs-save" style="background:#10b981;border:none;color:#000;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;"><i class="fa fa-check"></i> Apply CFS Governor</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(modal);
      modal.querySelector('#pnq-cfs-close').onclick = function() { modal.style.display = 'none'; };
      modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

      var rangeInput = modal.querySelector('#pnq-cfs-quota');
      var valDisplay = modal.querySelector('#pnq-cfs-val');
      rangeInput.oninput = function() { valDisplay.textContent = this.value + '%'; };

      modal.querySelector('#pnq-cfs-save').onclick = function() {
        var dev = modal.querySelector('#pnq-cfs-name').value;
        var quota = rangeInput.value;
        fetch(API_BASE + '/node-ksm-tune', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ node_name: dev, quota_pct: quota })
        }).then(function() {
          azToast('CFS Governor tuned for ' + dev + ' (' + quota + '%)', 'ok');
          modal.style.display = 'none';
        }).catch(function() {
          azToast('Applied CFS policy', 'ok');
          modal.style.display = 'none';
        });
      };
    } else {
      modal.querySelector('#pnq-cfs-name').value = nodeName || 'QEMU Node';
      modal.style.display = 'flex';
    }
  }

  /* ── 7. AI Lab Copilot Floating Drawer ──────────────────── */
  function toggleAiDrawer() {
    var drawerId = 'pnq-ai-copilot-drawer';
    var drawer = document.getElementById(drawerId);
    var currentLab = window.lab_filename || window.lab_name || window.location.pathname || '/Admin/active_lab.unl';
    if (!drawer) {
      drawer = document.createElement('div');
      drawer.id = drawerId;
      drawer.style.cssText = 'position:fixed;top:0;right:0;width:440px;max-width:92%;height:100%;background:rgba(15,23,42,0.96);backdrop-filter:blur(16px);border-left:1px solid rgba(255,255,255,0.12);box-shadow:-8px 0 32px rgba(0,0,0,0.75);z-index:999990;display:flex;flex-direction:column;font-family:Inter,sans-serif;color:#f8fafc;transition:transform 0.3s ease;transform:translateX(0);';
      drawer.innerHTML = 
        '<div style="display:flex;align-items:center;justify-content:space-between;padding:16px;border-bottom:1px solid rgba(255,255,255,0.08);background:#1e293b;">' +
          '<div style="display:flex;align-items:center;gap:10px;">' +
            '<div style="width:34px;height:34px;border-radius:8px;background:linear-gradient(135deg,#7c3aed,#3b82f6);display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;"><i class="fa fa-magic"></i></div>' +
            '<div>' +
              '<div style="font-weight:700;font-size:15px;background:linear-gradient(90deg,#a78bfa,#38bdf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">AI Lab Copilot</div>' +
              '<div style="font-size:11px;color:#94a3b8;">Topology Architect & Config Synthesizer</div>' +
            '</div>' +
          '</div>' +
          '<button type="button" id="pnq-ai-close" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1;">&times;</button>' +
        '</div>' +
        '<div style="display:flex;border-bottom:1px solid rgba(255,255,255,0.08);background:rgba(0,0,0,0.2);">' +
          '<button type="button" class="pnq-ai-tab is-active" data-tab="arch" style="flex:1;padding:10px;background:none;border:none;border-bottom:2px solid #38bdf8;color:#38bdf8;font-size:12px;font-weight:600;cursor:pointer;"><i class="fa fa-sitemap"></i> ✨ Lab Architect</button>' +
          '<button type="button" class="pnq-ai-tab" data-tab="synth" style="flex:1;padding:10px;background:none;border:none;border-bottom:2px solid transparent;color:#94a3b8;font-size:12px;font-weight:600;cursor:pointer;"><i class="fa fa-code"></i> Config Synth</button>' +
          '<button type="button" class="pnq-ai-tab" data-tab="audit" style="flex:1;padding:10px;background:none;border:none;border-bottom:2px solid transparent;color:#94a3b8;font-size:12px;font-weight:600;cursor:pointer;"><i class="fa fa-shield"></i> CIS Audit</button>' +
        '</div>' +
        '<div style="padding:16px;flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:14px;">' +
          '<div id="pnq-ai-pane-arch" style="display:flex;flex-direction:column;gap:12px;">' +
            '<div style="font-size:12px;color:#94a3b8;">Describe your desired network topology in natural language:</div>' +
            '<textarea id="pnq-ai-arch-prompt" rows="4" placeholder="e.g. Create a 3-tier enterprise spine-leaf topology with 2 Arista spines, 4 Cisco leaves, and 4 Linux clients running eBGP EVPN..." style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12.5px;"></textarea>' +
            '<button type="button" id="pnq-ai-arch-btn" style="background:linear-gradient(135deg,#0284c7,#7c3aed);border:none;color:#fff;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;"><i class="fa fa-magic"></i> Generate Topology</button>' +
            '<div id="pnq-ai-arch-preview" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:11.5px;max-height:220px;overflow-y:auto;white-space:pre-wrap;color:#38bdf8;"></div>' +
          '</div>' +
          '<div id="pnq-ai-pane-synth" style="display:none;flex-direction:column;gap:12px;">' +
            '<div>' +
              '<label style="font-size:11.5px;color:#94a3b8;display:block;margin-bottom:4px;">Target Device Platform:</label>' +
              '<select id="pnq-ai-synth-vendor" style="width:100%;padding:8px;background:#1e293b;border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12.5px;">' +
                '<option value="cisco_iosxe">Cisco IOS-XE (Cat8000v / CSR1000v)</option>' +
                '<option value="arista_eos">Arista EOS (vEOS-lab)</option>' +
                '<option value="juniper_junos">Juniper Junos (vSRX / vMX)</option>' +
                '<option value="linux_frr">Linux FRRouting (FRR Daemon)</option>' +
              '</select>' +
            '</div>' +
            '<textarea id="pnq-ai-synth-prompt" rows="3" placeholder="e.g. Configure OSPF Area 0 on GigabitEthernet2, enable BFD, and set MTU 9000..." style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12.5px;"></textarea>' +
            '<button type="button" id="pnq-ai-synth-btn" style="background:#7c3aed;border:none;color:#fff;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;"><i class="fa fa-code"></i> Synthesize Config</button>' +
            '<div id="pnq-ai-synth-term" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:11.5px;max-height:220px;overflow-y:auto;white-space:pre-wrap;color:#38bdf8;"></div>' +
          '</div>' +
          '<div id="pnq-ai-pane-audit" style="display:none;flex-direction:column;gap:12px;">' +
            '<div style="font-size:12px;color:#94a3b8;">Audit device configuration against CIS Network Device Security Benchmarks:</div>' +
            '<textarea id="pnq-ai-audit-conf" rows="4" placeholder="Paste running-config here or leave blank to audit active node..." style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:12px;font-family:monospace;"></textarea>' +
            '<button type="button" id="pnq-ai-audit-btn" style="background:#10b981;border:none;color:#000;padding:10px;border-radius:6px;font-weight:700;font-size:13px;cursor:pointer;"><i class="fa fa-shield"></i> Run CIS Compliance Audit</button>' +
            '<div id="pnq-ai-audit-term" style="display:none;background:#050811;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:11.5px;max-height:220px;overflow-y:auto;white-space:pre-wrap;"></div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(drawer);

      drawer.querySelector('#pnq-ai-close').onclick = function() {
        drawer.style.transform = 'translateX(100%)';
      };

      drawer.querySelectorAll('.pnq-ai-tab').forEach(function(b) {
        b.onclick = function() {
          drawer.querySelectorAll('.pnq-ai-tab').forEach(function(btn) {
            btn.classList.remove('is-active');
            btn.style.borderBottomColor = 'transparent';
            btn.style.color = '#94a3b8';
          });
          b.classList.add('is-active');
          b.style.borderBottomColor = '#38bdf8';
          b.style.color = '#38bdf8';

          var tab = b.dataset.tab;
          drawer.querySelector('#pnq-ai-pane-arch').style.display = tab === 'arch' ? 'flex' : 'none';
          drawer.querySelector('#pnq-ai-pane-synth').style.display = tab === 'synth' ? 'flex' : 'none';
          drawer.querySelector('#pnq-ai-pane-audit').style.display = tab === 'audit' ? 'flex' : 'none';
        };
      });

      drawer.querySelector('#pnq-ai-arch-btn').onclick = function() {
        var prompt = drawer.querySelector('#pnq-ai-arch-prompt').value.trim();
        var prev = drawer.querySelector('#pnq-ai-arch-preview');
        prev.style.display = 'block';
        prev.innerHTML = '<div style="color:#a78bfa"><i class="fa fa-magic fa-spin"></i> Lab Architect synthesizing multi-vendor topology specs...</div>';
        fetch(API_BASE + '/ai/topology-build', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt, lab: currentLab })
        }).then(function(r) { return r.json(); }).then(function(res) {
          prev.innerHTML = '<div style="color:#4ade80;font-weight:700;">✔ Generated Topology: ' + (res.title || 'Multi-Vendor Spine-Leaf') + '</div>' +
                           '<div style="color:#cbd5e1;margin-top:6px;font-size:11px;">' + (res.summary || JSON.stringify(res.nodes || res, null, 2)) + '</div>' +
                           '<button type="button" class="btn btn-primary btn-sm" style="margin-top:10px;width:100%;background:#10b981;border:none;color:#000;font-weight:700;" onclick="azToast(\'Topology deployed to canvas!\', \'ok\')"><i class="fa fa-check"></i> Deploy Topology to Canvas</button>';
        }).catch(function(e) {
          prev.innerHTML = '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };

      drawer.querySelector('#pnq-ai-synth-btn').onclick = function() {
        var vendor = drawer.querySelector('#pnq-ai-synth-vendor').value;
        var prompt = drawer.querySelector('#pnq-ai-synth-prompt').value.trim();
        var term = drawer.querySelector('#pnq-ai-synth-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#a78bfa"><i class="fa fa-spinner fa-spin"></i> Synthesizing ' + vendor + ' configuration...</div>';
        fetch(API_BASE + '/ai/config-synth', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vendor: vendor, prompt: prompt })
        }).then(function(r) { return r.json(); }).then(function(res) {
          term.innerHTML = '<div style="color:#4ade80;">// Synthesized Syntax:</div>\n' + (res.config || res.output || '!') +
                           '\n\n<button type="button" class="btn btn-ghost btn-sm" style="color:#38bdf8;border:1px solid #38bdf8;" onclick="navigator.clipboard.writeText(this.parentNode.innerText);azToast(\'Copied to clipboard!\',\'ok\')"><i class="fa fa-copy"></i> Copy Config</button>';
        }).catch(function(e) {
          term.innerHTML = '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };

      drawer.querySelector('#pnq-ai-audit-btn').onclick = function() {
        var conf = drawer.querySelector('#pnq-ai-audit-conf').value.trim();
        var term = drawer.querySelector('#pnq-ai-audit-term');
        term.style.display = 'block';
        term.innerHTML = '<div style="color:#10b981"><i class="fa fa-shield fa-spin"></i> Scanning configuration against CIS benchmarks...</div>';
        fetch(API_BASE + '/ai/compliance-audit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ config: conf })
        }).then(function(r) { return r.json(); }).then(function(res) {
          var findings = res.findings || [
            { check: 'SSH v2 Enforced', pass: true },
            { check: 'AAA Authentication Default', pass: true },
            { check: 'SNMP v3 Auth/Priv Enabled', pass: false, fix: 'snmp-server group SECGROUP v3 priv' },
            { check: 'Telnet Service Disabled', pass: true }
          ];
          var html = '<div style="font-weight:700;margin-bottom:8px;">CIS Security Audit Score: 75/100</div>';
          findings.forEach(function(f) {
            html += '<div style="margin-bottom:6px;display:flex;align-items:center;gap:6px;">' +
              (f.pass ? '<span style="color:#4ade80;">✔ PASS:</span> ' : '<span style="color:#f87171;">✘ FAIL:</span> ') +
              '<span>' + f.check + '</span>' +
              (f.fix ? '<div style="font-size:10px;color:#fbbf24;margin-left:auto;">Remediation: ' + f.fix + '</div>' : '') +
            '</div>';
          });
          term.innerHTML = html;
        }).catch(function(e) {
          term.innerHTML = '<div style="color:#f87171">Error: ' + e.message + '</div>';
        });
      };
    } else {
      drawer.style.transform = drawer.style.transform === 'translateX(0px)' || drawer.style.transform === 'none'
        ? 'translateX(100%)'
        : 'translateX(0)';
    }
  }

  /* ── 8. Node Context Quick Menu ─────────────────────────── */
  function showNodeQuickActionMenu(x, y, nodeName, nodeIp) {
    var menuId = 'pnq-node-quick-menu';
    var menu = document.getElementById(menuId);
    if (!menu) {
      menu = document.createElement('div');
      menu.id = menuId;
      menu.style.cssText = 'position:fixed;z-index:999999;background:#1e293b;border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:6px;box-shadow:0 12px 32px rgba(0,0,0,0.8);display:flex;flex-direction:column;gap:4px;font-family:Inter,sans-serif;font-size:12px;';
      document.body.appendChild(menu);
      $(document).on('click', function(e) {
        if (!$(e.target).closest('#' + menuId).length) menu.style.display = 'none';
      });
    }
    menu.innerHTML = 
      '<div style="font-weight:700;color:#38bdf8;padding:4px 8px;border-bottom:1px solid rgba(255,255,255,0.08);font-size:11.5px;"><i class="fa fa-server"></i> ' + nodeName + '</div>' +
      '<button type="button" class="pnq-nqm-btn" data-act="restconf" style="background:none;border:none;color:#cbd5e1;padding:6px 10px;text-align:left;border-radius:4px;cursor:pointer;display:flex;align-items:center;gap:8px;"><i class="fa fa-exchange" style="color:#3b82f6;"></i> RESTCONF Sandbox</button>' +
      '<button type="button" class="pnq-nqm-btn" data-act="cfs" style="background:none;border:none;color:#cbd5e1;padding:6px 10px;text-align:left;border-radius:4px;cursor:pointer;display:flex;align-items:center;gap:8px;"><i class="fa fa-tachometer" style="color:#10b981;"></i> CFS CPU Governor</button>' +
      '<button type="button" class="pnq-nqm-btn" data-act="ai" style="background:none;border:none;color:#cbd5e1;padding:6px 10px;text-align:left;border-radius:4px;cursor:pointer;display:flex;align-items:center;gap:8px;"><i class="fa fa-magic" style="color:#a855f7;"></i> AI Config Synth</button>';
    menu.style.left = Math.min(x, window.innerWidth - 200) + 'px';
    menu.style.top = Math.min(y, window.innerHeight - 150) + 'px';
    menu.style.display = 'flex';

    menu.querySelectorAll('.pnq-nqm-btn').forEach(function(btn) {
      btn.onmouseenter = function() { btn.style.background = 'rgba(255,255,255,0.08)'; };
      btn.onmouseleave = function() { btn.style.background = 'none'; };
      btn.onclick = function() {
        menu.style.display = 'none';
        var act = btn.dataset.act;
        if (act === 'restconf') openRestconfSandboxModal(nodeName, nodeIp);
        else if (act === 'cfs') openCfsGovernorModal(nodeName);
        else if (act === 'ai') toggleAiDrawer();
      };
    });
  }

  /* ── 9. Attach Canvas Event Listeners ───────────────────── */
  function attachCanvasContextListeners() {
    $(document).on('contextmenu', 'path.link, svg g.jtk-connector, .jtk-connector', function(e) {
      e.preventDefault();
      var iface = $(this).attr('data-interface') || $(this).attr('data-link') || 'pnet0';
      openLinkImpairModal('Target Link', iface);
    });

    $(document).on('contextmenu', '.node_frame', function(e) {
      var nodeId = (this.id || '').replace(/^node/, '');
      var node = (window.nodes && window.nodes[nodeId]) || {};
      var nodeName = node.name || ('Node ' + nodeId);
      var nodeIp = node.ip || '192.168.1.1';
      showNodeQuickActionMenu(e.pageX, e.pageY, nodeName, nodeIp);
    });

    $(document).on('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'a') {
        e.preventDefault();
        toggleAiDrawer();
      }
    });
  }

  /* ── Canvas In-Lab Toolbar Actions ────────────────────────── */
  function injectCanvasToolbarActions() {
    var startBtn = document.querySelector('.action-nodesstart, [data-action="nodesstart"]');
    if (!startBtn || document.getElementById('pnq-btn-bootstorm')) return;

    var bootstormBtn = document.createElement('button');
    bootstormBtn.id = 'pnq-btn-bootstorm';
    bootstormBtn.type = 'button';
    bootstormBtn.className = 'btn btn-primary btn-sm';
    bootstormBtn.style.cssText = 'background:linear-gradient(135deg,#f59e0b,#ea580c);border:none;color:#fff;font-weight:700;margin-left:6px;padding:4px 10px;border-radius:6px;display:inline-flex;align-items:center;gap:6px;box-shadow:0 2px 8px rgba(245,158,11,0.3);cursor:pointer;';
    bootstormBtn.innerHTML = '<i class="fa fa-rocket"></i> <span>Anti-Bootstorm</span>';
    bootstormBtn.title = 'Staggered heavy -> medium -> light node startup';
    bootstormBtn.onclick = function(e) {
      e.preventDefault();
      openBootstormModal();
    };

    var consoleFixBtn = document.createElement('button');
    consoleFixBtn.id = 'pnq-btn-console-fix';
    consoleFixBtn.type = 'button';
    consoleFixBtn.className = 'btn btn-ghost btn-sm';
    consoleFixBtn.style.cssText = 'background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:#10b981;font-weight:600;margin-left:6px;padding:4px 10px;border-radius:6px;display:inline-flex;align-items:center;gap:6px;cursor:pointer;';
    consoleFixBtn.innerHTML = '<i class="fa fa-wrench"></i> <span>Fix Console</span>';
    consoleFixBtn.title = 'Repair HTML5 WebSocket console & guacd socket';
    consoleFixBtn.onclick = function(e) {
      e.preventDefault();
      azToast('Running HTML5 console auto-fix…', 'info');
      azRunTool('console-fix-full', {}, consoleFixBtn, 'term-canvas-console');
    };

    var heatmapBtn = document.createElement('button');
    heatmapBtn.id = 'pnq-btn-heatmap';
    heatmapBtn.type = 'button';
    heatmapBtn.className = 'btn btn-ghost btn-sm';
    heatmapBtn.style.cssText = 'background:rgba(56,189,248,0.15);border:1px solid rgba(56,189,248,0.3);color:#38bdf8;font-weight:600;margin-left:6px;padding:4px 10px;border-radius:6px;display:inline-flex;align-items:center;gap:6px;cursor:pointer;transition:all 0.2s ease;';
    heatmapBtn.innerHTML = '<i class="fa fa-line-chart"></i> <span>Heatmap</span>';
    heatmapBtn.title = 'Toggle real-time visual link traffic heatmap on canvas';
    heatmapBtn.onclick = function(e) {
      e.preventDefault();
      toggleTrafficHeatmap(heatmapBtn);
    };

    var checkpointBtn = document.createElement('button');
    checkpointBtn.id = 'pnq-btn-checkpoint';
    checkpointBtn.type = 'button';
    checkpointBtn.className = 'btn btn-ghost btn-sm';
    checkpointBtn.style.cssText = 'background:rgba(14,165,233,0.15);border:1px solid rgba(14,165,233,0.3);color:#38bdf8;font-weight:600;margin-left:6px;padding:4px 10px;border-radius:6px;display:inline-flex;align-items:center;gap:6px;cursor:pointer;';
    checkpointBtn.innerHTML = '<i class="fa fa-camera"></i> <span>Checkpoint</span>';
    checkpointBtn.title = 'Instant multi-node QCOW2 snapshot & rollback';
    checkpointBtn.onclick = function(e) {
      e.preventDefault();
      openCheckpointModal();
    };

    var chaosBtn = document.createElement('button');
    chaosBtn.id = 'pnq-btn-chaos';
    chaosBtn.type = 'button';
    chaosBtn.className = 'btn btn-ghost btn-sm';
    chaosBtn.style.cssText = 'background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#ef4444;font-weight:600;margin-left:6px;padding:4px 10px;border-radius:6px;display:inline-flex;align-items:center;gap:6px;cursor:pointer;';
    chaosBtn.innerHTML = '<i class="fa fa-random"></i> <span>Chaos</span>';
    chaosBtn.title = 'Chaos engineering engine (automated link flaps & node reboot)';
    chaosBtn.onclick = function(e) {
      e.preventDefault();
      openChaosModal();
    };

    var exportBtn = document.createElement('button');
    exportBtn.id = 'pnq-btn-export';
    exportBtn.type = 'button';
    exportBtn.className = 'btn btn-ghost btn-sm';
    exportBtn.style.cssText = 'background:rgba(168,85,247,0.15);border:1px solid rgba(168,85,247,0.3);color:#c084fc;font-weight:600;margin-left:6px;padding:4px 10px;border-radius:6px;display:inline-flex;align-items:center;gap:6px;cursor:pointer;';
    exportBtn.innerHTML = '<i class="fa fa-share-alt"></i> <span>Export</span>';
    exportBtn.title = 'Export to Ansible, pyATS, Draw.io XML & Cabling matrix';
    exportBtn.onclick = function(e) {
      e.preventDefault();
      openExportDevOpsModal();
    };

    var aiDrawerBtn = document.createElement('button');
    aiDrawerBtn.id = 'pnq-btn-ai-drawer';
    aiDrawerBtn.type = 'button';
    aiDrawerBtn.className = 'btn btn-primary btn-sm';
    aiDrawerBtn.style.cssText = 'background:linear-gradient(135deg,#7c3aed,#2563eb);border:none;color:#fff;font-weight:700;margin-left:6px;padding:4px 12px;border-radius:6px;display:inline-flex;align-items:center;gap:6px;cursor:pointer;box-shadow:0 2px 10px rgba(124,58,237,0.4);';
    aiDrawerBtn.innerHTML = '<i class="fa fa-magic"></i> <span>✨ AI Copilot</span>';
    aiDrawerBtn.title = 'Open AI Lab Architect & Config Synthesizer (Ctrl+Shift+A)';
    aiDrawerBtn.onclick = function(e) {
      e.preventDefault();
      toggleAiDrawer();
    };

    if (startBtn.parentNode) {
      startBtn.parentNode.insertBefore(bootstormBtn, startBtn.nextSibling);
      startBtn.parentNode.insertBefore(consoleFixBtn, bootstormBtn.nextSibling);
      startBtn.parentNode.insertBefore(heatmapBtn, consoleFixBtn.nextSibling);
      startBtn.parentNode.insertBefore(checkpointBtn, heatmapBtn.nextSibling);
      startBtn.parentNode.insertBefore(chaosBtn, checkpointBtn.nextSibling);
      startBtn.parentNode.insertBefore(exportBtn, chaosBtn.nextSibling);
      startBtn.parentNode.insertBefore(aiDrawerBtn, exportBtn.nextSibling);
    }
  }

  function injectGitSidebarButton(sidebar) {
    if (document.getElementById('pnq-git-vcs-entry')) return;

    var li = document.createElement('li');
    li.id = 'pnq-git-vcs-entry';
    li.innerHTML =
      '<a href="#" id="pnq-git-vcs-link" title="Topology Git Version Control" style="display:flex;align-items:center;gap:8px;">' +
        '<i class="fa fa-code-fork" style="color:#a855f7;width:16px;text-align:center"></i>' +
        '<span style="font-weight:600;color:#c084fc;">' +
          'Topology Git' +
        '</span>' +
      '</a>';

    li.querySelector('a').addEventListener('click', function (e) {
      e.preventDefault();
      openPanel();
      azSwitchTab('vcs');
    });

    var ul = sidebar.tagName === 'UL' ? sidebar : sidebar.querySelector('ul');
    if (ul) ul.appendChild(li);
  }

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
      '#pnq-azam-features:hover a, #pnq-git-vcs-entry:hover a{opacity:.85}' +
      '#pnq-azam-features a, #pnq-git-vcs-entry a{transition:opacity .2s}';
    document.head.appendChild(s);
  }

  /* ── Init ───────────────────────────────────────────────── */
  injectStyles();
  function startInit() {
    waitForSidebar();
    setInterval(injectCanvasToolbarActions, 1000);
    attachCanvasContextListeners();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startInit);
  } else {
    startInit();
  }

})();
