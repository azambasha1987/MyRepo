# AzamGNS3 Documentation Suite

Welcome to the **AzamGNS3** documentation library. This folder contains the architectural blueprints, implementation records, performance deep-dives, installation guides, and future roadmap for the next-generation, high-performance, browser-native network emulation platform.

---

## Documentation Index

| Document | Description |
| :--- | :--- |
| **[01. Implementation Plan](file:///e:/Git/AzamGNS3/docs/01_IMPLEMENTATION_PLAN.md)** | Baseline repository setup, component selection, branch strategy (`master` bleeding-edge), and Git submodule structure. |
| **[02. Architecture & Ubuntu 26 Blueprint](file:///e:/Git/AzamGNS3/docs/02_ARCHITECTURE_EVE_STYLE_UBUNTU26.md)** | Full architectural design for zero-install client-less operations (EVE-NG / PNETLab model) and Ubuntu 26 (26.04 LTS) kernel integration. |
| **[03. Installation & Deployment Guide](file:///e:/Git/AzamGNS3/docs/03_INSTALLATION_AND_DEPLOYMENT.md)** | 1-click automated Ubuntu 26 installation, manual deployment, systemd v256+ management, Windows local testing, and browser access. |
| **[04. Performance Optimizations Deep-Dive](file:///e:/Git/AzamGNS3/docs/04_PERFORMANCE_OPTIMIZATIONS.md)** | Technical breakdown of the Lossless CFS CPU Governor, Weighted Anti-Bootstorm Engine, KSM Smart-Scan, `io_uring`, and `vhost-net`. |
| **[05. Future Roadmap & Extensibility](file:///e:/Git/AzamGNS3/docs/05_FUTURE_ROADMAP.md)** | Strategic roadmap for future iterations: In-browser WebShark live packet dissection, Containerlab/CNF presets, distributed clustering, and multi-tenant RBAC. |

---

## Core Value Proposition

```
┌────────────────────────────────────────────────────────────────────────┐
│                              AzamGNS3                                  │
│             Next-Gen Web-Native Network Emulation Platform             │
├────────────────────────────────────────────────────────────────────────┤
│  ✓ 100% In-Browser (Zero client-side app installation)                 │
│  ✓ EVE-NG / PNETLab User Experience (HTML5 xterm.js Consoles)          │
│  ✓ 40% - 70% Less RAM via Linux KSM Smart-Scan & Memory Ballooning     │
│  ✓ Zero DPDK Spin-Loop CPU Waste via Lossless CFS Governor             │
│  ✓ Zero I/O Freezes via Weighted Anti-Bootstorm Orchestration          │
│  ✓ Fine-Tuned for Ubuntu 26 (26.04 LTS) Kernel 6.x/7.x & Python 3.14   │
└────────────────────────────────────────────────────────────────────────┘
```
