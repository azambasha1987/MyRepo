#!/usr/bin/env bash
# ==============================================================================
# AzamGNS3 - Automated 1-Click Installer for Ubuntu 26 (26.04 LTS)
# ==============================================================================
# Sets up AzamGNS3 like EVE-NG / PNETLab:
#  - Zero client software required (pure browser access on port 3080)
#  - Linux Kernel KSM smart-scan, MGLRU, ZRAM memory deduplication
#  - Lossless dynamic CPU governor (cgroups v2)
#  - Anti-bootstorm startup orchestration
#  - Systemd service daemon with cgroups v2 delegation
# ==============================================================================

set -euo pipefail

INSTALL_DIR="/opt/azamgns3"
CONFIG_DIR="/etc/azamgns3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "===================================================================="
echo " [AzamGNS3] 1-Click Automated Installer for Ubuntu 26 (26.04 LTS)    "
echo "===================================================================="

if [[ $EUID -ne 0 ]]; then
   echo "[-] Error: Please run this installer as root (sudo ./install.sh)" 1>&2
   exit 1
fi

# 1. Install System Dependencies
echo "[1/6] Installing Ubuntu 26 system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    qemu-system-x86 \
    qemu-utils \
    libvirt-clients \
    libvirt-daemon-system \
    bridge-utils \
    iproute2 \
    iptables \
    socat \
    mtools \
    curl \
    git \
    systemd-zram-generator

# 2. Run High-Performance System Tuning
echo "[2/6] Running AzamGNS3 kernel and memory tuning..."
bash "${SCRIPT_DIR}/azamgns3-system-tune.sh"

# 3. Create Application User & Directories
echo "[3/6] Configuring directories and permissions..."
if ! id -u azam >/dev/null 2>&1; then
    useradd -r -m -s /bin/bash azam || true
fi
usermod -aG kvm,libvirt,adm azam || true

mkdir -p "${INSTALL_DIR}"
mkdir -p "${CONFIG_DIR}"
mkdir -p /var/log/azamgns3
mkdir -p /opt/gns3/images/QEMU
mkdir -p /opt/gns3/projects

# Copy code to /opt/azamgns3
cp -r "${REPO_DIR}/AzamGNS3/gns3-server" "${INSTALL_DIR}/"
cp -r "${REPO_DIR}/AzamGNS3/scripts" "${INSTALL_DIR}/"

# 4. Setup Python 3.14 Virtual Environment
echo "[4/6] Creating Python 3.14 virtual environment and installing packages..."
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip setuptools wheel
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/gns3-server/requirements.txt"
"${INSTALL_DIR}/venv/bin/pip" install -e "${INSTALL_DIR}/gns3-server"

# 5. Create Default Configuration
echo "[5/6] Creating server configuration..."
cat << 'EOF' > "${CONFIG_DIR}/gns3_server.conf"
[Server]
host = 0.0.0.0
port = 3080
images_path = /opt/gns3/images
projects_path = /opt/gns3/projects
report_errors = False
auto_start = True

[Qemu]
enable_kvm = True
require_kvm = False
allow_unsafe_options = True

[VirtualBox]
EOF

chown -R azam:azam "${INSTALL_DIR}" "${CONFIG_DIR}" /var/log/azamgns3 /opt/gns3

# 6. Install & Start Systemd Service
echo "[6/6] Installing systemd service..."
cp "${SCRIPT_DIR}/azamgns3.service" /etc/systemd/system/azamgns3.service
systemctl daemon-reload
systemctl enable azamgns3.service
systemctl restart azamgns3.service

# Get host primary IP address
HOST_IP=$(hostname -I | awk '{print $1}' || echo "localhost")

echo "===================================================================="
echo " [AzamGNS3] Installation successfully completed!                    "
echo "===================================================================="
echo ""
echo " Access your zero-install Web Studio in any browser:"
echo "   -> http://${HOST_IP}:3080/"
echo ""
echo " Status command:  sudo systemctl status azamgns3"
echo " Live logs:       sudo journalctl -u azamgns3 -f"
echo "===================================================================="
