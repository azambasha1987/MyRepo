# Weekly Upstream Intelligence & Implementation Plan: Week 37 (September 2026)

*Scan Timestamp: 2026-09-18 19:45:27* | *Target Repository: netkillui/Pnetlabv8* | *Platform: Ubuntu 26.04 (Resolute)*

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

To push and apply all verified updates, fixes, and version synchronization safely to your Azam-Pnet VM, run:

```bash
# 1. Synchronize Web-GUI Version to latest implemented release (v6.8.79):
sudo bash scripts/azambasha-sync-gui-version.sh 6.8.79 6.8.79resolute1

# 2. Push changes and run all essential fixes on target VM:
python scripts/deploy-to-vm.py -H <VM_IP> -p azam --apply-all

# 3. Execute non-regression sanity verification:
python scripts/deploy-to-vm.py -H <VM_IP> -p azam --verify
```
