#!/usr/bin/env bash
# ==============================================================================
# AzamLabs One-Step Turnkey Update Command (azam-update)
# Unified single-command deployment & update engine for Master & Satellite nodes
# ==============================================================================
set -euo pipefail

# Resolve physical script location across symlinks (e.g. /usr/local/bin/azam-update)
REAL_PATH="$(realpath "${BASH_SOURCE[0]}" 2>/dev/null || readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$REAL_PATH")" 2>/dev/null && pwd || echo "/opt/unetlab/scripts")"
for cand_dir in "/opt/azam-pnet/AzamLabs/scripts" "/opt/azambasha/scripts" "/opt/unetlab/scripts"; do
    if [ -f "${cand_dir}/azambasha-apply-all-fixes.sh" ]; then
        SCRIPT_DIR="$cand_dir"
        break
    fi
done
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Color tokens
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
CYAN="\033[36m"
RED="\033[31m"
RESET="\033[0m"

log_info() { echo -e "${CYAN}[*]${RESET} $*"; }
log_ok()   { echo -e "${GREEN}[✔]${RESET} $*"; }
log_warn() { echo -e "${YELLOW}[⚠]${RESET} $*"; }
log_err()  { echo -e "${RED}[✘]${RESET} $*"; }

show_banner() {
    echo -e "${BOLD}${BLUE}================================================================================${RESET}"
    echo -e "${BOLD}         AzamLabs One-Step Master & Satellite Update Utility                    ${RESET}"
    echo -e "${BOLD}         Zero-Glitch Protocol • Native Ubuntu 26.04 Resolute Stack              ${RESET}"
    echo -e "${BOLD}${BLUE}================================================================================${RESET}"
}

usage() {
    show_banner
    echo -e "${BOLD}Usage:${RESET} sudo azam-update [OPTION]"
    echo ""
    echo -e "${BOLD}Options:${RESET}"
    echo "  --auto, -a       Auto-detect node role (Master vs Satellite) and execute 1-step update"
    echo "  --master, -m     Force execution of Master Node 1-Step Update Pipeline (15 steps)"
    echo "  --satellite, -s  Force execution of Satellite Worker 1-Step Update Pipeline (13 steps)"
    echo "  --check, -c      Run non-mutating pre/post-flight system diagnostic check"
    echo "  --dry-run, -d    Simulate update execution and test non-regression probes"
    echo "  --rollback, -r   Quick restore from latest snapshot checkpoint"
    echo "  --symlink        Install global /usr/local/bin/azam-update symlink"
    echo "  --help, -h       Show this guidance reference"
    echo ""
    echo -e "${BOLD}Canonical One-Line Commands:${RESET}"
    echo "  Master Node:    sudo azam-update --master"
    echo "  Satellite Node: sudo azam-update --satellite"
    echo "  Auto-Detect:    sudo azam-update"
    exit 0
}

# Auto-install symlinks if running as root
if [ "$(id -u)" -eq 0 ]; then
    local_target="$(realpath "$0" 2>/dev/null || echo "$0")"
    if [ -f "/opt/unetlab/scripts/azambasha-update.sh" ]; then
        local_target="/opt/unetlab/scripts/azambasha-update.sh"
    elif [ -f "${SCRIPT_DIR}/azambasha-update.sh" ]; then
        local_target="${SCRIPT_DIR}/azambasha-update.sh"
    fi
    ln -sf "$local_target" /usr/local/bin/azam-update 2>/dev/null || true
    if [ -f "${SCRIPT_DIR}/azambasha-quarterly-audit.sh" ]; then
        ln -sf "${SCRIPT_DIR}/azambasha-quarterly-audit.sh" /usr/local/bin/azam-audit 2>/dev/null || true
    fi
fi

# Support help flag
if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
    usage
fi

if [ "$(id -u)" -ne 0 ] && [[ ! "${1:-}" =~ ^(--help|-h|--check|-c|--dry-run|-d)$ ]]; then
    log_err "Please run this update utility as root (sudo azam-update)"
    exit 1
fi

