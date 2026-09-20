#!/usr/bin/env bash
# ==============================================================================
# Azam Basha — Home Screen Logo Universal Deployer
#
# Propagates the home screen avatar image (azam_home_avatar.png) to every
# logo, favicon, and Plymouth boot-splash path across the platform so that
# the brand identity is consistent on every page, widget, and system screen.
#
# Paths covered:
#   • /opt/unetlab/data/branding/logo.png           (Branding API)
#   • /opt/unetlab/html/images/logo.png             (Stock HTML asset)
#   • /opt/unetlab/html/themes/default/images/logo.png  (Lab canvas theme)
#   • /opt/unetlab/html/assets-common/img/logo.png  (Shared JS/CSS asset)
#   • /opt/unetlab/html/assets-common/img/favicon.{png,ico}
#   • /opt/unetlab/html/images/favicon.png
#   • /opt/unetlab/html/themes/default/images/favicon.ico
#   • /opt/unetlab/html/favicon.ico
#   • /usr/share/plymouth/themes/pnetlab/logo*.png  (Boot splash)
# ==============================================================================
set -Eeuo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] This script must be run as root. Please run: sudo bash $0" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "/opt/unetlab/scripts")"
PARENT_DIR="$(cd "${SCRIPT_DIR}/.." 2>/dev/null && pwd || echo "/opt/azambasha")"

echo "============================================================"
echo "   Azam Basha — Home Screen Logo Universal Deployer        "
echo "============================================================"

# --- Resolve the avatar source ---
# Primary: already deployed on the live VM by the login page installer
AVATAR_VM="/opt/unetlab/html/login/img/azam_home_avatar.png"
# Fallback: source from the repository bundle on this machine
AVATAR_REPO="${PARENT_DIR}/login/img/azam_home_avatar.png"

if [ -f "$AVATAR_VM" ]; then
    AVATAR_SRC="$AVATAR_VM"
    echo "  [*] Source: $AVATAR_VM (live VM copy)"
elif [ -f "$AVATAR_REPO" ]; then
    AVATAR_SRC="$AVATAR_REPO"
    echo "  [*] Source: $AVATAR_REPO (repo bundle)"
else
    echo "  [ERROR] Cannot find azam_home_avatar.png in either:" >&2
    echo "          $AVATAR_VM" >&2
    echo "          $AVATAR_REPO" >&2
    exit 1
fi

# --- Create target directories ---
mkdir -p \
    /opt/unetlab/data/branding \
    /opt/unetlab/html/images \
    /opt/unetlab/html/themes/default/images \
    /opt/unetlab/html/assets-common/img \
    /opt/unetlab/html/favicon \
    /opt/unetlab/html/login/img \
    2>/dev/null || true

