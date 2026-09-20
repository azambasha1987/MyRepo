# 🚀 AzamLabs: Getting Started & Deployment Guide

> **"Deploy in 60 Seconds on Ubuntu 26 or Docker."**

This guide provides step-by-step instructions for deploying **AzamLabs** on bare-metal servers, virtual machines, and Docker containers.

---

## 📋 System Requirements

| Specification | Minimum (Light Labs) | Recommended (Enterprise CCIE / Multi-Cloud) |
| :--- | :--- | :--- |
| **Operating System** | **Ubuntu 26.04 LTS ("Resolute")** or any modern Docker host | **Ubuntu 26.04 LTS Bare-Metal** |
| **Virtualization** | Intel VT-x or AMD-V (Nested Virtualization enabled in VMs) | Hardware Virtualization enabled |
| **CPU** | 4 Cores | 8–16+ Cores |
| **RAM** | 8 GB | 16–32+ GB (Consolidation engine lets 16GB run 50+ nodes!) |
| **Disk** | 40 GB SSD / NVMe | 100+ GB SSD / NVMe |

---

## 🐳 Deployment Option 1: Docker-Proof (One-Click)

AzamLabs is 100% "Docker-proof" and can be deployed in a single command on any Linux or WSL2 system with Docker installed:

```bash
# Clone the repository
git clone https://github.com/azambasha1987/AzamLabs.git
cd AzamLabs

# Launch the entire AzamLabs stack
docker compose up -d
```

Access the Studio Web UI immediately at **`http://localhost:8000`**!

---

## 🖥️ Deployment Option 2: Ubuntu 26 Native Host Installer (Recommended for Hypervisors)

For dedicated bare-metal servers or VMware/Proxmox VMs running **Ubuntu 26.04 LTS**:

```bash
# Run the automated host installer
sudo bash install-azamlabs.sh
```

### What the Host Installer Does Automatically:
1. Verifies Intel VT-x / AMD-V hardware virtualization support.
2. Configures the Ubuntu 26 modern **Netplan v2** bridge (`azam0`) with eBPF anti-DHCP leak isolation.
3. Tunes the kernel **KSM (Kernel Same-Page Merging)** engine for 100:1 RAM deduplication.
4. Installs QEMU, KVM, Python 3.12, Docker, and systemd services (`azamlabs.service`).
5. Configures automated Let's Encrypt / self-signed SSL certificates.

---

## 💻 Deployment Option 3: Local Developer / Workstation Mode

To run AzamLabs locally during development:

```bash
cd AzamLabs/backend

# Install dependencies
pip install -r requirements.txt

# Launch FastAPI development server
python -m uvicorn azamlabs.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ⚡ The `azam` CLI Power Tool Cheat Sheet

AzamLabs includes a high-velocity command-line tool (`azam`) for terminal power users:

| Command | Action | Example |
| :--- | :--- | :--- |
| `azam run <file>` | Deploy and start a lab in 2 seconds | `azam run labs/demo-dual-router.clab.yml` |
| `azam status` | Show formatted table with node states, IPs, ports | `azam status` |
| `azam console <node>` | Open instant direct terminal console | `azam console r1` |
| `azam capture <node:iface>` | Pipe live packet capture to terminal or Wireshark | `azam capture r1:eth1` |
| `azam diff <node>` | Show running-config changes vs startup-config | `azam diff r1` |
| `azam generate` | Generate parameterized Clos spine-leaf fabric | `azam generate --spines 2 --leaves 4` |
| `azam image-harvest` | Migrate images from legacy EVE/PNET folders | `azam image-harvest /opt/unetlab/addons` |
| `azam destroy` | Tear down lab and cleanly release all resources | `azam destroy` |

---

## 🔄 Universal Lab Import Quickstart

AzamLabs allows you to open labs from ANY platform with zero manual conversion:

1. Open **AzamLabs Studio** in your browser at `http://<your-server-ip>:8000`.
2. Simply **drag and drop** any lab file directly onto the canvas:
   - Containerlab: `my-topology.clab.yml`
   - Cisco CML 2.x: `cml-lab.yaml`
   - EVE-NG / PNETLab: `enterprise-bgp.unl`
   - GNS3: `sdwan-project.gns3`
3. AzamLabs auto-detects the format, converts the schema, and renders the interactive topology with vendor icons instantly!
4. Click **"Start All"** to boot the lab with anti-bootstorm staggered startup.
