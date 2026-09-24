# AzamLabs One-Step Update Commands: Master & Satellite Nodes

*Reference Guide • Platform: Ubuntu 26.04 Resolute & Windows Host • Authoritative Identity: `root:azam`*

---

## ⚡ Quick-Reference: Canonical One-Line Update Commands

| Target Node | Local One-Line Command (on Linux VM) | Remote One-Line Command (from Windows Host) |
|---|---|---|
| **Master Node (Controller)** | `sudo azam-update --master` | `python scripts/deploy-to-vm.py -H <MASTER_IP> -p azam --apply-all` |
| **Satellite Node (Worker)** | `sudo azam-update --satellite` | `python scripts/deploy-to-vm.py -H <SATELLITE_IP> -p azam --satellite-fixes` |
| **Universal (Auto-Detect Role)** | `sudo azam-update` | `python scripts/deploy-to-vm.py -H <NODE_IP> -p azam --auto` |
| **Fleet-Wide Simultaneous** | *Execute on each node* | `python scripts/deploy-to-vm.py -H <MASTER_IP> <SATELLITE_IP> -p azam --fleet` |

---

## 🖥️ 1. Master Controller Node One-Line Commands

The Master Controller node runs the PNetLab Web-GUI, Apache FastCGI, MySQL database, Guacamole console proxy, and cluster orchestration.

### A. Direct Execution on Master Node (SSH / Console)
```bash
# Option 1: Using the turnkey AzamLabs update utility (Recommended)
sudo azam-update --master

# (If running directly from repository path: sudo bash /opt/azambasha/scripts/azambasha-update.sh --master)

# Option 2: Direct execution via Master Fix Suite
sudo bash /opt/azambasha/scripts/azambasha-apply-all-fixes.sh 19
```

### B. Remote Execution from Windows Management Host
```powershell
python scripts/deploy-to-vm.py -H <MASTER_IP> -p azam --apply-all
```

### What Happens in the Master Node Update Pipeline (15 Steps):
1. **Permanent Session Fix**: Configures 10-year session cookies (`Never-Logout`).
2. **Lab Export & APT Fix**: Installs `zip`/`unzip`, handles nested folder structures.
3. **Upload & Docker Subsystem**: 512MB PHP/Apache limits, Docker CE repository, official `pnet-capture-web:1.0` HTML5 packet capture container, and `pnetlab-docker-image-watcher.service`.
4. **SSL IP-SAN & Console Fix**: Self-signed 5-year IP-SAN cert, Guacamole `:8081` proxy, and 32-byte crypto key.
5. **Database Deep-Fix**: Cleans SQL modes, raises 1M query limits, configures logrotate.
6. **File Permissions & Sockets**: Resets `/dev/kvm` and lab node permissions.
7. **Speed Optimizer Suite**: Activates Ultra-KSM 4KB RAM deduplication (65–80% savings) and OPcache.
8. **Silicon Dataplane Fast-Path**: Sets MTU 9000 jumbo frames and kernel bypass.
9. **Cgroups v2 & System Limits**: Configures systemd slice resource isolation.
10. **Version Freeze & Anti-Conflict**: Blocks unvetted upstream background overwrites.
11. **AzamLabs Branding**: Deploys pure black dark mode and custom platform branding.
12. **Universal Platform Logo**: Deploys home screen avatar icon across all web views.
13. **Node Startup & Cisco IOSv**: Fixes SMM UEFI for Windows 11 and Cisco IOSv boot delays.
14. **Canvas Tools & Diagnostics**: Synchronizes Network Watcher (packet sniffing), Network Painter (topology styling), and Network Analyzer (in-browser capture container).
15. **GUI Version Synchronization**: Synchronizes `/main/#/version` and DB to latest release (`v6.8.83`).
16. **Web Credentials Reset**: Re-asserts canonical admin credentials (`admin` / `azam`).
17. **Authentication Self-Healing & Systemd Rate-Limit Immunity**: Deploys `StartLimitIntervalSec=0` drop-ins to prevent `start-limit-hit` lockouts, executes live verification probe (HTTP 200), and clears shared memory lockouts.

---

## 🛰️ 2. Satellite Worker Node One-Line Commands

Satellite Worker nodes provide headless compute density, KVM virtualization, Soft-RoCE RDMA pipelines, and Docker container execution across cluster nodes.

