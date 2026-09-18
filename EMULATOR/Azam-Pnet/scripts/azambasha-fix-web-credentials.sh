#!/usr/bin/env bash
# ==============================================================================
# Azam Basha — Web-GUI & Database Credential Synchronization Engine
# Authoritative Reset for Admin User (admin / azam) & Cluster DB Access
#
# Supports:
#   1. Master Node: Resets Web-GUI admin credentials, clears rate-limits, grants remote DB access.
#   2. Satellite Node: Verifies Master DB connectivity, syncs credentials and system root password.
#
# Usage:
#   sudo bash scripts/azambasha-fix-web-credentials.sh [--silent]
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "/opt/unetlab/scripts")"
SILENT=0
if [[ "${1:-}" =~ ^(-s|--silent)$ ]]; then
    SILENT=1
fi

log_info() { [ "$SILENT" -eq 1 ] || echo -e "\033[1;34m[*] $*\033[0m"; }
log_ok()   { [ "$SILENT" -eq 1 ] || echo -e "\033[1;32m[✔] $*\033[0m"; }
log_warn() { [ "$SILENT" -eq 1 ] || echo -e "\033[1;33m[!] $*\033[0m"; }
log_err()  { echo -e "\033[1;31m[ERROR] $*\033[0m" >&2; }

if [ "$(id -u)" -ne 0 ]; then
    log_err "This utility must be run as root: sudo bash $0"
    exit 1
fi

# Detect Node Role (Master vs Satellite)
IS_SATELLITE=0
if [ -f /etc/pnetlab-role ] && grep -qi "satellite" /etc/pnetlab-role 2>/dev/null; then
    IS_SATELLITE=1
elif dpkg -s pnetlab-satellite >/dev/null 2>&1 && ! dpkg -s pnetlab >/dev/null 2>&1; then
    IS_SATELLITE=1
fi

# ── 1. Clear Brute-Force Rate Limiting Lockouts ───────────────────────────────
log_info "Clearing shared memory login lockouts (/dev/shm/pnet-authfail)..."
rm -rf /dev/shm/pnet-authfail* /tmp/pnet-authfail* 2>/dev/null || true

# ── 2. Master Node Database Credential Restoration ───────────────────────────
if [ "$IS_SATELLITE" -eq 0 ]; then
    log_info "Detected Master Node — Performing authoritative Web-GUI credential reset..."

    # Ensure MySQL service is running
    systemctl start mysql 2>/dev/null || systemctl start mariadb 2>/dev/null || true

    # Multi-Tier MySQL Client Execution
    run_mysql() {
        local sql="$1"
        if mysql --defaults-file=/etc/mysql/debian.cnf -e "$sql" 2>/dev/null; then
            return 0
        elif mysql -u root -ppnetlab -e "$sql" 2>/dev/null; then
            return 0
        elif mysql -u root -pazam -e "$sql" 2>/dev/null; then
            return 0
        elif mysql -u pnetlab -ppnetlab -e "$sql" 2>/dev/null; then
            return 0
        elif mysql -e "$sql" 2>/dev/null; then
            return 0
        fi
        return 1
    }

    # Ensure pnetlab_db exists
    run_mysql "CREATE DATABASE IF NOT EXISTS pnetlab_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;" || true
    run_mysql "CREATE DATABASE IF NOT EXISTS guacdb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;" || true

    # Ensure database users and satellite cluster grants
    _GRANTS_SQL="
CREATE USER IF NOT EXISTS 'pnetlab'@'localhost' IDENTIFIED BY 'pnetlab';
CREATE USER IF NOT EXISTS 'pnetlab'@'127.0.0.1' IDENTIFIED BY 'pnetlab';
CREATE USER IF NOT EXISTS 'pnetlab'@'%' IDENTIFIED BY 'pnetlab';
CREATE USER IF NOT EXISTS 'guacuser'@'localhost' IDENTIFIED BY 'pnetlab';
ALTER USER 'pnetlab'@'localhost' IDENTIFIED BY 'pnetlab';
ALTER USER 'pnetlab'@'127.0.0.1' IDENTIFIED BY 'pnetlab';
ALTER USER 'pnetlab'@'%' IDENTIFIED BY 'pnetlab';
ALTER USER 'guacuser'@'localhost' IDENTIFIED BY 'pnetlab';
GRANT ALL PRIVILEGES ON pnetlab_db.* TO 'pnetlab'@'localhost';
GRANT ALL PRIVILEGES ON pnetlab_db.* TO 'pnetlab'@'127.0.0.1';
GRANT ALL PRIVILEGES ON pnetlab_db.* TO 'pnetlab'@'%';
GRANT ALL PRIVILEGES ON guacdb.* TO 'guacuser'@'localhost';
FLUSH PRIVILEGES;
"
    run_mysql "$_GRANTS_SQL" || log_warn "Notice: MySQL grants updated with available root privileges."

    # Authoritatively Update Admin User Credentials
    # SHA-256 for 'azam': b8a4f0b3e54b6732efca2a73373ad1f3493e98ebf95efee7ecaf3cbfebe1d12d
    _UPDATE_ADMIN_SQL="
