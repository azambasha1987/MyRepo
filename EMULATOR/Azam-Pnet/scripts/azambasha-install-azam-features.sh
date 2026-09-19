#!/bin/bash
# ==============================================================================
# azambasha-install-azam-features.sh
# Deploys the Azam-Features GUI tab into:
#   1. PNetLab Main Dashboard (/main/) as a primary navigation tab
#   2. PNetLab Lab Canvas (/themes/default/) as a quick-access sidebar entry
# Run once on Master (192.168.1.23) as root.
# ==============================================================================
set -euo pipefail

GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
CYAN='\033[1;36m'
RESET='\033[0m'
BOLD='\033[1m'

PNET_HTML="/opt/unetlab/html"
MAIN_HTML="${PNET_HTML}/main"
MAIN_INDEX="${MAIN_HTML}/index.html"
MAIN_JS="${MAIN_HTML}/js"
THEME_JS="${PNET_HTML}/themes/default/js"
THEME_INDEX="${PNET_HTML}/themes/default/index.html"
# Resolve dynamic paths for install environment (git clone, /opt/unetlab, or /opt/azambasha)
INSTALL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd || echo "")"
if [ -d "/opt/unetlab/scripts" ] && [ -f "/opt/unetlab/scripts/azambasha-ops-api.py" ]; then
    SCRIPTS="/opt/unetlab/scripts"
elif [ -n "$INSTALL_ROOT" ] && [ -d "${INSTALL_ROOT}/scripts" ]; then
    SCRIPTS="${INSTALL_ROOT}/scripts"
else
    SCRIPTS="/opt/azambasha/scripts"
fi

if [ -n "$INSTALL_ROOT" ] && [ -d "${INSTALL_ROOT}/html" ]; then
    AZAM_DIR="$INSTALL_ROOT"
elif [ -d "/opt/azambasha/html" ]; then
    AZAM_DIR="/opt/azambasha"
elif [ -d "/opt/azam-pnet/EMULATOR/Azam-Pnet/html" ]; then
    AZAM_DIR="/opt/azam-pnet/EMULATOR/Azam-Pnet"
else
    AZAM_DIR="/opt/unetlab"
fi

# Ensure /opt/azambasha compatibility directory and symlinks
mkdir -p /opt/azambasha 2>/dev/null || true
if [ ! -e "/opt/azambasha/scripts" ]; then
    ln -sfn "$SCRIPTS" /opt/azambasha/scripts 2>/dev/null || true
fi
if [ ! -e "/opt/azambasha/html" ] && [ -d "${AZAM_DIR}/html" ]; then
    ln -sfn "${AZAM_DIR}/html" /opt/azambasha/html 2>/dev/null || true
fi

IS_SATELLITE=0
for arg in "$@"; do
    case "$arg" in
        --satellite|-s)
            IS_SATELLITE=1
            ;;
    esac
done

API_PORT=8889

echo -e "${CYAN}================================================================${RESET}"
if [ "$IS_SATELLITE" -eq 1 ]; then
    echo -e "  ${BOLD}Azam-Features Satellite Compute Worker Provisioning${RESET}"
else
    echo -e "  ${BOLD}Azam-Features Master GUI & Operations Center Installation${RESET}"
fi
echo -e "${CYAN}================================================================${RESET}"

# ── 1. Register Global Administrative CLI Commands ──────────────────────────
echo -e "\n${CYAN}[1/7]${RESET} Registering global CLI toolchains in /usr/local/bin/…"
chmod +x "${SCRIPTS}"/azambasha-*.py 2>/dev/null || true
chmod +x "${SCRIPTS}"/azambasha-*.sh 2>/dev/null || true

