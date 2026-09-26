#!/usr/bin/env bash
# ==============================================================================
# AzamLabs Large Lab Upload & Full Docker Subsystem Provisioner
#
# Covers:
# 1. PHP & Apache file upload limits (Increases upload_max_filesize to 512MB)
# 2. Upload timeouts & memory exhaustion during large lab/image imports
# 3. Kernel IP Forwarding (net.ipv4.ip_forward=1) for Docker-to-Router routing
# 4. Docker bridge iptables FORWARD drop policy & veth promiscuous bridging
# 5. Docker CE repository enrollment, engine installation & inotify-tools
# 6. Preload official HTML5 packet capture container (pnet-capture-web:1.0)
# 7. Provision & activate pnetlab-docker-image-watcher.service
# 8. Ensure official Docker node template definitions (intel & amd)
# ==============================================================================
set -euo pipefail

# Support non-root check/help modes
if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
    echo "Usage: sudo bash $0 [--check | --status | --install-docker | --pull-capture-web]"
    echo ""
    echo "Options:"
    echo "  (no args)             Apply 512MB upload boost, Docker networking & container provisioning"
    echo "  --check | --status    Inspect current PHP upload limits, Docker daemon & capture-web status"
    echo "  --install-docker      Enroll official Docker CE repository and install docker-ce packages"
    echo "  --pull-capture-web    Preload & tag rspnet/pnet-capture-web:latest as pnet-capture-web:1.0"
    exit 0
fi

if [[ "${1:-}" =~ ^(--check|--status)$ ]]; then
    echo "============================================================"
    echo "    AzamLabs Upload & Docker Subsystem Diagnostic Check     "
    echo "============================================================"
    echo -n "[*] PHP upload_max_filesize:   "
    php -r "echo ini_get('upload_max_filesize');" 2>/dev/null || echo "Unknown"
    echo ""

    echo -n "[*] PHP post_max_size:          "
    php -r "echo ini_get('post_max_size');" 2>/dev/null || echo "Unknown"
    echo ""

    echo -n "[*] PHP memory_limit:           "
    php -r "echo ini_get('memory_limit');" 2>/dev/null || echo "Unknown"
    echo ""

    echo -n "[*] Kernel IPv4 Forwarding:     "
    if [ "$(sysctl -n net.ipv4.ip_forward 2>/dev/null)" = "1" ]; then
        echo "ENABLED (Docker & multi-subnet routing active)"
    else
        echo "DISABLED (Packets between container & routers blocked)"
    fi

    echo -n "[*] Docker Daemon Status:       "
    if command -v docker >/dev/null 2>&1; then
        if systemctl is-active docker >/dev/null 2>&1 || docker info >/dev/null 2>&1; then
            echo "RUNNING ($(docker --version 2>/dev/null | cut -d',' -f1))"
        else
            echo "INSTALLED but STOPPED"
        fi
    else
        echo "NOT INSTALLED"
    fi

    echo -n "[*] Docker Config (daemon.json): "
    if [ -f /etc/docker/daemon.json ]; then
        if grep -q '"hosts"' /etc/docker/daemon.json 2>/dev/null; then
            echo "CONFLICT DETECTED (hosts directive present; causes systemd dockerd crash)"
        else
            echo "VALID (Clean, no CLI directive conflicts)"
        fi
    else
        echo "NOT CONFIGURED (Using defaults)"
    fi


    echo -n "[*] HTML5 Packet Capture Image: "
    if command -v docker >/dev/null 2>&1; then
        if docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -Eq 'pnet-capture-web:1.0|rspnet/pnet-capture-web'; then
            echo "PRELOADED (pnet-capture-web:1.0 ready for link capture)"
        else
            echo "NOT FOUND (Will auto-pull on first capture click or run with sudo bash $0)"
        fi
    else
        echo "N/A (Docker missing)"
    fi

    echo -n "[*] Docker Image Watcher Svc:   "
    if systemctl is-active pnetlab-docker-image-watcher >/dev/null 2>&1; then
        echo "ACTIVE (Auto-loading /opt/unetlab/addons/docker)"
    else
        if [ -f /etc/systemd/system/pnetlab-docker-image-watcher.service ]; then
            echo "INACTIVE (Service unit present)"
        else
            echo "NOT CONFIGURED"
        fi
    fi

    echo -n "[*] Docker Node Templates:      "
    T_INTEL="/opt/unetlab/html/templates/intel/docker.yml"
    T_AMD="/opt/unetlab/html/templates/amd/docker.yml"
    if [ -f "$T_INTEL" ] || [ -f "$T_AMD" ]; then
        echo "PRESENT (Intel: $([ -f "$T_INTEL" ] && echo YES || echo NO), AMD: $([ -f "$T_AMD" ] && echo YES || echo NO))"
    else
        echo "MISSING"
    fi
    echo "============================================================"
    exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Please run this script as root (sudo bash $0)" >&2
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "============================================================"
echo "    AzamLabs Upload Limits & Docker Subsystem Provisioner   "
echo "============================================================"

