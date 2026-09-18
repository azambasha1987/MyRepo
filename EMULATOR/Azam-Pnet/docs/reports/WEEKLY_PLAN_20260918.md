# Weekly Upstream Intelligence & Implementation Plan: Week 37 (September 2026)

*Scan Timestamp: 2026-09-18 19:54:42* | *Target Repository: netkillui/Pnetlabv8* | *Platform: Ubuntu 26.04 (Resolute)*

## Mandatory Production Safeguards (Zero-Glitch Protocol)

> [!CAUTION]
> ### NON-REGRESSION DIRECTIVE
> All actions and feature additions in this implementation plan must strictly follow the **Azam-Pnet Zero-Glitch Protocol**:
> 1. **Zero Disruption to Active Labs & Running Nodes**:
>    - No blanket service restarts (`systemctl restart unetlab*`) or network bridge reloads during execution. Running Cisco, Juniper, Linux, or Windows nodes remain completely undisturbed.
> 2. **Automated Rollback Checkpoints (`.bak.<timestamp>`)**:
>    - Every production file must have an immutable, timestamped backup created prior to mutation, backed by an instant 1-command rollback runbook.
> 3. **Additive Template & Feature Isolation**:
>    - New capabilities and node templates are deployed as standalone, modular add-ons—leaving all existing appliances (`c8000v`, `csr1000v`, `iol`, `qemu`, `docker`) 100% untouched.
> 4. **Preservation of Hyper-Tuning & Custom Core**:
>    - **Ultra-KSM**: Active 4KB RAM deduplication (65% to 80%+ memory savings) preserved.
>    - **CPU Governor & Fast-Path**: KVM halt-poll deactivation (`halt_poll_ns = 0`) and Silicon Dataplane (MTU 9000 jumbo frames) preserved without regression.
>    - **Authoritative Identity**: Root password **`azam`** and custom Azam-Pnet branding remain canonical.
> 5. **Pre-Flight Syntax & Sanity Probes**:
>    - Every shell script is verified with `bash -n` and Python scripts compiled with `py_compile` before execution.


---

## Executive Summary

- **Total Tracked Issues**: 33 (9 Open, 24 Closed)
- **Latest Upstream Version Implemented**: `v6.8.79` (Package: `6.8.79resolute1`)
- **Web-GUI Display Status**: Synchronized with latest implemented release (`PNetLab v6.8.79`).
- **Recent Upstream Commits**: 12 commits inspected
- **Platform Alignment**: Native Ubuntu 26.04 Resolute & Linux Kernel 7.0 stack verified.
- **Performance State**: Ultra-KSM memory deduplication (65-80% savings) & CPU governor intact.


---

## Dynamic Web-GUI Version Synchronization

> [!IMPORTANT]
> ### Authoritative Web-GUI Version Alignment
> The Web-GUI Version display (`/main/#/version`) dynamically reflects the latest release implemented rather than remaining frozen at legacy placeholders:
> - **Implemented Release Version**: `v6.8.79`
> - **Implemented Package Version**: `6.8.79resolute1`
> - **Header Title**: `PNetLab v6.8.79`
> - **Release Row**: `v6.8.79`
> - **Package Row**: `6.8.79resolute1`
> - **Database Setting**: `pnetlab_db.control.ctrl_version` = `6.8.79`

Whenever new features or bug fixes from higher upstream versions are integrated, `scripts/azambasha-sync-gui-version.sh` automatically updates `/opt/unetlab/html/includes/version.php` and the database control table.

---

## Dual Node Architecture: Master vs Satellite Remediation Matrix

Every feature addition, bug fix, and performance hyper-tuning in Azam-Pnet is explicitly engineered for both Master Controller and Satellite Worker nodes:

