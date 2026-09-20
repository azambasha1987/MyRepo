<p align="center">
  <img src="assets/logo.png" alt="AzamLabs Logo" width="180">
</p>

# AzamLabs — Standalone Virtual Network Emulation Platform

AzamLabs is a self-hosted virtual network emulation platform designed for building, testing, and automating complex multi-vendor network topologies in your browser. It integrates high-performance virtualization (QEMU/KVM, Cisco IOL, Docker) with modern NetDevOps toolchains, telemetry overlays, and AI-assisted lab operations.

---

## Core Capabilities

### High-Density Multi-Vendor Virtualization
* **Hypervisor Integration**: Full support for Cisco IOL (L2/L3), QEMU/KVM (Cisco IOS-XE, IOS-XRv, Arista vEOS, Juniper vSRX, Fortinet FortiGate, Linux), and Docker containers.
* **Kernel Dataplane Acceleration**: Fast-path kernel bridge bypass minimizing latency and maximizing throughput across high-density inter-node connections.
* **Memory & CPU Optimization**: Built-in Kernel Same-page Merging (KSM) memory deduplication, OPcache acceleration, and dynamic CPU governor management.

### Advanced Visual Lab Canvas
* **Smart Alignment & Layout Engine**: Precision dock for one-click horizontal/vertical distribution, grid snapping, and centering of topology nodes.
* **Spotlight Quick-Switcher**: Keyboard-driven command palette for instant node search, console launching, and command execution.
* **Radar Mini-Map**: Dynamic interactive viewport navigator for managing sprawling network designs.
* **In-Browser Wireshark Dissector**: Live packet capturing and WebAssembly-based dissector modal directly in the canvas.

### Enterprise Cluster Architecture
* **Master-Worker Scaling**: Cluster compute scaling across multiple physical servers with automated node registration and state distribution.
* **Automated Security & TLS**: Automated IP-SAN TLS certificate generation, Windows CA trust scripts, and secure session management.

---

## Technical Specifications & Requirements

* **Architecture**: 64-bit x86_64 host with hardware virtualization (Intel VT-x / AMD-V) enabled.
* **Operating System**: Ubuntu 26.04 LTS ("Resolute").
* **Recommended Compute**: Minimum 4 vCPU / 8 GB RAM for small topologies; 8+ vCPU / 32+ GB RAM recommended for multi-vendor enterprise topologies.

---

## Administration Scripts & Platform Toolchains

AzamLabs includes an extensive administrative and operational toolchain located in [`scripts/`](scripts/):

| Script | Purpose |
| :--- | :--- |
| [`scripts/azambasha-apply-all-fixes.sh`](scripts/azambasha-apply-all-fixes.sh) | **Master Runner**: Interactive menu to launch any utility or apply platform optimizations. |
| [`scripts/azambasha-dataplane-engine.sh`](scripts/azambasha-dataplane-engine.sh) | **Dataplane Accelerator**: Fast-path kernel bridge bypass and queue tuning. |
| [`scripts/azambasha-link-impairment.sh`](scripts/azambasha-link-impairment.sh) | **Link Quality & Impairment**: Injects latency, jitter, loss, and bandwidth constraints on any link. |
| [`scripts/azambasha-capture-stream.sh`](scripts/azambasha-capture-stream.sh) | **Packet Capture & Streamer**: Low-overhead packet recording and live Wireshark streaming. |
| [`scripts/azambasha-dataplane-stats.py`](scripts/azambasha-dataplane-stats.py) | **Real-Time Telemetry**: Per-interface live PPS/BPS top monitor and JSON metrics export. |
| [`scripts/azambasha-health-check.sh`](scripts/azambasha-health-check.sh) | **Health Dashboard**: Visual audit of CPU virtualization, RAM, disk, services, and image counts. |
| [`scripts/azambasha-speed-optimizer.sh`](scripts/azambasha-speed-optimizer.sh) | **Speed Optimizer**: KSM memory deduplication, OPcache bytecode acceleration, and sysctl tuning. |
| [`scripts/azambasha-disable-logout.sh`](scripts/azambasha-disable-logout.sh) | **Permanent Session Fix**: Long-lived session management across PHP, MySQL, and keepalive heartbeat. |
| [`scripts/azambasha-fix-permissions.sh`](scripts/azambasha-fix-permissions.sh) | **Permission & Node Recovery**: Repairs `/opt/unetlab` ownership, `/dev/kvm` permissions, and licenses. |
| [`scripts/azambasha-backup-restore.sh`](scripts/azambasha-backup-restore.sh) | **Backup & Restore**: Snapshot and restore of database state, lab topologies, and configurations. |
| [`scripts/azambasha-image-doctor.sh`](scripts/azambasha-image-doctor.sh) | **Image Doctor**: Audits node image naming conventions, template mappings, and disk integrity. |
| [`connect_azambasha.bat`](connect_azambasha.bat) | **Windows Host Connector**: Auto-discovers VM IP, launches Web UI, and checks console ports. |
| [`scripts/setup-ollama.sh`](scripts/setup-ollama.sh) | **AI Lab Builder VM Setup**: Integrates local Ollama LLM copilot into the topology engine. |

---

## Technical Documentation & Guides

Comprehensive architecture and operations documentation is located in [`docs/`](docs/):

- **High-Performance Dataplane Guide**: [`docs/AZAMBASHA_HIGH_PERFORMANCE_DATAPLANE_GUIDE.md`](docs/AZAMBASHA_HIGH_PERFORMANCE_DATAPLANE_GUIDE.md)
- **Master Administration Toolkit Guide**: [`docs/AZAMBASHA_ADMIN_TOOLKIT_GUIDE.md`](docs/AZAMBASHA_ADMIN_TOOLKIT_GUIDE.md)
- **Speed & Resource Optimization Guide**: [`docs/AZAMBASHA_SPEED_OPTIMIZER_GUIDE.md`](docs/AZAMBASHA_SPEED_OPTIMIZER_GUIDE.md)
- **AI Lab Builder & Ollama Architecture**: [`docs/AI_LAB_BUILDER_OLLAMA_GUIDE.md`](docs/AI_LAB_BUILDER_OLLAMA_GUIDE.md)
- **Permanent Session Architecture**: [`docs/AZAMBASHA_PERMANENT_SESSION_GUIDE.md`](docs/AZAMBASHA_PERMANENT_SESSION_GUIDE.md)
- **Lab Export & APT Operations**: [`docs/AZAMBASHA_EXPORT_AND_APT_FIX_GUIDE.md`](docs/AZAMBASHA_EXPORT_AND_APT_FIX_GUIDE.md)