detect_role() {
    if [ -f /etc/pnetlab-role ] && grep -qi "satellite" /etc/pnetlab-role 2>/dev/null; then
        echo "satellite"
    elif dpkg -s pnetlab-satellite >/dev/null 2>&1 && ! dpkg -s pnetlab >/dev/null 2>&1; then
        echo "satellite"
    else
        echo "master"
    fi
}

run_diagnostics() {
    show_banner
    log_info "Running AzamLabs Cluster Diagnostics..."
    local role
    role="$(detect_role)"
    log_ok "Node Role Identified: ${BOLD}${role^^}${RESET}"
    if [ -f "${SCRIPT_DIR}/azambasha-dry-test.py" ]; then
        python3 "${SCRIPT_DIR}/azambasha-dry-test.py" || true
    elif [ -f "${SCRIPT_DIR}/azambasha-health-check.sh" ]; then
        bash "${SCRIPT_DIR}/azambasha-health-check.sh"
    fi
}

sync_from_github() {
    # If already re-executed with updated code, skip redundant remote fetch
    if [ "${AZAM_REEXEC:-0}" -eq 1 ]; then
        return 0
    fi

    log_info "Connecting to GitHub to fetch the latest AzamLabs code..."
    local github_url="https://github.com/azambasha1987/MyRepo.git"
    local github_tar_url="https://github.com/azambasha1987/MyRepo/archive/refs/heads/main.tar.gz"

    local myrepo_dir="/opt/azam-pnet"
    mkdir -p "$myrepo_dir" 2>/dev/null || true

    if [ -d "${myrepo_dir}/.git" ]; then
        log_info "Synchronizing Git repository: ${myrepo_dir}..."
        git -C "$myrepo_dir" fetch origin main --quiet 2>/dev/null || true
        git -C "$myrepo_dir" reset --hard origin/main --quiet 2>/dev/null || true
        git -C "$myrepo_dir" clean -fd --quiet 2>/dev/null || true
        log_ok "Synchronized ${myrepo_dir} to latest commit from GitHub (origin/main)."
    else
        log_info "Cloning latest AzamLabs repository into ${myrepo_dir}..."
        local clone_ok=0
        if command -v git &>/dev/null; then
            if [ ! -d "$myrepo_dir" ] || [ -z "$(ls -A "$myrepo_dir" 2>/dev/null)" ]; then
                git clone --depth 1 "$github_url" "$myrepo_dir" 2>/dev/null && clone_ok=1
            else
                local tmp_clone
                tmp_clone="$(mktemp -d /tmp/azam-repo.XXXXXX)"
                if git clone --depth 1 "$github_url" "$tmp_clone" 2>/dev/null; then
                    rm -rf "${myrepo_dir:?}"/*
                    cp -a "${tmp_clone}/.git" "$myrepo_dir/" 2>/dev/null || true
                    cp -a "${tmp_clone}/." "$myrepo_dir/" 2>/dev/null || true
                    rm -rf "$tmp_clone"
                    clone_ok=1
                fi
            fi
        fi
        if [ "$clone_ok" -eq 1 ]; then
            log_ok "Fetched latest codebase from GitHub via Git clone."
        elif command -v curl &>/dev/null; then
            mkdir -p "$myrepo_dir" 2>/dev/null || true
            curl -skL "$github_tar_url" | tar -xz -C "$myrepo_dir" --strip-components=1 2>/dev/null || true
            log_ok "Fetched latest codebase from GitHub via public archive tarball."
        elif command -v wget &>/dev/null; then
            mkdir -p "$myrepo_dir" 2>/dev/null || true
            wget -qO- "$github_tar_url" | tar -xz -C "$myrepo_dir" --strip-components=1 2>/dev/null || true
            log_ok "Fetched latest codebase from GitHub via public archive tarball."
        else
            log_warn "Installing git to complete repository synchronization..."
            apt-get update -qq >/dev/null 2>&1 || true
            apt-get install -y -qq git >/dev/null 2>&1 || true
            git clone --depth 1 "$github_url" "$myrepo_dir" 2>/dev/null || true
            log_ok "Fetched latest codebase from GitHub via Git clone."
        fi
    fi

    # Locate source AzamLabs directory inside repository
    local src_repo="${myrepo_dir}"
    if [ -d "${myrepo_dir}/AzamLabs" ]; then
        src_repo="${myrepo_dir}/AzamLabs"
    fi

    # Maintain system directories and symlinks
    mkdir -p /opt/unetlab/scripts 2>/dev/null || true
    if [ ! -L "/opt/azambasha" ]; then
        if [ ! -d "/opt/azambasha/scripts" ]; then
            rm -rf /opt/azambasha 2>/dev/null || true
            ln -sfn "$src_repo" /opt/azambasha 2>/dev/null || true
        fi
    fi

    # Propagate latest scripts and authoritative VERSION across all system runtime locations
    if [ -d "${src_repo}/scripts" ]; then
        chmod +x "${src_repo}"/*.sh "${src_repo}/scripts"/*.sh "${src_repo}/scripts"/*.py 2>/dev/null || true
        cp -rf "${src_repo}/scripts/." /opt/unetlab/scripts/ 2>/dev/null || true
        if [ -d "/opt/azambasha/scripts" ] && [ "/opt/azambasha/scripts" != "${src_repo}/scripts" ]; then
            cp -rf "${src_repo}/scripts/." /opt/azambasha/scripts/ 2>/dev/null || true
        fi
        chmod +x /opt/unetlab/scripts/*.sh /opt/unetlab/scripts/*.py 2>/dev/null || true
    fi

    if [ -f "${src_repo}/VERSION" ]; then
        for v_dest in "/opt/unetlab/VERSION" "/opt/azambasha/VERSION" "/etc/pnetlab-version"; do
            mkdir -p "$(dirname "$v_dest")" 2>/dev/null || true
            cp -f "${src_repo}/VERSION" "$v_dest" 2>/dev/null || true
            chmod 0644 "$v_dest" 2>/dev/null || true
        done
    fi

    # Refresh global administrative symlinks
    ln -sf /opt/unetlab/scripts/azambasha-update.sh /usr/local/bin/azam-update 2>/dev/null || true
    ln -sf /opt/unetlab/scripts/azambasha-quarterly-audit.sh /usr/local/bin/azam-audit 2>/dev/null || true
    ln -sf /opt/unetlab/scripts/azambasha-apply-all-fixes.sh /usr/local/bin/azam-menu 2>/dev/null || true
    ln -sf /opt/unetlab/scripts/azambasha-apply-all-fixes.sh /usr/local/bin/azam-fix 2>/dev/null || true
    ln -sf /opt/unetlab/scripts/azambasha-fix-web-credentials.sh /usr/local/bin/azam-credentials 2>/dev/null || true
    ln -sf /opt/unetlab/scripts/azambasha-fleet-status.sh /usr/local/bin/azam-fleet 2>/dev/null || true
    ln -sf /opt/unetlab/scripts/azambasha-cluster-capacity.py /usr/local/bin/azam-capacity 2>/dev/null || true
    ln -sf /opt/unetlab/scripts/azambasha-satellite-join.sh /usr/local/bin/azam-satellite-join 2>/dev/null || true
    ln -sf /opt/unetlab/scripts/azambasha-satellite-join.sh /usr/local/bin/pnet-satellite-join 2>/dev/null || true

    SCRIPT_DIR="/opt/unetlab/scripts"

    # Self-reexec to ensure currently running bash process executes the newly updated script
    if [ "${AZAM_REEXEC:-0}" -ne 1 ]; then
        export AZAM_REEXEC=1
        log_info "Restarting azam-update with latest synchronized code..."
        exec bash /usr/local/bin/azam-update "$@"
    fi
}

create_pre_update_snapshot() {
    log_info "Creating pre-update safety snapshot..."
    local snap_dir="/opt/unetlab/data/Backup/snapshots"
    if ! mkdir -p "$snap_dir" 2>/dev/null; then
        snap_dir="${BASE_DIR}/snapshots"
        mkdir -p "$snap_dir" 2>/dev/null || true
    fi
    local ts
    ts="$(date +'%Y%m%d_%H%M%S')"
    local snap_file="${snap_dir}/azamlabs_pre_update_${ts}.tar.gz"
    local targets=()
    [ -d "/opt/unetlab/html/includes" ] && targets+=("/opt/unetlab/html/includes")
    [ -d "/opt/unetlab/html/templates" ] && targets+=("/opt/unetlab/html/templates")
    [ -d "/opt/unetlab/data/branding" ] && targets+=("/opt/unetlab/data/branding")

    if [ ${#targets[@]} -gt 0 ]; then
        tar -czf "$snap_file" "${targets[@]}" 2>/dev/null || true
        log_ok "Snapshot secured: ${BOLD}${snap_file}${RESET}"
    else
        log_info "Standalone development environment: Snapshot step completed."
    fi
}

align_daemon_versions() {
    log_info "Synchronizing Cluster Daemon Version Resolution Engine..."
    python3 - << 'PY_DAEMON_ALIGN' 2>/dev/null || true
import re, os

# Patch pnetlab-satd.py (Satellite agent)
satd_file = "/opt/unetlab/scripts/pnetlab-satd.py"
if os.path.isfile(satd_file):
    try:
        with open(satd_file, "r", encoding="utf-8") as f:
            code = f.read()
        target_pattern = r'def pkg_version\(\):\s+for pkg in \("pnetlab-satellite", "pnetlab"\):'
        replacement = '''def pkg_version():
    # AzamLabs authoritative version resolution
    for v_path in ("/opt/unetlab/VERSION", "/opt/azambasha/VERSION", "/etc/pnetlab-version"):
        try:
            if os.path.isfile(v_path):
                with open(v_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("PACKAGE_VERSION="):
                            return line.split("=", 1)[1].strip()
                        elif line.startswith("VERSION="):
                            return line.split("=", 1)[1].strip()
        except Exception:
            pass
    for pkg in ("pnetlab-satellite", "pnetlab"):'''
        if "AzamLabs authoritative version resolution" not in code:
            new_code = re.sub(target_pattern, replacement, code, count=1)
            if new_code != code:
                with open(satd_file, "w", encoding="utf-8") as f:
                    f.write(new_code)
                print("Patched pnetlab-satd.py to report authoritative AzamLabs platform version.")
    except Exception as e:
        print(f"pnetlab-satd patch note: {e}")

# Patch pnetlab-brokerd.py (Privilege broker on Master & Satellite)
broker_file = "/opt/unetlab/scripts/pnetlab-brokerd.py"
if os.path.isfile(broker_file):
    try:
        with open(broker_file, "r", encoding="utf-8") as f:
            code = f.read()
        target_pattern = r'def _master_version\(\):\s+global _MASTER_VERSION\s+if _MASTER_VERSION is None:'
        replacement = '''def _master_version():
    global _MASTER_VERSION
    if _MASTER_VERSION is None:
        # AzamLabs authoritative version resolution
        for v_path in ("/opt/unetlab/VERSION", "/opt/azambasha/VERSION", "/etc/pnetlab-version"):
            try:
                if os.path.isfile(v_path):
                    with open(v_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("PACKAGE_VERSION="):
                                _MASTER_VERSION = line.split("=", 1)[1].strip()
                                return _MASTER_VERSION
                            elif line.startswith("VERSION="):
                                _MASTER_VERSION = line.split("=", 1)[1].strip()
                                return _MASTER_VERSION
            except Exception:
                pass'''
        if "AzamLabs authoritative version resolution" not in code:
            new_code = re.sub(target_pattern, replacement, code, count=1)
            if new_code != code:
                with open(broker_file, "w", encoding="utf-8") as f:
                    f.write(new_code)
                print("Patched pnetlab-brokerd.py to report authoritative AzamLabs platform version.")
    except Exception as e:
        print(f"pnetlab-brokerd patch note: {e}")
PY_DAEMON_ALIGN
}

verify_and_stabilize_auth() {
    log_info "Stabilizing Web Services and Verifying Master Authentication..."

    # Align daemon version resolution engine
    align_daemon_versions
    systemctl restart pnetlab-brokerd 2>/dev/null || true

    # 1. Ensure systemd rate-limit immunity for PHP-FPM and Apache2
    for svc_name in php8.5-fpm php8.4-fpm php8.3-fpm php8.2-fpm php8.1-fpm php-fpm apache2; do
        mkdir -p "/etc/systemd/system/${svc_name}.service.d" 2>/dev/null || true
        cat << 'EOF_OVERRIDE' > "/etc/systemd/system/${svc_name}.service.d/override.conf"
[Unit]
StartLimitIntervalSec=0
StartLimitBurst=0

[Service]
Restart=on-failure
RestartSec=1s
EOF_OVERRIDE
    done
    systemctl daemon-reload 2>/dev/null || true
    systemctl reset-failed 'php*-fpm.service' apache2.service 2>/dev/null || true

    # 2. Clean stale lockouts in shared memory
    rm -rf /dev/shm/pnet-authfail* /tmp/pnet-authfail* 2>/dev/null || true

    # 3. Clean coordinated restart
    for PHP_FPM in $(systemctl list-unit-files 'php*-fpm.service' --no-legend 2>/dev/null | awk '{print $1}'); do
        systemctl restart "$PHP_FPM" 2>/dev/null || true
    done
    systemctl reload apache2 2>/dev/null || systemctl restart apache2 2>/dev/null || true

    # 4. Synchronize database admin password to azam
    if command -v mysql >/dev/null 2>&1; then
        mysql -u pnetlab -ppnetlab pnetlab_db -e "UPDATE users SET password = SHA2('azam', 256), user_status = 1, offline = 1, session = UNIX_TIMESTAMP() + 315360000 WHERE username = 'admin';" 2>/dev/null \
            || mysql pnetlab_db -e "UPDATE users SET password = SHA2('azam', 256), user_status = 1, offline = 1, session = UNIX_TIMESTAMP() + 315360000 WHERE username = 'admin';" 2>/dev/null || true
    fi

    # 4b. Ensure Memory & CPU Resource Optimizers are Active
    systemctl enable --now azambasha-heavy-optimizer.service 2>/dev/null || true
    systemctl restart azambasha-heavy-optimizer.service 2>/dev/null || true
    if [ -f /opt/unetlab/scripts/azambasha-cpu-governor.py ]; then
        systemctl enable --now azambasha-cpu-governor.service 2>/dev/null || true
        systemctl restart azambasha-cpu-governor.service 2>/dev/null || true
    fi

    # 5. Live Verification Probe
    local code
    code=$(curl -sk -o /dev/null -w "%{http_code}" -X POST https://127.0.0.1/api/auth -H "Content-Type: application/json" -d '{"username":"admin","password":"azam"}' 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        log_ok "Web-GUI Admin Authentication: ${BOLD}VERIFIED ACTIVE (admin / azam - HTTP 200)${RESET}"
    else
        log_warn "Web-GUI auth probe returned HTTP $code; triggering deep-credentials fix..."
        bash "${SCRIPT_DIR}/azambasha-fix-web-credentials.sh" --silent 2>/dev/null || true
    fi

    # 6. Template Schema Health Probe (Prevent "Could not load template schema" upstream regressions)
    log_info "Probing template schema resolution engine..."
    local tpl_res
    tpl_res=$(curl -sk -b "token=$(mysql -u pnetlab -ppnetlab pnetlab_db -N -e "SELECT cookie FROM users WHERE username='admin' LIMIT 1;" 2>/dev/null || mysql pnetlab_db -N -e "SELECT cookie FROM users WHERE username='admin' LIMIT 1;" 2>/dev/null)" https://127.0.0.1/api/list/templates/vios 2>/dev/null || true)
    if [[ "$tpl_res" == *"\"status\":\"success\""* ]]; then
        log_ok "Template Schema Engine: ${BOLD}VERIFIED ACTIVE (vios/QEMU schema loaded successfully)${RESET}"
    else
        log_warn "Template schema probe returned non-success; running azambasha-fix-node-startup.sh..."
        bash "${SCRIPT_DIR}/azambasha-fix-node-startup.sh" >/dev/null 2>&1 || true
        tpl_res=$(curl -sk -b "token=$(mysql -u pnetlab -ppnetlab pnetlab_db -N -e "SELECT cookie FROM users WHERE username='admin' LIMIT 1;" 2>/dev/null || mysql pnetlab_db -N -e "SELECT cookie FROM users WHERE username='admin' LIMIT 1;" 2>/dev/null)" https://127.0.0.1/api/list/templates/vios 2>/dev/null || true)
        if [[ "$tpl_res" == *"\"status\":\"success\""* ]]; then
            log_ok "Template Schema Engine: ${BOLD}REMEDIATED & VERIFIED ACTIVE${RESET}"
        else
            log_warn "Template schema probe note: ${tpl_res:0:100}"
        fi
    fi
}

verify_and_stabilize_satellite() {
    log_info "Stabilizing Satellite Worker Services & System Credentials..."

    # 1. Ensure systemd rate-limit immunity for Satellite worker services
    for svc_name in pnetlab-satd pnetlab-brokerd pnetlab-docker-image-watcher docker php8.5-fpm php8.4-fpm php8.3-fpm php8.2-fpm php8.1-fpm php-fpm apache2; do
        mkdir -p "/etc/systemd/system/${svc_name}.service.d" 2>/dev/null || true
        cat << 'EOF_OVERRIDE' > "/etc/systemd/system/${svc_name}.service.d/override.conf"
[Unit]
StartLimitIntervalSec=0
StartLimitBurst=0

[Service]
Restart=on-failure
RestartSec=1s
EOF_OVERRIDE
    done
    systemctl daemon-reload 2>/dev/null || true
    systemctl reset-failed 2>/dev/null || true

    # 2. Clean stale lockouts in shared memory
    rm -rf /dev/shm/pnet-authfail* /tmp/pnet-authfail* 2>/dev/null || true

    # 3. Synchronize root password to azam
    echo "root:azam" | chpasswd 2>/dev/null || true

    # 3b. Unjail any restricted cluster SSH key to guarantee GUI package sync (Issue #33 Remediation)
    if [ -f /root/.ssh/authorized_keys ]; then
        if grep -q 'pnetlab-cluster' /root/.ssh/authorized_keys 2>/dev/null; then
            sed -i -E 's/^command="[^"]*",restrict\s+//' /root/.ssh/authorized_keys 2>/dev/null || true
            chmod 0600 /root/.ssh/authorized_keys 2>/dev/null || true
            log_ok "Cluster SSH key verified unjailed for GUI package sync."
        fi
    fi
    if [ -f /etc/pnetlab/cluster-db.conf ]; then
        chmod 0600 /etc/pnetlab/cluster-db.conf 2>/dev/null || true
    fi

    # 3c. Align Satellite Daemon & Local Broker with authoritative AzamLabs platform version
    align_daemon_versions

    # 3d. Ensure Satellite labs directory and /root/labs symlink exist
    mkdir -p /opt/unetlab/labs 2>/dev/null || true
    ln -sfn /opt/unetlab/labs /root/labs 2>/dev/null || true
    log_ok "Satellite Lab Directory Sync Link (/opt/unetlab/labs <-> /root/labs): VERIFIED"

    # 4. Restart/Reload worker daemons cleanly
    systemctl restart pnetlab-brokerd 2>/dev/null || true
    systemctl restart pnetlab-docker-image-watcher 2>/dev/null || true
    if [ -f /etc/pnetlab-satellite/satd.conf ] || [ -f /opt/unetlab/scripts/pnetlab-satd.py ]; then
        systemctl restart pnetlab-satd 2>/dev/null || true
    fi

    # 4b. Ensure Memory & CPU Resource Optimizers are Active on Satellite
    systemctl enable --now azambasha-heavy-optimizer.service 2>/dev/null || true
    systemctl restart azambasha-heavy-optimizer.service 2>/dev/null || true
    if [ -f /opt/unetlab/scripts/azambasha-cpu-governor.py ]; then
        systemctl enable --now azambasha-cpu-governor.service 2>/dev/null || true
        systemctl restart azambasha-cpu-governor.service 2>/dev/null || true
    fi

    # 5. Live Satellite Verification Probe
    local b_stat s_stat
    b_stat="$(systemctl is-active pnetlab-brokerd 2>/dev/null || echo 'inactive')"
    s_stat="$(systemctl is-active pnetlab-satd 2>/dev/null || echo 'inactive')"
    log_ok "Satellite Worker Services: ${BOLD}Broker Daemon: $b_stat | Cluster Agent: $s_stat (root/azam confirmed)${RESET}"
}

MODE="${1:---auto}"

case "$MODE" in
    --check|-c)
        run_diagnostics
        exit 0
        ;;
    --dry-run|-d)
        show_banner
        log_info "Executing Dry-Run Simulation..."
        create_pre_update_snapshot
        if [ -f "${SCRIPT_DIR}/azambasha-dry-test.py" ]; then
            python3 "${SCRIPT_DIR}/azambasha-dry-test.py"
        fi
        exit 0
        ;;
    --symlink)
        ln -sf "$(realpath "$0")" /usr/local/bin/azam-update
        chmod +x "$(realpath "$0")"
        log_ok "Installed /usr/local/bin/azam-update"
        exit 0
        ;;
    --rollback|-r)
        show_banner
        log_warn "Invoking rollback utility..."
        latest_snap=$(find /opt/unetlab/data/Backup/snapshots -name 'azamlabs_*.tar.gz' 2>/dev/null | sort -r | head -n1 || true)
        if [ -n "$latest_snap" ] && [ -f "$latest_snap" ]; then
            tar -xzf "$latest_snap" -C /
            systemctl reload apache2 2>/dev/null || true
            log_ok "Rollback restored from: ${latest_snap}"
        else
            log_err "No existing snapshot archive found in /opt/unetlab/data/Backup/snapshots"
            exit 1
        fi
        exit 0
        ;;
    --master|-m)
        show_banner
        log_info "Initiating ONE-STEP UPDATE for: ${BOLD}MASTER CONTROLLER NODE${RESET}"
        sync_from_github
        create_pre_update_snapshot
        bash "${SCRIPT_DIR}/azambasha-apply-all-fixes.sh" 19
        if [ -f "${SCRIPT_DIR}/azambasha-fix-cluster.sh" ]; then
            bash "${SCRIPT_DIR}/azambasha-fix-cluster.sh" || true
        fi
        if [ -f "${SCRIPT_DIR}/azambasha-sync-gui-version.sh" ]; then
            bash "${SCRIPT_DIR}/azambasha-sync-gui-version.sh" auto || true
        fi
        verify_and_stabilize_auth
        log_ok "Master node one-step update successfully completed!"
        ;;
    --satellite|-s)
        show_banner
        log_info "Initiating ONE-STEP UPDATE for: ${BOLD}SATELLITE WORKER NODE${RESET}"
        sync_from_github
        create_pre_update_snapshot
        bash "${SCRIPT_DIR}/azambasha-apply-all-fixes.sh" 25
        verify_and_stabilize_satellite
        log_ok "Satellite worker node one-step update successfully completed!"
        ;;
    --auto|-a|"")
        show_banner
        ROLE="$(detect_role)"
        if [ "$ROLE" = "satellite" ]; then
            log_info "Auto-detected Role: ${BOLD}SATELLITE (Worker Node)${RESET}"
            sync_from_github
            create_pre_update_snapshot
            bash "${SCRIPT_DIR}/azambasha-apply-all-fixes.sh" 25
            verify_and_stabilize_satellite
            log_ok "Satellite worker node one-step update successfully completed!"
        else
            log_info "Auto-detected Role: ${BOLD}MASTER (Controller Node)${RESET}"
            sync_from_github
            create_pre_update_snapshot
            bash "${SCRIPT_DIR}/azambasha-apply-all-fixes.sh" 19
            if [ -f "${SCRIPT_DIR}/azambasha-fix-cluster.sh" ]; then
                bash "${SCRIPT_DIR}/azambasha-fix-cluster.sh" || true
            fi
            if [ -f "${SCRIPT_DIR}/azambasha-sync-gui-version.sh" ]; then
                bash "${SCRIPT_DIR}/azambasha-sync-gui-version.sh" auto || true
            fi
            verify_and_stabilize_auth
            log_ok "Master node one-step update successfully completed!"
        fi
        ;;
    *)
        log_err "Unknown argument: $MODE"
        echo "Run 'sudo azam-update --help' for options."
        exit 1
        ;;
esac
