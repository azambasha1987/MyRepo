#!/usr/bin/env bash
# ==============================================================================
# Azam Basha 1-Click Multi-Node Fleet Dashboard (azam-fleet)
# ==============================================================================
# Displays real-time cluster health, running node density, Ultra-KSM memory 
# savings, Soft-RoCE MTU 9000 status, and Master/Satellite sync status.
# ==============================================================================
# ANSI color tokens
GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
MAGENTA="\033[1;35m"
BOLD="\033[1m"
RESET="\033[0m"

# Install symlink to /usr/local/bin/azam-fleet
if [ "$(id -u)" -eq 0 ]; then
    ln -sf "$(realpath "$0")" /usr/local/bin/azam-fleet 2>/dev/null || true
fi

# Detect Node Role
IS_MASTER=true
if [ -f "/etc/pnetlab/cluster-db.conf" ] && ! systemctl is-active mysql &>/dev/null; then
    IS_MASTER=false
fi

NODE_IP=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | grep -v '169.254' | head -n1 || echo "127.0.0.1")
HOSTNAME=$(hostname 2>/dev/null || echo "azam-node")

# Memory & KSM
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "16384000")
AVAIL_RAM_KB=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "12288000")
TOTAL_RAM_GB=$(awk "BEGIN {printf \"%.1f\", $TOTAL_RAM_KB/1024/1024}" 2>/dev/null || echo "16.0")
AVAIL_RAM_GB=$(awk "BEGIN {printf \"%.1f\", $AVAIL_RAM_KB/1024/1024}" 2>/dev/null || echo "12.0")

KSM_PAGES=$(cat /sys/kernel/mm/ksm/pages_sharing 2>/dev/null || echo "0")
KSM_SAVED_MB=$(awk "BEGIN {printf \"%.1f\", ($KSM_PAGES * 4096) / (1024 * 1024)}" 2>/dev/null || echo "0.0")
KSM_SAVED_GB=$(awk "BEGIN {printf \"%.2f\", ($KSM_PAGES * 4096) / (1024 * 1024 * 1024)}" 2>/dev/null || echo "0.00")
KSM_RUN=$(cat /sys/kernel/mm/ksm/run 2>/dev/null || echo "0")

# Running Nodes
QEMU_COUNT=$(ps -ef 2>/dev/null | grep -c "[q]emu-system" || true)
IOL_COUNT=$(ps -ef 2>/dev/null | grep -c "[i]ol" || true)
DOCKER_COUNT=$(docker ps -q 2>/dev/null | wc -l || true)
QEMU_COUNT=${QEMU_COUNT:-0}
IOL_COUNT=${IOL_COUNT:-0}
DOCKER_COUNT=${DOCKER_COUNT:-0}
TOTAL_NODES=$((QEMU_COUNT + IOL_COUNT + DOCKER_COUNT))

# Dataplane & Network
MTU9000_COUNT=$(ip link show 2>/dev/null | grep -c "mtu 9000" || true)
BPDU_MASK=$(cat /sys/class/net/pnet0/bridge/group_fwd_mask 2>/dev/null || echo "N/A")

# Version
VERSION_STR="v6.8.79 (6.8.79resolute1)"
if [ -f "/opt/unetlab/html/includes/version.php" ]; then
    VERSION_VAL=$(grep -oP "(?<=define\('PNET_RELEASE', ')[^']+" /opt/unetlab/html/includes/version.php 2>/dev/null || echo "v6.8.79")
    PKG_VAL=$(grep -oP "(?<=define\('PNET_PACKAGE_VERSION', ')[^']+" /opt/unetlab/html/includes/version.php 2>/dev/null || echo "6.8.79resolute1")
    if [ -n "$VERSION_VAL" ]; then
        VERSION_STR="${VERSION_VAL} (${PKG_VAL})"
    fi
fi

echo -e "${CYAN}================================================================================"
echo -e "       ${BOLD}AZAM-PNET DUAL-NODE CLUSTER FLEET DASHBOARD (azam-fleet)${RESET}${CYAN}"
echo -e "================================================================================${RESET}"

if [ "$IS_MASTER" = true ]; then
    echo -e " Node Role:         ${GREEN}${BOLD}MASTER CONTROLLER${RESET} [Cluster Head]"
else
    echo -e " Node Role:         ${MAGENTA}${BOLD}SATELLITE WORKER${RESET} [Execution Node]"
fi

echo -e " Hostname / IP:     ${BOLD}${HOSTNAME}${RESET} (${NODE_IP})"
echo -e " Web-GUI Release:   ${GREEN}${BOLD}${VERSION_STR}${RESET}"
echo -e " Physical RAM:      ${BOLD}${TOTAL_RAM_GB} GB${RESET} (Available: ${AVAIL_RAM_GB} GB)"

if [ "$KSM_RUN" = "1" ]; then
    echo -e " Ultra-KSM State:   ${GREEN}${BOLD}ACTIVE (4KB Deduplication)${RESET} -> ${GREEN}${BOLD}${KSM_SAVED_GB} GB RAM Saved${RESET}"
else
    echo -e " Ultra-KSM State:   ${YELLOW}INACTIVE / STANDBY${RESET}"
fi

echo -e " Active Lab Nodes:  ${BOLD}${TOTAL_NODES}${RESET} (QEMU: ${QEMU_COUNT} | IOL: ${IOL_COUNT} | Docker: ${DOCKER_COUNT})"
echo -e " Dataplane MTU:     ${BOLD}MTU 9000${RESET} (${MTU9000_COUNT} interfaces verified)"
echo -e " LACP BPDU Mask:    ${BOLD}${BPDU_MASK}${RESET} (0xffff = full hardware pass-through)"

# Check Satellites if Master
if [ "$IS_MASTER" = true ] && command -v mysql &>/dev/null; then
    echo -e "${CYAN}--------------------------------------------------------------------------------${RESET}"
    echo -e " ${BOLD}Connected Satellite Worker Nodes:${RESET}"
    SATS=$(mysql -u root -pazam -N -e "SELECT id, name, ip, status FROM pnetlab_db.satellites;" 2>/dev/null || true)
    if [ -n "$SATS" ]; then
        echo "$SATS" | while read -r sat_id sat_name sat_ip sat_status; do
            PING_RES=$(ping -c 1 -W 1 "$sat_ip" &>/dev/null && echo -e "${GREEN}ONLINE (Ping OK)${RESET}" || echo -e "${RED}UNREACHABLE${RESET}")
            echo -e "  ↳ [Sat #${sat_id}] ${BOLD}${sat_name}${RESET} (${sat_ip}) -> Status: ${sat_status} | Link: ${PING_RES}"
        done
    else
        echo -e "  ↳ (No satellite workers registered in database yet. Deploy via: ${BOLD}python scripts/deploy-to-vm.py --satellite${RESET})"
    fi
fi

echo -e "${CYAN}================================================================================"
echo -e " Tips: Run ${BOLD}azam-capacity${RESET} for node headroom | Run ${BOLD}azam-doctor${RESET} for disk cleanup"
echo -e "================================================================================${RESET}"