# Symlinks for CLI tools (Available identically on Master and Satellite)
ln -sf "${SCRIPTS}/azambasha-ai-copilot.py"       /usr/local/bin/azam-ai
ln -sf "${SCRIPTS}/azambasha-config-diff.py"      /usr/local/bin/azam-config-diff
ln -sf "${SCRIPTS}/azambasha-ping-mesh.py"        /usr/local/bin/azam-ping-mesh
ln -sf "${SCRIPTS}/azambasha-scheduler.py"        /usr/local/bin/azam-scheduler
ln -sf "${SCRIPTS}/azambasha-cloud-backup.py"     /usr/local/bin/azam-cloud-backup
ln -sf "${SCRIPTS}/azambasha-lab-grader.py"       /usr/local/bin/azam-grader
ln -sf "${SCRIPTS}/azambasha-sniffer.py"          /usr/local/bin/azam-sniffer
ln -sf "${SCRIPTS}/azambasha-cloud-bridge.py"     /usr/local/bin/azam-cloud-bridge
ln -sf "${SCRIPTS}/azambasha-image-shrink.py"     /usr/local/bin/azam-image-shrink
ln -sf "${SCRIPTS}/azambasha-topology-doc.py"     /usr/local/bin/azam-topology-doc
ln -sf "${SCRIPTS}/azambasha-bootstorm.py"        /usr/local/bin/azam-bootstorm
ln -sf "${SCRIPTS}/azambasha-templates.sh"        /usr/local/bin/azam-templates
ln -sf "${SCRIPTS}/azambasha-perf.py"             /usr/local/bin/azam-perf
ln -sf "${SCRIPTS}/azambasha-console-fix.sh"      /usr/local/bin/azam-console-fix
ln -sf "${SCRIPTS}/azambasha-lab-backup.sh"       /usr/local/bin/azam-backup
ln -sf "${SCRIPTS}/azambasha-lab-backup.sh"       /usr/local/bin/azam-restore
ln -sf "${SCRIPTS}/azambasha-topology-git.py"     /usr/local/bin/azam-topology-git
ln -sf "${SCRIPTS}/azambasha-watchdog.py"         /usr/local/bin/azam-watchdog
ln -sf "${SCRIPTS}/azambasha-fleet-status.sh"     /usr/local/bin/azam-fleet
ln -sf "${SCRIPTS}/azambasha-cluster-capacity.py" /usr/local/bin/azam-capacity
ln -sf "${SCRIPTS}/azambasha-image-doctor.sh"     /usr/local/bin/azam-doctor
ln -sf "${SCRIPTS}/azambasha-notify.py"           /usr/local/bin/azam-notify
ln -sf "${SCRIPTS}/azambasha-bench.sh"            /usr/local/bin/azam-bench
ln -sf "${SCRIPTS}/azambasha-ssl.sh"              /usr/local/bin/azam-ssl
ln -sf "${SCRIPTS}/azambasha-fix-web-credentials.sh" /usr/local/bin/azam-credentials
ln -sf "${SCRIPTS}/azambasha-airgap-pack.sh"      /usr/local/bin/azam-airgap-pack
ln -sf "${SCRIPTS}/azambasha-link-impairment.sh"   /usr/local/bin/azam-link-impair
ln -sf "${SCRIPTS}/azambasha-roce-engine.sh"       /usr/local/bin/azam-roce
ln -sf "${SCRIPTS}/azambasha-cgroups-v2-engine.sh" /usr/local/bin/azam-cgroups
ln -sf "${SCRIPTS}/azambasha-cpu-governor.py"      /usr/local/bin/azam-cpu-governor
ln -sf "${SCRIPTS}/azambasha-eve-lab-importer.py"   /usr/local/bin/azam-lab-importer
chmod +x "${SCRIPTS}/azambasha-eve-lab-importer.py" 2>/dev/null || true

# Install scheduler timer and 24/7 autonomous watchdog daemon
python3 "${SCRIPTS}/azambasha-scheduler.py" --install 2>/dev/null || true
python3 "${SCRIPTS}/azambasha-watchdog.py" --install 2>/dev/null || true

# Deploy Nightly SSD TRIM & Maintenance Cron (Master & Satellite)
cat << 'TRIMEOF' > /etc/cron.d/azambasha-maintenance
# Azam-Pnet Scheduled Maintenance & Storage TRIM
0 3 * * * root /sbin/fstrim -av > /var/log/azambasha-trim.log 2>&1
TRIMEOF
chmod 0644 /etc/cron.d/azambasha-maintenance 2>/dev/null || true

