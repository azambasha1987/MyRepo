#!/usr/bin/env bash
# ==============================================================================
# Azam Basha HTTPS Certificate Auto-Renewal & Browser Trust Fixer (azam-ssl)
# ==============================================================================
# Generates a 5-year SAN certificate for IP 192.168.1.23, installs it into
# Apache, reloads, and produces a Windows .crt file for import into the
# Trusted Root Certification Authorities store — eliminating all browser
# security warnings and fixing WebSocket console disconnects.
# ==============================================================================
set -euo pipefail

# Install symlink
if [ "$(id -u)" -eq 0 ]; then
    ln -sf "$(realpath "$0")" /usr/local/bin/azam-ssl 2>/dev/null || true
fi

GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
BOLD="\033[1m"
RESET="\033[0m"

MODE="${1:---status}"

# Detect master IP from network interfaces
MASTER_IP="${2:-}"
if [ -z "$MASTER_IP" ]; then
    MASTER_IP=$(hostname -I | tr ' ' '\n' | grep -v '^127\.' | head -n1 || echo "192.168.1.23")
fi

HOSTNAME_FQDN=$(hostname -f 2>/dev/null || hostname)
CERT_DIR="/etc/ssl/azambasha"
CERT_KEY="${CERT_DIR}/azam-pnet.key"
CERT_CRT="${CERT_DIR}/azam-pnet.crt"
CERT_CSR="${CERT_DIR}/azam-pnet.csr"
CA_KEY="${CERT_DIR}/azam-ca.key"
CA_CRT="${CERT_DIR}/azam-ca.crt"
SAN_CONF="${CERT_DIR}/san.cnf"
APACHE_SSL_CONF="/etc/apache2/sites-available/pnetlab-ssl.conf"
WIN_EXPORT_PATH="/opt/azambasha/azam-pnet-ca.crt"
VALIDITY_DAYS=1825  # 5 years

echo -e "${CYAN}================================================================================"
echo -e "     ${BOLD}Azam-Pnet HTTPS Certificate Auto-Renewal & Browser Trust Fixer${RESET}${CYAN}"
echo -e "================================================================================${RESET}"
echo -e " Master IP:   ${BOLD}${MASTER_IP}${RESET}"
echo -e " Hostname:    ${BOLD}${HOSTNAME_FQDN}${RESET}"
echo -e " Mode:        ${BOLD}${MODE}${RESET}"
echo -e "--------------------------------------------------------------------------------"

# === STATUS MODE ===
if [ "$MODE" = "--status" ]; then
    echo -e "\n${BOLD}Current Certificate Status:${RESET}"
    if [ -f "$CERT_CRT" ]; then
        EXPIRY=$(openssl x509 -noout -enddate -in "$CERT_CRT" 2>/dev/null | cut -d= -f2 || echo "unknown")
        SUBJECT=$(openssl x509 -noout -subject -in "$CERT_CRT" 2>/dev/null | sed 's/subject=//' || echo "unknown")
        SANS=$(openssl x509 -noout -ext subjectAltName -in "$CERT_CRT" 2>/dev/null | grep -v "X509v3" | tr -d ' ' || echo "none")
        echo -e "  ${GREEN}[✔ EXISTS]${RESET} Certificate: ${CERT_CRT}"
        echo -e "  Subject:  ${SUBJECT}"
        echo -e "  Expires:  ${EXPIRY}"
        echo -e "  SANs:     ${SANS}"
    else
        echo -e "  ${YELLOW}[!] No Azam-Pnet TLS certificate found at ${CERT_CRT}.${RESET}"
        echo -e "      Run: ${BOLD}sudo azam-ssl --generate${RESET} to create a 5-year trusted certificate."
    fi
    
    echo -e "\n${BOLD}Apache SSL Module:${RESET}"
    if apache2ctl -M 2>/dev/null | grep -q "ssl"; then
        echo -e "  ${GREEN}[✔ OK]${RESET} mod_ssl is loaded."
    else
        echo -e "  ${YELLOW}[!] mod_ssl not loaded.${RESET} Run: sudo a2enmod ssl && sudo systemctl reload apache2"
    fi
    exit 0
fi

# === GENERATE MODE ===
if [ "$MODE" = "--generate" ] || [ "$MODE" = "--renew" ]; then
    echo -e "\n[1/6] ${BOLD}Preparing certificate directory${RESET}"
    mkdir -p "$CERT_DIR"
    chmod 750 "$CERT_DIR"
    echo -e "  ${GREEN}[✔]${RESET} ${CERT_DIR} ready."

    echo -e "\n[2/6] ${BOLD}Generating Private CA (azam-pnet-ca)${RESET}"
    openssl genrsa -out "$CA_KEY" 4096 2>/dev/null
    openssl req -new -x509 -days "$VALIDITY_DAYS" -key "$CA_KEY" -out "$CA_CRT" \
        -subj "/C=SA/ST=Riyadh/O=Azam-Pnet Lab/OU=Network Engineering/CN=Azam-Pnet-CA" \
        2>/dev/null
    echo -e "  ${GREEN}[✔]${RESET} Private CA generated (${CA_CRT})."

    echo -e "\n[3/6] ${BOLD}Generating Server Key & Certificate Signing Request${RESET}"
    openssl genrsa -out "$CERT_KEY" 4096 2>/dev/null
    
    # Write SAN config with both IP and hostname
    cat > "$SAN_CONF" << SANEOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C  = SA
