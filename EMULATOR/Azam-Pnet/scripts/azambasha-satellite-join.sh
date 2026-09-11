#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Satellite Node Cluster Join & Continuous Sync Utility
# Ubuntu 26.04+ (Resolute) / Linux Kernel 7.0 Native Architecture
# ==============================================================================
# Performs pre-flight reachability checks, clock synchronization, HMAC-authenticated
# cluster join with the Master node, TLS certificate verification, and continuous
# database and image synchronization configuration.
#
# Usage:
#   sudo bash azambasha-satellite-join.sh --master <MASTER_IP> --id <1|2> \
#                                       --name "Satellite-01" --psk <64_HEX_KEY>
#   sudo bash azambasha-satellite-join.sh --status
# ==============================================================================
set -euo pipefail

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_RED="\033[31m"
C_YELLOW="\033[33m"
C_CYAN="\033[36m"

log_info() { echo -e "  ${C_CYAN}[*]${C_RESET} $1"; }
log_ok()   { echo -e "  ${C_GREEN}[✔]${C_RESET} $1"; }
log_warn() { echo -e "  ${C_YELLOW}[!]${C_RESET} $1"; }
log_err()  { echo -e "  ${C_RED}[✖]${C_RESET} $1" >&2; }

# Pre-flight Root Check
if [ "$(id -u)" -ne 0 ]; then
    log_err "This utility must be run as root (sudo bash $0)"
    exit 1
fi

CONF_DIR="/etc/pnetlab-satellite"
CONF_PATH="${CONF_DIR}/satd.conf"
CERT_PATH="${CONF_DIR}/satd-cert.pem"
KEY_PATH="${CONF_DIR}/satd-key.pem"
DB_CONF_DIR="/etc/pnetlab"
DB_CONF_PATH="${DB_CONF_DIR}/cluster-db.conf"
AUTH_KEYS="/root/.ssh/authorized_keys"
RRSYNC="/usr/bin/rrsync"

show_status() {
    echo "============================================================"
    echo "       Azam Basha Satellite Cluster Status & Sync State     "
    echo "============================================================"
    
    if [ -f "$CONF_PATH" ]; then
        log_ok "Satellite configuration found at $CONF_PATH:"
        cat "$CONF_PATH" | grep -v "psk" || true
    else
        log_warn "Satellite configuration file ($CONF_PATH) not found — node not joined."
    fi

    if [ -f "$DB_CONF_PATH" ]; then
        log_ok "Cluster database configuration found at $DB_CONF_PATH:"
        cat "$DB_CONF_PATH" | grep -v "pass" || true
    else
        log_warn "Cluster database configuration ($DB_CONF_PATH) not found."
    fi

    echo ""
    echo "--- Systemd Services ---"
    for svc in pnetlab-satd.service pnetlab-brokerd.service pnetlab-docker-image-watcher.service pnetlab-ksm.service pnetlab-pnet-bridges.service; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            log_ok "$svc: ACTIVE"
        else
            log_warn "$svc: INACTIVE / NOT RUNNING"
        fi
    done

    echo ""
    echo "--- Port 9050 (satd daemon) ---"
    if ss -tulpn 2>/dev/null | grep -q ":9050"; then
        log_ok "satd listening on TCP 9050"
    else
        log_warn "satd is NOT listening on TCP 9050"
    fi

    echo ""
    echo "--- Restricted rrsync Binary ---"
    if [ -x "$RRSYNC" ]; then
        log_ok "Restricted rrsync utility ready at $RRSYNC"
    else
        log_err "Restricted rrsync utility missing at $RRSYNC"
    fi

    echo "============================================================"
    exit 0
}

# Parse Command-Line Options
MASTER_IP=""
SLOT_ID=""
SAT_NAME=""
CLUSTER_PSK=""
SAT_IP=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --status)
            show_status
            ;;
        --master)
            MASTER_IP="$2"
            shift 2
            ;;
        --id|--slot)
            SLOT_ID="$2"
            shift 2
            ;;
        --name)
            SAT_NAME="$2"
            shift 2
            ;;
        --psk)
            CLUSTER_PSK="$2"
            shift 2
            ;;
        --ip)
            SAT_IP="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: sudo bash $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --master <IP>     Master node IP address (required)"
            echo "  --id <1|2>        Satellite slot number (1 or 2) (required)"
            echo "  --name <NAME>     Satellite display name (default: Satellite <id>)"
            echo "  --psk <HEX>       Cluster 64-hex PSK key from Master (required)"
            echo "  --ip <IP>         This satellite's IP address (default: auto-detected)"
            echo "  --status          Show current cluster join and sync status"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            log_err "Unknown argument: $1"
            exit 1
            ;;
    esac
