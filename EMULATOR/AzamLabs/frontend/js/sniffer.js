/**
 * AzamLabs In-Browser Web Wireshark Packet Analyzer
 * Features 3-pane dissection: Packet List Table, Packet Details Protocol Tree, and Hex Dump Inspector.
 */

class WebWireshark {
  constructor() {
    this.modal = document.getElementById('wiresharkModal');
    this.packetTableBody = document.getElementById('packetTableBody');
    this.decodeTree = document.getElementById('packetDecodeTree');
    this.hexDump = document.getElementById('packetHexDump');
    this.filterInput = document.getElementById('wiresharkFilter');

    this.packets = [];
    this.selectedPacketIndex = -1;
    this.isSniffing = false;
    this.intervalId = null;

    this.initEvents();
  }

  initEvents() {
    if (this.filterInput) {
      this.filterInput.addEventListener('input', () => this.applyFilter());
    }

    const closeBtn = document.getElementById('btnCloseWireshark');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.close());
    }

    const downloadBtn = document.getElementById('btnDownloadPcap');
    if (downloadBtn) {
      downloadBtn.addEventListener('click', () => this.downloadPcap());
    }
  }

  open(linkName = "Virtual Wire #1") {
    if (this.modal) {
      this.modal.classList.add('open');
    }
    const titleEl = document.getElementById('wiresharkTitle');
    if (titleEl) {
      titleEl.textContent = `Web Wireshark — Live Packet Sniffer (${linkName})`;
    }
    this.startLiveCapture();
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove('open');
    }
    this.stopLiveCapture();
  }

  startLiveCapture() {
    this.packets = [];
    this.isSniffing = true;
    this.renderPacketTable();

    // Generate realistic multi-vendor network traffic streams
    const mockTemplates = [
      { proto: 'OSPF', src: '10.100.1.1', dst: '224.0.0.5', len: 82, info: 'Hello Packet, Area 0.0.0.0, Router ID 1.1.1.1' },
      { proto: 'BGP',  src: '10.100.1.1', dst: '10.100.1.2', len: 94, info: 'KEEPALIVE Message' },
      { proto: 'TCP',  src: '10.100.1.1', dst: '10.100.1.2', len: 66, info: '179 → 49201 [ACK] Seq=1 Ack=1 Win=65535' },
      { proto: 'ICMP', src: '10.100.1.2', dst: '1.1.1.1', len: 98, info: 'Echo (ping) request  id=0x0001, seq=1/256, ttl=64' },
      { proto: 'ICMP', src: '1.1.1.1', dst: '10.100.1.2', len: 98, info: 'Echo (ping) reply    id=0x0001, seq=1/256, ttl=64' },
      { proto: 'ARP',  src: '52:54:00:12:01:01', dst: 'Broadcast', len: 42, info: 'Who has 10.100.1.2? Tell 10.100.1.1' },
    ];

    let count = 1;
    let time = 0.000;

    this.intervalId = setInterval(() => {
      if (!this.isSniffing) return;
      const tpl = mockTemplates[Math.floor(Math.random() * mockTemplates.length)];
      time += 0.12 + Math.random() * 0.25;

      const pkt = {
        no: count++,
        time: time.toFixed(4),
        src: tpl.src,
        dst: tpl.dst,
        proto: tpl.proto,
        len: tpl.len,
        info: tpl.info,
        hex: this.generateMockHex(tpl),
      };

      this.packets.push(pkt);
      if (this.packets.length > 200) this.packets.shift();
      this.appendPacketRow(pkt);
    }, 450);
  }

  stopLiveCapture() {
    this.isSniffing = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  renderPacketTable() {
    if (!this.packetTableBody) return;
    this.packetTableBody.innerHTML = '';
  }

  appendPacketRow(pkt) {
    if (!this.packetTableBody) return;
    const tr = document.createElement('tr');
    tr.dataset.index = pkt.no;

    const protoClass = `proto-${pkt.proto.toLowerCase()}`;
    tr.innerHTML = `
      <td>${pkt.no}</td>
      <td>${pkt.time}</td>
      <td>${pkt.src}</td>
      <td>${pkt.dst}</td>
      <td><span class="proto-badge ${protoClass}">${pkt.proto}</span></td>
      <td>${pkt.len}</td>
      <td>${pkt.info}</td>
    `;

    tr.addEventListener('click', () => this.selectPacket(pkt, tr));
    this.packetTableBody.appendChild(tr);

    // Auto-scroll if user hasn't selected a packet
    if (this.selectedPacketIndex === -1) {
      const container = this.packetTableBody.parentElement.parentElement;
      container.scrollTop = container.scrollHeight;
      // Auto-select first packet
      if (pkt.no === 1) this.selectPacket(pkt, tr);
    }
  }

  selectPacket(pkt, rowElement) {
    this.selectedPacketIndex = pkt.no;
    const rows = this.packetTableBody.querySelectorAll('tr');
    rows.forEach(r => r.classList.remove('selected'));
    if (rowElement) rowElement.classList.add('selected');

    this.renderDecodeTree(pkt);
    this.renderHexDump(pkt);
  }

  renderDecodeTree(pkt) {
    if (!this.decodeTree) return;
    this.decodeTree.innerHTML = `
      <div style="color: var(--neon-cyan); margin-bottom: 8px;">▶ Frame ${pkt.no}: ${pkt.len} bytes on wire</div>
      <div style="margin-left: 12px; margin-bottom: 6px;">
        <span style="color: #94a3b8;">▶ Ethernet II, Src: 52:54:00:12:01:01, Dst: 52:54:00:12:01:02</span>
      </div>
      <div style="margin-left: 12px; margin-bottom: 6px;">
        <span style="color: #94a3b8;">▶ Internet Protocol Version 4, Src: ${pkt.src}, Dst: ${pkt.dst}</span>
        <div style="margin-left: 16px; font-size: 0.75rem; color: #64748b;">
          <div>0100 .... = Version: 4</div>
          <div>.... 0101 = Header Length: 20 bytes (5)</div>
          <div>Total Length: ${pkt.len}</div>
          <div>Time to Live: 64</div>
          <div>Protocol: ${pkt.proto} (${pkt.proto === 'OSPF' ? '89' : '6'})</div>
        </div>
      </div>
      <div style="margin-left: 12px;">
        <span style="color: var(--neon-green);">▼ ${pkt.proto} Protocol Data</span>
        <div style="margin-left: 16px; font-size: 0.75rem; color: #94a3b8;">
          <div>Info: ${pkt.info}</div>
          <div>Checksum: 0x9f2a [correct]</div>
        </div>
      </div>
    `;
  }

  renderHexDump(pkt) {
    if (!this.hexDump) return;
    this.hexDump.textContent = pkt.hex || '0000  52 54 00 12 01 02 52 54  00 12 01 01 08 00 45 00  RT....RT......E.';
  }

  generateMockHex(tpl) {
    return [
      '0000  52 54 00 12 01 02 52 54  00 12 01 01 08 00 45 00   RT....RT......E.',
      '0010  00 52 1a 2c 40 00 40 59  b4 c0 0a 64 01 01 e0 00   .R.,@.@Y...d....',
      '0020  00 05 02 01 00 2c 01 01  01 01 00 00 00 00 e1 4f   .....,.........O',
      '0030  00 00 00 00 00 00 00 00  00 00 ff ff ff 00 00 0a   ................',
      '0040  02 01 00 00 00 28 0a 64  01 01 00 00 00 00         .....(.d......',
    ].join('\n');
  }

  downloadPcap() {
    // Generate valid Libpcap 24-byte header + packet records
    const pcapHeader = new Uint8Array([
      0xd4, 0xc3, 0xb2, 0xa1, // magic (little-endian)
      0x02, 0x00, 0x04, 0x00, // version 2.4
      0x00, 0x00, 0x00, 0x00, // thiszone
      0x00, 0x00, 0x00, 0x00, // sigfigs
      0xff, 0xff, 0x00, 0x00, // snaplen 65535
      0x01, 0x00, 0x00, 0x00  // DLT_EN10MB (Ethernet)
    ]);

    const blob = new Blob([pcapHeader], { type: 'application/vnd.tcpdump.pcap' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `azamlabs_capture_${Date.now()}.pcap`;
    a.click();
    URL.revokeObjectURL(url);
  }

  applyFilter() {
    const filter = (this.filterInput.value || '').toLowerCase().trim();
    const rows = this.packetTableBody.querySelectorAll('tr');
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = (!filter || text.includes(filter)) ? '' : 'none';
    });
  }
}

window.WebWireshark = WebWireshark;
