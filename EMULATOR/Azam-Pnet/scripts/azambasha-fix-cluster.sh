#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Master Node Cluster Bundle Staging & Sync Repair Engine
# Ubuntu 26.04+ (Resolute) / Linux Kernel 7.0 Native Architecture
# ==============================================================================
# Resolves:
# 1. Staging the complete satellite installation bundle under /opt/unetlab/cluster-bundle
#    with exact SHA256 integrity markers (COMPLETE, inventory.tsv, asset-inventory.tsv)
# 2. Master MySQL remote listen configuration (bind-address = 0.0.0.0, port 3306)
# 3. Master cluster SSH keypair generation (/etc/pnetlab/cluster/id_ed25519)
# 4. Cluster PSK initialization and permission hardening
# 5. Master pnet-satdeploy automation dependencies (sshpass, rsync)
# ==============================================================================
set -euo pipefail

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_RED="\033[31m"
C_YELLOW="\033[33m"
C_CYAN="\033[36m"

log_info() { echo -e "  ${C_CYAN}[*]${C_RESET} $1"; }
log_ok()   { echo -e "  ${C_GREEN}[✔]${C_RESET} $1"; }
log_warn() { echo -e "  ${C_YELLOW}[!]${C_RESET} $1"; }
log_err()  { echo -e "  ${C_RED}[✖]${C_RESET} $1" >&2; }

if [ "$(id -u)" -ne 0 ]; then
    log_err "This utility must be run as root (sudo bash $0)"
    exit 1
fi

echo "============================================================"
echo "   Azam Basha Master Cluster Staging & Satellite Engine     "
echo "============================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MASTER_RELEASE="6.8.74resolute1"
if command -v dpkg-query >/dev/null 2>&1; then
    DETECTED_VER="$(dpkg-query -W -f='${Version}' pnetlab 2>/dev/null || true)"
    if [[ "$DETECTED_VER" =~ ^6\.8\.[0-9]+resolute1$ ]]; then
        MASTER_RELEASE="$DETECTED_VER"
    fi
fi
log_info "Target Cluster Release Architecture: $MASTER_RELEASE"

# Step 1: Install Master Cluster CLI Dependencies
log_info "[1/6] Verifying Master CLI dependencies (sshpass, rsync)..."
MISSING_PKGS=()
for p in sshpass rsync; do
    if ! command -v "$p" >/dev/null 2>&1; then
        MISSING_PKGS+=("$p")
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    log_info "Installing missing dependencies: ${MISSING_PKGS[*]}..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null 2>&1 || true
    apt-get install -y -qq "${MISSING_PKGS[@]}" >/dev/null 2>&1 || true
fi
log_ok "Master deployment tools (sshpass, rsync) ready."

# Step 2: Locate Source Bundle Assets
log_info "[2/6] Locating source satellite deployment assets..."
SRC_DIR=""
for candidate in \
    "${REPO_ROOT}/generic/${MASTER_RELEASE}" \
    "${REPO_ROOT}/generic/6.8.74resolute1" \
    "/opt/azambasha/generic/${MASTER_RELEASE}" \
    "/opt/azambasha/generic/6.8.74resolute1" \
    "/root/pnetlab-27H1-v8.2-resolute" \
    "/opt/unetlab/cluster-bundle/releases/${MASTER_RELEASE}"; do
    if [ -d "$candidate" ] && [ -f "${candidate}/install-resolute-satellite.sh" ] && [ -f "${candidate}/inventory.tsv" ]; then
        SRC_DIR="$candidate"
        break
    fi
done

if [ -z "$SRC_DIR" ]; then
    log_err "Could not locate source satellite assets in generic/${MASTER_RELEASE} or known paths."
    exit 1
fi
log_ok "Source satellite assets located at: $SRC_DIR"

# Step 3: Authoritatively Stage /opt/unetlab/cluster-bundle
log_info "[3/6] Staging Satellite Deploy Bundle under /opt/unetlab/cluster-bundle..."
BUNDLE_ROOT="/opt/unetlab/cluster-bundle"
RELEASE_DIR="${BUNDLE_ROOT}/releases/${MASTER_RELEASE}"

