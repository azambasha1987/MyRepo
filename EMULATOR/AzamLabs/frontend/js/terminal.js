/**
 * AzamLabs Multi-Tab Web Terminal Manager & Flow-Controlled Bulk Paster
 */

class TerminalManager {
  constructor() {
    this.drawer = document.getElementById('terminalDrawer');
    this.tabsList = document.getElementById('terminalTabsList');
    this.screen = document.getElementById('terminalScreen');
    this.input = document.getElementById('terminalInput');
    this.prompt = document.getElementById('terminalPrompt');

    this.tabs = []; // [{ node, ws, history: [] }]
    this.activeTabIndex = -1;
    this.isOpen = false;

    this.initEvents();
  }

  initEvents() {
    // Terminal input submission
    if (this.input) {
      this.input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const cmd = this.input.value;
          this.sendCommand(cmd);
          this.input.value = '';
        }
      });
    }
  }

  toggleDrawer(forceOpen = null) {
    this.isOpen = forceOpen !== null ? forceOpen : !this.isOpen;
    if (this.drawer) {
      this.drawer.classList.toggle('open', this.isOpen);
    }
    const btn = document.getElementById('btnToggleTerminal');
    if (btn) {
      btn.classList.toggle('active', this.isOpen);
    }
  }

  openTerminal(node, labId) {
    this.toggleDrawer(true);

    // Check if already open
    const existingIdx = this.tabs.findIndex(t => t.node.id === node.id);
    if (existingIdx !== -1) {
      this.selectTab(existingIdx);
      return;
    }

    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    const wsUrl = `${protocol}//${host}/ws/console/${labId}/${node.id}`;

    const tabEntry = {
      node: node,
      labId: labId,
      ws: null,
      output: '',
    };

    try {
      const ws = new WebSocket(wsUrl);
      tabEntry.ws = ws;

      ws.onopen = () => {
        this.appendOutput(`\x1b[32m[AzamLabs] Connected to ${node.name} console on port ${node.console_port || 23}\x1b[0m\n\n`);
      };

      ws.onmessage = (event) => {
        this.appendOutput(event.data);
      };

      ws.onclose = () => {
        this.appendOutput(`\n\x1b[33m[AzamLabs] Console connection to ${node.name} closed.\x1b[0m\n`);
      };

      ws.onerror = (err) => {
        this.appendOutput(`\n\x1b[31m[AzamLabs] WebSocket error on ${node.name}\x1b[0m\n`);
      };
    } catch (e) {
      tabEntry.output = `Failed to open console WebSocket: ${e}\n`;
    }

    this.tabs.push(tabEntry);
    this.renderTabs();
    this.selectTab(this.tabs.length - 1);
  }

  closeTab(index, event) {
    if (event) event.stopPropagation();
    const tab = this.tabs[index];
    if (tab && tab.ws) {
      tab.ws.close();
    }
    this.tabs.splice(index, 1);
    this.renderTabs();

    if (this.tabs.length === 0) {
      this.activeTabIndex = -1;
      this.clearScreen();
      this.toggleDrawer(false);
    } else {
      this.selectTab(Math.max(0, index - 1));
    }
  }

  selectTab(index) {
    if (index < 0 || index >= this.tabs.length) return;
    this.activeTabIndex = index;
    const tab = this.tabs[index];

    // Update tab bar active classes
    const tabElements = this.tabsList.querySelectorAll('.tab-item');
    tabElements.forEach((el, idx) => {
      el.classList.toggle('active', idx === index);
    });

    if (this.prompt) {
      this.prompt.textContent = `${tab.node.name}#`;
    }

    this.renderCurrentTabOutput();
    if (this.input) this.input.focus();
  }

  renderTabs() {
    if (!this.tabsList) return;
    this.tabsList.innerHTML = '';

    this.tabs.forEach((tab, idx) => {
      const el = document.createElement('div');
      el.className = `tab-item ${idx === this.activeTabIndex ? 'active' : ''}`;
      el.innerHTML = `
        <span>${tab.node.name}</span>
        <span class="tab-close" title="Close console">&times;</span>
      `;
      el.addEventListener('click', () => this.selectTab(idx));
      el.querySelector('.tab-close').addEventListener('click', (e) => this.closeTab(idx, e));
      this.tabsList.appendChild(el);
    });
  }

  appendOutput(text) {
    if (this.activeTabIndex >= 0 && this.tabs[this.activeTabIndex]) {
      this.tabs[this.activeTabIndex].output += text;
      this.renderCurrentTabOutput();
    }
  }

  renderCurrentTabOutput() {
    if (!this.screen || this.activeTabIndex < 0) return;
    const tab = this.tabs[this.activeTabIndex];
    if (tab) {
      this.screen.textContent = tab.output;
      this.screen.scrollTop = this.screen.scrollHeight;
    }
  }

  clearScreen() {
    if (this.screen) this.screen.textContent = '';
  }

  sendCommand(cmd) {
    if (this.activeTabIndex >= 0 && this.tabs[this.activeTabIndex]) {
      const tab = this.tabs[this.activeTabIndex];
      if (tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        tab.ws.send(cmd + '\r\n');
      } else {
        this.appendOutput(`\n\x1b[31m[AzamLabs] Not connected to ${tab.node.name}.\x1b[0m\n`);
      }
    }
  }

  // Flow-Controlled Bulk Configuration Paster
  async injectFlowPaster(labId, nodeId, configText, delayMs = 50) {
    try {
      const resp = await fetch(`/api/v1/console/${labId}/${nodeId}/paste`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config_text: configText,
          inter_line_delay_ms: delayMs,
          stop_on_error: false
        })
      });
      return await resp.json();
    } catch (e) {
      return { success: false, errors: [{ error: String(e) }] };
    }
  }
}

window.TerminalManager = TerminalManager;