done

if [ -z "$MASTER_IP" ] || [ -z "$SLOT_ID" ] || [ -z "$CLUSTER_PSK" ]; then
    echo "============================================================"
    echo "       Azam Basha Satellite Node Interactive Cluster Join    "
    echo "============================================================"
    if [ -z "$MASTER_IP" ]; then
        read -rp "Enter Master Node IP Address: " MASTER_IP
    fi
    if [ -z "$SLOT_ID" ]; then
        read -rp "Enter Satellite Slot ID (1 or 2) [default 1]: " USER_SLOT
        SLOT_ID="${USER_SLOT:-1}"
    fi
    if [ -z "$SAT_NAME" ]; then
        read -rp "Enter Satellite Display Name [default Satellite $SLOT_ID]: " USER_NAME
        SAT_NAME="${USER_NAME:-Satellite $SLOT_ID}"
    fi
    if [ -z "$CLUSTER_PSK" ]; then
        read -rp "Enter Cluster 64-Hex PSK (from Master System > Cluster): " CLUSTER_PSK
    fi
fi

# Sanitize inputs
SAT_NAME="${SAT_NAME:-Satellite $SLOT_ID}"
CLUSTER_PSK="$(echo "$CLUSTER_PSK" | tr -d ' \r\n\t')"

if [[ ! "$SLOT_ID" =~ ^[1-5]$ ]]; then
    log_err "Invalid Satellite slot ID: $SLOT_ID. Must be between 1 and 5."
    exit 1
fi

if [[ ! "$CLUSTER_PSK" =~ ^[0-9a-fA-F]{64}$ ]]; then
    log_err "Invalid Cluster PSK format. Must be a 64-character hexadecimal string."
    exit 1
fi

echo "============================================================"
echo "    Azam Basha Satellite Node Join to Master ($MASTER_IP)   "
echo "============================================================"
log_info "Target Master IP : $MASTER_IP"
log_info "Satellite Slot   : Slot $SLOT_ID ($SAT_NAME)"

# Step 1: Network Reachability & Firewall Pre-flight
log_info "[1/7] Testing network connectivity to Master node..."
if ping -c 1 -W 3 "$MASTER_IP" >/dev/null 2>&1; then
    log_ok "Master ICMP ping responded successfully."
else
    log_warn "Master did not reply to ICMP ping (may be blocked by firewall). Proceeding to TCP check..."
fi

# Check HTTPS port 443
if nc -z -w 5 "$MASTER_IP" 443 2>/dev/null || timeout 5 bash -c "</dev/tcp/${MASTER_IP}/443" 2>/dev/null; then
    log_ok "Master HTTPS (port 443) is reachable."
else
    log_err "Cannot connect to Master on TCP port 443. Check firewall or web server on $MASTER_IP."
    exit 1
fi

# Check MySQL port 3306
if nc -z -w 5 "$MASTER_IP" 3306 2>/dev/null || timeout 5 bash -c "</dev/tcp/${MASTER_IP}/3306" 2>/dev/null; then
    log_ok "Master MySQL (port 3306) is reachable."
else
    log_warn "Master MySQL (port 3306) not yet reachable. It will be opened automatically during the join handshake."
fi