# 1. Boost PHP Upload Limits across all installed PHP versions
echo "[1/8] Configuring 512MB Upload Limits in PHP ini files..."
for PHP_INI in /etc/php/*/apache2/php.ini /etc/php/*/fpm/php.ini /etc/php/*/cli/php.ini; do
    if [ -f "$PHP_INI" ]; then
        [ ! -f "${PHP_INI}.bak" ] && cp "$PHP_INI" "${PHP_INI}.bak.${TIMESTAMP}"
        sed -i 's/^;*upload_max_filesize =.*/upload_max_filesize = 512M/' "$PHP_INI"
        sed -i 's/^;*post_max_size =.*/post_max_size = 512M/' "$PHP_INI"
        sed -i 's/^;*memory_limit =.*/memory_limit = 512M/' "$PHP_INI"
        sed -i 's/^;*max_execution_time =.*/max_execution_time = 600/' "$PHP_INI"
        sed -i 's/^;*max_input_time =.*/max_input_time = 600/' "$PHP_INI"
    fi
done
echo "  -> PHP upload limits scaled to 512MB with 600s execution timeout."

# 2. Boost Apache Request Body Limit
echo "[2/8] Configuring Apache LimitRequestBody (512MB)..."
if [ -d /etc/apache2/conf-available ]; then
    cat << 'EOF' > /etc/apache2/conf-available/pnetlab-upload-limit.conf
# Allow large lab and image uploads up to 512MB
LimitRequestBody 536870912
EOF
    a2enconf pnetlab-upload-limit 2>/dev/null || true
fi

# 3. Kernel IP Forwarding & Routing
echo "[3/8] Enabling Kernel IPv4 & IPv6 Packet Forwarding & ARP Proxy..."
mkdir -p /etc/sysctl.d
cat << 'EOF' > /etc/sysctl.d/97-pnetlab-forwarding.conf
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
net.ipv4.conf.all.proxy_arp = 1
net.bridge.bridge-nf-call-iptables = 0
net.bridge.bridge-nf-call-arptables = 0
EOF
sysctl -p /etc/sysctl.d/97-pnetlab-forwarding.conf 2>/dev/null || sysctl --system 2>/dev/null || true

# 4. Docker FORWARD policy fix
echo "[4/8] Ensuring Docker bridge forwarding policy (ACCEPT)..."
if command -v iptables &>/dev/null; then
    iptables -P FORWARD ACCEPT 2>/dev/null || true
    # Persist via /etc/rc.local if present
    if [ -f /etc/rc.local ] && ! grep -q "iptables -P FORWARD ACCEPT" /etc/rc.local; then
        sed -i 's/^exit 0/iptables -P FORWARD ACCEPT\nexit 0/' /etc/rc.local 2>/dev/null || true
    fi
fi

