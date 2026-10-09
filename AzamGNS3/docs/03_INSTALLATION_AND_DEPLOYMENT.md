# 03. Installation & Deployment Guide

## 1. Quick-Start Summary
AzamGNS3 offers multiple deployment options:
- **Production Server (Ubuntu 26 LTS)**: Automated 1-click script or manual systemd service installation.
- **Local Testing (Windows 11/10)**: Automated batch launcher with Python 3.14 virtual environment.

---

## 2. Production Deployment on Ubuntu 26 (26.04 LTS)

### 2.1 One-Click Automated Deployment
Execute as root:

```bash
cd AzamGNS3/scripts/ubuntu26
sudo chmod +x install.sh azamgns3-system-tune.sh
sudo ./install.sh
```

### 2.2 What the Script Configures
1. Installs APT packages: `qemu-system-x86`, `qemu-utils`, `bridge-utils`, `vhost_net`, `socat`, `mtools`, `python3-venv`.
2. Tunes kernel parameters: KSM Smart-Scan, MGLRU, `vhost_net`, ZRAM swap, network buffer sysctls.
3. Sets up application directory `/opt/azamgns3` and system user `azam` (added to `kvm`, `libvirt`).
4. Configures Python 3.14 virtual environment and installs `gns3-server` in editable mode.
5. Deploys, enables, and starts `/etc/systemd/system/azamgns3.service`.

### 2.3 Operational Commands
```bash
# Check service status
sudo systemctl status azamgns3

# Tail live application logs
sudo journalctl -u azamgns3 -f

# Restart service
sudo systemctl restart azamgns3
```

---

## 3. Local Development on Windows

### 3.1 One-Click Windows Launcher
Double-click or run:
```cmd
E:\Git\AzamGNS3\scripts\run-windows.bat
```

### 3.2 Manual PowerShell Execution
```powershell
cd E:\Git\AzamGNS3
.\venv\Scripts\Activate.ps1
gns3server --host 0.0.0.0 --port 3080 --local
```

---

## 4. Client-Side Browser Access

From any client workstation (Windows, macOS, Linux, iPad, Android tablet):
1. Open any web browser: Google Chrome, Firefox, Safari, Edge.
2. Navigate to:
   ```
   http://<SERVER-IP>:3080/
   ```
3. Create projects, draw topologies, and click on nodes to interact via embedded HTML5 xterm.js terminals.
