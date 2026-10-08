/**
 * azamlabs-sequenced-console.js
 * ─────────────────────────────────────────────────────────────
 * Azam Basha Sequenced Node Console Dispatcher (SecureCRT & HTML5)
 *
 * Solves the unordered/scrambled terminal tabs issue:
 *  1. Discovers active nodes and applies Chunked Natural Alphanumeric Sorting
 *     (R1..R20, SW1..SW10, Server-1..Server-10, Sever-1..Sever-2, user-1..user-20, VPC-1..VPC-20).
 *  2. Groups devices hierarchically: Routers → Switches → Servers → VPCs/Users,
 *     with quick options for VPCs-First, Servers-First, or Pure Natural Name.
 *  3. Dynamic VPCS port resolution from authoritative canvas DOM links.
 *  4. Routes dispatches through an Asynchronous FIFO Staggered Queue
 *     (350ms for SecureCRT, 200ms for HTML5) so the OS / Browser
 *     window manager docks tabs in strict sequential order.
 *  5. Invisible iframe protocol dispatch: Eliminates blank browser tab storms
 *     and enforces strictly serialized Windows ShellExecute delivery.
 *  6. Injects floating Cyber Progress HUD with real-time abort control.
 *  7. Intercepts sidebar, context-menu, and shortcut console triggers.
 * ─────────────────────────────────────────────────────────────
 */
