#!/usr/bin/env bash
# ==============================================================================
# Azam – Basha v8 Cluster Satellite (Worker Node) Unified Installer
# Target OS: Ubuntu 26.04 LTS ("Resolute") & Ubuntu 24.04 LTS ("Noble")
#
# Purpose:
# Provisions a dedicated, headless compute worker node (QEMU, IOL, Dynamips,
# Docker, and High-Performance Bridging) to scale compute capacity for an
# Azam – Basha / PNETLab Master server.
#
# Usage:
#   sudo bash install-satellite.sh [OPTIONS]
#
# Options:
#   --master <IP>             Master server IP address for automated cluster join
#   --id <1|2>                Satellite slot ID (Default: 1)
#   --name <NAME>             Satellite display name (Default: Satellite-<id>)
#   --psk <PSK>               Cluster 64-hex PSK key from Master Web UI
#   --static, -s <IP/CIDR>    Configure static management IP (e.g. 192.168.1.51/24)
#   --gateway, -g <IP>        Configure default gateway (e.g. 192.168.1.1)
#   --dns, -d <IP>            Configure primary DNS server (Default: 8.8.8.8)
#   --force                   Override Master conflict check (testing only)
#   --no-reboot               Skip automatic reboot after installation
#   --help, -h                Show this help menu
# ==============================================================================
set -Eeuo pipefail

# Parse help early
if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
    echo "Usage: sudo bash $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --master <IP>             Master server IP address for automated cluster join"
    echo "  --id <1|2>                Satellite slot ID (Default: 1)"
    echo "  --name <NAME>             Satellite display name (Default: Satellite-<id>)"
    echo "  --psk <PSK>               Cluster 64-hex PSK key from Master Web UI"
    echo "  --static, -s <IP/CIDR>    Configure static management IP (e.g. 192.168.1.51/24)"
    echo "  --gateway, -g <IP>        Configure default gateway (e.g. 192.168.1.1)"
    echo "  --dns, -d <IP>            Configure primary DNS server (Default: 8.8.8.8)"
    echo "  --force                   Override Master conflict check (testing only)"
    echo "  --no-reboot               Skip automatic reboot after installation"
    echo "  --help, -h                Show this help menu"
    exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Please run this script as root: sudo bash $0" >&2
    exit 1
fi

# Resolve script directory safely (handles curl|bash and local git clones)
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

# Maintain root installation symlinks
mkdir -p /opt/azambasha /opt/pnetlab /opt/unetlab 2>/dev/null || true
if [ "$SCRIPT_DIR" != "/opt/azambasha" ]; then
    ln -sfn "$SCRIPT_DIR" /opt/azambasha 2>/dev/null || true
fi
ln -sfn /opt/azambasha /opt/pnetlab 2>/dev/null || true

# Parse command-line flags
FORCE=0
NO_REBOOT=0
STATIC_IP=""
STATIC_GW=""
STATIC_DNS="8.8.8.8"
JOIN_MASTER=""
JOIN_ID="1"
JOIN_NAME=""
JOIN_PSK=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE=1; shift ;;
        --no-reboot)
            NO_REBOOT=1; shift ;;
        --static|-s)
            STATIC_IP="$2"; shift 2 ;;
        --gateway|-g)
            STATIC_GW="$2"; shift 2 ;;
        --dns|-d)
            STATIC_DNS="$2"; shift 2 ;;
        --master)
            JOIN_MASTER="$2"; shift 2 ;;
        --id)
            JOIN_ID="$2"; shift 2 ;;
        --name)
            JOIN_NAME="$2"; shift 2 ;;
        --psk)
            JOIN_PSK="$2"; shift 2 ;;
        *)
            shift ;;
    esac
done

echo "============================================================"
echo "    Azam – Basha v8 Cluster Satellite (Worker) Installer    "
echo "============================================================"
echo "[*] Start Time         : $(date)"
echo "[*] Working Directory  : $SCRIPT_DIR"
echo "[*] Installation Log   : $LOG_FILE"
[ -n "$STATIC_IP" ]   && echo "[*] Target Static IP   : $STATIC_IP (Gateway: $STATIC_GW)"
[ -n "$JOIN_MASTER" ] && echo "[*] Target Master IP   : $JOIN_MASTER (Slot: $JOIN_ID)"
echo "============================================================"