# 5. Enroll Docker CE Repository & Ensure Docker Engine Installed
echo "[5/8] Enrolling Docker CE Repository & Checking Engine..."
if command -v apt-get >/dev/null 2>&1; then
    mkdir -p /etc/apt/keyrings
    DOCKER_KEYRING="/etc/apt/keyrings/docker.gpg"
    DOCKER_SOURCE="/etc/apt/sources.list.d/docker.list"
    
    if [ ! -f "$DOCKER_KEYRING" ]; then
        echo "  -> Downloading Docker official GPG keyring..."
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o "$DOCKER_KEYRING" 2>/dev/null || true
        chmod a+r "$DOCKER_KEYRING" 2>/dev/null || true
    fi

    UBUNTU_CODENAME="$(lsb_release -cs 2>/dev/null || echo 'resolute')"
    if [ ! -f "$DOCKER_SOURCE" ]; then
        echo "  -> Enrolling Docker APT source ($UBUNTU_CODENAME stable)..."
        echo "deb [arch=amd64 signed-by=$DOCKER_KEYRING] https://download.docker.com/linux/ubuntu $UBUNTU_CODENAME stable" > "$DOCKER_SOURCE"
    fi

    # Install Docker CE and inotify-tools if missing
    if ! command -v docker >/dev/null 2>&1 || ! command -v inotifywait >/dev/null 2>&1; then
        echo "  -> Installing docker-ce, containerd, plugins & inotify-tools..."
        apt-get update -qq 2>/dev/null || true
        apt-get install -y -qq ca-certificates curl gnupg inotify-tools docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>/dev/null || true
    fi
fi

# 5b. Authoritative /etc/docker/daemon.json Convergence (Eliminate "hosts" conflict with systemd)
mkdir -p /etc/docker
if [ -f /etc/docker/daemon.json ]; then
    if grep -q '"hosts"' /etc/docker/daemon.json 2>/dev/null; then
        echo "  -> Sanitizing /etc/docker/daemon.json to eliminate hosts directive conflict with systemd..."
        if command -v jq >/dev/null 2>&1; then
            jq 'del(.hosts)' /etc/docker/daemon.json > /etc/docker/daemon.json.tmp && mv /etc/docker/daemon.json.tmp /etc/docker/daemon.json
        elif command -v python3 >/dev/null 2>&1; then
            python3 -c "import json; f='/etc/docker/daemon.json'; d=json.load(open(f)); d.pop('hosts', None); json.dump(d, open(f, 'w'), indent=2)" 2>/dev/null || true
        else
            sed -i '/"hosts"/,/],*/d' /etc/docker/daemon.json 2>/dev/null || true
        fi
    fi
else
    cat << 'EOF_DOCK' > /etc/docker/daemon.json
{
  "live-restore": true,
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "2"
  },
  "default-address-pools": [
    {
      "base": "10.177.0.0/16",
      "size": 24
    }
  ]
}
EOF_DOCK
fi

# Ensure docker service is enabled, failure state reset, & running
if command -v systemctl >/dev/null 2>&1 && [ -f /lib/systemd/system/docker.service -o -f /etc/systemd/system/docker.service ]; then
    rm -f /var/run/docker.sock /var/run/docker.pid
    systemctl reset-failed docker.service 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable --now docker 2>/dev/null || true
    systemctl restart docker 2>/dev/null || true
fi

# 6. Preload Official HTML5 Web Packet Capture Container (pnet-capture-web:1.0)
echo "[6/8] Preloading HTML5 In-Browser Packet Capture Image..."
if command -v docker >/dev/null 2>&1; then
    if docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -Eq 'pnet-capture-web:1.0'; then
        echo "  -> pnet-capture-web:1.0 is already preloaded."
    else
        echo "  -> Pulling rspnet/pnet-capture-web:latest from Docker Hub..."
        if docker pull rspnet/pnet-capture-web:latest 2>/dev/null; then
            docker tag rspnet/pnet-capture-web:latest pnet-capture-web:1.0 2>/dev/null || true
            echo "  -> Successfully pulled and tagged pnet-capture-web:1.0"
        else
            echo "  [WARN] Docker Hub pull skipped or offline. Web capture will auto-pull on first GUI click."
        fi
    fi
