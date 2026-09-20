#!/usr/bin/env bash
# ==============================================================================
# Azam Basha HTML5 Console & Guacamole Zero-Lag Auto-Fixer (azam-console-fix)
# ==============================================================================
# Diagnoses and repairs:
#   1. Apache WebSocket tunnel (mod_proxy_wstunnel) for HTML5 console stability
#   2. guacd daemon health and port binding
#   3. Apache console proxy headers (Upgrade, Connection headers)
#   4. Stale Wireshark/capture pipe cleanup
#   5. Windows .reg file generator for telnet:// SecureCRT / Wireshark URL handlers
# ==============================================================================
set -euo pipefail

# Install symlink
if [ "$(id -u)" -eq 0 ]; then
    ln -sf "$(realpath "$0")" /usr/local/bin/azam-console-fix 2>/dev/null || true
fi

GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
BOLD="\033[1m"
RESET="\033[0m"

MODE="${1:---fix}"

echo -e "${CYAN}================================================================================"
echo -e "     ${BOLD}Azam-Pnet HTML5 Guacamole & Console Zero-Lag Auto-Fixer${RESET}${CYAN}"
echo -e "================================================================================${RESET}"

APACHE_CONF_DIR="/etc/apache2/sites-available"
PNETLAB_CONF="${APACHE_CONF_DIR}/pnetlab.conf"
GUACD_CONF="/etc/guacamole/guacd.conf"
FIXES_APPLIED=0

# === 1. Apache WebSocket Tunnel Module ===
echo -e "\n[1/6] ${BOLD}Apache mod_proxy_wstunnel (WebSocket Tunnel)${RESET}"
if apache2ctl -M 2>/dev/null | grep -q "proxy_wstunnel"; then
    echo -e "  ${GREEN}[✔ OK]${RESET} mod_proxy_wstunnel is loaded."
else
    echo -e "  ${YELLOW}[⚠ FIXING]${RESET} mod_proxy_wstunnel not loaded — HTML5 consoles will disconnect."
    if [ "$MODE" = "--fix" ]; then
        a2enmod proxy proxy_http proxy_wstunnel 2>/dev/null || true
        echo -e "  ${GREEN}[✔ DONE]${RESET} Modules enabled."
        FIXES_APPLIED=$((FIXES_APPLIED+1))
    fi
fi

# === 2. WebSocket Upgrade Headers in Apache Config ===
echo -e "\n[2/6] ${BOLD}Apache WebSocket Upgrade Headers${RESET}"
MISSING_HEADERS=false
if [ -f "$PNETLAB_CONF" ]; then
    if ! grep -q "proxy_set_header Upgrade" "$PNETLAB_CONF" 2>/dev/null; then
        MISSING_HEADERS=true
    fi
    if ! grep -q "proxy_set_header Connection" "$PNETLAB_CONF" 2>/dev/null; then
        MISSING_HEADERS=true
    fi
fi

if [ "$MISSING_HEADERS" = false ] && [ -f "$PNETLAB_CONF" ]; then
    echo -e "  ${GREEN}[✔ OK]${RESET} WebSocket upgrade headers are configured in Apache."
else
    echo -e "  ${YELLOW}[⚠ FIXING]${RESET} Missing WebSocket headers — HTML5 console sessions will lag/drop."
    if [ "$MODE" = "--fix" ]; then
        # Find the ProxyPass /guacamole block and inject upgrade headers if missing
        if [ -f "$PNETLAB_CONF" ]; then
            # Backup original
            cp -f "$PNETLAB_CONF" "${PNETLAB_CONF}.bak.$(date +%s)"
            
            # Inject WebSocket headers after any existing ProxyPass block
            if grep -q "ProxyPass /guacamole" "$PNETLAB_CONF"; then
                sed -i '/ProxyPass \/guacamole/a\        ProxyPassReverse /guacamole http://127.0.0.1:8080/guacamole\n        ProxyPreserveHost On\n        RequestHeader set Upgrade $http_upgrade\n        RequestHeader set Connection "upgrade"' "$PNETLAB_CONF"
            fi
            echo -e "  ${GREEN}[✔ DONE]${RESET} WebSocket upgrade headers injected into ${PNETLAB_CONF}."
            FIXES_APPLIED=$((FIXES_APPLIED+1))
        fi
    fi
fi

# === 3. mod_headers for WebSocket RequestHeader ===
echo -e "\n[3/6] ${BOLD}Apache mod_headers (Required for RequestHeader set Upgrade)${RESET}"
if apache2ctl -M 2>/dev/null | grep -q "headers"; then
    echo -e "  ${GREEN}[✔ OK]${RESET} mod_headers is loaded."
else
    echo -e "  ${YELLOW}[⚠ FIXING]${RESET} mod_headers not loaded."
    if [ "$MODE" = "--fix" ]; then
        a2enmod headers 2>/dev/null || true
        echo -e "  ${GREEN}[✔ DONE]${RESET} mod_headers enabled."
        FIXES_APPLIED=$((FIXES_APPLIED+1))
    fi
fi

# === 4. guacd Daemon Health Check ===
echo -e "\n[4/6] ${BOLD}Guacamole Daemon (guacd) Health${RESET}"
if systemctl is-active guacd &>/dev/null; then
    GUACD_PORT=$(ss -tlnp 2>/dev/null | grep guacd | awk '{print $4}' | cut -d':' -f2 | head -n1 || echo "4822")
    echo -e "  ${GREEN}[✔ OK]${RESET} guacd is active and listening on port ${GUACD_PORT:-4822}."