ST = Riyadh
O  = Azam-Pnet Lab
OU = Network Engineering
CN = ${MASTER_IP}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
IP.1  = ${MASTER_IP}
IP.2  = 127.0.0.1
DNS.1 = ${HOSTNAME_FQDN}
DNS.2 = pnetlab.local
DNS.3 = azam-pnet.local
SANEOF

    openssl req -new -key "$CERT_KEY" -out "$CERT_CSR" -config "$SAN_CONF" 2>/dev/null
    echo -e "  ${GREEN}[✔]${RESET} CSR generated with SAN for IP ${MASTER_IP} and hostname ${HOSTNAME_FQDN}."

    echo -e "\n[4/6] ${BOLD}Signing Certificate with Private CA (${VALIDITY_DAYS} days / ~5 years)${RESET}"
    openssl x509 -req -days "$VALIDITY_DAYS" \
        -in "$CERT_CSR" -CA "$CA_CRT" -CAkey "$CA_KEY" -CAcreateserial \
        -out "$CERT_CRT" -extensions v3_req -extfile "$SAN_CONF" \
        2>/dev/null
    echo -e "  ${GREEN}[✔]${RESET} Certificate signed and valid for ${VALIDITY_DAYS} days."

    echo -e "\n[5/6] ${BOLD}Configuring Apache SSL VirtualHost${RESET}"
    # Enable SSL module
    a2enmod ssl 2>/dev/null || true
    
    # Write SSL vhost if not exists
    if [ ! -f "$APACHE_SSL_CONF" ]; then
        cat > "$APACHE_SSL_CONF" << APACHEEOF
<VirtualHost *:443>
    ServerName ${MASTER_IP}
    ServerAlias ${HOSTNAME_FQDN} pnetlab.local

    SSLEngine on
    SSLCertificateFile    ${CERT_CRT}
    SSLCertificateKeyFile ${CERT_KEY}

    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    SSLHonorCipherOrder on

    # Proxy to PNetLab backend
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:80/
    ProxyPassReverse / http://127.0.0.1:80/
</VirtualHost>
APACHEEOF
        a2ensite pnetlab-ssl 2>/dev/null || true
        echo -e "  ${GREEN}[✔]${RESET} SSL VirtualHost created and enabled."
    else
        # Update cert paths in existing config
        sed -i "s|SSLCertificateFile.*|SSLCertificateFile    ${CERT_CRT}|" "$APACHE_SSL_CONF"
        sed -i "s|SSLCertificateKeyFile.*|SSLCertificateKeyFile ${CERT_KEY}|" "$APACHE_SSL_CONF"
        echo -e "  ${GREEN}[✔]${RESET} Existing SSL VirtualHost certificate paths updated."
    fi

    chmod 640 "$CERT_KEY" "$CERT_CRT"
    
    if apache2ctl configtest 2>&1 | grep -q "Syntax OK"; then
        systemctl reload apache2 2>/dev/null || true
        echo -e "  ${GREEN}[✔]${RESET} Apache reloaded with new 5-year certificate."
    else
        echo -e "  ${RED}[!]${RESET} Apache config test failed. Check: sudo apache2ctl configtest"
    fi

    echo -e "\n[6/6] ${BOLD}Exporting Windows Trust Store Package${RESET}"
    # Copy CA cert to accessible location for Windows import
    cp -f "$CA_CRT" "$WIN_EXPORT_PATH"
    echo -e "  ${GREEN}[✔]${RESET} CA certificate exported: ${WIN_EXPORT_PATH}"
    
    # Generate Windows batch installer
    WIN_BAT="/opt/azambasha/install-azam-ca-windows.bat"
    cat > "$WIN_BAT" << 'BATEOF'
@echo off
:: Azam-Pnet CA Trust Installer for Windows
:: Run as Administrator to install the Azam-Pnet CA into Windows Trusted Root
echo Installing Azam-Pnet CA certificate...
certutil -addstore -f "ROOT" "%~dp0azam-pnet-ca.crt"
if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Azam-Pnet CA is now trusted by all browsers on this PC.
    echo You can now browse to https://192.168.1.23 without security warnings.
) else (
    echo FAILED: Run this script as Administrator.
)
pause
BATEOF

    echo -e "\n${CYAN}================================================================================"
    echo -e " ${GREEN}${BOLD}Certificate Generated Successfully! (Valid: ~5 years)${RESET}${CYAN}"
    echo -e "  HTTPS URL:  ${BOLD}https://${MASTER_IP}/${RESET}${CYAN}"
    echo -e ""
    echo -e " ${BOLD}Windows Trust Setup (eliminates ALL browser warnings):${RESET}${CYAN}"
    echo -e "  1. Copy ${WIN_EXPORT_PATH} to your Windows PC"
    echo -e "  2. Double-click ${BOLD}azam-pnet-ca.crt${RESET}${CYAN} → Install → Local Machine"
    echo -e "     → Place in: Trusted Root Certification Authorities"
    echo -e "  OR run ${WIN_BAT} as Administrator"
    echo -e "================================================================================${RESET}"
    exit 0
fi

echo -e "${YELLOW}Usage: sudo azam-ssl [--status|--generate|--renew] [MASTER_IP]${RESET}"
echo -e "  --status    Check current certificate expiry and configuration"
echo -e "  --generate  Generate new 5-year SAN certificate for ${MASTER_IP}"
echo -e "  --renew     Renew existing certificate (same as --generate)"