# --- Deploy avatar to all logo paths ---
PASS=0
FAIL=0
deploy() {
    local dest="$1"
    if cp -f "$AVATAR_SRC" "$dest" 2>/dev/null; then
        chmod 0644 "$dest" 2>/dev/null || true
        echo "  [✔] $dest"
        PASS=$((PASS + 1))
    else
        echo "  [-] Skipped (path not writable): $dest"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "  [1/3] Core logo paths (sidebar, topbar, branding API)..."
deploy /opt/unetlab/data/branding/logo.png
deploy /opt/unetlab/html/images/logo.png
deploy /opt/unetlab/html/themes/default/images/logo.png
deploy /opt/unetlab/html/assets-common/img/logo.png

echo ""
echo "  [2/3] Favicon paths (browser tab icon)..."
deploy /opt/unetlab/html/assets-common/img/favicon.png
deploy /opt/unetlab/html/assets-common/img/favicon.ico
deploy /opt/unetlab/html/images/favicon.png
deploy /opt/unetlab/html/themes/default/images/favicon.ico
deploy /opt/unetlab/html/favicon.ico

echo ""
echo "  [3/3] Plymouth boot splash logo..."
PLYMOUTH_HIT=0
for p in /usr/share/plymouth/themes/pnetlab/logo*.png; do
    if [ -f "$p" ]; then
        deploy "$p"
        PLYMOUTH_HIT=1
    fi
done
[ "$PLYMOUTH_HIT" -eq 0 ] && echo "  [-] No Plymouth logo files found (non-critical)"

# --- Ensure avatar is also present in login/img (idempotent safety copy) ---
if [ "$AVATAR_SRC" != "$AVATAR_VM" ] && [ -f "$AVATAR_REPO" ]; then
    cp -f "$AVATAR_REPO" "$AVATAR_VM" 2>/dev/null || true
    chmod 0644 "$AVATAR_VM" 2>/dev/null || true
fi

# --- Fix ownership ---
chown -R www-data:www-data \
    /opt/unetlab/data/branding \
    /opt/unetlab/html/assets-common/img \
    /opt/unetlab/html/images \
    /opt/unetlab/html/themes/default/images \
    /opt/unetlab/html/login/img \
    2>/dev/null || true

# --- Update branding config timestamp to bust PHP/browser cache ---
CONFIG_JSON="/opt/unetlab/data/branding/config.json"
if [ -f "$CONFIG_JSON" ]; then
    NOW_TS="$(date +%s)"
    # Update or insert the updated_at field
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<PYEOF
import json, sys
try:
    with open('$CONFIG_JSON', 'r') as fh:
        cfg = json.load(fh)
    cfg['updated_at'] = $NOW_TS
    cfg['logo_source'] = 'azam_home_avatar.png'
    with open('$CONFIG_JSON', 'w') as fh:
        json.dump(cfg, fh, indent=2)
    print("  [✔] Branding config.json cache-busted (updated_at=$NOW_TS)")
except Exception as e:
    print(f"  [-] Could not update config.json: {e}")
PYEOF
    else
        sed -i "s/\"updated_at\": [0-9]*/\"updated_at\": $NOW_TS/" "$CONFIG_JSON" 2>/dev/null || true
        echo "  [✔] Branding config.json timestamp updated"
    fi
fi

# --- MD5 integrity verification ---
echo ""
echo "  [Verify] Checking MD5 fingerprint consistency..."
AVATAR_MD5="$(md5sum "$AVATAR_SRC" 2>/dev/null | awk '{print $1}')"
MISMATCH=0
for f in \
    /opt/unetlab/data/branding/logo.png \
    /opt/unetlab/html/images/logo.png \
    /opt/unetlab/html/themes/default/images/logo.png \
    /opt/unetlab/html/assets-common/img/logo.png; do
    if [ -f "$f" ]; then
        F_MD5="$(md5sum "$f" 2>/dev/null | awk '{print $1}')"
        if [ "$F_MD5" = "$AVATAR_MD5" ]; then
            echo "  [✔] Match: $f"
        else
            echo "  [✘] MISMATCH: $f"
            MISMATCH=$((MISMATCH + 1))
        fi
    fi
done

# --- Reload web server to flush PHP opcode cache ---
echo ""
echo "  [Cache] Reloading web server..."
if command -v systemctl >/dev/null 2>&1; then
    systemctl reload apache2 2>/dev/null && echo "  [✔] apache2 reloaded" || echo "  [-] apache2 reload skipped"
    systemctl reload php8.3-fpm 2>/dev/null || \
        systemctl reload php8.2-fpm 2>/dev/null || \
        systemctl reload php8.1-fpm 2>/dev/null || \
        systemctl reload php*-fpm 2>/dev/null || \
        echo "  [-] php-fpm reload skipped (not critical)"
fi

echo ""
echo "============================================================"
if [ "$MISMATCH" -eq 0 ] && [ "$FAIL" -eq 0 ]; then
    echo "  [SUCCESS] Home screen avatar is now the universal logo!"
    echo "            Deployed: $PASS paths | Mismatches: 0"
elif [ "$MISMATCH" -gt 0 ]; then
    echo "  [WARNING] $MISMATCH path(s) have MD5 mismatches — check permissions."
else
    echo "  [PARTIAL] $PASS deployed, $FAIL skipped (non-writable paths)."
fi
echo "============================================================"