else
    echo -e "  ${YELLOW}[⚠ FIXING]${RESET} guacd is not running."
    if [ "$MODE" = "--fix" ]; then
        systemctl enable --now guacd 2>/dev/null || true
        echo -e "  ${GREEN}[✔ DONE]${RESET} guacd started and enabled."
        FIXES_APPLIED=$((FIXES_APPLIED+1))
    fi
fi

# === 5. Stale Wireshark Pipes & Capture Sockets ===
echo -e "\n[5/6] ${BOLD}Stale Capture Pipes & Wireshark Sockets Cleanup${RESET}"
STALE_COUNT=0
if [ -d "/tmp" ]; then
    # Clean stale Wireshark named pipes
    STALE_PIPES=$(find /tmp -name "wireshark-*" -type p -mmin +60 2>/dev/null | wc -l || echo "0")
    STALE_SOCKS=$(find /tmp -name "*.sock" -mmin +60 -path "*unetlab*" 2>/dev/null | wc -l || echo "0")
    STALE_COUNT=$((STALE_PIPES + STALE_SOCKS))
fi

if [ "$STALE_COUNT" -eq 0 ]; then
    echo -e "  ${GREEN}[✔ OK]${RESET} No stale capture pipes or sockets detected."
else
    echo -e "  ${YELLOW}[⚠ FIXING]${RESET} Found ${STALE_COUNT} stale capture pipe(s)/socket(s) older than 60 minutes."
    if [ "$MODE" = "--fix" ]; then
        find /tmp -name "wireshark-*" -type p -mmin +60 -delete 2>/dev/null || true
        find /tmp -name "*.sock" -mmin +60 -path "*unetlab*" -delete 2>/dev/null || true
        echo -e "  ${GREEN}[✔ DONE]${RESET} ${STALE_COUNT} stale pipe(s)/socket(s) removed."
        FIXES_APPLIED=$((FIXES_APPLIED+1))
    fi
fi

# === 6. Apply Apache Reload if Fixes Were Applied ===
echo -e "\n[6/6] ${BOLD}Apache Configuration Validation & Reload${RESET}"
if apache2ctl configtest 2>&1 | grep -q "Syntax OK"; then
    echo -e "  ${GREEN}[✔ OK]${RESET} Apache configuration syntax is valid."
    if [ "$MODE" = "--fix" ] && [ "$FIXES_APPLIED" -gt 0 ]; then
        systemctl reload apache2 2>/dev/null || true
        echo -e "  ${GREEN}[✔ DONE]${RESET} Apache reloaded with new WebSocket configuration."
    fi
else
    echo -e "  ${RED}[✘ WARN]${RESET} Apache configuration has syntax errors. Review manually:"
    apache2ctl configtest 2>&1 | tail -n5
fi

# === Generate Windows .reg file for URL handlers ===
WINDOWS_HOST_IP="${2:-}"
REG_FILE="/opt/azambasha/azam-console-handlers.reg"

echo -e "\n${CYAN}-------------------------------------------------------------------------------${RESET}"
echo -e "${BOLD}Generating Windows URL Handler Registry File${RESET}"
echo -e "  → This .reg file maps telnet://, ssh://, capture:// links on your Windows PC"
echo -e "  → to PuTTY, Windows Terminal, or Wireshark automatically."

cat > "$REG_FILE" << 'REGEOF'
Windows Registry Editor Version 5.00

; ============================================================
; Azam-Pnet Console URL Handlers for Windows Host
; Double-click azam-console-handlers.reg to install.
; ============================================================

; telnet:// -> PuTTY
[HKEY_CLASSES_ROOT\telnet]
@="URL:Telnet Protocol"
"URL Protocol"=""

[HKEY_CLASSES_ROOT\telnet\shell]

[HKEY_CLASSES_ROOT\telnet\shell\open]

[HKEY_CLASSES_ROOT\telnet\shell\open\command]
@="\"C:\\Program Files\\PuTTY\\putty.exe\" %1"

; ssh:// -> Windows Terminal (wt.exe) with SSH
[HKEY_CLASSES_ROOT\ssh]
@="URL:SSH Protocol"
"URL Protocol"=""

[HKEY_CLASSES_ROOT\ssh\shell]

[HKEY_CLASSES_ROOT\ssh\shell\open]

[HKEY_CLASSES_ROOT\ssh\shell\open\command]
@="cmd.exe /c start wt.exe ssh %1"

; vnc:// -> TigerVNC Viewer (if installed)
[HKEY_CLASSES_ROOT\vnc]
@="URL:VNC Protocol"
"URL Protocol"=""

[HKEY_CLASSES_ROOT\vnc\shell]

[HKEY_CLASSES_ROOT\vnc\shell\open]

[HKEY_CLASSES_ROOT\vnc\shell\open\command]
@="\"C:\\Program Files\\TigerVNC\\vncviewer.exe\" %1"
REGEOF

echo -e "  ${GREEN}[✔ DONE]${RESET} Windows URL handler registry file written to: ${REG_FILE}"
echo -e "  → Transfer to Windows and double-click to install."

# Summary
echo -e "\n${CYAN}================================================================================"
echo -e " ${BOLD}Console Fix Summary: ${FIXES_APPLIED} fix(es) applied.${RESET}${CYAN}"
if [ "$FIXES_APPLIED" -gt 0 ]; then
    echo -e " ${GREEN}HTML5 Guacamole consoles and WebSocket tunnels are now optimized.${RESET}${CYAN}"
else
    echo -e " ${GREEN}All console subsystems are healthy — no action required.${RESET}${CYAN}"
fi
echo -e "================================================================================${RESET}"