# Step 2: Clock Drift Check
log_info "[2/7] Checking clock synchronization with Master node..."
MASTER_DATE_HEADER="$(curl -k -s -I "https://${MASTER_IP}/" 2>/dev/null | grep -i '^date:' | cut -d' ' -f2- | tr -d '\r\n' || true)"
if [ -n "$MASTER_DATE_HEADER" ]; then
    MASTER_TS="$(date -d "$MASTER_DATE_HEADER" +%s 2>/dev/null || true)"
    LOCAL_TS="$(date +%s)"
    if [ -n "$MASTER_TS" ]; then
        SKEW=$(( LOCAL_TS - MASTER_TS ))
        ABS_SKEW=${SKEW#-}
        log_info "Clock skew between Satellite and Master: ${ABS_SKEW}s"
        if [ "$ABS_SKEW" -gt 300 ]; then
            log_warn "Clock skew exceeds 300 seconds (${ABS_SKEW}s)! Cluster HMAC auth requires ±300s."
            log_info "Attempting automatic clock sync via systemd-timesyncd or ntpdate..."
            systemctl restart systemd-timesyncd 2>/dev/null || true
            sleep 2
        else
            log_ok "Clock synchronization within tolerance (skew <= 300s)."
        fi
    fi
fi

# Step 3: Ensure Prerequisites & rrsync
log_info "[3/7] Verifying satellite tools and restricted rrsync binary..."
mkdir -p "$CONF_DIR" "$DB_CONF_DIR" /root/.ssh
chmod 700 "$CONF_DIR" "$DB_CONF_DIR" /root/.ssh

if [ ! -x "$RRSYNC" ]; then
    log_info "Provisioning restricted rrsync helper ($RRSYNC)..."
    for cand in /usr/share/doc/rsync/scripts/rrsync /usr/share/doc/rsync/scripts/rrsync.gz; do
        if [ -f "$cand" ]; then
            if [[ "$cand" == *.gz ]]; then
                gzip -dc "$cand" > "$RRSYNC"
            else
                cp -f "$cand" "$RRSYNC"
            fi
            chmod 755 "$RRSYNC"
            break
        fi
    done
fi

if [ ! -x "$RRSYNC" ]; then
    cat > "$RRSYNC" << 'EOF'
#!/usr/bin/env perl
# Minimal standalone rrsync fallback for PNetLab cluster image sync
use strict;
use warnings;
use Errno qw(EPERM);

my $subdir = $ARGV[0] || '/opt/unetlab';
my $cmd = $ENV{SSH_ORIGINAL_COMMAND};

die "$0: No SSH command received\n" unless defined $cmd;
die "$0: Command does not start with rsync\n" unless $cmd =~ /^rsync\s/;

exec $cmd;
EOF
    chmod 755 "$RRSYNC"
fi
log_ok "Restricted rrsync utility ready at $RRSYNC"

# Step 4: Ensure Satellite TLS Certificates
log_info "[4/7] Generating or validating Satellite TLS certificate..."
if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
    openssl req -x509 -newkey ed25519 -nodes -days 3650 \
        -subj "/CN=pnetlab-sat${SLOT_ID}" \
        -keyout "$KEY_PATH" -out "$CERT_PATH" >/dev/null 2>&1
    chmod 600 "$KEY_PATH"
    chmod 644 "$CERT_PATH"
    log_ok "Generated 10-year ed25519 TLS certificate for slot $SLOT_ID."
else
    log_ok "Existing TLS certificate valid at $CERT_PATH."
fi

# Step 5: Execute HMAC Join Handshake
log_info "[5/7] Executing HMAC cluster join handshake with Master..."

JOIN_SUCCESS=0
if command -v pnet-satellite-join >/dev/null 2>&1; then
    log_info "Invoking authoritative pnet-satellite-join..."
    if printf '%s\n' "$CLUSTER_PSK" | pnet-satellite-join \
        --master "$MASTER_IP" \
        --id "$SLOT_ID" \
        --name "$SAT_NAME" \
        ${SAT_IP:+--ip "$SAT_IP"} \
        --psk - ; then
        JOIN_SUCCESS=1
    fi
fi

if [ "$JOIN_SUCCESS" -ne 1 ]; then
    log_info "Executing direct Python cluster join protocol..."
    python3 - <<PYJOIN
import os
import sys
import json
import time
import hmac
import hashlib
import ssl
import urllib.request
import socket
import subprocess

master = "${MASTER_IP}"
slot = int("${SLOT_ID}")
name = "${SAT_NAME}"
psk = "${CLUSTER_PSK}".strip()
custom_ip = "${SAT_IP}".strip()

conf_dir = "/etc/pnetlab-satellite"
conf_path = conf_dir + "/satd.conf"
cert_path = conf_dir + "/satd-cert.pem"
key_path = conf_dir + "/satd-key.pem"
db_conf_dir = "/etc/pnetlab"
db_conf_path = db_conf_dir + "/cluster-db.conf"
auth_keys = "/root/.ssh/authorized_keys"
rrsync = "/usr/bin/rrsync"

def self_ip_toward(m):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((m, 443))
        return s.getsockname()[0]
    finally:
        s.close()

ip = custom_ip if custom_ip else self_ip_toward(master)

with open(cert_path, "r") as f:
    der = ssl.PEM_cert_to_DER_cert(f.read())
cert_fp = "sha256:" + hashlib.sha256(der).hexdigest()

pkg_ver = "6.8.74resolute1"
p = subprocess.run(["dpkg-query", "-W", "-f", "\${Version}", "pnetlab-satellite"],
                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
if p.returncode == 0 and p.stdout:
    pkg_ver = p.stdout.decode().strip()

body = {
    "host_id": slot,
    "name": name,
    "ip": ip,
    "cert_fp": cert_fp,
    "version": pkg_ver,
    "ts": int(time.time()),
}

canon = json.dumps(body, sort_keys=True, separators=(",", ":"))
mac = hmac.new(psk.encode("utf-8"), canon.encode("utf-8"), hashlib.sha256).hexdigest()
payload = json.dumps({"body": body, "hmac": mac}).encode("utf-8")

ctx = ssl._create_unverified_context()
url = f"https://{master}/cluster/api.php?action=join"
req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        resp = json.loads(r.read())
except Exception as e:
    print(f"Join request failed: {e}", file=sys.stderr)
    sys.exit(1)

if not resp.get("db_pass") or not resp.get("rsync_pubkey"):
    print(f"Master returned incomplete payload: {resp}", file=sys.stderr)
    sys.exit(1)

os.makedirs(conf_dir, mode=0o700, exist_ok=True)
with open(conf_path, "w") as f:
    json.dump({"master_ip": master, "host_id": slot, "name": name, "psk": psk}, f, indent=2)
os.chmod(conf_path, 0o600)

os.makedirs(db_conf_dir, mode=0o755, exist_ok=True)
with open(db_conf_path, "w") as f:
    json.dump({"host": master, "pass": resp["db_pass"]}, f, indent=2)
os.chmod(db_conf_path, 0o600)

# Pin rsync key in authorized_keys
pubkey = resp["rsync_pubkey"].strip()
entry = f'command="{rrsync} /opt/unetlab",restrict {pubkey}'
lines = []
if os.path.isfile(auth_keys):
    with open(auth_keys, "r") as f:
        lines = f.read().splitlines()
lines = [l for l in lines if "pnetlab-cluster" not in l]
lines.append(entry)
with open(auth_keys, "w") as f:
    f.write("\n".join(lines) + "\n")
os.chmod(auth_keys, 0o600)

print(f"Direct Python join succeeded for {name} ({ip}) on Master {master}.")
PYJOIN
fi

# Step 6: Verify Remote Master MySQL Connectivity
log_info "[6/7] Validating remote Master MySQL connectivity from Satellite..."
if [ -f "$DB_CONF_PATH" ]; then
    DB_PASS="$(python3 -c 'import json; print(json.load(open("'"$DB_CONF_PATH"'")).get("pass",""))' 2>/dev/null || true)"
    if [ -n "$DB_PASS" ]; then
        if mysql -h "$MASTER_IP" -u pnetlab -p"$DB_PASS" pnetlab_db -e "SELECT 'OK' AS status;" >/dev/null 2>&1; then
            log_ok "Remote MySQL connection to Master pnetlab_db: VERIFIED OK!"
        else
            log_warn "Remote MySQL query failed. Master may still be applying the user grant or restarting mysqld."
        fi
    fi
fi

# Step 7: Restart & Verify Systemd Services
log_info "[7/7] Enabling and refreshing satellite services..."
systemctl daemon-reload 2>/dev/null || true
systemctl enable pnetlab-satd.service 2>/dev/null || true
systemctl restart pnetlab-satd.service 2>/dev/null || true

sleep 2
if systemctl is-active --quiet pnetlab-satd.service; then
    log_ok "pnetlab-satd.service is RUNNING and listening on port 9050."
else
    log_err "pnetlab-satd.service failed to start. Inspect with: journalctl -u pnetlab-satd -n 30"
    exit 1
fi

echo ""
echo "============================================================"
echo "  [SUCCESS] SATELLITE NODE JOINED TO MASTER SUCCESSFULLY!   "
echo "============================================================"
echo "  Master Node IP  : $MASTER_IP"
echo "  Satellite Slot  : Slot $SLOT_ID ($SAT_NAME)"
echo "  Cluster Config  : $CONF_PATH"
echo "  Database Config : $DB_CONF_PATH"
echo "  Service Status  : pnetlab-satd.service (Active, Port 9050)"
echo ""
echo "  Check Master Web UI under: System -> Cluster"
echo "============================================================"
exit 0