(function() {
  'use strict';

  if (window.azamSequencedConsole) return; // Prevent double registration

  window.azamSequencedConsole = {
    isBusy: false,
    abortFlag: false,

    // Natural numeric chunk comparator (handles Server-1, Server-2, Server-10, Sever-1, Sever-2, user-1, user-2, VPC-1, VPC-10)
    compareNatural: function(a, b) {
      var nameA = String(a || '').trim();
      var nameB = String(b || '').trim();
      if (nameA === nameB) return 0;

      var regex = /(\d+)/;
      var partsA = nameA.split(regex).filter(Boolean);
      var partsB = nameB.split(regex).filter(Boolean);
      var len = Math.max(partsA.length, partsB.length);

      for (var i = 0; i < len; i++) {
        var pA = partsA[i];
        var pB = partsB[i];
        if (pA === undefined) return -1;
        if (pB === undefined) return 1;

        var isNumA = /^\d+$/.test(pA);
        var isNumB = /^\d+$/.test(pB);

        if (isNumA && isNumB) {
          var diff = parseInt(pA, 10) - parseInt(pB, 10);
          if (diff !== 0) return diff;
        } else {
          var normA = pA.replace(/[-_\s]+/g, ' ').toLowerCase();
          var normB = pB.replace(/[-_\s]+/g, ' ').toLowerCase();
          var strComp = normA.localeCompare(normB, undefined, { sensitivity: 'base' });
          if (strComp !== 0) return strComp;
        }
      }
      return 0;
    },

    // Categorize device by name and template (Routers, Switches, Servers, VPCs, Others)
    getCategory: function(node) {
      var name = String((node && (this.getNodeDisplayName(node) || node.name || node.title)) || '').toUpperCase();
      var tpl = String((node && node.template) || '').toLowerCase();
      var ntype = String((node && node.type) || '').toLowerCase();

      // 1. Explicit user-given name patterns take TOP priority!
      // Routers (R1..Rn, Router-1, Core-1, Edge-1, GW-1)
      if (/^(R|ROUTER|CORE|EDGE|AGG|GW|VIOS[\-_]?R)(\b|\d|[-_]|$)/i.test(name)) {
        return 'routers';
      }
      // Switches (SW1..SWn, Switch-1, Leaf-1, Spine-1, Access-1, Dist-1)
      if (/^(SW|SWITCH|LEAF|SPINE|ACCESS|DIST|VIOS[\-_]?L2)(\b|\d|[-_]|$)/i.test(name)) {
        return 'switches';
      }
      // Servers (Server-1, Server-2, Sever-1, Sever-2 typo tolerance, SRV-1, SVR-1, Host-1, Linux-1, Win-1, Docker-1)
      if (/^(SERVER|SEVER|SRV|SVR|HOST|NODE|LINUX|UBUNTU|DEBIAN|CENTOS|WIN|DOCKER)(\b|\d|[-_]|$)/i.test(name)) {
        return 'servers';
      }
      // VPCs / Users / Clients (user-1, user-2, VPC-1, PC-1, Client-1, Workstation-1)
      if (/^(USER|USR|VPC|VPCS|PC|CLIENT|WORKSTATION)(\b|\d|[-_]|$)/i.test(name)) {
        return 'vpcs';
      }

      // 2. Secondary fallback by template / virtualization type
      if (tpl === 'vpcs' || ntype === 'vpcs') {
        return 'vpcs';
      }
      if (/server|linux|windows|docker/i.test(tpl)) {
        return 'servers';
      }
      if (/switch|l2/i.test(tpl)) {
        return 'switches';
      }
      if (/router/i.test(tpl)) {
        return 'routers';
      }
      return 'others';
    },

    getNodeDisplayName: function(node) {
      if (!node) return '';
      if (node.name && String(node.name).trim()) return String(node.name).trim();
      var domEl = document.getElementById('node' + node.id) || 
                  document.querySelector('.node_frame[data-path="' + node.id + '"]');
      if (domEl) {
        var label = domEl.querySelector('.node_name, .node-name, .node_title, label, span, p');
        if (label && label.textContent && label.textContent.trim()) {
          return label.textContent.trim();
        }
        var dataName = domEl.getAttribute('data-name') || domEl.getAttribute('title');
        if (dataName && dataName.trim()) return dataName.trim();
      }
      if (node.title && String(node.title).trim()) return String(node.title).trim();
      return 'Node_' + (node.id || '0');
    },

    // Natural alphanumeric collation supporting logical categories
    naturalSort: function(nodes, mode) {
      var self = this;
      var list = nodes.slice().sort(function(a, b) {
        var nameA = self.getNodeDisplayName(a);
        var nameB = self.getNodeDisplayName(b);
        return self.compareNatural(nameA, nameB);
      });

      if (mode === 'pure' || mode === 'name') {
        return list;
      }

      // Group by category
      var groups = { routers: [], switches: [], servers: [], vpcs: [], others: [] };
      list.forEach(function(n) {
        var cat = self.getCategory(n);
        groups[cat].push(n);
      });

      if (mode === 'vpcs-first' || mode === 'vpcs') {
        return groups.vpcs.concat(groups.servers, groups.routers, groups.switches, groups.others);
      }
      if (mode === 'vpcs-only') {
        return groups.vpcs;
      }
      if (mode === 'servers-first' || mode === 'servers') {
        return groups.servers.concat(groups.vpcs, groups.routers, groups.switches, groups.others);
      }
      if (mode === 'servers-only') {
        return groups.servers;
      }
      if (mode === 'switches-first') {
        return groups.switches.concat(groups.routers, groups.servers, groups.vpcs, groups.others);
      }
      if (mode === 'routers-first') {
        return groups.routers.concat(groups.switches, groups.servers, groups.vpcs, groups.others);
      }
      // Default: Logical Order (Routers -> Switches -> Servers -> VPCs -> Others)
      return groups.routers.concat(groups.switches, groups.servers, groups.vpcs, groups.others);
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
          $('.node_frame.ui-selected, .node_frame.free-selected').each(function() {
            var id = $(this).data('path') || $(this).attr('data-path') || (this.id || '').replace(/^node/, '');
            if (id && window.nodes && window.nodes[id]) {
              rawList.push(window.nodes[id]);
            }
          });
        }
      }
      // If not selected or empty selection, get all active nodes (status != 0 ensures VPCS/Servers are included)
      if (!rawList.length && window.nodes) {
        for (var id in window.nodes) {
          var node = window.nodes[id];
          if (node && (node.status !== 0 && node.status !== '0' && node.status !== false)) {
            rawList.push(node);
          }
        }
        // Fallback: If none active, take all nodes in topology
        if (!rawList.length) {
          for (var id2 in window.nodes) {
            if (window.nodes[id2]) rawList.push(window.nodes[id2]);
          }
        }
      }
      // Canvas DOM fallback: if rawList is still empty, scan canvas node frames
      if (!rawList.length && typeof document !== 'undefined') {
        var domFrames = document.querySelectorAll('.node_frame');
        domFrames.forEach(function(df) {
          var nid = df.getAttribute('data-path') || (df.id || '').replace(/^node/, '');
          var nname = df.getAttribute('data-name') || (df.querySelector('.node_name, .node-name, label, span') ? df.querySelector('.node_name, .node-name, label, span').textContent.trim() : ('Node_' + nid));
          var domA = df.querySelector('a');
          var durl = domA ? (domA.getAttribute('href') || '') : '';
          rawList.push({ id: nid, name: nname, url: durl, status: 2 });
        });
      }
      return this.naturalSort(rawList, mode);
    },

    // Open single node console session
    openSingle: function(node) {
      if (!node) return;
      var host = window.location.hostname || '127.0.0.1';
      var proto = node.console || 'telnet';
      var nodeName = this.getNodeDisplayName(node);

      // 1. Authoritative DOM Link on canvas (guarantees correct dynamic VPCS / Server port)
      var domNode = document.getElementById('node' + node.id) || 
                    document.querySelector('.node_frame[data-path="' + node.id + '"]');
      var domA = domNode ? domNode.querySelector('a') : null;
      var domHref = domA ? (domA.getAttribute('href') || domA.href) : '';

      var url = '';
      if (domHref && domHref !== '#' && domHref.indexOf('javascript:') === -1) {
        url = domHref;
      } else if (node.url) {
        url = node.url;
      } else {
        var port = node.port || (32768 + parseInt(node.id, 10));
        url = proto + '://' + host + ':' + port;
      }

      var isHtml5 = (window.userConsolePref === 'html5') || 
                    (document.cookie && document.cookie.indexOf('console=html5') !== -1) ||
                    (url && (url.indexOf('html5') !== -1 || url.indexOf('guacamole') !== -1));

      if (isHtml5) {
        // HTML5 In-Browser Web Console
        if (url.indexOf('http') === -1 && url.indexOf('/html5') === -1) {
          url = '/html5/#/client/' + btoa(node.id || '1') + '?token=' + (window.sessionToken || '');
        }
        window.open(url, '_blank');
      } else {
        // Native Client (SecureCRT / PuTTY / Windows Terminal)
        var nativeUrl = url;
        var passTabNames = localStorage.getItem('pnq_seq_tab_names') === 'true';
        if (passTabNames && nativeUrl.indexOf('telnet://') === 0 && nativeUrl.indexOf('#') === -1) {
          nativeUrl += '#' + encodeURIComponent(nodeName);
        } else if (!passTabNames && nativeUrl.indexOf('#') !== -1) {
          nativeUrl = nativeUrl.split('#')[0];
        }

        // 1. In-place top-level link trigger without target="_blank"
        // This delivers protocol URL to Windows ShellExecute for SecureCRT without opening blank tabs
        var link = document.createElement('a');
        link.href = nativeUrl;
        link.style.cssText = 'position:absolute;left:-9999px;top:-9999px;opacity:0.01;pointer-events:none;';
        document.body.appendChild(link);
        link.click();
        setTimeout(function() {
          if (link.parentNode) link.parentNode.removeChild(link);
        }, 2500);

        // 2. Sandboxed iframe protocol fallback for browsers requiring subframe hints
        try {
          var ifr = document.createElement('iframe');
          ifr.style.cssText = 'position:absolute;width:1px;height:1px;left:-9999px;top:-9999px;border:none;opacity:0.01;pointer-events:none;';
          ifr.setAttribute('sandbox', 'allow-scripts allow-top-navigation allow-top-navigation-to-custom-protocols');
          ifr.src = nativeUrl;
          document.body.appendChild(ifr);
          setTimeout(function() {
            if (ifr.parentNode) ifr.parentNode.removeChild(ifr);
          }, 3000);
        } catch (e) {}
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

      var defaultDelay = isHtml5 ? 200 : 350;
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
        var nodeName = self.getNodeDisplayName(node);
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
    function interceptConsoleClick(e) {
      var target = e.target;
      if (!target) return;

      var el = target.closest ? target.closest('a, button, li, .context-menu-item, [data-action], .action-nodesconsole, span, div') : target;
      if (!el) return;

      var isConsoleAll = false;
      var isConsoleSelected = false;

      // 1. Selector / action / data-path matching
      if (el.matches && el.matches('.action-nodesconsole, [data-action="nodesconsole"], [data-path="nodes/console"], .action-nodesopen, a[href*="nodes/console"], a[href*="console/all"], [data-name="nodesconsole"], .action-nodes-console')) {
        isConsoleAll = true;
      }

      // 2. Menu text, title, or aria-label matching
      var txt = (el.innerText || el.textContent || el.getAttribute('title') || el.getAttribute('aria-label') || '').trim().toLowerCase();
      var inMenu = !!(el.closest && el.closest('#context-menu, .context-menu, .context-menu-list, ul.context-menu-root, #sidebar, .sidebar, .dropdown-menu, #menu-collapse, .menu-collapse, .menu-manage'));

      if (txt.indexOf('console to all') !== -1 || txt.indexOf('console all') !== -1 || txt.indexOf('open all console') !== -1 || txt.indexOf('all nodes console') !== -1) {
        isConsoleAll = true;
      } else if (txt.indexOf('console to selected') !== -1 || txt.indexOf('console selected') !== -1 || txt.indexOf('selected nodes console') !== -1) {
        isConsoleSelected = true;
      } else if (inMenu && (txt === 'console' || txt === 'open consoles' || txt === 'nodes console' || txt === 'consoles')) {
        isConsoleAll = true;
      }

      if ((isConsoleAll || isConsoleSelected) && window.azamSequencedConsole && !window.azamSequencedConsole.isBusy) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.azamSequencedConsole.launch({ mode: isConsoleSelected ? 'selected' : 'all' });
        return false;
      }
    }

    // 1. Capture-phase listener runs BEFORE any jQuery or native element listeners
    window.addEventListener('click', interceptConsoleClick, true);

    // 2. Wrap known global EVE-NG console functions
    if (typeof window.openAllNodesConsole === 'function') {
      window.openAllNodesConsole = function() { window.azamSequencedConsole.launch({ mode: 'all' }); };
    }
    if (typeof window.nodesConsole === 'function') {
      window.nodesConsole = function() { window.azamSequencedConsole.launch({ mode: 'all' }); };
    }

    // 3. Fallback jQuery delegation for synthetic click triggers
    if (typeof $ !== 'undefined') {
      $(document).on('click', '.action-nodesconsole, [data-action="nodesconsole"], [data-path="nodes/console"], .action-nodesopen, a[href*="nodes/console"], a[href*="console/all"], [data-name="nodesconsole"], #context-menu a, #context-menu li, .context-menu a, .context-menu-item', function(e) {
        var t = ($(this).text() || '').trim().toLowerCase();
        if (t.indexOf('selected') !== -1) {
          if (window.azamSequencedConsole && !window.azamSequencedConsole.isBusy) {
            e.preventDefault();
            e.stopImmediatePropagation();
            window.azamSequencedConsole.launch({ mode: 'selected' });
            return false;
          }
        } else if (t.indexOf('console') !== -1 || $(this).is('.action-nodesconsole, [data-path="nodes/console"]')) {
          if (window.azamSequencedConsole && !window.azamSequencedConsole.isBusy) {
            e.preventDefault();
            e.stopImmediatePropagation();
            window.azamSequencedConsole.launch({ mode: 'all' });
            return false;
          }
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHooks);
  } else {
    initHooks();
  }
})();