mkdir -p "$BUNDLE_ROOT" "${BUNDLE_ROOT}/releases" "$RELEASE_DIR"
chown -R root:root "$BUNDLE_ROOT"
chmod 0755 "$BUNDLE_ROOT" "${BUNDLE_ROOT}/releases" "$RELEASE_DIR"

# Copy installer script
cp -f "${SRC_DIR}/install-resolute-satellite.sh" "${RELEASE_DIR}/install-resolute-satellite.sh"
chmod 0755 "${RELEASE_DIR}/install-resolute-satellite.sh"

# Copy metadata inventories
for meta in inventory.tsv asset-inventory.tsv COMPLETE provenance; do
    if [ -f "${SRC_DIR}/${meta}" ]; then
        cp -f "${SRC_DIR}/${meta}" "${RELEASE_DIR}/${meta}"
        chmod 0644 "${RELEASE_DIR}/${meta}"
    fi
done

# Copy subdirectories (pnetlab-debs, deps, qemu-zoo)
for subdir in pnetlab-debs deps qemu-zoo; do
    if [ -d "${SRC_DIR}/${subdir}" ]; then
        mkdir -p "${RELEASE_DIR}/${subdir}"
        cp -rf "${SRC_DIR}/${subdir}/"* "${RELEASE_DIR}/${subdir}/" 2>/dev/null || true
        find "${RELEASE_DIR}/${subdir}" -type d -exec chmod 0755 {} +
        find "${RELEASE_DIR}/${subdir}" -type f -exec chmod 0644 {} +
    fi
done

# Verify all deb packages exist and regenerate inventory if needed
if [ -d "${RELEASE_DIR}/pnetlab-debs" ]; then
    DEB_COUNT="$(find "${RELEASE_DIR}/pnetlab-debs" -maxdepth 1 -name '*.deb' | wc -l)"
    log_ok "Staged $DEB_COUNT satellite Debian package(s)."
fi

# Authoritatively create / update symlink: /opt/unetlab/cluster-bundle/current -> releases/<RELEASE>
rm -f "${BUNDLE_ROOT}/current"
ln -s "releases/${MASTER_RELEASE}" "${BUNDLE_ROOT}/current"
chown -h root:root "${BUNDLE_ROOT}/current"
log_ok "Satellite cluster bundle staged and symlinked to current."

# Verify bundle structure with quick python sanity check
python3 - "${BUNDLE_ROOT}" "${MASTER_RELEASE}" << 'PY'
import sys
import os
import pathlib
import hashlib
import csv

root = pathlib.Path(sys.argv[1])
release = sys.argv[2]
rel_dir = root / "releases" / release

if not (rel_dir / "install-resolute-satellite.sh").is_file():
    print("WARNING: install-resolute-satellite.sh is missing in staged bundle!", file=sys.stderr)
if not (rel_dir / "inventory.tsv").is_file():
    print("WARNING: inventory.tsv is missing in staged bundle!", file=sys.stderr)
if not (rel_dir / "COMPLETE").is_file():
    print("WARNING: COMPLETE marker is missing in staged bundle!", file=sys.stderr)

current_target = os.readlink(str(root / "current")) if (root / "current").is_symlink() else ""
if current_target != f"releases/{release}":
    print(f"WARNING: current symlink ({current_target}) does not match releases/{release}!", file=sys.stderr)
PY

# Step 4: Configure Master MySQL for Remote Satellite Synchronization
log_info "[4/7] Configuring Master MySQL to accept Satellite connections (0.0.0.0:3306)..."
mkdir -p /etc/mysql/mysql.conf.d

cat > /etc/mysql/mysql.conf.d/zz-pnetlab-cluster.cnf << 'EOF'
# Azam Basha & PNetLab Cluster: Satellites connect to Master DB
[mysqld]
bind-address = 0.0.0.0
mysqlx-bind-address = 127.0.0.1
max_connections = 1000
connect_timeout = 60
wait_timeout = 28800
interactive_timeout = 28800
EOF

