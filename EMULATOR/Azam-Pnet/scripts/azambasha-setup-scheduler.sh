#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Automated Weekly Scanner & WhatsApp Alert Scheduler
# ==============================================================================
# Installs a systemd timer and cron job to automatically run the Codeberg 
# Intelligence Scanner every Monday at 06:00 UTC and dispatch WhatsApp alerts.
# ==============================================================================
set -euo pipefail

PHONE="${1:-}"
APIKEY="${2:-}"
WEBHOOK="${3:-}"

echo "================================================================================"
echo "    Azam-Pnet Automated Weekly Intelligence & Alert Scheduler Setup"
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
Description=Azam-Pnet Weekly Codeberg Upstream Intelligence Scanner
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/azambasha
ExecStart=/usr/bin/python3 /opt/azambasha/scripts/azambasha-weekly-codeberg-scanner.py --output /opt/azambasha/docs/WEEKLY_IMPLEMENTATION_PLAN.md --notify
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 2. Create Systemd Timer (Every Monday at 06:00 UTC)
TIMER_FILE="/etc/systemd/system/azambasha-scanner.timer"
echo "[*] Installing systemd timer: $TIMER_FILE..."
cat > "$TIMER_FILE" << 'EOF'
[Unit]
Description=Run Azam-Pnet Weekly Upstream Intelligence Scan every Monday at 06:00 UTC

[Timer]
OnCalendar=Mon *-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 3. Create Cron Fallback in /etc/cron.weekly/
CRON_FILE="/etc/cron.weekly/azambasha-scanner"
echo "[*] Installing cron fallback: $CRON_FILE..."
cat > "$CRON_FILE" << 'EOF'
#!/usr/bin/env bash
if [ -d "/opt/azambasha" ]; then
    cd /opt/azambasha
    python3 scripts/azambasha-weekly-codeberg-scanner.py --output docs/WEEKLY_IMPLEMENTATION_PLAN.md --notify >/dev/null 2>&1 || true
fi
EOF
chmod +x "$CRON_FILE"

# 4. Enable and start timer
systemctl daemon-reload
systemctl enable --now azambasha-scanner.timer

echo "================================================================================"
echo "[✔] Automated Weekly Scanner Scheduler successfully installed & activated!"
echo "    - Timer Schedule: Every Monday at 06:00 UTC (systemctl list-timers)"
echo "    - Manual Trigger: sudo systemctl start azambasha-scanner.service"
echo "    - Configuration:  $NOTIFY_CONF"
echo "================================================================================"