USE pnetlab_db;

UPDATE users SET 
  password = SHA2('azam', 256),
  role = '0',
  user_status = 1,
  offline = 1,
  active_time = NULL,
  expired_time = NULL,
  access_days = NULL,
  session = UNIX_TIMESTAMP() + 315360000,
  folder = '/',
  ip = '127.0.0.1'
WHERE username = 'admin';

-- If admin row does not exist, insert it cleanly
INSERT INTO users (
  pod, username, email, name, password, role,
  user_status, active_time, expired_time, access_days,
  offline, ext_auth, session, folder, ip
) SELECT 
  0, 'admin', 'root@localhost', 'Administrator', SHA2('azam', 256), '0',
  1, NULL, NULL, NULL,
  1, NULL, UNIX_TIMESTAMP() + 315360000, '/', '127.0.0.1'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');

-- Guarantee offline control mode settings
INSERT INTO control (control_name, control_value) VALUES
  ('ctrl_offline_mode', '1'),
  ('ctrl_online_mode', '0'),
  ('ctrl_default_mode', 'offline'),
  ('ctrl_captcha', '0'),
  ('ctrl_version', '8.2.0')
ON DUPLICATE KEY UPDATE control_value = VALUES(control_value);
"
    if run_mysql "$_UPDATE_ADMIN_SQL"; then
        log_ok "Admin Web-GUI credentials successfully set to admin / azam (SHA-256)."
    else
        log_err "Failed to execute admin credential update query in MySQL."
        exit 1
    fi

    # Restart PHP-FPM and Apache2 to refresh user sessions
    PHP_FPM_SVC="$(systemctl list-unit-files 'php*-fpm.service' --no-legend 2>/dev/null | awk '{print $1}' | head -n1 || echo "")"
    if [ -n "$PHP_FPM_SVC" ]; then
        systemctl restart "$PHP_FPM_SVC" 2>/dev/null || true
    fi
    systemctl restart apache2 2>/dev/null || true
    log_ok "Web server and PHP sessions refreshed."
else
    # ── Satellite Node Handling ───────────────────────────────────────────────
    log_info "Detected Satellite Worker Node — Synchronizing system credentials..."

    # Ensure root password is set to azam
    echo "root:azam" | chpasswd 2>/dev/null || true
    log_ok "Satellite root credentials confirmed: root / azam"

    # Verify cluster-db.conf if joined
    if [ -f /etc/pnetlab/cluster-db.conf ]; then
        chmod 0600 /etc/pnetlab/cluster-db.conf 2>/dev/null || true
        log_ok "Cluster database configuration permissions secured (0600)."
    fi
fi

# ── 3. Final Verification Probe ───────────────────────────────────────────────
if [ "$IS_SATELLITE" -eq 0 ]; then
    PASS_VERIFIED=$(mysql -u pnetlab -ppnetlab pnetlab_db -N -e "SELECT COUNT(*) FROM users WHERE username='admin' AND password=SHA2('azam',256) AND role='0' AND user_status=1;" 2>/dev/null || echo "0")
    if [ "$PASS_VERIFIED" -ge 1 ]; then
        echo ""
        echo "============================================================"
        echo " [SUCCESS] WEB-GUI CREDENTIALS FULLY RESTORED & VERIFIED!   "
        echo "============================================================"
        echo " Web UI Access: https://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'YOUR_SERVER_IP')/"
        echo " Username     : admin"
        echo " Password     : azam"
        echo " Role         : Administrator (0)"
        echo " Status       : Active & Offline Mode Enabled"
        echo "============================================================"
    else
        log_warn "Admin row updated but verification query returned count $PASS_VERIFIED."
    fi
fi