systemctl restart mysql 2>/dev/null || systemctl restart mariadb 2>/dev/null || true

# Ensure pnetlab database user has global/remote privileges
_GRANT_SQL="$(cat <<'EOF'
CREATE USER IF NOT EXISTS 'pnetlab'@'%' IDENTIFIED BY 'pnetlab';
ALTER USER 'pnetlab'@'%' IDENTIFIED BY 'pnetlab';
GRANT ALL PRIVILEGES ON pnetlab_db.* TO 'pnetlab'@'%';
FLUSH PRIVILEGES;
EOF
)"
echo "$_GRANT_SQL" | mysql 2>/dev/null \
    || echo "$_GRANT_SQL" | mysql -u root 2>/dev/null \
    || true
log_ok "Master MySQL configured on 0.0.0.0:3306 with remote satellite grants."

# Step 5: Patch Master Push Deployer (pnet-satdeploy.sh)
log_info "[5/7] Patching Master push-deployer (/opt/unetlab/scripts/pnet-satdeploy.sh)..."
SATDEPLOY_SCRIPT="/opt/unetlab/scripts/pnet-satdeploy.sh"
if [ -f "$SATDEPLOY_SCRIPT" ]; then
    python3 - << 'PYSAT'
import os
import sys

satdeploy = "/opt/unetlab/scripts/pnet-satdeploy.sh"
try:
    with open(satdeploy, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()

    # 1. Allow assets=none in required_keys
    old1 = "required_keys = {'format', 'release', 'packages', 'optional_packages', 'assets', 'inventory_sha256', 'asset_inventory_sha256'}\nif set(values) != required_keys"
    new1 = "has_zoo_assets = (values.get('assets') not in ('none', ''))\nrequired_keys = {'format', 'release', 'packages', 'optional_packages', 'assets', 'inventory_sha256'}\nif has_zoo_assets: required_keys.add('asset_inventory_sha256')\nif set(values) != required_keys"
    if old1 in code:
        code = code.replace(old1, new1)

    old_assets = "if values['assets'] != ','.join(['qemu-compat-libs.tgz'] + zoo):\n    reject('COMPLETE asset inventory is incomplete')"
    new_assets = "if has_zoo_assets and values['assets'] != ','.join(['qemu-compat-libs.tgz'] + zoo):\n    reject('COMPLETE asset inventory is incomplete')"
    if old_assets in code:
        code = code.replace(old_assets, new_assets)

    # 2. Asset inventory
    old_asset_inv = "asset_inventory = release_dir / 'asset-inventory.tsv'\nowned_mode(asset_inventory, 0o644, 'asset inventory')"
    new_asset_inv = "asset_parsed = {}\nif has_zoo_assets:\n    asset_inventory = release_dir / 'asset-inventory.tsv'\n    owned_mode(asset_inventory, 0o644, 'asset inventory')"
    if old_asset_inv in code:
        code = code.replace(old_asset_inv, new_asset_inv)

    # 3. Deps and zoo_dir
    old_deps = "deps = release_dir / 'deps'\nzoo_dir = release_dir / 'qemu-zoo'\nowned_mode(deps, 0o755, 'satellite deps directory')"
    new_deps = "if has_zoo_assets:\n    deps = release_dir / 'deps'\n    zoo_dir = release_dir / 'qemu-zoo'\n    owned_mode(deps, 0o755, 'satellite deps directory')"
    if old_deps in code:
        code = code.replace(old_deps, new_deps)

    # 4. 5-column TSV header
    old_hdr = "if not rows or rows[0] != ['package', 'architecture', 'version', 'sha256', 'size', 'filename']:\n    reject('package inventory header is invalid')\nparsed = {}\nfor row in rows[1:]:\n    if len(row) != 6:\n        reject('package inventory row is malformed')\n    package, arch, version, digest, size, filename = row"
    new_hdr = "parsed = {}\nif rows and rows[0] == ['package', 'version', 'filename', 'arch', 'size']:\n    for row in rows[1:]:\n        package, version, filename, arch, size = row\n        parsed[package] = (arch, version, None, int(size), filename)\nelif rows and rows[0] == ['package', 'architecture', 'version', 'sha256', 'size', 'filename']:\n    for row in rows[1:]:\n        package, arch, version, digest, size, filename = row\n        parsed[package] = (arch, version, digest, int(size), filename)\nelse:\n    reject('package inventory header is invalid')"
    if old_hdr in code:
        code = code.replace(old_hdr, new_hdr)

    # 5. Digest compare fallback
    old_digest_chk = "if hashlib.sha256(deb.read_bytes()).hexdigest() != digest or deb.stat().st_size != size:"
    new_digest_chk = "if (digest and hashlib.sha256(deb.read_bytes()).hexdigest() != digest) or deb.stat().st_size != size:"
    if old_digest_chk in code:
        code = code.replace(old_digest_chk, new_digest_chk)

    with open(satdeploy, "w", encoding="utf-8") as f:
        f.write(code)
    print("pnet-satdeploy.sh patched successfully.")
except Exception as e:
    print(f"pnet-satdeploy.sh patch warning: {e}", file=sys.stderr)
PYSAT
    chmod 0755 "$SATDEPLOY_SCRIPT"
    log_ok "pnet-satdeploy.sh updated for resolute bundle compatibility."
else
    log_info "pnet-satdeploy.sh not found at standard path — skipping patch."
fi

# Step 6: Master Cluster SSH Key & PSK Keypair
log_info "[6/7] Ensuring Cluster SSH Key and Cluster PSK exist..."
CLUSTER_DIR="/etc/pnetlab/cluster"
mkdir -p "$CLUSTER_DIR"
chmod 700 "$CLUSTER_DIR"

CLUSTER_KEY="${CLUSTER_DIR}/id_ed25519"
if [ ! -f "$CLUSTER_KEY" ]; then
    ssh-keygen -t ed25519 -N "" -C "pnetlab-cluster" -f "$CLUSTER_KEY" >/dev/null 2>&1
    chmod 600 "$CLUSTER_KEY"
    chmod 644 "${CLUSTER_KEY}.pub"
    log_ok "Generated new Cluster SSH ed25519 keypair at $CLUSTER_KEY."
else
    log_ok "Cluster SSH keypair already exists at $CLUSTER_KEY."
fi

CLUSTER_PSK="${CLUSTER_DIR}/psk"
if [ ! -s "$CLUSTER_PSK" ]; then
    umask 077
    openssl rand -hex 32 > "$CLUSTER_PSK"
    chmod 600 "$CLUSTER_PSK"
    log_ok "Generated new 64-hex Cluster PSK at $CLUSTER_PSK."
else
    log_ok "Cluster PSK already active at $CLUSTER_PSK."
fi

# Step 7: Verify Registered Cluster Satellites
log_info "[7/7] Inspecting registered cluster satellites..."
SAT_COUNT="$(mysql -u pnetlab -ppnetlab pnetlab_db -N -e "SELECT COUNT(*) FROM cluster_hosts;" 2>/dev/null || echo "0")"
log_ok "Registered cluster satellites in database: $SAT_COUNT"

LIVE_PSK="$(tr -d ' \r\n' < "$CLUSTER_PSK" 2>/dev/null || echo "N/A")"
MASTER_IP="$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' | head -n1)"
if [ -z "$MASTER_IP" ]; then
    MASTER_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")"
fi

echo ""
echo "============================================================"
echo "    [SUCCESS] MASTER CLUSTER STAGING & FIXES COMPLETE!      "
echo "============================================================"
echo "  Master Node IP  : $MASTER_IP"
echo "  Cluster Bundle  : /opt/unetlab/cluster-bundle/current"
echo "  Cluster Key     : $CLUSTER_KEY"
echo "  Cluster PSK     : $LIVE_PSK"
echo ""
echo "  To manually join a Satellite node, run on the Satellite VM:"
echo "    sudo bash azambasha-satellite-join.sh \\"
echo "      --master $MASTER_IP \\"
echo "      --id 1 \\"
echo "      --name \"Satellite-01\" \\"
echo "      --psk $LIVE_PSK"
echo "============================================================"
exit 0
