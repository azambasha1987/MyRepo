#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Automated 3-Months Intelligence Scanner & Alert Scheduler
# ==============================================================================
# Installs a systemd timer and cron job to automatically run the Codeberg 
# Intelligence Scanner every 3 months on the 19th at 09:00 IST (03:30 UTC)
# and dispatch WhatsApp / Webhook alerts.
# ==============================================================================
set -euo pipefail

PHONE="${1:-}"
APIKEY="${2:-}"
WEBHOOK="${3:-}"

echo "================================================================================"
echo "    Azam-Pnet Automated 3-Months Intelligence & Alert Scheduler Setup"
echo "================================================================================"

# Check root
if [ "$(id -u)" -ne 0 ]; then
    echo "[!] Error: This setup script must be run as root (sudo bash $0)."
    exit 1
fi

NOTIFY_CONF="/etc/pnetlab/azambasha-notify.conf"
mkdir -p /etc/pnetlab

# If credentials provided, write them to /etc/pnetlab/azambasha-notify.conf
if [ -n "$PHONE" ] || [ -n "$APIKEY" ] || [ -n "$WEBHOOK" ]; then
    echo "[*] Storing notification credentials in $NOTIFY_CONF..."
    cat > "$NOTIFY_CONF" << EOF
# Azam-Pnet Cluster Notification Configuration
WHATSAPP_PHONE="${PHONE}"
WHATSAPP_APIKEY="${APIKEY}"
WEBHOOK_URL="${WEBHOOK}"
EOF
    chmod 0600 "$NOTIFY_CONF"
    echo "[✔] Credentials saved."
fi

# 1. Cleanup / Decommission Scanner Service and Timer
echo "[*] Decommissioning Upstream Scanner systemd units and cron jobs..."
systemctl stop azambasha-scanner.timer 2>/dev/null || true
systemctl disable azambasha-scanner.timer 2>/dev/null || true
systemctl stop azambasha-scanner.service 2>/dev/null || true
rm -f /etc/systemd/system/azambasha-scanner.service /etc/systemd/system/azambasha-scanner.timer
rm -f /etc/cron.d/azambasha-quarterly-scanner /etc/cron.weekly/azambasha-scanner

systemctl daemon-reload

echo "================================================================================"
echo "[✔] Scanner systemd services and timers have been completely removed."
echo "    - Configuration preserved: $NOTIFY_CONF"
echo "================================================================================"

