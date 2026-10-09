# Installation & Deployment Guide: AzamGNS3

## Architecture Overview
AzamGNS3 runs as a **central server daemon** that provides a **100% browser-based (EVE-NG / PNETLab style)** experience:
- **Zero Client Software**: Open any browser on your laptop/PC (`http://<server-ip>:3080/`) — no desktop app, PuTTY, or Wireshark installation required.
- **In-Browser Web Consoles**: Direct HTML5 xterm.js terminals for router/switch consoles via WebSockets.
- **Host Performance Tuning**: Kernel Samepage Merging (KSM) memory deduplication, Lossless Dynamic CPU Governor, and Anti-Bootstorm staggered startup.

---

## Method 1: Ubuntu 26 (26.04 LTS) Server Deployment (Recommended - EVE-NG Style)

### Option A: 1-Click Automated Installer
Run the automated installation script as root on your Ubuntu 26 machine:

```bash
cd /path/to/MyRepo/AzamGNS3/scripts/ubuntu26
sudo chmod +x install.sh azamgns3-system-tune.sh
sudo ./install.sh
```

This single command will:
1. Install all Ubuntu 26 virtualization packages (`qemu-system-x86`, `bridge-utils`, `vhost_net`, `mtools`, `socat`).
2. Run kernel tuning (KSM Smart-Scan, MGLRU, ZRAM zstd compression, and sysctl buffers).
3. Create the Python 3.14 virtual environment in `/opt/azamgns3/venv`.
4. Install `gns3-server` with our CPU Governor and Bootstorm optimizations.
5. Register, enable, and start the systemd service `azamgns3.service`.

### Option B: Step-by-Step Manual Installation on Ubuntu 26

#### Step 1: Install System Packages
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip qemu-system-x86 qemu-utils \
                    bridge-utils vhost_net socat mtools curl git
```

#### Step 2: Apply Ubuntu 26 Performance Tuning
```bash
sudo bash /path/to/MyRepo/AzamGNS3/scripts/ubuntu26/azamgns3-system-tune.sh
```

#### Step 3: Set up Python 3.14 Virtual Environment
```bash
sudo mkdir -p /opt/azamgns3 /opt/gns3/images /opt/gns3/projects
sudo python3 -m venv /opt/azamgns3/venv
sudo /opt/azamgns3/venv/bin/pip install --upgrade pip setuptools wheel
sudo /opt/azamgns3/venv/bin/pip install -r /path/to/MyRepo/AzamGNS3/gns3-server/requirements.txt
sudo /opt/azamgns3/venv/bin/pip install -e /path/to/MyRepo/AzamGNS3/gns3-server
```

#### Step 4: Configure & Start Systemd Service
```bash
sudo cp /path/to/MyRepo/AzamGNS3/scripts/ubuntu26/azamgns3.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now azamgns3
```

#### Step 5: Service Verification
```bash
sudo systemctl status azamgns3
sudo journalctl -u azamgns3 -f
```

---

## Method 2: Local Windows Development / Testing

If you want to test and run the server directly on your local Windows PC:

### Option A: Using the 1-Click Batch Launcher
Double-click or run:
```cmd
E:\Git\AzamGNS3\scripts\run-windows.bat
```

### Option B: Using PowerShell
```powershell
cd E:\Git\AzamGNS3
.\venv\Scripts\Activate.ps1
gns3server --host 0.0.0.0 --port 3080 --local
```

---

## Accessing the Web Studio (Client-Side)

Once the server is running (either on Ubuntu 26 or Windows):
1. Open **Google Chrome**, **Firefox**, **Edge**, or **Safari** on any client device.
2. Navigate to:
   ```
   http://<SERVER-IP>:3080/
   ```
3. You will immediately see the complete topology canvas:
   - Click **New Project** to create a topology.
   - Drag and drop nodes onto the canvas.
   - Click any node to open the **in-browser HTML5 xterm.js console** directly.
