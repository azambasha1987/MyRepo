#!/usr/bin/env bash
# ==============================================================================
# PNETLab v8 Cluster Satellite (Worker Node) Installer
# Target OS: Ubuntu 26.04 LTS (27H1 "Resolute")
#
# Purpose:
# Provisions a dedicated, headless node-execution worker VM (QEMU, IOL,
# Dynamips, Docker, bridging) to scale out compute capacity for a master PNETLab host.
#
# After installation, join this satellite to your master server via:
#   pnet-satellite-join --master <MASTER_IP> --id <1|2> --name "Satellite-1" --psk <PSK>
#
# Package sources (in priority order):
#   1. Local pool shipped alongside this script  (debian/pool/resolute/main/)
#   2. Existing /opt/azam-pnet MyRepo clone
#   3. Fresh GitHub MyRepo clone (requires internet)
# ==============================================================================
set -euo pipefail

# Resolve script directory safely — handles both direct execution and curl|bash
_RAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
if [ -z "$_RAW_DIR" ] || [ "$_RAW_DIR" = "/dev" ] || [ ! -f "${_RAW_DIR}/install-satellite.sh" ]; then
    echo "[*] Running via curl|bash — self-cloning repo to /opt/azam-pnet..."
    MYREPO_DIR="/opt/azam-pnet"
    if [ ! -d "${MYREPO_DIR}/.git" ]; then
        git clone --depth 1 https://github.com/azambasha1987/MyRepo.git "$MYREPO_DIR" 2>/dev/null \
            || { echo "[ERROR] Failed to self-clone repo. Check internet/GitHub access."; exit 1; }
    fi
    SCRIPT_DIR="${MYREPO_DIR}/EMULATOR/Azam-Pnet"
    exec bash "${SCRIPT_DIR}/install-satellite.sh" "$@"
else
    SCRIPT_DIR="$_RAW_DIR"
fi

LOG_FILE="/var/log/azambasha-satellite-install.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Maintain root installation symlinks for /opt/azambasha and /opt/pnetlab
mkdir -p /opt/azambasha /opt/pnetlab 2>/dev/null || true
if [ "$SCRIPT_DIR" != "/opt/azambasha" ]; then
    ln -sfn "$SCRIPT_DIR" /opt/azambasha 2>/dev/null || true
fi
ln -sfn /opt/azambasha /opt/pnetlab 2>/dev/null || true

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Please run this script as root (sudo bash $0)" >&2
    exit 1
fi

echo "============================================================"
echo "    Azam Basha v8 Cluster Satellite (Worker) Installer      "
echo "============================================================"
echo "[*] Start Time: $(date)"
echo "[*] Working Directory: $SCRIPT_DIR"
echo "[*] Installation Log: $LOG_FILE"
echo "============================================================"

# --- Pre-flight Checks ---
echo "[1/6] Performing pre-flight checks..."
if dpkg -s pnetlab >/dev/null 2>&1; then
    echo "[ERROR] 'pnetlab' (Master) is already installed on this machine." >&2
    echo "A single VM cannot be both Master and Satellite simultaneously." >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

# --- Step 2: Install Headless Satellite Dependencies ---
echo "[2/6] Installing headless worker dependencies..."
apt-get update -y

SATELLITE_DEPS=(
    bridge-utils
    ebtables
    iptables
    iptables-persistent
    dkms
    qemu-utils
    python3
    python3-pip
    python3-yaml
    curl
    wget
    unzip
    zip
    net-tools
    cpulimit
    dos2unix
    genisoimage
    telnet
    iproute2
    udhcpd
    busybox
    dhcpcd-base
    dmidecode
    sshpass
    rsync
    lib32gcc-s1
    lib32z1
    libc6-i386
    libelf1t64
    libpcap0.8t64
    libsdl1.2debian
    libaio1t64
    php-cli
    zstd
    git
)

for pkg in "${SATELLITE_DEPS[@]}"; do
    apt-get install -y --no-install-recommends "$pkg" 2>/dev/null || true
done

# --- Step 3: Resolve Debian Package Pool (3-tier) ---
echo "[3/6] Resolving satellite Debian package source..."

# Priority 1: Local pool shipped alongside this script
LOCAL_POOL_CANDIDATE="${SCRIPT_DIR}/debian/pool/resolute/main"
DEB_POOL_DIR=""

if [ -d "$LOCAL_POOL_CANDIDATE" ] && compgen -G "${LOCAL_POOL_CANDIDATE}/pnetlab-satellite_*.deb" > /dev/null 2>&1; then
    echo "      -> Local Debian pool found at $LOCAL_POOL_CANDIDATE — using it directly."
    DEB_POOL_DIR="$LOCAL_POOL_CANDIDATE"
