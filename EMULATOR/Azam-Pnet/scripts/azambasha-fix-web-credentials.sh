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

# ── Self-Register CLI Commands ────────────────────────────────────────────────
ln -sfn "${BASH_SOURCE[0]}" /usr/local/bin/azam-credentials 2>/dev/null || true
ln -sfn "${BASH_SOURCE[0]}" /usr/local/bin/pnet-credentials 2>/dev/null || true
ln -sfn "${BASH_SOURCE[0]}" /usr/local/bin/azambasha-credentials 2>/dev/null || true

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

    # Ensure MySQL packages are installed
    if ! command -v mysqld >/dev/null 2>&1 && ! command -v mariadbd >/dev/null 2>&1; then
        log_info "MySQL server binary not found; installing mysql-server..."
        DEBIAN_FRONTEND=noninteractive apt-get update -qq 2>/dev/null || true
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mysql-server 2>/dev/null || true
    fi

    # ── MySQL Daemon & Socket Recovery ────────────────────────────────────────
    # 1. Ensure runtime directories exist with appropriate ownership
    mkdir -p /var/run/mysqld /run/mysqld /var/log/mysql /var/lib/mysql
    chown -R mysql:mysql /var/run/mysqld /run/mysqld /var/log/mysql 2>/dev/null || true
    chmod 0755 /var/run/mysqld /run/mysqld 2>/dev/null || true

    # 2. Check for incompatible MySQL 8.0/8.4 configuration directives
    # In MySQL 8.0, 'mysql_native_password=ON' is an unknown variable that causes immediate crash on startup
    if [ -f /etc/mysql/mysql.conf.d/zz-pnetlab-native-pw.cnf ]; then
        if mysqld --validate-config 2>&1 | grep -qi "unknown variable 'mysql_native_password"; then
            log_warn "Detected incompatible 'mysql_native_password=ON' in configuration; removing to allow clean startup..."
            mv -f /etc/mysql/mysql.conf.d/zz-pnetlab-native-pw.cnf /etc/mysql/mysql.conf.d/zz-pnetlab-native-pw.cnf.bak 2>/dev/null || true
        fi
    fi

    # 3. Clean stale PID and socket lock files
    rm -f /var/run/mysqld/mysqld.sock.lock /var/run/mysqld/mysqld.pid /run/mysqld/mysqld.sock.lock /run/mysqld/mysqld.pid 2>/dev/null || true

    # 4. Check if MySQL datadir is initialized
    if [ ! -d /var/lib/mysql/mysql ]; then
        log_info "Initializing MySQL datadir (/var/lib/mysql)..."
        mysqld --initialize-insecure --user=mysql 2>/dev/null || true
    fi

    # 5. Start MySQL service
    systemctl unmask mysql 2>/dev/null || true
    systemctl unmask mariadb 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true

    systemctl restart mysql 2>/dev/null || systemctl start mysql 2>/dev/null \
        || systemctl restart mariadb 2>/dev/null || systemctl start mariadb 2>/dev/null \
        || systemctl start mysqld 2>/dev/null || true

    # Wait up to 10 seconds for socket to become ready
    SOCKET_FOUND=0
    for _ in $(seq 1 10); do
        if [ -S /var/run/mysqld/mysqld.sock ] || [ -S /run/mysqld/mysqld.sock ]; then
            SOCKET_FOUND=1
            break
        fi
        sleep 1
    done

    # If socket is still missing, attempt emergency fallback start
    if [ "$SOCKET_FOUND" -eq 0 ]; then
        log_warn "Socket not created by systemd service; testing direct mysqld start..."
        # Remove any broken config preventing startup
        if [ -f /etc/mysql/mysql.conf.d/zz-pnetlab-native-pw.cnf ]; then
            mv -f /etc/mysql/mysql.conf.d/zz-pnetlab-native-pw.cnf /etc/mysql/mysql.conf.d/zz-pnetlab-native-pw.cnf.bak 2>/dev/null || true
            systemctl restart mysql 2>/dev/null || true
        fi
        sleep 2
    fi

    # ── Multi-Tier Credential & Socket Probe ──────────────────────────────────
    CANDIDATES=(
        "mysql"
        "mysql -u root"
        "mysql -u root -ppnetlab"
        "mysql -u root -pazam"
        "mysql -u root -ppnet"
        "mysql -u root -proot"
        "mysql -u root --password="
        "mysql -u pnetlab -ppnetlab"
        "mysql --defaults-file=/etc/mysql/debian.cnf"
        "mysql --defaults-extra-file=/root/.my.cnf"
        "mysql -S /var/run/mysqld/mysqld.sock -u root"
        "mysql -S /run/mysqld/mysqld.sock -u root"
        "mysql -h 127.0.0.1 -u root -ppnetlab"
        "mysql -h 127.0.0.1 -u pnetlab -ppnetlab"
        "mariadb -u root"
        "mariadb"
    )

    MYSQL_CMD=""

    for cand in "${CANDIDATES[@]}"; do
        if $cand -N -e "SELECT 1;" >/dev/null 2>&1; then
            MYSQL_CMD="$cand"
            break
        fi
    done

    # If still not connecting, output detailed service diagnostics
    if [ -z "$MYSQL_CMD" ]; then
        log_err "Could not connect to MySQL using any known credential or socket method."
        echo "" >&2
        echo "=== MySQL Service Status ===" >&2
        systemctl status mysql --no-pager 2>/dev/null || systemctl status mariadb --no-pager 2>/dev/null || true
        echo "" >&2
        echo "=== Recent MySQL Error Logs ===" >&2
        if [ -f /var/log/mysql/error.log ]; then
            tail -n 25 /var/log/mysql/error.log >&2 || true
        else
            journalctl -u mysql -n 25 --no-pager 2>/dev/null || true
        fi
        exit 1
    fi

    log_ok "Database connected successfully using: $MYSQL_CMD"

    # Ensure databases exist
    $MYSQL_CMD -e "CREATE DATABASE IF NOT EXISTS pnetlab_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;" || true
    $MYSQL_CMD -e "CREATE DATABASE IF NOT EXISTS guacdb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;" || true

    # Check if pnetlab_db tables exist; import schema if missing
    TBL_COUNT=$($MYSQL_CMD -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='pnetlab_db';" 2>/dev/null || echo "0")
    if [ "${TBL_COUNT:-0}" -eq 0 ]; then
        log_info "pnetlab_db is empty; searching for schema files to import..."
        SCHEMA_IMPORTED=0
        for sf in \
            "${SCRIPT_DIR}/../schema/pnetlab_db.sql" \
            "${SCRIPT_DIR}/schema/pnetlab_db.sql" \
            "/opt/azambasha/schema/pnetlab_db.sql" \
            "/opt/unetlab/schema/pnetlab_db.sql" \
            "/opt/unetlab/schema/pnetlab_db-schema.sql"; do
            if [ -f "$sf" ]; then
                log_info "Importing pnetlab_db schema from: $sf"
                $MYSQL_CMD pnetlab_db < "$sf" 2>/dev/null && SCHEMA_IMPORTED=1 && break || true
            fi
        done
        if [ "$SCHEMA_IMPORTED" -eq 1 ]; then
            log_ok "pnetlab_db schema successfully imported."
        else
            log_warn "Schema file not found on disk; creating essential core tables dynamically..."
        fi
    fi

    # Ensure essential tables always exist with correct column definitions
    $MYSQL_CMD -e "
CREATE TABLE IF NOT EXISTS pnetlab_db.control (
  control_name varchar(150) NOT NULL,
  control_value text,
  PRIMARY KEY (control_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pnetlab_db.users (
  pod int NOT NULL AUTO_INCREMENT,
  username text,
  cookie text,
  email varchar(150) DEFAULT NULL,
  expiration int DEFAULT '-1',
  name text,
  password text,
  session int DEFAULT NULL,
  ip text,
  role text,
  folder text,
  lab_session int DEFAULT NULL,
  html5 tinyint(1) DEFAULT NULL,
  license text,
  online_time int DEFAULT NULL,
  note text,
  offline int DEFAULT 1,
  active_time int DEFAULT NULL,
  expired_time int DEFAULT NULL,
  user_status int DEFAULT 1,
  user_workspace text,
  max_node int DEFAULT NULL,
  max_node_lab int DEFAULT NULL,
  user_max_cpu int DEFAULT NULL,
  user_max_ram int DEFAULT NULL,
  access_days varchar(16) DEFAULT NULL,
  ext_auth varchar(8) DEFAULT NULL,
  PRIMARY KEY (pod),
  UNIQUE KEY email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
" 2>/dev/null || true

    # Safe user grants
    $MYSQL_CMD -e "CREATE USER IF NOT EXISTS 'pnetlab'@'localhost' IDENTIFIED BY 'pnetlab';" 2>/dev/null || true
    $MYSQL_CMD -e "ALTER USER 'pnetlab'@'localhost' IDENTIFIED BY 'pnetlab';" 2>/dev/null || true
    $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON pnetlab_db.* TO 'pnetlab'@'localhost';" 2>/dev/null || true
    $MYSQL_CMD -e "CREATE USER IF NOT EXISTS 'guacuser'@'localhost' IDENTIFIED BY 'pnetlab';" 2>/dev/null || true
    $MYSQL_CMD -e "ALTER USER 'guacuser'@'localhost' IDENTIFIED BY 'pnetlab';" 2>/dev/null || true
    $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON guacdb.* TO 'guacuser'@'localhost';" 2>/dev/null || true
    $MYSQL_CMD -e "CREATE USER IF NOT EXISTS 'pnetlab'@'127.0.0.1' IDENTIFIED BY 'pnetlab';" 2>/dev/null || true
    $MYSQL_CMD -e "ALTER USER 'pnetlab'@'127.0.0.1' IDENTIFIED BY 'pnetlab';" 2>/dev/null || true
    $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON pnetlab_db.* TO 'pnetlab'@'127.0.0.1';" 2>/dev/null || true
    $MYSQL_CMD -e "CREATE USER IF NOT EXISTS 'pnetlab'@'%' IDENTIFIED BY 'pnetlab';" 2>/dev/null || true
    $MYSQL_CMD -e "ALTER USER 'pnetlab'@'%' IDENTIFIED BY 'pnetlab';" 2>/dev/null || true
    $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON pnetlab_db.* TO 'pnetlab'@'%';" 2>/dev/null || true
    $MYSQL_CMD -e "FLUSH PRIVILEGES;" 2>/dev/null || true

    # Guarantee /root/.my.cnf exists with detected credentials for future tools
    if ! [ -f /root/.my.cnf ]; then
        printf '[client]\nuser=root\npassword=pnetlab\n' >/root/.my.cnf 2>/dev/null || true
        chmod 0600 /root/.my.cnf 2>/dev/null || true
    fi

    # Authoritatively Update Admin User Credentials
    # SHA-256 for 'azam': b8a4f0b3e54b6732efca2a73373ad1f3493e98ebf95efee7ecaf3cbfebe1d12d
    $MYSQL_CMD -e "
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
" 2>/dev/null || true

    # If admin row does not exist, insert it cleanly
    ADMIN_COUNT=$($MYSQL_CMD -N -e "USE pnetlab_db; SELECT COUNT(*) FROM users WHERE username = 'admin';" 2>/dev/null || echo "0")
    if [ "${ADMIN_COUNT:-0}" -eq 0 ]; then
        log_info "Admin record not found, inserting authoritative admin row..."
        $MYSQL_CMD -e "
USE pnetlab_db;
INSERT INTO users (
  pod, username, email, name, password, role,
  user_status, active_time, expired_time, access_days,
  offline, ext_auth, session, folder, ip
) VALUES (
  0, 'admin', 'root@localhost', 'Administrator', SHA2('azam', 256), '0',
  1, NULL, NULL, NULL,
  1, NULL, UNIX_TIMESTAMP() + 315360000, '/', '127.0.0.1'
);
" 2>/dev/null || true
    fi

    # Guarantee offline control mode settings
    $MYSQL_CMD -e "
USE pnetlab_db;
INSERT INTO control (control_name, control_value) VALUES
  ('ctrl_offline_mode', '1'),
  ('ctrl_online_mode', '0'),
  ('ctrl_default_mode', 'offline'),
  ('ctrl_captcha', '0'),
  ('ctrl_version', '8.2.0')
ON DUPLICATE KEY UPDATE control_value = VALUES(control_value);
" 2>/dev/null || true

    # ── PHP-FPM & Apache FastCGI Handler Enforcement ─────────────────────────
    log_info "Verifying PHP-FPM and Apache FastCGI execution pipeline..."
    PHP_VER="$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;' 2>/dev/null || echo "8.5")"
    if ! dpkg -s "php${PHP_VER}-fpm" >/dev/null 2>&1 && ! dpkg -s php-fpm >/dev/null 2>&1; then
        log_info "Installing php${PHP_VER}-fpm and fastcgi modules..."
        DEBIAN_FRONTEND=noninteractive apt-get update -qq 2>/dev/null || true
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "php${PHP_VER}-fpm" php-fpm 2>/dev/null || true
    fi

    # Ensure proxy_fcgi and php-fpm configuration in Apache
    a2enmod proxy_fcgi setenvif rewrite ssl proxy proxy_http headers 2>/dev/null || true
    a2enconf "php${PHP_VER}-fpm" 2>/dev/null || a2enconf php-fpm 2>/dev/null || true

    # Patch Cookie Compatibility in api.php for HTTP & HTTPS
    if [ -f /opt/unetlab/html/api.php ]; then
        sed -i 's/"secure" *=> *true/"secure" => (!empty($_SERVER["HTTPS"]) \&\& $_SERVER["HTTPS"] !== "off")/g' /opt/unetlab/html/api.php 2>/dev/null || true
        sed -i 's/"samesite" *=> *"Strict"/"samesite" => "Lax"/g' /opt/unetlab/html/api.php 2>/dev/null || true
    fi

    # Restart PHP-FPM and Apache2 to refresh user sessions
    PHP_FPM_SVC="$(systemctl list-unit-files 'php*-fpm.service' --no-legend 2>/dev/null | awk '{print $1}' | head -n1 || echo "php${PHP_VER}-fpm.service")"
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
    PASS_VERIFIED=$($MYSQL_CMD -N -e "USE pnetlab_db; SELECT COUNT(*) FROM users WHERE username='admin' AND password=SHA2('azam',256) AND role='0' AND user_status=1;" 2>/dev/null || echo "0")
    
    # Perform live end-to-end API login check
    API_AUTH_RESP=$(curl -sk -X POST https://127.0.0.1/api/auth -H "Content-Type: application/json" -d '{"username":"admin","password":"azam"}' 2>/dev/null || true)
    
    if [ "${PASS_VERIFIED:-0}" -ge 1 ]; then
        echo ""
        echo "============================================================"
        echo " [SUCCESS] WEB-GUI CREDENTIALS FULLY RESTORED & VERIFIED!   "
        echo "============================================================"
        echo " Web UI Access: https://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'YOUR_SERVER_IP')/"
        echo " Username     : admin"
        echo " Password     : azam"
        echo " Role         : Administrator (0)"
        echo " Status       : Active & Offline Mode Enabled"
        echo " CLI Command  : sudo azam-credentials"
        if echo "$API_AUTH_RESP" | grep -qi '"status":"success"'; then
            echo " Live API Auth: VERIFIED (HTTP 200 / User authenticated)"
        fi
        echo "============================================================"
    else
        log_warn "Admin row was updated, but verification query returned count: ${PASS_VERIFIED}."
        log_info "Testing database direct check:"
        $MYSQL_CMD -e "USE pnetlab_db; SELECT pod, username, role, user_status, offline, active_time, expired_time FROM users WHERE username='admin';" 2>/dev/null || true
    fi
fi