# If Satellite Node: finish here (no web UI or apache needed on headless workers)
if [ "$IS_SATELLITE" -eq 1 ]; then
    echo -e "  ${GREEN}[✔]${RESET} All 26 CLI tools, watchdog daemon, and maintenance cron installed on Satellite!"
    echo -e "${CYAN}================================================================${RESET}"
    exit 0
fi

# ── 1b. Copy Backend API and Install Service (Master Mode) ───────────────────
python3 "${SCRIPTS}/azambasha-ops-api.py" --install
systemctl restart azam-ops-api.service 2>/dev/null || true
echo -e "  ${GREEN}[✔]${RESET} azam-ops-api.service installed and running on port ${API_PORT}."

# ── 1c. Deploy In-Browser PDF Operations Manual ──────────────────────────────
mkdir -p "${PNET_HTML}/docs" 2>/dev/null || true
PDF_SRC="${AZAM_DIR}/docs/Azam-Pnet_Enterprise_Features_Operations_Manual.pdf"
if [ -f "${PDF_SRC}" ]; then
    cp -f "${PDF_SRC}" "${PNET_HTML}/docs/manual.pdf"
    cp -f "${PDF_SRC}" "${PNET_HTML}/docs/Azam-Pnet_Enterprise_Features_Operations_Manual.pdf"
    chmod 0644 "${PNET_HTML}/docs/manual.pdf" "${PNET_HTML}/docs/Azam-Pnet_Enterprise_Features_Operations_Manual.pdf" 2>/dev/null || true
    echo -e "  ${GREEN}[✔]${RESET} Published Operations Manual PDF to ${PNET_HTML}/docs/manual.pdf"
fi

# ── 2. Configure Apache proxy for /azam-ops/api/ ────────────────────────────
echo -e "${CYAN}[2/7]${RESET} Configuring Apache reverse proxy for Azam-Ops API…"
APACHE_CONF="/etc/apache2/conf-available/azam-ops-api.conf"
cat > "${APACHE_CONF}" << 'APACHEEOF'
# Azam-Pnet Operations Dashboard API proxy
# Backend: python3 azambasha-ops-api.py running on 127.0.0.1:8889

<Location /azam-ops/api>
    ProxyPass http://127.0.0.1:8889/azam-ops/api
    ProxyPassReverse http://127.0.0.1:8889/azam-ops/api
    Require all granted
</Location>

<IfModule mod_headers.c>
    <FilesMatch "azam-features.*\.js$">
        Header set Cache-Control "no-cache, no-store, must-revalidate, max-age=0"
        Header set Pragma "no-cache"
        Header set Expires 0
    </FilesMatch>
</IfModule>
APACHEEOF

a2enmod proxy proxy_http headers 2>/dev/null || true
a2enconf azam-ops-api 2>/dev/null || true
echo -e "  ${GREEN}[✔]${RESET} Apache proxy config installed and enabled."

# ── 3. Install Main Dashboard JS Module ─────────────────────────────────────
echo -e "${CYAN}[3/7]${RESET} Installing Azam-Features into Main GUI (/main/js/)…"
MAIN_SRC="${AZAM_DIR}/html/main/azam-features.js"
if [ -f "${MAIN_SRC}" ]; then
    cp "${MAIN_SRC}" "${MAIN_JS}/azam-features.js"
    echo -e "  ${GREEN}[✔]${RESET} Copied azam-features.js → ${MAIN_JS}/"
else
    echo -e "  ${RED}[✘]${RESET} Main JS file not found at ${MAIN_SRC}"
    exit 1
fi

# ── 4. Inject Nav Item and Script into Main GUI index.html ──────────────────
echo -e "${CYAN}[4/7]${RESET} Injecting Azam-Features tab into Main GUI navigation…"
CACHE_BUST="?v=$(date +%s)"
if grep -q "azam-features" "${MAIN_INDEX}"; then
    echo -e "  ${YELLOW}[!]${RESET} Main GUI already contains Azam-Features references. Updating cache buster..."
    sed -i "s|/main/js/azam-features.js[^\"]*|/main/js/azam-features.js${CACHE_BUST}|g" "${MAIN_INDEX}"
