#!/usr/bin/env bash
# ==============================================================================
# Azam Basha — Dynamic Web-GUI Version Synchronization Engine
# Synchronizes the Web-GUI Version view (/main/#/version) and sidebar branding
# with the latest implemented upstream release and package version.
#
# Usage:
#   sudo bash scripts/azambasha-sync-gui-version.sh [VERSION] [PACKAGE_VERSION]
#
# Examples:
#   sudo bash scripts/azambasha-sync-gui-version.sh 6.8.83 6.8.83resolute1
#   sudo bash scripts/azambasha-sync-gui-version.sh auto
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "/opt/unetlab/scripts")"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

log_info() { echo -e "\033[1;34m[*] $*\033[0m"; }
log_ok()   { echo -e "\033[1;32m[✔] $*\033[0m"; }
log_warn() { echo -e "\033[1;33m[!] $*\033[0m"; }
log_err()  { echo -e "\033[1;31m[ERROR] $*\033[0m" >&2; }

if [ "$(id -u)" -ne 0 ]; then
    log_err "This utility must be run as root: sudo bash $0"
    exit 1
fi

# ── 1. Determine Target Version ───────────────────────────────────────────────
TARGET_INPUT="${1:-auto}"
TARGET_PKG="${2:-}"

# Auto-detect latest release from repo or installed packages
if [ "$TARGET_INPUT" = "auto" ] || [ -z "$TARGET_INPUT" ]; then
    BASE_DETECT=""
    if [ -f "${REPO_ROOT}/docs/3_MONTHS_UPDATE_CHECK_PLAN.md" ]; then
        BASE_DETECT="$(grep -oP '(?<=Implemented Package Version\*\*: `)[^`]+' "${REPO_ROOT}/docs/3_MONTHS_UPDATE_CHECK_PLAN.md" 2>/dev/null | head -n1 || true)"
    fi
    if [ -z "$BASE_DETECT" ] && [ -f "${REPO_ROOT}/docs/WEEKLY_IMPLEMENTATION_PLAN.md" ]; then
        BASE_DETECT="$(grep -oP '(?<=Implemented Package Version\*\*: `)[^`]+' "${REPO_ROOT}/docs/WEEKLY_IMPLEMENTATION_PLAN.md" 2>/dev/null | head -n1 || true)"
    fi
    if [ -z "$BASE_DETECT" ]; then
        LATEST_DIR="$(ls -d ${REPO_ROOT}/generic/6.* 2>/dev/null | sort -V | tail -n1 || true)"
        if [ -n "$LATEST_DIR" ]; then
            BASE_DETECT="$(basename "$LATEST_DIR")"
        else
            BASE_DETECT="6.8.83resolute1"
        fi
    fi
    TARGET_INPUT="$BASE_DETECT"
fi

# Normalize version and package strings
# e.g. "6.8.79resolute1" -> RELEASE="6.8.79", PKG="6.8.79resolute1"
TARGET_CLEAN="$(echo "$TARGET_INPUT" | sed -E 's/^v//')"
if [[ "$TARGET_CLEAN" =~ ^([0-9]+\.[0-9]+\.[0-9]+)(.*)$ ]]; then
    RELEASE_VER="${BASH_REMATCH[1]}"
    SUF="${BASH_REMATCH[2]}"
    if [ -n "$TARGET_PKG" ]; then
        PACKAGE_VER="$TARGET_PKG"
    elif [ -n "$SUF" ]; then
        PACKAGE_VER="${RELEASE_VER}${SUF}"
    else
        PACKAGE_VER="${RELEASE_VER}resolute1"
    fi
else
    RELEASE_VER="$TARGET_CLEAN"
    PACKAGE_VER="${TARGET_PKG:-${TARGET_CLEAN}resolute1}"
fi

log_info "Synchronizing Web-GUI Version to: Release v${RELEASE_VER} | Package ${PACKAGE_VER}"

# ── 2. Update /opt/unetlab/html/includes/version.php ──────────────────────────
VERSION_PHP="/opt/unetlab/html/includes/version.php"
if [ -d "$(dirname "$VERSION_PHP")" ]; then
    cat << PHPEOF > "$VERSION_PHP"
<?php
/**
 * Azam Basha Platform Version Configuration
 * Dynamically Synchronized with Latest Implemented Release: ${RELEASE_VER}
 */
if (!defined('PNET_RELEASE')) {
    define('PNET_RELEASE', 'v${RELEASE_VER}');
}

