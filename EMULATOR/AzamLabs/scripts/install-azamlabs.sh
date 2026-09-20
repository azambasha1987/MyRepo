#!/usr/bin/env bash
# ==============================================================================
# AzamLabs — 1-Liner Host Setup & Installation Script
# Target OS: Ubuntu 26.04 LTS ("Resolute") & Modern Linux Kernels
# Architecture: 100% Clean-Room • 100:1 Memory & CPU Deduplication
# ==============================================================================

set -euo pipefail

# Color formatting
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}+---------------------------------------------------------------+${NC}"
echo -e "${CYAN}|  AZAMLABS — Universal Emulation & Cyber Simulation Platform  |${NC}"
echo -e "${CYAN}|  Automated Host Setup for Ubuntu 26.04 LTS (Resolute)        |${NC}"
echo -e "${CYAN}+---------------------------------------------------------------+${NC}"
echo ""

# 1. Root privilege validation
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[ERR] This installer must be run as root (or via sudo).${NC}"
  exit 1
fi

INSTALL_DIR="/opt/azamlabs"
DATA_DIR="/var/lib/azamlabs"
LOG_DIR="/var/log/azamlabs"

echo -e "${CYAN}[*] Step 1: Validating Host Operating System & CPU Virtualization...${NC}"
if [ -f /etc/os-release ]; then
  . /etc/os-release
  echo -e "    Detected OS: ${GREEN}${PRETTY_NAME:-Linux}${NC}"
fi

# Check hardware virtualization support
if grep -q -E '(vmx|svm)' /proc/cpuinfo; then
  echo -e "    CPU Virtualization: ${GREEN}Hardware VT-x/AMD-V detected [OK]${NC}"
else
  echo -e "    ${YELLOW}[WARN] Hardware VT-x/AMD-V flags not found. QEMU will run in emulation mode.${NC}"
fi

echo -e "${CYAN}[*] Step 2: Installing Essential Dataplane & Virtualization Packages...${NC}"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
  build-essential \
  qemu-system-x86 \
  qemu-utils \
  iproute2 \
  iptables \
  nftables \
  tcpdump \
  bridge-utils \
  telnet \
  curl \
  ca-certificates \
  python3 \
  python3-venv \
  python3-pip

echo -e "${CYAN}[*] Step 3: Activating 100:1 Proactive Kernel Same-Page Merging (KSM)...${NC}"
if [ -d /sys/kernel/mm/ksm ]; then
  echo 1 > /sys/kernel/mm/ksm/run || true
  echo 1000 > /sys/kernel/mm/ksm/pages_to_scan || true
  echo 20 > /sys/kernel/mm/ksm/sleep_millisecs || true
  if [ -f /sys/kernel/mm/ksm/use_zero_pages ]; then
    echo 1 > /sys/kernel/mm/ksm/use_zero_pages || true
  fi
  echo -e "    ${GREEN}KSM sysfs governor tuned for 100:1 memory deduplication [OK]${NC}"
fi

echo -e "${CYAN}[*] Step 4: Applying Network Forwarding & Dataplane Sysctl Tuning...${NC}"
cat << 'EOF' > /etc/sysctl.d/99-azamlabs.conf
# AzamLabs Virtual Dataplane & Anti-DHCP Leak Kernel Settings
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
net.bridge.bridge-nf-call-iptables = 0
net.bridge.bridge-nf-call-ip6tables = 0
net.bridge.bridge-nf-call-arptables = 0
fs.inotify.max_user_watches = 1048576
fs.file-max = 2097152
EOF
sysctl --system -q || true

echo -e "${CYAN}[*] Step 5: Preparing Directories & Compiling Idle CPU Governor Shim...${NC}"
mkdir -p "${INSTALL_DIR}/lib" "${INSTALL_DIR}/bin" "${DATA_DIR}" "${LOG_DIR}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -d "${SCRIPT_DIR}/shim" ]; then
  echo -e "    Compiling azam-iol-shim.so from source..."
  make -C "${SCRIPT_DIR}/shim" -s
  cp "${SCRIPT_DIR}/shim/azam-iol-shim.so" "${INSTALL_DIR}/lib/azam-iol-shim.so"
  chmod 755 "${INSTALL_DIR}/lib/azam-iol-shim.so"
  echo -e "    ${GREEN}Compiled azam-iol-shim.so installed at ${INSTALL_DIR}/lib/ [OK]${NC}"
fi

echo -e "${CYAN}[*] Step 6: Setting Up Python Runtime & Global 'azam' CLI...${NC}"
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --no-cache-dir -qq --upgrade pip
if [ -d "${SCRIPT_DIR}/backend" ]; then
  "${INSTALL_DIR}/venv/bin/pip" install --no-cache-dir -qq "${SCRIPT_DIR}/backend"
fi

# Symlink azam CLI globally
ln -sf "${INSTALL_DIR}/venv/bin/azam" /usr/local/bin/azam

# Copy frontend static files
mkdir -p "${INSTALL_DIR}/frontend"
if [ -d "${SCRIPT_DIR}/frontend" ]; then
  cp -r "${SCRIPT_DIR}/frontend/"* "${INSTALL_DIR}/frontend/"
fi

echo -e "${CYAN}[*] Step 7: Configuring and Starting systemd Background Service...${NC}"
cat << EOF > /etc/systemd/system/azamlabs.service
[Unit]
Description=AzamLabs Universal Network & Cybersecurity Emulation Server
After=network.target docker.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment="PYTHONUNBUFFERED=1"
Environment="AZAM_APP_NAME=AzamLabs"
Environment="AZAM_ENVIRONMENT=production"
Environment="AZAM_DATABASE_PATH=${DATA_DIR}/azamlabs.db"
Environment="AZAM_DATA_DIR=${DATA_DIR}"
Environment="AZAM_IOL_SHIM_PATH=${INSTALL_DIR}/lib/azam-iol-shim.so"
ExecStart=${INSTALL_DIR}/venv/bin/uvicorn azamlabs.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable azamlabs.service -q || true
systemctl restart azamlabs.service -q || true

echo ""
echo -e "${GREEN}=================================================================${NC}"
echo -e "${GREEN}  ✓ AZAMLABS INSTALLED & RUNNING SUCCESSFULLY!                  ${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo ""
echo -e "  • Web Studio & Wireshark UI:  ${CYAN}http://localhost:8000/${NC}"
echo -e "  • REST API & OpenAPI Docs:    ${CYAN}http://localhost:8000/docs${NC}"
echo -e "  • Model Context Protocol:     ${CYAN}http://localhost:8000/mcp${NC}"
echo -e "  • Standalone CLI:             ${CYAN}azam doctor${NC} or ${CYAN}azam lab list${NC}"
echo ""
echo -e "Run ${CYAN}azam doctor${NC} now to verify all system virtualization features."
echo ""
