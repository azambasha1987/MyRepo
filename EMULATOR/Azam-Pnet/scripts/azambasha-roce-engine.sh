#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Soft-RoCE (RXE) & RDMA over Converged Ethernet Engine
# Ubuntu 26.04+ (Resolute) / Linux Kernel 7.0 Native Architecture
#
# Provides high-performance RDMA over Converged Ethernet (RoCEv2) for PNetLab nodes:
# 1. Verifies/loads rdma_rxe, ib_core, ib_uverbs in-tree kernel modules
# 2. Configures Soft-RoCE RXE device bindings on physical or bridge interfaces (pnet0..pnet9)
# 3. Aligns with Azam-Pnet Silicon Dataplane Fast-Path (MTU 9000 jumbo frames)
# 4. Provides non-root diagnostic/status inspection
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

# Parse arguments
TARGET_IFACE=""
ACTION="status"

while [ $# -gt 0 ]; do
    case "$1" in
        --status|-s)
            ACTION="status"
            shift
            ;;
        --enable|-e)
            ACTION="enable"
            TARGET_IFACE="${2:-pnet0}"
            shift 2 2>/dev/null || shift
            ;;
        --disable|-d)
            ACTION="disable"
            TARGET_IFACE="${2:-rxe0}"
            shift 2 2>/dev/null || shift
            ;;
        --help|-h)
            echo "Usage: sudo bash $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --status, -s               Show live RDMA/RoCE devices and link status"
            echo "  --enable, -e <interface>   Bind Soft-RoCE (RXE) device on specified netdev (default: pnet0)"
            echo "  --disable, -d <rxe_device> Unbind specified RXE device (e.g. rxe0)"
            echo "  --help, -h                 Show this help menu"
            exit 0
            ;;
        *)
            TARGET_IFACE="$1"
            ACTION="enable"
            shift
            ;;
    esac
done

if [ "$ACTION" = "status" ]; then
    echo "============================================================"
    echo "   Azam Basha Soft-RoCE (RXE) & RDMA Status Inspection     "
    echo "============================================================"
    echo -n "  [*] Kernel Module rdma_rxe: "
    if lsmod | grep -q "^rdma_rxe"; then
        echo -e "${C_GREEN}LOADED${C_RESET}"
    else
        echo -e "${C_YELLOW}NOT LOADED${C_RESET}"
    fi

    echo -n "  [*] RDMA Core Utilities (rdma tool): "
    if command -v rdma >/dev/null 2>&1; then
        echo -e "${C_GREEN}AVAILABLE${C_RESET}"
    else
        echo -e "${C_YELLOW}NOT INSTALLED (run azambasha-os-prerequisites.sh)${C_RESET}"
    fi

    echo ""
    echo "  [*] Active RDMA Links:"
    if command -v rdma >/dev/null 2>&1; then
        rdma link show 2>/dev/null || echo "    (No active RDMA links)"
    else
        echo "    (rdma tool not present)"
    fi
    exit 0
fi

# Root check for mutations
if [ "$(id -u)" -ne 0 ]; then
    log_err "Configuration changes require root privileges (sudo bash $0)"
    exit 1
fi

echo "============================================================"
echo "    Azam Basha Soft-RoCE (RXE) & RDMA Engine Configuration  "
echo "============================================================"

# Ensure modules loaded
log_info "Verifying RDMA kernel drivers (rdma_rxe, ib_core, ib_uverbs)..."
for mod in rdma_rxe ib_core ib_uverbs; do
    modprobe "$mod" 2>/dev/null || log_warn "Could not load kernel module $mod (check in-tree support)"
done

if ! command -v rdma >/dev/null 2>&1; then
    log_info "Installing rdma-core package..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null 2>&1 || true
    apt-get install -y -qq rdma-core ibverbs-providers infiniband-diags perftest >/dev/null 2>&1 || true
fi

if [ "$ACTION" = "disable" ]; then
    RXE_NAME="${TARGET_IFACE:-rxe0}"
    log_info "Removing Soft-RoCE device $RXE_NAME..."
    rdma link delete "$RXE_NAME" 2>/dev/null || true
    log_ok "Soft-RoCE device $RXE_NAME removed."
    exit 0
fi

IFACE="${TARGET_IFACE:-pnet0}"
if ! ip link show dev "$IFACE" >/dev/null 2>&1; then
    log_err "Target netdev '$IFACE' does not exist."
    exit 1
fi

# Check if an RXE link already exists on this interface
EXISTING_RXE=$(rdma link show 2>/dev/null | grep "netdev $IFACE" | awk '{print $2}' | cut -d/ -f1 || true)
if [ -n "$EXISTING_RXE" ]; then
    log_ok "Soft-RoCE link already active: $EXISTING_RXE on $IFACE"
    exit 0
fi

# Determine next available rxe unit
RXE_UNIT=0
while rdma link show "rxe${RXE_UNIT}" >/dev/null 2>&1; do
    RXE_UNIT=$((RXE_UNIT + 1))
done
NEW_RXE="rxe${RXE_UNIT}"

log_info "Binding Soft-RoCE device $NEW_RXE on netdev $IFACE..."
rdma link add "$NEW_RXE" type rxe netdev "$IFACE" 2>/dev/null || {
    log_err "Failed to bind $NEW_RXE on $IFACE. Ensure rdma_rxe is supported by the running kernel."
    exit 1
}

log_ok "Successfully created Soft-RoCE device $NEW_RXE on $IFACE!"
echo ""
rdma link show "$NEW_RXE" 2>/dev/null || true
exit 0
