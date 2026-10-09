# 02. Architectural Blueprint: Web-Native & Ubuntu 26 Specialized

## 1. System Vision
AzamGNS3 shifts network emulation from a desktop application requiring client installations to a **100% browser-based, high-density server architecture** modeled on EVE-NG and PNETLab:

- **Client Environment**: Pure Web Browser (Chrome, Firefox, Safari, Edge). **No software installed on user's machine**.
- **Host Environment**: Headless Linux Server optimized specifically for **Ubuntu 26 (26.04 LTS)** with modern kernel 6.x/7.x and Python 3.14.

---

## 2. Comparison Architecture

```
Traditional GNS3 Topology (Client Fatigue):
[User Laptop] ───────── (Needs PyQt GUI + PuTTY + Wireshark + Npcap)
       │ (Heavy local CPU / RAM)
       ▼
[Remote GNS3 Server] ── (Unthrottled QEMU, Memory Duplication, Boot-Storms)

========================================================================

AzamGNS3 Topology (EVE-NG / PNETLab Model):
[User Laptop / iPad] ── (Only Web Browser: http://server-ip:3080/)
       │ (Zero install, HTML5 Canvas, xterm.js WebSockets)
       ▼
[Ubuntu 26 Server] ──── ┌─ Dynamic CFS CPU Governor (Tames DPDK idle spin)
                        ├─ Weighted Anti-Bootstorm Scheduler
                        ├─ Kernel Samepage Merging (40-70% RAM saved)
                        ├─ Direct io_uring Async QCOW2 Overlays
                        └─ vhost-net Kernel Acceleration
```

---

## 3. Ubuntu 26 (26.04 LTS) Platform Modernization

### 3.1 Linux Kernel 6.x/7.x Memory & I/O Subsystem
1. **Kernel Samepage Merging (KSM) with Smart-Scan**:
   - Ubuntu 26 features Linux 6.6+ smart scanning (`/sys/kernel/mm/ksm/smart_scan`), which monitors page change frequencies to cut KSM CPU overhead by up to 80% while aggressively deduplicating guest OS memory pages.
2. **Multi-Gen LRU (MGLRU)**:
   - Enabled via `/sys/kernel/mm/lru_gen/enabled` for superior page aging and eviction under heavy multi-node lab pressure.
3. **ZRAM with `zstd` Compression**:
   - Integrated via `systemd-zram-generator` with priority 100 to provide instant in-RAM compressed swap without disk thrashing.
4. **Asynchronous `io_uring`**:
   - Replaces synchronous host block I/O with kernel-level SQPOLL rings, direct-to-disk NVMe streaming, and unmap support (`cache=none,aio=io_uring,discard=unmap`).

### 3.2 Systemd v256+ Cgroups v2 Delegation
- Ubuntu 26 enforces unified cgroups v2.
- The `azamgns3.service` unit configures `Delegate=yes` along with `CPUAccounting=yes` and `MemoryAccounting=yes`.
- This enables the AzamGNS3 server process (running as an unprivileged service account) to adjust CPU weights (`cpu.weight`) and memory limits on child QEMU node cgroups without sudo or root escalation.

### 3.3 Python 3.14 Runtime Compatibility
- Native Python 3.14 support with zero deprecation warnings.
- Explicit `aiohttp.web` imports resolved across controller and compute handlers.
- Isolated Python 3.14 virtual environment with PEP 668 compliance.
