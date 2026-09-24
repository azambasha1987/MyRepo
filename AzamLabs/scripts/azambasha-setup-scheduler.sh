#!/usr/bin/env bash
# ==============================================================================
# AzamLabs Automated 3-Months Intelligence & Alert Scheduler Setup
# ==============================================================================
# Configures notification credentials (/etc/pnetlab/azambasha-notify.conf)
# targeting azambasha1987@gmail.com and installs the turnkey azam-audit tool.
# ==============================================================================
set -euo pipefail

# Resolve physical script location across symlinks
REAL_PATH="$(realpath "${BASH_SOURCE[0]}" 2>/dev/null || readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$REAL_PATH")" 2>/dev/null && pwd || echo "")"
if [ ! -f "${SCRIPT_DIR}/azambasha-quarterly-audit.sh" ]; then
    if [ -f "/opt/azambasha/scripts/azambasha-quarterly-audit.sh" ]; then
        SCRIPT_DIR="/opt/azambasha/scripts"
    elif [ -f "/opt/unetlab/scripts/azambasha-quarterly-audit.sh" ]; then
        SCRIPT_DIR="/opt/unetlab/scripts"
    fi
fi

EMAIL="${1:-azambasha1987@gmail.com}"
PHONE="${2:-}"
APIKEY="${3:-}"
WEBHOOK="${4:-}"

echo "================================================================================"
echo "    AzamLabs Automated 3-Months Intelligence & Alert Setup                      "
echo "    Target Recipient: ${EMAIL}                                                  "
echo "================================================================================"

# Check root
if [ "$(id -u)" -ne 0 ]; then
    echo "[!] Error: This setup script must be run as root (sudo bash $0)."
    exit 1
fi

NOTIFY_CONF="/etc/pnetlab/azambasha-notify.conf"
mkdir -p /etc/pnetlab

# Store notification configuration
echo "[*] Storing notification configuration in $NOTIFY_CONF..."
cat > "$NOTIFY_CONF" << EOF
# AzamLabs Cluster Notification Configuration
EMAIL_TO="${EMAIL}"
EMAIL_USER=""
EMAIL_PASS=""
SMTP_SERVER=""
SMTP_PORT=""
WHATSAPP_PHONE="${PHONE}"
WHATSAPP_APIKEY="${APIKEY}"
WEBHOOK_URL="${WEBHOOK}"
EOF
chmod 0600 "$NOTIFY_CONF"
echo "[✔] Configuration saved."

# 1. Cleanup / Decommission Retired Scanner Service and Timer
echo "[*] Decommissioning legacy Upstream Scanner systemd units and cron jobs..."
systemctl stop azambasha-scanner.timer 2>/dev/null || true
systemctl disable azambasha-scanner.timer 2>/dev/null || true
systemctl stop azambasha-scanner.service 2>/dev/null || true
rm -f /etc/systemd/system/azambasha-scanner.service /etc/systemd/system/azambasha-scanner.timer
rm -f /etc/cron.d/azambasha-quarterly-scanner /etc/cron.weekly/azambasha-scanner

systemctl daemon-reload 2>/dev/null || true

# 2. Symlink azam-audit & azam-update commands
if [ -f "${SCRIPT_DIR}/azambasha-quarterly-audit.sh" ]; then
    ln -sf "${SCRIPT_DIR}/azambasha-quarterly-audit.sh" /usr/local/bin/azam-audit
    chmod +x "${SCRIPT_DIR}/azambasha-quarterly-audit.sh"
    echo "[✔] Installed /usr/local/bin/azam-audit"
fi
if [ -f "${SCRIPT_DIR}/azambasha-update.sh" ]; then
    ln -sf "${SCRIPT_DIR}/azambasha-update.sh" /usr/local/bin/azam-update
    chmod +x "${SCRIPT_DIR}/azambasha-update.sh"
    echo "[✔] Installed /usr/local/bin/azam-update"
fi

echo "================================================================================"
echo "[✔] Setup complete. Turnkey quarterly audit is ready:"
echo "    Run: sudo azam-audit --check"
echo "    Configuration: $NOTIFY_CONF"
echo "================================================================================"