| Subsystem / Issue Fix | Master Node (Controller) | Satellite Node (Worker) | Target Scripts & Engines |
|---|:---:|:---:|---|
| **OS Prerequisites (`swtpm`, `ovmf`, `rdma-core`, `nodejs`)** | Active | Active | `azambasha-os-prerequisites.sh`, `install-satellite.sh` |
| **Bridge LACP BPDU Forwarding (`group_fwd_mask = 0xffff`)** | Configured | Configured | `azambasha-system-and-console-fix.sh`, `install-satellite.sh` |
| **Soft-RoCE (RXE) Dataplane Engine & MTU 9000** | Configured | Configured | `azambasha-roce-engine.sh`, `azambasha-dataplane-engine.sh` |
| **Ultra-KSM 4KB RAM Deduplication & CPU Governor** | Active | Active | `azambasha-speed-optimizer.sh`, `pnetlab-ksm.service` |
| **Node Templates (`win11.yml`, `xrd.yml`, `virtioc` multi-disk)** | Applied | Applied | `azambasha-fix-node-startup.sh`, `install-satellite.sh` |
| **High-Density Heavy Node Optimizer** | Master Mode | Worker Mode (`--satellite`) | `apply-heavy-node-optimizer.sh` |
| **Dual Wireshark Capture Permissions & Stale TPM Cleaner** | Active | Active | `azambasha-system-and-console-fix.sh`, `azambasha-fix-permissions.sh` |
| **Authoritative Identity (`root:azam`) & APT Self-Healing Hook** | Enforced | Enforced | `/etc/apt/apt.conf.d/99pnetlab-credentials` |
| **Satellite Cluster Interconnect & Tri-Tier Password Fallback** | Cluster DB Host | Worker Client (`0600`) | `azambasha-fix-cluster.sh`, `extracted_pnet-satdeploy.sh` |
| **Dynamic Web-GUI Version Synchronization (`v6.8.79`)** | Active (`v6.8.79`) | N/A (Headless Worker) | `azambasha-sync-gui-version.sh` |
| **Apache Event FastCGI, PHP-FPM & Session Cookies** | Active | N/A (Headless Worker) | `azambasha-fix-web-credentials.sh` |


---

## Satellite Cluster Deployment & Resiliency Safeguards

> [!TIP]
> ### Satellite Installation & Mid-Way Failure Protection (Issues #33, #32, #23)
> Upstream satellite deployment scripts frequently fail mid-way because upstream `.deb` post-install scripts forcefully re-hash the root password to `"pnet"`. When subsequent deployment scripts send `$SSHPASS`, the connection drops with exit code 5 (Authentication failure).
>
> **Azam-Pnet Dual-Node Protocol**:
> 1. **Tri-Tier Password Auto-Negotiation**: Automatically cycles `$SSHPASS` -> `azam` -> `pnet`, detects authentication, and immediately normalizes `root:azam`.
> 2. **Cluster DB Configuration Permissions**: Enforces `0600` permissions on `/etc/pnetlab/cluster-db.conf` on Satellite nodes to guarantee secure Master communications.
> 3. **Inter-Node Dataplane MTU Alignment**: Master and Satellites operate in lockstep with MTU 9000 jumbo frames and RoCEv2 RXE interfaces for zero packet-fragmentation cross-cluster links.


---

## Upstream Issues Audit & Azam-Pnet Alignment Ledger

