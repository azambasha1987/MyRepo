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

# 1. Create Systemd Service
SERVICE_FILE="/etc/systemd/system/azambasha-scanner.service"
echo "[*] Installing systemd service: $SERVICE_FILE..."
cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=Azam-Pnet 3 Months Upstream Intelligence Scanner
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/azambasha
ExecStart=/usr/bin/python3 /opt/azambasha/scripts/azambasha-weekly-codeberg-scanner.py --output /opt/azambasha/docs/3_MONTHS_UPDATE_CHECK_PLAN.md --notify
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 2. Create Systemd Timer (Every 3 Months on the 19th at 09:00 IST = 03:30 UTC)
TIMER_FILE="/etc/systemd/system/azambasha-scanner.timer"
echo "[*] Installing systemd timer: $TIMER_FILE..."
cat > "$TIMER_FILE" << 'EOF'
[Unit]
Description=Run Azam-Pnet Upstream Intelligence Scan Every 3 Months on the 19th at 09:00 IST (03:30 UTC)

[Timer]
OnCalendar=*-03,06,09,12-19 03:30:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 3. Create Cron Fallback in /etc/cron.d/
CRON_FILE="/etc/cron.d/azambasha-quarterly-scanner"
echo "[*] Installing cron fallback: $CRON_FILE..."
cat > "$CRON_FILE" << 'EOF'
# Run on the 19th of March, June, September, and December at 03:30 UTC (09:00 AM IST)
30 3 19 3,6,9,12 * root if [ -d "/opt/azambasha" ]; then cd /opt/azambasha && python3 scripts/azambasha-weekly-codeberg-scanner.py --output docs/3_MONTHS_UPDATE_CHECK_PLAN.md --notify >/dev/null 2>&1; fi
EOF
chmod 0644 "$CRON_FILE"

# Clean up legacy weekly cron if present
rm -f /etc/cron.weekly/azambasha-scanner 2>/dev/null || true

# 4. Enable and start timer
systemctl daemon-reload
systemctl enable --now azambasha-scanner.timer

echo "================================================================================"
echo "[✔] Automated 3-Months Scanner Scheduler successfully installed & activated!"
echo "    - Timer Schedule: Every 3 Months on the 19th at 09:00 IST (03:30 UTC)"
echo "    - Next Runs:      19 Dec 2026, 19 Mar 2027, 19 Jun 2027, 19 Sep 2027"
echo "    - Manual Trigger: sudo systemctl start azambasha-scanner.service"
echo "    - Configuration:  $NOTIFY_CONF"
echo "================================================================================"