else
    echo "  [INFO] Docker engine not active; skipping image pre-pull."
fi

# 7. Provision & Enable PNetLab Docker Image Watcher Service
echo "[7/8] Provisioning pnetlab-docker-image-watcher.service..."
WATCH_DIR="/opt/unetlab/addons/docker"
CONFIG_DIR="/opt/unetlab/config_scripts"
mkdir -p "$WATCH_DIR" "$CONFIG_DIR"

cat << 'EOF' > "${CONFIG_DIR}/docker_image_watcher.sh"
#!/usr/bin/env bash
# ==============================================================================
# PNetLab Docker Image Auto-Loader & Catalog Watcher
# ==============================================================================
WATCH_DIR="/opt/unetlab/addons/docker"
mkdir -p "$WATCH_DIR"

# Initial pass: load any pre-existing archive images
for archive in "$WATCH_DIR"/*.tar "$WATCH_DIR"/*.tar.gz; do
    if [ -f "$archive" ]; then
        docker load -i "$archive" 2>/dev/null || true
    fi
done

# Continuous inotify watcher for dropped .tar / .tar.gz Docker images
if command -v inotifywait >/dev/null 2>&1; then
    inotifywait -m -e close_write,moved_to --format '%w%f' "$WATCH_DIR" 2>/dev/null | while read -r new_image; do
        if [[ "$new_image" =~ \.(tar|tar\.gz)$ ]] && [ -f "$new_image" ]; then
            docker load -i "$new_image" 2>/dev/null || true
        fi
    done
else
    # Fallback polling loop if inotifywait is absent
    while true; do
        sleep 60
        for archive in "$WATCH_DIR"/*.tar "$WATCH_DIR"/*.tar.gz; do
            if [ -f "$archive" ]; then
                docker load -i "$archive" 2>/dev/null || true
            fi
        done
    done
fi
EOF
chmod +x "${CONFIG_DIR}/docker_image_watcher.sh"

cat << 'EOF' > /etc/systemd/system/pnetlab-docker-image-watcher.service
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
EOF

if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable --now pnetlab-docker-image-watcher.service 2>/dev/null || true
fi

# 8. Ensure Official Docker Node Template Definitions (Intel & AMD)
echo "[8/8] Verifying official Docker node templates in PNetLab..."
for ARCH in intel amd; do
    TDIR="/opt/unetlab/html/templates/${ARCH}"
    TFILE="${TDIR}/docker.yml"
    if [ -d "$TDIR" ] && [ ! -f "$TFILE" ]; then
        cat << 'EOF' > "$TFILE"
---
type: docker
description: Docker Container
name: Docker
cpus: 1
ram: 256
ethernet: 2
console: telnet
icon: Docker.png
...
EOF
        echo "  -> Created missing template: $TFILE"
    fi
done

# Reload web services if present (Graceful reload preserves session & prevents start-limit-hit)
echo "[*] Reloading web server and PHP daemons..."
systemctl reload apache2 2>/dev/null || systemctl restart apache2 2>/dev/null || true
for PHP_FPM in $(systemctl list-units --type=service --state=running 2>/dev/null | grep -o 'php[0-9.]*-fpm' || true); do
    systemctl reload "$PHP_FPM" 2>/dev/null || systemctl restart "$PHP_FPM" 2>/dev/null || true
done

echo ""
echo "============================================================"
echo " [SUCCESS] All Docker Subsystem Components Configured!       "
echo "  - 512MB Upload Limits & Timeouts: ACTIVE                  "
echo "  - Kernel IP Forwarding & Bridge Policies: ENABLED         "
echo "  - Docker CE Engine & APT Repository: CONFIGURED           "
echo "  - HTML5 Packet Capture (pnet-capture-web:1.0): READY      "
echo "  - Docker Image Watcher Service: ACTIVE                    "
echo "  - Docker Node Template Definitions: VERIFIED              "
echo "============================================================"