| Issue # | State | Severity | Title | Azam-Pnet Resolution Status |
|---|:---:|:---:|---|---|
| [#33](https://codeberg.org/netkillui/Pnetlabv8/issues/33) | **OPEN** | `CRITICAL` | Satellite Mid Way install Failure Bug... | REMEDIATED in Azam-Pnet (Tri-Tier Fallback / 6.8.79 Manifest Patch) |
| [#32](https://codeberg.org/netkillui/Pnetlabv8/issues/32) | **OPEN** | `CRITICAL` | upgraded to 8.7.9 - Satellite issue - STEP BY... | REMEDIATED in Azam-Pnet (Tri-Tier Fallback / 6.8.79 Manifest Patch) |
| [#31](https://codeberg.org/netkillui/Pnetlabv8/issues/31) | **OPEN** | `CRITICAL` | release 6.8.79resolute1 is not ready: manifes... | REMEDIATED in Azam-Pnet (Tri-Tier Fallback / 6.8.79 Manifest Patch) |
| [#23](https://codeberg.org/netkillui/Pnetlabv8/issues/23) | **CLOSED** | `CRITICAL` | Satellite Bundle not present in 8.7.8... | REMEDIATED in Azam-Pnet (Tri-Tier Fallback / 6.8.79 Manifest Patch) |
| [#29](https://codeberg.org/netkillui/Pnetlabv8/issues/29) | **OPEN** | `LOW` | Bug 41 Nodes stop but are showing as running ... | AUDITED (No Action Required) |
| [#27](https://codeberg.org/netkillui/Pnetlabv8/issues/27) | **CLOSED** | `HIGH` | Update not working... | REMEDIATED in Azam-Pnet (Prerequisites / SMM / OVMF Symlinks) |
| [#26](https://codeberg.org/netkillui/Pnetlabv8/issues/26) | **CLOSED** | `LOW` | Export & Import Start-up config option is mis... | AUDITED (No Action Required) |
| [#24](https://codeberg.org/netkillui/Pnetlabv8/issues/24) | **CLOSED** | `LOW` | Bug 27 inside Lab Fix-permissions Reloading t... | AUDITED (No Action Required) |
| [#22](https://codeberg.org/netkillui/Pnetlabv8/issues/22) | **CLOSED** | `LOW` | Bug 27 inside Lab  Fix-permissions Reloading ... | AUDITED (No Action Required) |
| [#21](https://codeberg.org/netkillui/Pnetlabv8/issues/21) | **CLOSED** | `LOW` | lots of bug... | AUDITED (No Action Required) |
| [#20](https://codeberg.org/netkillui/Pnetlabv8/issues/20) | **CLOSED** | `LOW` | The vIOS router configuration is not being sa... | AUDITED (No Action Required) |
| [#19](https://codeberg.org/netkillui/Pnetlabv8/issues/19) | **OPEN** | `HIGH` | error when i insalling pnet on bare metal... | REMEDIATED in Azam-Pnet (Prerequisites / SMM / OVMF Symlinks) |
| [#30](https://codeberg.org/netkillui/Pnetlabv8/issues/30) | **OPEN** | `MEDIUM` | Lab settings resetting on reopening the exist... | REMEDIATED in Azam-Pnet (Canvas Persistence / Draggable Modals / SVG Handles) |
| [#28](https://codeberg.org/netkillui/Pnetlabv8/issues/28) | **CLOSED** | `MEDIUM` | Lab canvas auto zoom in issue ||  after a whi... | REMEDIATED in Azam-Pnet (Canvas Persistence / Draggable Modals / SVG Handles) |
| [#25](https://codeberg.org/netkillui/Pnetlabv8/issues/25) | **OPEN** | `MEDIUM` | Bug 31 connector edit styles  MID-point bar a... | REMEDIATED in Azam-Pnet (Canvas Persistence / Draggable Modals / SVG Handles) |
| [#17](https://codeberg.org/netkillui/Pnetlabv8/issues/17) | **OPEN** | `MEDIUM` | Bug list 6.8.77 resolute1... | REMEDIATED in Azam-Pnet (Canvas Persistence / Draggable Modals / SVG Handles) |
| [#5](https://codeberg.org/netkillui/Pnetlabv8/issues/5) | **CLOSED** | `MEDIUM` | The Running Labs link is missing.... | REMEDIATED in Azam-Pnet (Canvas Persistence / Draggable Modals / SVG Handles) |

---

## Detected Capabilities & Feature Status

1. **Dynamic Web-GUI Version Synchronization**:
   - *Status*: Deployed in `scripts/azambasha-sync-gui-version.sh`. Aligns GUI to `v6.8.79` / `6.8.79resolute1`.
2. **RoCEv2 Soft-RoCE (RXE) Dataplane Engine**:
   - *Status*: Deployed in `scripts/azambasha-roce-engine.sh` with MTU 9000 jumbo frame support.
3. **Windows 11 Hardware-Compliant QEMU Template (`win11.yml`)**:
   - *Status*: Deployed with TPM 2.0 (`swtpm`), UEFI SMM, Q35 chipset, and Ultra-KSM memory merging.
4. **Cisco XRd-9k Cloud-Native Router (`xrd.yml`)**:
   - *Status*: Deployed with Cgroups v2 delegation and systemd slice optimization.
5. **Google AI Studio / Gemini 2.5 Flash Integration**:
   - *Status*: Enabled in `scripts/setup-ollama.sh` alongside local Ollama.
6. **Canvas Usability & Settings Persistence**:
   - *Status*: Per-lab zoom persistence, draggable modals, and SVG curviness handles active.

---

## Ready-to-Apply Action Plan for Azam Basha

Run the corresponding runbook below based on the target node type:

### A. Master Node Deployment & Optimization

```bash
# Option 1: Remote deployment from Windows host (full Master pipeline):
python scripts/deploy-to-vm.py -H <MASTER_IP> -p azam --apply-all

# Option 2: Direct execution on Master node:
sudo bash scripts/azambasha-apply-all-fixes.sh 19
```

### B. Satellite Worker Node Deployment & Optimization

```bash
# Option 1: Provision fresh Satellite Worker and join to Master:
python scripts/deploy-to-vm.py -H <SATELLITE_IP> -p azam --satellite --join-master <MASTER_IP> --cluster-id 1 --cluster-psk <PSK_HEX>

# Option 2: Apply full optimization & issue remediation suite to existing Satellite Worker:
python scripts/deploy-to-vm.py -H <SATELLITE_IP> -p azam --satellite-fixes

# Option 3: Direct execution on Satellite Worker node:
sudo bash scripts/azambasha-apply-all-fixes.sh 25
```

### C. Cluster-Wide Sanity Health Probes

```bash
# Execute non-regression health verification across Master and Satellite:
python scripts/deploy-to-vm.py -H <MASTER_IP> <SATELLITE_IP> -p azam --verify
```