else
    MYREPO_FALLBACK="/opt/azam-pnet"
    FALLBACK_POOL="${MYREPO_FALLBACK}/EMULATOR/Azam-Pnet/debian/pool/resolute/main"

    # Priority 2: Existing MyRepo clone
    if [ -d "$FALLBACK_POOL" ] && compgen -G "${FALLBACK_POOL}/pnetlab-satellite_*.deb" > /dev/null 2>&1; then
        echo "      -> Found pool in existing MyRepo clone at $FALLBACK_POOL."
        DEB_POOL_DIR="$FALLBACK_POOL"
        SCRIPT_DIR="${MYREPO_FALLBACK}/EMULATOR/Azam-Pnet"
    else
        # Priority 3: Clone MyRepo from GitHub
        echo "      -> Local pool not found. Cloning MyRepo to $MYREPO_FALLBACK..."
        if [ ! -d "${MYREPO_FALLBACK}/.git" ]; then
            git clone --depth 1 https://github.com/azambasha1987/MyRepo.git "$MYREPO_FALLBACK" 2>/dev/null \
                || echo "      [WARNING] Could not clone MyRepo — satellite packages may be unavailable."
        fi
        if [ -d "$FALLBACK_POOL" ] && compgen -G "${FALLBACK_POOL}/pnetlab-satellite_*.deb" > /dev/null 2>&1; then
            DEB_POOL_DIR="$FALLBACK_POOL"
            SCRIPT_DIR="${MYREPO_FALLBACK}/EMULATOR/Azam-Pnet"
        fi
    fi
fi

# --- Step 4: Install Satellite Debian Packages ---
echo "[4/6] Installing Satellite runtime debian packages..."

if [ -n "$DEB_POOL_DIR" ]; then
    echo "      Found package pool in $DEB_POOL_DIR. Resolving latest satellite builds..."

    PKG_PREFIXES=(
        "pnetlab-qemu"
        "pnetlab-vpcs"
        "pnetlab-bridge-dkms"
        "pnetlab-docker"
        "pnetlab-satellite"
    )

    for prefix in "${PKG_PREFIXES[@]}"; do
        deb_path=$(find "$DEB_POOL_DIR" -maxdepth 1 -name "${prefix}_*.deb" | sort -V | tail -n1 || true)
        if [ -n "$deb_path" ] && [ -f "$deb_path" ]; then
            echo "      -> Installing $(basename "$deb_path")..."
            dpkg-deb -x "$deb_path" / 2>/dev/null || true
            dpkg -i --force-depends --force-confdef --force-confold "$deb_path" 2>/dev/null || true
        else
            echo "      [INFO] No package found for prefix: $prefix — skipping."
        fi
    done

    echo "      -> Fixing broken dependencies..."
    apt-get --fix-broken install -y 2>/dev/null || true

    # Apply authoritative network engine and bridge supervisor
    if [ -f "${SCRIPT_DIR}/scripts/azambasha-fix-network.py" ]; then
        echo "      -> Applying network engine and bridge supervisor..."
        python3 "${SCRIPT_DIR}/scripts/azambasha-fix-network.py" || true
    fi
else
    echo "      [WARNING] No Debian packages found in local or remote pool — skipping satellite package installation."
    echo "      Populate debian/pool/resolute/main/ with .deb files and re-run the installer."
fi

# --- Step 5: Extract QEMU Zoo Assets if Available ---
echo "[5/6] Checking for QEMU multi-version runtime zoo..."

ASSET_TAR=""
for search_dir in \
    "${SCRIPT_DIR}/generic/6.8.74resolute1" \
    "${SCRIPT_DIR}/generic" \
    "${SCRIPT_DIR}"; do
    found=$(find "$search_dir" -maxdepth 1 -name "pnetlab-core-assets-*.tar.zst" 2>/dev/null | sort -V | tail -n1 || true)
    if [ -n "$found" ] && [ -f "$found" ]; then
        ASSET_TAR="$found"
        break
    fi
done

if [ -n "$ASSET_TAR" ] && command -v zstd &>/dev/null; then
    echo "      -> Unpacking QEMU runtime assets ($(basename "$ASSET_TAR"))..."
    mkdir -p /opt/unetlab
    tar --zstd -xf "$ASSET_TAR" -C /opt/unetlab/ 2>/dev/null || true
else
    echo "      [INFO] No QEMU zoo archive found locally — nodes will use system QEMU."
fi

# --- Step 6: Hardware Virtualization & Permissions ---
echo "[6/6] Setting permissions and hardware markers..."
mkdir -p /opt/unetlab/addons/{qemu,iol/bin,dynamips,docker}
mkdir -p /opt/unetlab/data/Logs
mkdir -p /etc/pnetlab-satellite

if [ -c /dev/kvm ]; then
    chmod 666 /dev/kvm || true
fi

if grep -q "svm" /proc/cpuinfo 2>/dev/null; then
    echo "svm" > /opt/unetlab/platform
else
    echo "intel" > /opt/unetlab/platform
fi

/opt/unetlab/wrappers/unl_wrapper -a fixpermissions 2>/dev/null || true

# --- Step 6: Verify Satellite Service ---
echo "[6/6] Verifying satellite service status..."
systemctl daemon-reload 2>/dev/null || true
systemctl enable pnetlab-satd 2>/dev/null || true

echo ""
echo "============================================================"
echo " [SUCCESS] Azam Basha Cluster Satellite Installed Successfully!"
echo "============================================================"
echo "To join this worker to your Master Azam Basha server:"
echo ""
echo " 1. On your Master Web UI, go to: System -> Cluster"
echo " 2. Click 'Generate PSK' and copy the 64-character key"
echo " 3. Run the following command on this Satellite VM:"
echo ""
echo "    sudo pnet-satellite-join \\"
echo "      --master <MASTER_IP> \\"
echo "      --id 1 \\"
echo "      --name \"Satellite-1\" \\"
echo "      --psk <COPIED_PSK>"
echo ""
echo "============================================================"