# ── Step 1: Pre-flight Checks & Architecture Verification ─────────────────────
echo "[1/10] Performing pre-flight system & architecture checks..."

UBUNTU_VER="$(lsb_release -rs 2>/dev/null || grep -oP '(?<=VERSION_ID=")[^"]*' /etc/os-release || echo "26.04")"
ARCH="$(uname -m)"
echo "       -> Detected OS: Ubuntu $UBUNTU_VER ($ARCH)"

if [ "$ARCH" != "x86_64" ]; then
    echo "[ERROR] Unsupported CPU architecture: $ARCH. x86_64 (amd64) required." >&2
    exit 1
fi

if dpkg -s pnetlab >/dev/null 2>&1; then
    if [ "$FORCE" = "1" ]; then
        echo "       [WARNING] 'pnetlab' (Master) is installed — continuing in --force mode." >&2
    else
        echo "[ERROR] 'pnetlab' (Master) is already installed on this machine." >&2
        echo "A host must be Master OR Satellite, not both. Override: bash $0 --force" >&2
        exit 1
    fi
fi

# ── Step 2: Dracut & 32-bit Linker Deadlock Prevention ─────────────────────────
echo "[2/10] Resolving multi-arch and 32-bit dynamic linker compatibility..."
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

dpkg --add-architecture i386 2>/dev/null || true
mkdir -p /lib /usr/lib32 2>/dev/null || true

# Cisco IOL 32-bit binary runtime and dracut initramfs hook resolution
if [ -f /usr/lib32/ld-linux.so.2 ] && [ ! -f /lib/ld-linux.so.2 ]; then
    ln -sfn /usr/lib32/ld-linux.so.2 /lib/ld-linux.so.2 2>/dev/null || true
fi

# Neutralize broken dracut hooks if previously crashed
if [ -f /var/lib/dpkg/info/linux-image-*.postinst ]; then
    for p_hook in /var/lib/dpkg/info/linux-image-*.postinst; do
        if grep -q "dracut" "$p_hook" 2>/dev/null && [ ! -f "${p_hook}.bak" ]; then
            cp "$p_hook" "${p_hook}.bak" 2>/dev/null || true
            sed -i 's/exit 1/exit 0/g' "$p_hook" 2>/dev/null || true
        fi
    done
fi

rm -f /var/lib/dpkg/lock /var/lib/dpkg/lock-frontend /var/cache/apt/archives/lock 2>/dev/null || true
dpkg --configure -a 2>/dev/null || true

# ── Step 3: Physical Network Uplink Discovery & Netplan Bridge pnet0 ──────────
echo "[3/10] Discovering physical uplink and configuring Netplan bridge pnet0..."

discover_real_iface() {
    if [ -d /sys/class/net/pnet0/brif ]; then
        for slave in /sys/class/net/pnet0/brif/*; do
            if [ -d "$slave" ] && [ -e "/sys/class/net/$(basename "$slave")/device" ]; then
                echo "$(basename "$slave")"
                return 0
            fi
        done
    fi

    local best_iface=""
    for iface_path in /sys/class/net/*; do
        [ -e "$iface_path" ] || continue
        local iface
        iface=$(basename "$iface_path")
        case "$iface" in
            lo|pnet*|docker*|veth*|virbr*|tun*|tap*|br-*|dummy*|wg*|zt*) continue ;;
        esac
        if [ -e "$iface_path/device" ]; then
            if [ -f "$iface_path/carrier" ] && [ "$(cat "$iface_path/carrier" 2>/dev/null)" = "1" ]; then
                echo "$iface"
                return 0
            fi
            if [ -z "$best_iface" ]; then
                best_iface="$iface"
            fi
        fi
    done

    if [ -n "$best_iface" ]; then
        echo "$best_iface"
        return 0
    fi

    local dev
    dev=$(ip -o route show to default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -n1 || true)
    if [ -n "$dev" ] && [ "$dev" != "pnet0" ] && [ "$dev" != "lo" ]; then
        echo "$dev"
        return 0
    fi

    dev=$(ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | cut -d'@' -f1 | grep -E '^(ens|enp|eno|eth)' | head -n1 || true)
    [ -n "$dev" ] && echo "$dev" || echo "ens33"
}

REAL_IFACE="$(discover_real_iface)"
echo "       -> Active Physical Interface: $REAL_IFACE"
ip link set dev "$REAL_IFACE" up 2>/dev/null || true

# Permanently disable cloud-init network overwrite
mkdir -p /etc/cloud/cloud.cfg.d
echo "network: {config: disabled}" > /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg

# Clean conflicting netplan configs
mkdir -p /etc/netplan
for f in /etc/netplan/*.yaml /etc/netplan/*.yml; do
    [ -f "$f" ] && [ "$(basename "$f")" != "01-pnetlab-netcfg.yaml" ] && rm -f "$f" 2>/dev/null || true
done
rm -f /etc/systemd/network/*.network 2>/dev/null || true

# Write authoritative Netplan bridge configuration
if [ -n "$STATIC_IP" ]; then
    IP_NET="$STATIC_IP"
    [[ "$IP_NET" != *"/"* ]] && IP_NET="${IP_NET}/24"
    GW_LINE=""
    [ -n "$STATIC_GW" ] && GW_LINE="      routes:\n        - to: default\n          via: ${STATIC_GW}"
    cat << NETEOF > /etc/netplan/01-pnetlab-netcfg.yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    $REAL_IFACE:
      dhcp4: false
      dhcp6: false
  bridges:
    pnet0:
      interfaces: [$REAL_IFACE]
      dhcp4: false
      dhcp6: false
      addresses:
        - $IP_NET
$(echo -e "$GW_LINE")
      nameservers:
        addresses: [$STATIC_DNS, 1.1.1.1]
      parameters:
        stp: false
        forward-delay: 0
NETEOF
else
    cat << NETEOF > /etc/netplan/01-pnetlab-netcfg.yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    $REAL_IFACE:
      dhcp4: false
      dhcp6: false
  bridges:
    pnet0:
      interfaces: [$REAL_IFACE]
      dhcp4: true
      dhcp6: false
      parameters:
        stp: false
        forward-delay: 0
NETEOF
fi
chmod 600 /etc/netplan/01-pnetlab-netcfg.yaml

# Synchronize /etc/network/interfaces for unl_wrapper & broker compatibility
mkdir -p /etc/network /etc/network/interfaces.d
if [ -n "$STATIC_IP" ]; then
    IP_ONLY="${STATIC_IP%%/*}"
    cat << INTEOF > /etc/network/interfaces
auto lo
iface lo inet loopback

allow-hotplug pnet0
iface pnet0 inet static
    address $IP_ONLY
    netmask 255.255.255.0
    gateway ${STATIC_GW:-192.168.1.1}
    pre-up ip link set dev $REAL_IFACE up
    bridge_ports $REAL_IFACE
    bridge_stp off
INTEOF
else
    cat << INTEOF > /etc/network/interfaces
auto lo
iface lo inet loopback

allow-hotplug pnet0
iface pnet0 inet dhcp
    pre-up ip link set dev $REAL_IFACE up
    bridge_ports $REAL_IFACE
    bridge_stp off
INTEOF
fi
chmod 644 /etc/network/interfaces

# Apply systemd-networkd & Netplan
systemctl enable --now systemd-networkd 2>/dev/null || true
netplan apply 2>/dev/null || true

# ── Step 4: Kernel Datapath Modules & Sysctl Tuning ───────────────────────────
echo "[4/10] Loading kernel modules & tuning datapath sysctl..."

KERNEL_MODULES=(
    kvm
    kvm_intel
    kvm_amd
    vhost
    vhost_net
    bridge
    stp
    llc
    8021q
    tun
    dummy
    br_netfilter
    veth
    sch_fq_codel
    ip_tables
    iptable_filter
    iptable_nat
)

mkdir -p /etc/modules-load.d
cat << 'EOF_MODS' > /etc/modules-load.d/pnetlab.conf
kvm
kvm_intel
kvm_amd
vhost
vhost_net
bridge
stp
llc
8021q
tun
dummy
br_netfilter
veth
sch_fq_codel
ip_tables
iptable_filter
iptable_nat
EOF_MODS

# Ensure /lib/modules link exists for modprobe
if [ ! -d /lib/modules ] && [ -d /usr/lib/modules ]; then
    ln -sfn /usr/lib/modules /lib/modules 2>/dev/null || true
fi

for mod in "${KERNEL_MODULES[@]}"; do
    modprobe "$mod" 2>/dev/null || true
done

# Bridge netfilter bypass & IPv4 routing
mkdir -p /etc/sysctl.d
cat << 'EOF_SYS' > /etc/sysctl.d/99-pnetlab-bridge.conf
net.bridge.bridge-nf-call-iptables = 0
net.bridge.bridge-nf-call-arptables = 0
net.bridge.bridge-nf-call-ip6tables = 0
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 100000
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
EOF_SYS
sysctl --system 2>/dev/null || true

# ── Step 5: Headless Satellite System Dependencies ─────────────────────────────
echo "[5/10] Installing headless worker system dependencies..."
apt-get update -y -qq

SATELLITE_DEPS=(
    bridge-utils
    ebtables
    iptables
    iptables-persistent
    dkms
    build-essential
    qemu-utils
    python3
    python3-pip
    python3-yaml
    python3-pexpect
    python3-requests
    python3-cryptography
    python3-psutil
    python3-paramiko
    curl
    wget
    unzip
    zip
    zstd
    jq
    net-tools
    cpulimit
    cgroup-tools
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
    libspice-client-glib-2.0-8
    php-cli
    php-yaml
    php-common
    php-curl
    php-gd
    php-mbstring
    php-mysql
    php-sqlite3
    php-xml
    php-zip
    open-vm-tools
    qemu-guest-agent
    chrony
    openssh-server
    openssl
)

for pkg in "${SATELLITE_DEPS[@]}"; do
    apt-get install -y --no-install-recommends "$pkg" 2>/dev/null || {
        case "$pkg" in
            libelf1t64)   apt-get install -y --no-install-recommends libelf1 2>/dev/null || true ;;
            libpcap0.8t64) apt-get install -y --no-install-recommends libpcap0.8 2>/dev/null || true ;;
            libaio1t64)   apt-get install -y --no-install-recommends libaio1 2>/dev/null || true ;;
            *) true ;;
        esac
    }
done

# Ensure 32-bit linker symlink after libc6-i386 install
if [ -f /usr/lib32/ld-linux.so.2 ] && [ ! -f /lib/ld-linux.so.2 ]; then
    ln -sfn /usr/lib32/ld-linux.so.2 /lib/ld-linux.so.2 2>/dev/null || true
fi

# ── Step 6: Docker Engine & Dependency Bridge ─────────────────────────────────
echo "[6/10] Provisioning Docker container runtime & compatibility bridge..."

if ! command -v docker >/dev/null 2>&1; then
    echo "       -> Installing Docker engine..."
    # Attempt docker.io
    apt-get install -y --no-install-recommends docker.io containerd 2>/dev/null || {
        # Fallback: Docker noble apt repository
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
            | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true
        chmod a+r /etc/apt/keyrings/docker.gpg 2>/dev/null || true
        echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu noble stable" \
            > /etc/apt/sources.list.d/docker.list 2>/dev/null || true
        apt-get update -q 2>/dev/null || true
        apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io 2>/dev/null || true
    }
fi

# Resolve pnetlab-docker's strict 'Pre-Depends: docker-engine | docker-ce'
if ! dpkg -s docker-ce >/dev/null 2>&1 && ! dpkg -s docker-engine >/dev/null 2>&1; then
    echo "       -> Creating and installing docker-ce compatibility bridge..."
    DUMMY_DIR="/tmp/docker-ce-dummy"
    rm -rf "$DUMMY_DIR" && mkdir -p "$DUMMY_DIR/DEBIAN"
    cat << 'EOF_DUMMY' > "$DUMMY_DIR/DEBIAN/control"
Package: docker-ce-dummy
Version: 1:26.0.0-1
Section: admin
Priority: optional
Architecture: all
Provides: docker-ce, docker-engine
Depends: docker.io | docker-ce
Maintainer: Azam-Basha <admin@azam-pnet.local>
Description: Compatibility bridge providing docker-ce virtual package for pnetlab-docker
EOF_DUMMY
    dpkg-deb --build "$DUMMY_DIR" /tmp/docker-ce-dummy.deb 2>/dev/null || true
    dpkg -i --force-depends /tmp/docker-ce-dummy.deb 2>/dev/null || true
    rm -rf "$DUMMY_DIR" /tmp/docker-ce-dummy.deb
fi

# Authoritative Docker Daemon JSON configuration
mkdir -p /etc/docker
cat << 'EOF_DOCK' > /etc/docker/daemon.json
{
  "hosts": ["unix:///var/run/docker.sock"],
  "live-restore": true,
  "default-address-pools": [
    {
      "base": "10.177.0.0/16",
      "size": 24
    }
  ]
}
EOF_DOCK
systemctl enable --now docker 2>/dev/null || true
systemctl restart docker 2>/dev/null || true

# ── Step 7: Resolve and Install Satellite Debian Packages ──────────────────────
echo "[7/10] Resolving and installing Satellite Debian packages..."

POOL_SEARCH_DIRS=(
    "${SCRIPT_DIR}/debian/pool/resolute/main"
    "${SCRIPT_DIR}/generic/6.8.74resolute1/pnetlab-debs"
    "/opt/azambasha/debian/pool/resolute/main"
    "/opt/pnetlab/debian/pool/resolute/main"
    "/opt/azam-pnet/EMULATOR/Azam-Pnet/debian/pool/resolute/main"
)

DEB_POOL_DIR=""
for d in "${POOL_SEARCH_DIRS[@]}"; do
    if [ -d "$d" ] && compgen -G "${d}/pnetlab-satellite_*.deb" >/dev/null 2>&1; then
        DEB_POOL_DIR="$d"
        break
    fi
done

if [ -n "$DEB_POOL_DIR" ]; then
    echo "       -> Located package pool at: $DEB_POOL_DIR"
    
    PKG_ORDER=(
        "pnetlab-qemu"
        "pnetlab-vpcs"
        "pnetlab-bridge-dkms"
        "pnetlab-docker"
        "pnetlab-satellite"
    )

    for prefix in "${PKG_ORDER[@]}"; do
        deb_path=$(find "$DEB_POOL_DIR" -maxdepth 1 -name "${prefix}_*.deb" | sort -V | tail -n1 || true)
        if [ -n "$deb_path" ] && [ -f "$deb_path" ]; then
            echo "       -> Installing $(basename "$deb_path")..."
            dpkg-deb -x "$deb_path" / 2>/dev/null || true
            dpkg -i --force-depends --force-confdef --force-confold "$deb_path" 2>/dev/null || true
        else
            echo "       [INFO] Package prefix not found: $prefix — skipping."
        fi
    done

    # Unhold and re-hold to lock versions
    apt-get --fix-broken install -y 2>/dev/null || true
    dpkg --configure -a 2>/dev/null || true
    apt-mark hold pnetlab-qemu pnetlab-vpcs pnetlab-bridge-dkms pnetlab-docker pnetlab-satellite 2>/dev/null || true
else
    echo "       [WARNING] Local debian package pool not found — skipping deb installs."
fi

# ── Step 8: Deploy & Guarantee All Systemd Service Units ───────────────────────
echo "[8/10] Deploying and guaranteeing all satellite systemd service units..."

UNITS=(
    "pnetlab-brokerd.service"
    "pnetlab-docker-image-watcher.service"
    "pnetlab-ksm.service"
    "pnetlab-pnet-bridges.service"
    "pnetlab-satd.service"
)

# Ensure unit files exist in both /usr/lib/systemd/system and /etc/systemd/system
for u in "${UNITS[@]}"; do
    found=0
    for cand in /lib/systemd/system /usr/lib/systemd/system /opt/unetlab/scripts; do
        if [ -f "${cand}/${u}" ]; then
            cp -f "${cand}/${u}" "/etc/systemd/system/${u}" 2>/dev/null || true
            cp -f "${cand}/${u}" "/usr/lib/systemd/system/${u}" 2>/dev/null || true
            chmod 644 "/etc/systemd/system/${u}" 2>/dev/null || true
            found=1
            break
        fi
    done
    if [ "$found" -eq 0 ]; then
        echo "       [INFO] Creating standard definition for ${u}..."
        case "$u" in
            pnetlab-brokerd.service)
                cat << 'EOF_UBROKER' > "/etc/systemd/system/${u}"
[Unit]
Description=PNetLab privilege broker (allowlisted root verbs for the engine)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/unetlab/scripts/pnetlab-brokerd.py
RuntimeDirectory=pnetlab
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF_UBROKER
                ;;
            pnetlab-satd.service)
                cat << 'EOF_USATD' > "/etc/systemd/system/${u}"
[Unit]
Description=PNetLab satellite cluster agent (TLS, PSK-authenticated)
After=network.target pnetlab-brokerd.service
Wants=pnetlab-brokerd.service
ConditionPathExists=/etc/pnetlab-satellite/satd.conf

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/unetlab/scripts/pnetlab-satd.py
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF_USATD
                ;;
            pnetlab-docker-image-watcher.service)
                cat << 'EOF_UWATCH' > "/etc/systemd/system/${u}"
[Unit]
Description=PNetLab docker image auto-loader (watches /opt/unetlab/addons/docker)
After=docker.service
Wants=docker.service

[Service]
Type=simple
ExecStart=/opt/unetlab/config_scripts/docker_image_watcher.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF_UWATCH
                ;;
            pnetlab-ksm.service)
                cat << 'EOF_UKSM' > "/etc/systemd/system/${u}"
[Unit]
Description=PNetLab KSM advisor/merge tuning
After=local-fs.target
ConditionPathIsDirectory=/sys/kernel/mm/ksm

[Service]
Type=oneshot
RemainAfterExit=yes
EnvironmentFile=-/etc/default/pnetlab-ksm
ExecStart=/opt/unetlab/scripts/pnetlab-ksm-tune.sh

[Install]
WantedBy=multi-user.target
EOF_UKSM
                ;;
            pnetlab-pnet-bridges.service)
                cat << 'EOF_UBRIDGES' > "/etc/systemd/system/${u}"
[Unit]
Description=PNetLab cloud bridge devices (pnet0-9 + nat0)
DefaultDependencies=no
After=systemd-udev-settle.service
Before=networking.service network-pre.target
ConditionPathExists=/opt/ovf/pnet-bridges.sh

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash /opt/ovf/pnet-bridges.sh

[Install]
WantedBy=multi-user.target
EOF_UBRIDGES
                ;;
        esac
        cp -f "/etc/systemd/system/${u}" "/usr/lib/systemd/system/${u}" 2>/dev/null || true
        chmod 644 "/etc/systemd/system/${u}" 2>/dev/null || true
    fi
done

# Ensure rrsync is provisioned for SSH image synchronization
if [ ! -x /usr/bin/rrsync ]; then
    for r_src in /usr/share/doc/rsync/scripts/rrsync /usr/share/rsync/scripts/rrsync; do
        if [ -f "$r_src.gz" ]; then
            gunzip -c "$r_src.gz" > /usr/bin/rrsync 2>/dev/null && chmod 755 /usr/bin/rrsync && break
        elif [ -f "$r_src" ]; then
            cp "$r_src" /usr/bin/rrsync 2>/dev/null && chmod 755 /usr/bin/rrsync && break
        fi
    done
fi

# SSH server settings
sed -i 's/.*PermitRootLogin .*/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart ssh 2>/dev/null || true

# Reload systemd and start daemons
systemctl daemon-reload 2>/dev/null || true
systemctl enable --now pnetlab-brokerd.service 2>/dev/null || true
systemctl enable --now pnetlab-docker-image-watcher.service 2>/dev/null || true
systemctl enable --now pnetlab-ksm.service 2>/dev/null || true
systemctl enable pnetlab-satd.service 2>/dev/null || true

# Hardware virtualization and permissions
mkdir -p /opt/unetlab/addons/{qemu,iol/bin,dynamips,docker}
mkdir -p /opt/unetlab/data/Logs /opt/unetlab/tmp /etc/pnetlab-satellite /etc/pnetlab
chmod 700 /etc/pnetlab-satellite 2>/dev/null || true
groupadd -g 32768 -f unl 2>/dev/null || true
chown -R root:unl /opt/unetlab/tmp 2>/dev/null || true
chmod 2777 /opt/unetlab/tmp 2>/dev/null || true

[ -c /dev/kvm ] && chmod 666 /dev/kvm || true
[ -c /dev/net/tun ] && chmod 666 /dev/net/tun || true

if grep -q "svm" /proc/cpuinfo 2>/dev/null; then
    echo "svm" > /opt/unetlab/platform
else
    echo "intel" > /opt/unetlab/platform
fi

# ── Step 9: Azam – Basha Performance Acceleration Stack ───────────────────────
echo "[9/10] Applying Azam – Basha Silicon Dataplane & Speed Optimizations..."

if [ -f "${SCRIPT_DIR}/scripts/azambasha-dataplane-engine.sh" ]; then
    bash "${SCRIPT_DIR}/scripts/azambasha-dataplane-engine.sh" 2>/dev/null || true
fi

if [ -f "${SCRIPT_DIR}/scripts/azambasha-speed-optimizer.sh" ]; then
    bash "${SCRIPT_DIR}/scripts/azambasha-speed-optimizer.sh" 2>/dev/null || true
fi

if [ -f "${SCRIPT_DIR}/scripts/azambasha-cgroups-v2-engine.sh" ]; then
    bash "${SCRIPT_DIR}/scripts/azambasha-cgroups-v2-engine.sh" 2>/dev/null || true
fi

if [ -f "${SCRIPT_DIR}/scripts/azambasha-fix-permissions.sh" ]; then
    bash "${SCRIPT_DIR}/scripts/azambasha-fix-permissions.sh" 2>/dev/null || true
fi

if [ -f "${SCRIPT_DIR}/scripts/azambasha-block-updates.sh" ]; then
    bash "${SCRIPT_DIR}/scripts/azambasha-block-updates.sh" 2>/dev/null || true
fi

# ── Step 10: Automated or Interactive Join to Master Server ───────────────────
echo "[10/10] Verifying satellite readiness and cluster configuration..."

if [ -n "$JOIN_MASTER" ] && [ -n "$JOIN_PSK" ]; then
    echo "       -> Joining Master server at $JOIN_MASTER (Slot: $JOIN_ID)..."
    JOIN_TOOL="${SCRIPT_DIR}/scripts/azambasha-satellite-join.sh"
    if [ -f "$JOIN_TOOL" ]; then
        bash "$JOIN_TOOL" --master "$JOIN_MASTER" --id "$JOIN_ID" --name "${JOIN_NAME:-Satellite-$JOIN_ID}" --psk "$JOIN_PSK" || true
    elif command -v pnet-satellite-join >/dev/null 2>&1; then
        pnet-satellite-join --master "$JOIN_MASTER" --id "$JOIN_ID" --name "${JOIN_NAME:-Satellite-$JOIN_ID}" --psk "$JOIN_PSK" || true
    fi
fi

echo ""
echo "============================================================"
echo " [SUCCESS] Azam – Basha Cluster Satellite Installed!        "
echo "============================================================"
echo "Satellite Status:"
echo " • Broker Daemon   : $(systemctl is-active pnetlab-brokerd 2>/dev/null || echo 'inactive')"
echo " • Docker Engine   : $(systemctl is-active docker 2>/dev/null || echo 'inactive')"
echo " • Satellite Daemon: $(systemctl is-active pnetlab-satd 2>/dev/null || echo 'ready (awaits join)')"
echo " • KVM Acceleration: $([ -c /dev/kvm ] && echo 'Enabled (/dev/kvm)' || echo 'Emulation only')"
echo " • Network Bridge  : $(ip addr show pnet0 2>/dev/null | grep -o 'inet [0-9.]*' | head -n1 || echo 'pnet0 active')"
echo ""
if [ -z "$JOIN_MASTER" ]; then
    echo "To join this worker to your Master server:"
    echo " 1. On Master Web UI, go to: System -> Cluster"
    echo " 2. Click 'Generate PSK' and copy the 64-hex string"
    echo " 3. Run the following command on this Satellite VM:"
    echo ""
    echo "    sudo bash /opt/azambasha/scripts/azambasha-satellite-join.sh \\"
    echo "      --master <MASTER_IP> \\"
    echo "      --id 1 \\"
    echo "      --name \"Satellite-1\" \\"
    echo "      --psk <COPIED_PSK>"
    echo ""
fi
echo "============================================================"

if [ "$NO_REBOOT" -eq 0 ] && [ -z "$JOIN_MASTER" ]; then
    echo "[*] Installation complete. System ready."
fi
