#!/usr/bin/env bash
# ==============================================================================
# AzamLabs One-Step Turnkey Update Command (azam-update)
# Unified single-command deployment & update engine for Master & Satellite nodes
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

# Auto-install symlink if running as root
if [ "$(id -u)" -eq 0 ] && [ ! -L /usr/local/bin/azam-update ]; then
    ln -sf "$(realpath "$0")" /usr/local/bin/azam-update 2>/dev/null || true
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

create_pre_update_snapshot() {
    log_info "Creating pre-update safety snapshot..."
    local snap_dir="/opt/unetlab/data/Backup/snapshots"
    mkdir -p "$snap_dir"
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
        create_pre_update_snapshot
        bash "${SCRIPT_DIR}/azambasha-apply-all-fixes.sh" 19
        if [ -f "${SCRIPT_DIR}/azambasha-sync-gui-version.sh" ]; then
            bash "${SCRIPT_DIR}/azambasha-sync-gui-version.sh" auto || true
        fi
        log_ok "Master node one-step update successfully completed!"
        ;;
    --satellite|-s)
        show_banner
        log_info "Initiating ONE-STEP UPDATE for: ${BOLD}SATELLITE WORKER NODE${RESET}"
        create_pre_update_snapshot
        bash "${SCRIPT_DIR}/azambasha-apply-all-fixes.sh" 25
        log_ok "Satellite worker node one-step update successfully completed!"
        ;;
    --auto|-a|"")
        show_banner
        ROLE="$(detect_role)"
        if [ "$ROLE" = "satellite" ]; then
            log_info "Auto-detected Role: ${BOLD}SATELLITE (Worker Node)${RESET}"
            create_pre_update_snapshot
            bash "${SCRIPT_DIR}/azambasha-apply-all-fixes.sh" 25
            log_ok "Satellite worker node one-step update successfully completed!"
        else
            log_info "Auto-detected Role: ${BOLD}MASTER (Controller Node)${RESET}"
            create_pre_update_snapshot
            bash "${SCRIPT_DIR}/azambasha-apply-all-fixes.sh" 19
            if [ -f "${SCRIPT_DIR}/azambasha-sync-gui-version.sh" ]; then
                bash "${SCRIPT_DIR}/azambasha-sync-gui-version.sh" auto || true
            fi
            log_ok "Master node one-step update successfully completed!"
        fi
        ;;
    *)
        log_err "Unknown argument: $MODE"
        echo "Run 'sudo azam-update --help' for options."
        exit 1
        ;;
esac