else
    cp "${MAIN_INDEX}" "${MAIN_INDEX}.bak"
    # Inject sidebar nav item right after the 'ai' nav item
    sed -i '/data-route="ai"/a \			<a class="nav-item" data-route="azam-features" href="#/azam-features">\n				<i class="fa fa-bolt" aria-hidden="true" style="color:#0ea5e9;"></i><span>Azam-Features</span></a>' "${MAIN_INDEX}"
    # Inject script tag before </body>
    sed -i "s|</body>|<script src=\"/main/js/azam-features.js${CACHE_BUST}\"></script>\n</body>|" "${MAIN_INDEX}"
    echo -e "  ${GREEN}[✔]${RESET} Successfully injected Azam-Features into Main GUI navigation."
fi

# ── 5. Install Lab Canvas Sidebar Script ────────────────────────────────────
echo -e "${CYAN}[5/7]${RESET} Installing Lab Canvas sidebar integration…"
CANVAS_SRC="${AZAM_DIR}/html/azam-ops/pnetlab-azam-features.js"
if [ -f "${CANVAS_SRC}" ]; then
    cp "${CANVAS_SRC}" "${THEME_JS}/pnetlab-azam-features.js"
    echo -e "  ${GREEN}[✔]${RESET} Copied pnetlab-azam-features.js → ${THEME_JS}/"
fi

if grep -q "pnetlab-azam-features.js" "${THEME_INDEX}"; then
    echo -e "  ${YELLOW}[!]${RESET} Lab Canvas script tag already present."
else
    cp "${THEME_INDEX}" "${THEME_INDEX}.bak"
    sed -i 's|</body>|<script src="/themes/default/js/pnetlab-azam-features.js" defer></script>\n</body>|' "${THEME_INDEX}"
    echo -e "  ${GREEN}[✔]${RESET} Successfully injected script into Lab Canvas."
fi

# ── 5b. Install Standalone Azam-Ops Dashboard ────────────────────────────────
mkdir -p "${PNET_HTML}/azam-ops"
OPS_SRC="${AZAM_DIR}/html/azam-ops/index.html"
if [ -f "${OPS_SRC}" ]; then
    cp "${OPS_SRC}" "${PNET_HTML}/azam-ops/index.html"
    echo -e "  ${GREEN}[✔]${RESET} Copied index.html → ${PNET_HTML}/azam-ops/"
fi

# ── 6. Reload Apache ────────────────────────────────────────────────────────
echo -e "${CYAN}[6/7]${RESET} Reloading Apache web server…"
apache2ctl configtest 2>&1 | grep -v "^Syntax OK" || true
systemctl reload apache2
echo -e "  ${GREEN}[✔]${RESET} Apache reloaded."

# ── 7. Verify API & GUI Endpoints ───────────────────────────────────────────
echo -e "${CYAN}[7/7]${RESET} Verifying live API connectivity…"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/azam-ops/api/stats || echo "000")
if [ "${HTTP_CODE}" = "200" ]; then
    echo -e "  ${GREEN}[✔]${RESET} Apache reverse proxy /azam-ops/api/stats returned HTTP 200 OK!"
else
    echo -e "  ${RED}[✘]${RESET} Health check failed with HTTP ${HTTP_CODE}."
fi

echo ""
echo -e "${CYAN}================================================================${RESET}"
echo -e "  ${GREEN}${BOLD}Azam-Features Tab Successfully Deployed!${RESET}"
echo -e "${CYAN}================================================================${RESET}"
echo -e "  ${BOLD}Where to find it:${RESET}"
echo -e "   1. ${CYAN}Main PNetLab GUI:${RESET} Navigate to ${BOLD}https://192.168.1.23/main/#/azam-features${RESET}"
echo -e "      (Click the new ${YELLOW}⚡ Azam-Features${RESET} tab in the main sidebar)"
echo -e "   2. ${CYAN}Lab Canvas GUI:${RESET} Inside any active lab, click ${YELLOW}⚡ Azam-Features${RESET} in the left toolbar."
echo -e "${CYAN}================================================================${RESET}"