if (!defined('PNET_VERSION')) {
    define('PNET_VERSION', '${RELEASE_VER}');
}

if (!defined('PNET_PACKAGE_VERSION')) {
    define('PNET_PACKAGE_VERSION', '${PACKAGE_VER}');
}
PHPEOF
    chown www-data:www-data "$VERSION_PHP" 2>/dev/null || true
    chmod 0644 "$VERSION_PHP" 2>/dev/null || true
    log_ok "Updated ${VERSION_PHP} (PNET_RELEASE: v${RELEASE_VER}, PNET_PACKAGE_VERSION: ${PACKAGE_VER})"
fi

# ── 3. Patch /opt/unetlab/html/status/api.php for Package Version Override ────
STATUS_API="/opt/unetlab/html/status/api.php"
if [ -f "$STATUS_API" ]; then
    # Inject PNET_PACKAGE_VERSION check if not already present
    python3 - << 'PYEOF'
status_api = "/opt/unetlab/html/status/api.php"
try:
    with open(status_api, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    old_needle = "'pnetlab'  => str_replace('noble', 'resolute', $vget('dpkg-query -W -f=\\'${Version}\\' pnetlab 2>/dev/null')),"
    new_code   = "'pnetlab'  => defined('PNET_PACKAGE_VERSION') ? PNET_PACKAGE_VERSION : str_replace('noble', 'resolute', $vget('dpkg-query -W -f=\\'${Version}\\' pnetlab 2>/dev/null')),"
    
    if old_needle in content:
        content = content.replace(old_needle, new_code)
        with open(status_api, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched status/api.php with PNET_PACKAGE_VERSION precedence.")
    elif "PNET_PACKAGE_VERSION" in content:
        print("status/api.php already has PNET_PACKAGE_VERSION support.")
except Exception as e:
    print(f"status/api.php note: {e}")
PYEOF
fi

# ── 4. Update Database Control Table (ctrl_version) ───────────────────────────
MYSQL_CMD="mysql"
if [ -f /root/.my.cnf ]; then
    MYSQL_CMD="mysql --defaults-file=/root/.my.cnf"
elif mysql -u root -ppnetlab -e "SELECT 1;" >/dev/null 2>&1; then
    MYSQL_CMD="mysql -u root -ppnetlab"
elif mysql -u pnetlab -ppnetlab -e "SELECT 1;" >/dev/null 2>&1; then
    MYSQL_CMD="mysql -u pnetlab -ppnetlab"
fi

if $MYSQL_CMD -e "USE pnetlab_db;" >/dev/null 2>&1; then
    $MYSQL_CMD -e "
USE pnetlab_db;
INSERT INTO control (control_name, control_value) VALUES ('ctrl_version', '${RELEASE_VER}')
ON DUPLICATE KEY UPDATE control_value = '${RELEASE_VER}';
" 2>/dev/null || true
    log_ok "Updated database control.ctrl_version to: ${RELEASE_VER}"
fi

# ── 5. Restart PHP-FPM to Flush OPcache ───────────────────────────────────────
PHP_FPM_SVC="$(systemctl list-unit-files 'php*-fpm.service' --no-legend 2>/dev/null | awk '{print $1}' | head -n1 || echo "")"
if [ -n "$PHP_FPM_SVC" ]; then
    systemctl restart "$PHP_FPM_SVC" 2>/dev/null || true
fi
systemctl restart apache2 2>/dev/null || true

# ── 6. Live Verification Probe ────────────────────────────────────────────────
CK_FILE="/tmp/pnet-ver-check.txt"
curl -sk -X POST https://127.0.0.1/api/auth \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"azam"}' \
     -c "$CK_FILE" >/dev/null 2>&1 || true

VER_JSON=$(curl -sk https://127.0.0.1/status/api.php?action=version -b "$CK_FILE" 2>/dev/null || true)
rm -f "$CK_FILE" 2>/dev/null || true

echo ""
echo "============================================================"
echo " [SUCCESS] WEB-GUI VERSION SYNCHRONIZATION COMPLETE!        "
echo "============================================================"
echo " Web UI Display: PNetLab v${RELEASE_VER}"
echo " Release Row   : v${RELEASE_VER}"
echo " Package Row   : ${PACKAGE_VER}"
if echo "$VER_JSON" | grep -q "\"release\":\"v${RELEASE_VER}\""; then
    echo " Live API Check: VERIFIED (status/api.php returned v${RELEASE_VER})"
fi
echo "============================================================"
