/**
 * azamlabs-sequenced-console.js
 * ─────────────────────────────────────────────────────────────
 * Azam Basha Sequenced Node Console Dispatcher (SecureCRT & HTML5)
 *
 * Solves the unordered/scrambled terminal tabs issue:
 *  1. Discovers active nodes and applies Natural Alphanumeric Sorting
 *     (R1, R2, ..., R9, R10, ..., R20 instead of R1, R10, R2).
 *  2. Routes dispatches through an Asynchronous FIFO Staggered Queue
 *     (250ms for SecureCRT, 180ms for HTML5) so the OS / Browser
 *     window manager docks tabs in strict sequential order.
 *  3. Injects floating Cyber Progress HUD with real-time abort control.
 *  4. Transparently intercepts default sidebar & context-menu clicks.
 * ─────────────────────────────────────────────────────────────
 */
(function() {
  'use strict';

  if (window.azamSequencedConsole) return; // Prevent double registration

  window.azamSequencedConsole = {
    isBusy: false,
    abortFlag: false,

    // Natural alphanumeric collation (R1, R2, ..., R9, R10, ..., R20)
    naturalSort: function(nodes, mode) {
      var list = nodes.slice().sort(function(a, b) {
        var nameA = String((a && a.name) || ('Node ' + (a && a.id)));
        var nameB = String((b && b.name) || ('Node ' + (b && b.id)));
        return nameA.localeCompare(nameB, undefined, { numeric: true, sensitivity: 'base' });
      });
      if (mode === 'routers-first') {
        var r = list.filter(function(n) { return /^r/i.test((n && n.name) || ''); });
        var o = list.filter(function(n) { return !/^r/i.test((n && n.name) || ''); });
        return r.concat(o);
      }
      if (mode === 'switches-first') {
        var s = list.filter(function(n) { return /^sw/i.test((n && n.name) || ''); });
        var o = list.filter(function(n) { return !/^sw/i.test((n && n.name) || ''); });
        return s.concat(o);
      }
      return list;
    },

    // Discover running or selected nodes
    getNodes: function(mode) {
      var rawList = [];
      if (mode === 'selected') {
        if (window.freeSelectedNodes && window.freeSelectedNodes.length > 0) {
          rawList = window.freeSelectedNodes.map(function(n) {
            return (window.nodes && window.nodes[n.path]) || n;
          });
        } else if (typeof $ !== 'undefined') {
          $('.node_frame.ui-selected').each(function() {
            var id = $(this).data('path') || $(this).attr('data-path') || (this.id || '').replace(/^node/, '');
            if (id && window.nodes && window.nodes[id]) {
              rawList.push(window.nodes[id]);
            }
          });
        }
      }
      // If not selected or empty selection, get all active nodes
      if (!rawList.length && window.nodes) {
        for (var id in window.nodes) {
          var node = window.nodes[id];
          if (node && (node.status == 2 || node.status === '2' || node.status === 3 || node.running)) {
            rawList.push(node);
          }
        }
        // Fallback: If none running, take all nodes in topology
        if (!rawList.length) {
          for (var id2 in window.nodes) {
            if (window.nodes[id2]) rawList.push(window.nodes[id2]);
          }
        }
      }
      return this.naturalSort(rawList, mode);
    },

    // Open single node console session
    openSingle: function(node) {
      if (!node) return;
      var host = window.location.hostname || '127.0.0.1';
      var port = node.port || (32768 + parseInt(node.id, 10));
      var proto = node.console || 'telnet';
      var nodeName = node.name || ('Node_' + node.id);

      var url = node.url;
      var isHtml5 = (window.userConsolePref === 'html5') || 
                    (document.cookie && document.cookie.indexOf('console=html5') !== -1) ||
                    (url && (url.indexOf('html5') !== -1 || url.indexOf('guacamole') !== -1));

      if (!url) {
        if (isHtml5) {
          url = '/html5/#/client/' + btoa(node.id || '1') + '?token=' + (window.sessionToken || '');
        } else {
          url = proto + '://' + host + ':' + port;
        }
      }

      if (isHtml5) {
        // HTML5 In-Browser Web Console
        window.open(url, '_blank');
      } else {
        // SecureCRT / Native Client
        // Format with #NodeName for SecureCRT session title parsing
        var nativeUrl = url;
        if (nativeUrl.indexOf('telnet://') === 0 && nativeUrl.indexOf('#') === -1) {
          nativeUrl += '#' + encodeURIComponent(nodeName);
        }
        var a = document.createElement('a');
        a.href = nativeUrl;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        setTimeout(function() {
          if (a.parentNode) a.parentNode.removeChild(a);
        }, 600);
      }
    },

    // HUD management
    showHud: function(total, engine) {
      this.hideHud();
      var hud = document.createElement('div');
      hud.id = 'pnq-seq-console-hud';
      hud.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:999999;background:rgba(15,23,42,0.92);' +
        'backdrop-filter:blur(12px);border:1px solid rgba(56,189,248,0.4);border-radius:10px;padding:14px 18px;' +
        'box-shadow:0 8px 32px rgba(0,0,0,0.6), 0 0 16px rgba(56,189,248,0.2);min-width:320px;font-family:"Inter",sans-serif;color:#f8fafc;';
      hud.innerHTML = 
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">' +
          '<div style="display:flex;align-items:center;gap:8px;">' +
            '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#38bdf8;box-shadow:0 0 8px #38bdf8;animation:pnqPulse 1s infinite alternate;"></span>' +
            '<span style="font-weight:700;font-size:13px;letter-spacing:0.5px;color:#38bdf8;">SEQUENCED CONSOLE</span>' +
          '</div>' +
          '<span id="pnq-seq-engine-badge" style="font-size:10px;background:rgba(56,189,248,0.15);color:#7dd3fc;padding:2px 7px;border-radius:4px;font-weight:600;">' + engine + '</span>' +
        '</div>' +
        '<div id="pnq-seq-status-text" style="font-size:12px;color:#cbd5e1;margin-bottom:10px;">Initializing queue...</div>' +
        '<div style="background:rgba(255,255,255,0.1);border-radius:4px;height:6px;overflow:hidden;margin-bottom:12px;">' +
          '<div id="pnq-seq-bar" style="background:linear-gradient(90deg,#0284c7,#38bdf8);width:0%;height:100%;transition:width 0.2s ease;"></div>' +
        '</div>' +
        '<div style="display:flex;justify-content:flex-end;">' +
          '<button id="pnq-seq-abort-btn" style="background:rgba(239,68,68,0.2);border:1px solid rgba(239,68,68,0.4);color:#fca5a5;padding:4px 12px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer;">Abort</button>' +
        '</div>';
      document.body.appendChild(hud);
      var abortBtn = document.getElementById('pnq-seq-abort-btn');
      if (abortBtn) {
        abortBtn.onclick = function() {
          window.azamSequencedConsole.abort();
          this.disabled = true;
          this.textContent = 'Aborting...';
        };
      }
    },

    updateHud: function(current, total, name, engine) {
      var pct = Math.round((current / total) * 100);
      var bar = document.getElementById('pnq-seq-bar');
      if (bar) bar.style.width = pct + '%';
      var txt = document.getElementById('pnq-seq-status-text');
      if (txt) {
        txt.innerHTML = 'Opening <b style="color:#fff;">[' + current + '/' + total + '] ' + name + '</b> in sequence...';
      }
    },

    hideHud: function() {
      var el = document.getElementById('pnq-seq-console-hud');
      if (el && el.parentNode) el.parentNode.removeChild(el);
    },

    // Main execution dispatcher
    launch: function(options) {
      options = options || {};
      var mode = options.mode || 'all';
      var self = this;

      if (self.isBusy) {
        if (typeof azToast === 'function') azToast('A sequenced console batch is already in progress.', 'warning');
        return;
      }

      var nodes = self.getNodes(mode);
      if (!nodes || !nodes.length) {
        if (typeof azToast === 'function') azToast('No active lab devices found to console into.', 'warning');
        return;
      }

      var isHtml5 = (window.userConsolePref === 'html5') || 
                    (document.cookie && document.cookie.indexOf('console=html5') !== -1) ||
                    (nodes[0] && nodes[0].url && (nodes[0].url.indexOf('html5') !== -1 || nodes[0].url.indexOf('guacamole') !== -1));

      var defaultDelay = isHtml5 ? 180 : 250;
      var delayMs = options.delayMs || parseInt(localStorage.getItem('pnq_seq_delay'), 10) || defaultDelay;
      var engineName = isHtml5 ? 'HTML5 Web' : 'SecureCRT / Native';

      self.isBusy = true;
      self.abortFlag = false;
      self.showHud(nodes.length, engineName);

      var idx = 0;
      function step() {
        if (self.abortFlag || idx >= nodes.length) {
          var finishedCount = idx;
          self.isBusy = false;
          setTimeout(function() { self.hideHud(); }, 600);
          if (self.abortFlag) {
            if (typeof azToast === 'function') azToast('Sequenced console aborted after ' + finishedCount + ' nodes.', 'info');
          } else {
            if (typeof azToast === 'function') azToast('All ' + finishedCount + ' consoles opened in sequence (' + engineName + ')!', 'success');
          }
          return;
        }

        var node = nodes[idx];
        var nodeName = (node && node.name) || ('Node ' + (node && node.id));
        self.updateHud(idx + 1, nodes.length, nodeName, engineName);

        try {
          self.openSingle(node);
        } catch (err) {
          console.error('[AzamLabs] Sequenced console error:', node, err);
        }

        idx++;
        setTimeout(step, delayMs);
      }

      step();
    },

    abort: function() {
      this.abortFlag = true;
    }
  };

  // Attach auto-interception when document is ready
  function initHooks() {
    if (typeof $ === 'undefined') return;

    $(document).on('click', '.action-nodesconsole, [data-action="nodesconsole"], [data-path="nodes/console"], .action-nodesopen', function(e) {
      if (window.azamSequencedConsole && !window.azamSequencedConsole.isBusy) {
        e.preventDefault();
        e.stopImmediatePropagation();
        window.azamSequencedConsole.launch({ mode: 'all' });
        return false;
      }
    });

    $(document).on('click', '#contextmenu a, .context-menu a, .dropdown-menu a', function(e) {
      var txt = ($(this).text() || '').trim().toLowerCase();
      if (txt === 'console to all nodes' || txt === 'console all' || txt === 'open all nodes console' || txt === 'open all consoles') {
        if (window.azamSequencedConsole && !window.azamSequencedConsole.isBusy) {
          e.preventDefault();
          e.stopImmediatePropagation();
          window.azamSequencedConsole.launch({ mode: 'all' });
          return false;
        }
      } else if (txt === 'console to selected nodes' || txt === 'console selected') {
        if (window.azamSequencedConsole && !window.azamSequencedConsole.isBusy) {
          e.preventDefault();
          e.stopImmediatePropagation();
          window.azamSequencedConsole.launch({ mode: 'selected' });
          return false;
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHooks);
  } else {
    initHooks();
  }
})();