### A. Direct Execution on Satellite Worker Node (SSH / Console)
```bash
# Option 1: Using the turnkey AzamLabs update utility (Recommended)
sudo azam-update --satellite

# (If running directly from repository path: sudo bash /opt/azambasha/scripts/azambasha-update.sh --satellite)

# Option 2: Direct execution via Satellite Optimization Suite
sudo bash /opt/azambasha/scripts/azambasha-apply-all-fixes.sh 25
```

### B. Remote Execution from Windows Management Host
```powershell
python scripts/deploy-to-vm.py -H <SATELLITE_IP> -p azam --satellite-fixes
```

### What Happens in the Satellite Worker Pipeline (14 Steps):
1. **OS Prerequisites**: Installs `swtpm`, `ovmf`, `rdma-core`, `libelf`, and `nodejs`.
2. **Bridge LACP BPDU Forwarding**: Sets `group_fwd_mask = 0xffff` to allow LACP/LLDP transit.
3. **Silicon Dataplane Accelerator**: Sets MTU 9000 jumbo frames for inter-node links.
4. **Speed Optimizer & Ultra-KSM**: Activates 4KB RAM deduplication for heavy worker density.
5. **Cgroups v2 & System Limits**: Configures task and memory slices for worker containers.
6. **Node Startup Engine**: Fixes Windows 11 UEFI SMM (`smm=on`) and Cisco IOSv boot timeouts.
7. **Soft-RoCE (RXE) Dataplane**: Enables `rdma_rxe` driver for lossless RDMA clustering.
8. **Heavy Node Optimizer**: Applies KVM halt-poll deactivation (`halt_poll_ns = 0`) and anti-bootstorm staggering.
9. **Docker Subsystem & Image Watcher**: Enforces `net.ipv4.ip_forward = 1`, bridge policies, and `pnetlab-docker-image-watcher.service`.
10. **Image Doctor**: Audits and repairs virtual disk QCOW2 images.
11. **File Permissions**: Normalizes permissions on `/opt/unetlab/addons/` and clears stale locks.
12. **Authoritative Credentials**: Enforces canonical `root:azam` password and MOTD banner.
13. **Satellite Root & Cluster DB**: Restores `0600` permissions on `/etc/pnetlab/cluster-db.conf`.
14. **Worker Daemon Self-Healing & Rate-Limit Immunity**: Deploys `StartLimitIntervalSec=0` drop-ins for `pnetlab-satd`, `pnetlab-brokerd`, and `docker`, resets failed states, and verifies root credentials (`root:azam`).

---

## 🌐 3. Auto-Detect Universal One-Line Command

If running directly on a node and you prefer the system to detect whether it is a Master or Satellite automatically:

```bash
sudo azam-update
```

The script inspects `/etc/pnetlab-role` and `dpkg -s pnetlab-satellite`:
- If Satellite is detected $\rightarrow$ runs the 13-step Satellite Worker pipeline.
- If Master is detected $\rightarrow$ runs the 15-step Master Controller pipeline.

---

## 🛡️ 4. Safety Snapshots & Instant 1-Line Rollback

In compliance with the **AzamLabs Zero-Glitch Protocol**, an immutable pre-update snapshot is automatically created before any files are altered:

### Create Manual Snapshot:
```bash
sudo azam-audit --snapshot
```

### Instant 1-Line Rollback Command:
```bash
# Rollback to the most recent pre-update snapshot:
sudo azam-update --rollback

# Or specify a target snapshot archive:
sudo azam-audit --rollback /opt/unetlab/data/Backup/snapshots/azamlabs_pre_update_<TIMESTAMP>.tar.gz
```

---

## 🔍 5. Post-Update Health Verification Commands

Validate system health and ensure 100% operational status after applying updates:

### Local Diagnostic Probe:
```bash
sudo azam-update --check
```

### Full Automated Dry-Run Test Suite (7 Probes):
```bash
python scripts/azambasha-dry-test.py
```
*Confirms 7/7 probes passed (100% Healthy):*
- Probe 1: Plan & 34-Issue Ledger Integrity
- Probe 2: Direct Email Dispatch Engine (`azambasha1987@gmail.com`)
- Probe 3: Additive QEMU Template Discovery
- Probe 4: Turnkey Audit Runner (`azam-audit`) & Rollback
- Probe 5: Issue #34 Canvas Viewport & Zoom Retention
- Probe 6: AzamLabs Operations Center Dashboard Card
- Probe 7: Docker Container Subsystem & Official Images
