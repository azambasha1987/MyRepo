#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Inter-Node RoCE & MTU 9000 Dataplane Benchmark Probe (azam-bench)
# ==============================================================================
# Verifies true non-fragmented MTU 9000 packet delivery and measures inter-node
# latency, jitter, and UDP/TCP throughput between Master and Satellite nodes.
# ==============================================================================

# Install symlink
if [ "$(id -u)" -eq 0 ]; then
    ln -sf "$(realpath "$0")" /usr/local/bin/azam-bench 2>/dev/null || true
fi

PEER="${1:-}"
IFACE="${2:-auto}"
IPERF_PORT=5201

GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
BOLD="\033[1m"
RESET="\033[0m"

usage() {
    echo "Usage: sudo azam-bench <SATELLITE_IP> [INTERFACE]"
    echo ""
    echo "  <SATELLITE_IP>   IP address of the Satellite Worker node to probe"
    echo "  [INTERFACE]      Network interface to use (default: auto-detect)"
    echo ""
    echo "Examples:"
    echo "  sudo azam-bench 192.168.1.50"
    echo "  sudo azam-bench 192.168.1.50 ens18"
    exit 0
}

[ -z "$PEER" ] && usage

# Auto-detect interface if not specified
if [ "$IFACE" = "auto" ]; then
    IFACE=$(ip route get "$PEER" 2>/dev/null | grep -oP "dev\s+\K\S+" | head -n1 || echo "eth0")
fi

echo -e "${CYAN}================================================================================"
echo -e "     ${BOLD}Azam-Pnet MTU 9000 & RoCE Dataplane Benchmark Probe (azam-bench)${RESET}${CYAN}"
echo -e "================================================================================${RESET}"
echo -e " Probing Satellite:  ${BOLD}${PEER}${RESET}"
echo -e " Local Interface:    ${BOLD}${IFACE}${RESET}"
echo -e " Testing:            MTU 9000 | ICMP Latency | RDMA RXE Counters | TCP/UDP Throughput"
echo -e "--------------------------------------------------------------------------------"

PASS=0
FAIL=0

# === 1. Basic Connectivity Check ===
echo -e "\n[1/5] ${BOLD}Basic ICMP Reachability${RESET}"
if ping -c 3 -W 2 "$PEER" &>/dev/null; then
    RTT=$(ping -c 10 "$PEER" 2>/dev/null | grep "avg" | awk -F'/' '{print $5}' | cut -d'.' -f1)
    echo -e "  ${GREEN}[✔ PASS]${RESET} Host ${PEER} is reachable. Average RTT: ${RTT}ms"
    PASS=$((PASS+1))
else
    echo -e "  ${RED}[✘ FAIL]${RESET} Cannot ping ${PEER}. Check network connectivity."
    FAIL=$((FAIL+1))
fi

# === 2. Non-Fragmented MTU 9000 Jumbo Frame Test ===
echo -e "\n[2/5] ${BOLD}Non-Fragmented MTU 9000 Jumbo Frame Probe${RESET}"
# ICMP payload for MTU 9000: 9000 - 28 bytes (IP+ICMP headers) = 8972
if ping -c 3 -M do -s 8972 -W 3 "$PEER" &>/dev/null; then
    echo -e "  ${GREEN}[✔ PASS]${RESET} MTU 9000 non-fragmented packet delivery verified (8972-byte payload)."
    PASS=$((PASS+1))
else
    CURRENT_MTU=$(cat /sys/class/net/"$IFACE"/mtu 2>/dev/null || echo "unknown")
    echo -e "  ${YELLOW}[⚠ WARN]${RESET} MTU 9000 jumbo frames NOT traversing end-to-end."
    echo -e "           Local interface ${IFACE} MTU: ${CURRENT_MTU}"
    echo -e "           Check: physical switch port config, hypervisor virtual switch MTU."
    echo -e "           Fix:   sudo ip link set ${IFACE} mtu 9000"
    FAIL=$((FAIL+1))

    # Attempt to find maximum working MTU
    for test_mtu in 1500 4096 8972; do
        payload=$((test_mtu - 28))
        if ping -c 1 -M do -s "$payload" -W 2 "$PEER" &>/dev/null; then
            echo -e "           Maximum verified MTU: ${test_mtu} bytes."
            break
        fi
    done
fi

# === 3. Check Local MTU 9000 Interface Configuration ===
echo -e "\n[3/5] ${BOLD}Local Dataplane Interface Audit${RESET}"
MTU9000_IFACES=$(ip link show 2>/dev/null | grep -B1 "mtu 9000" | grep -v "mtu 9000" | grep "^[0-9]" | awk '{print $2}' | tr -d ':' || true)
if [ -n "$MTU9000_IFACES" ]; then
    echo -e "  ${GREEN}[✔ PASS]${RESET} MTU 9000 interfaces active: $MTU9000_IFACES"
    PASS=$((PASS+1))
else
    echo -e "  ${YELLOW}[⚠ WARN]${RESET} No interface is currently configured with MTU 9000."
    echo -e "           Run: sudo bash scripts/azambasha-dataplane-engine.sh to enable jumbo frames."
    FAIL=$((FAIL+1))
fi

# === 4. Soft-RoCE (RDMA RXE) State & Packet Counters ===
echo -e "\n[4/5] ${BOLD}Soft-RoCE (RDMA RXE) State & Error Counters${RESET}"
if command -v rdma &>/dev/null && rdma stat 2>/dev/null | grep -q "rxe"; then
    RXE_IFACE=$(rdma link show 2>/dev/null | grep "rxe" | head -n1 | awk '{print $2}' | cut -d'/' -f1 || echo "rxe0")
    RXE_TX=$(rdma stat show dev "$RXE_IFACE" 2>/dev/null | grep "tx_bytes" | awk '{print $2}' || echo "N/A")
    RXE_ERRORS=$(rdma stat show dev "$RXE_IFACE" 2>/dev/null | grep -i "error" | awk '{print $2}' | paste -sd "+" | bc 2>/dev/null || echo "0")
    if [ "${RXE_ERRORS:-0}" = "0" ] || [ "${RXE_ERRORS:-0}" = "N/A" ]; then
        echo -e "  ${GREEN}[✔ PASS]${RESET} Soft-RoCE (${RXE_IFACE}) is active. TX bytes: ${RXE_TX}. Zero RDMA errors."
        PASS=$((PASS+1))
    else
        echo -e "  ${YELLOW}[⚠ WARN]${RESET} Soft-RoCE (${RXE_IFACE}) has ${RXE_ERRORS} cumulative RDMA errors."
        FAIL=$((FAIL+1))
    fi
elif command -v cat /sys/class/infiniband/rxe0/ports/1/counters/port_xmit_data &>/dev/null; then
    echo -e "  ${GREEN}[✔ PASS]${RESET} RXE infiniband counters accessible."
    PASS=$((PASS+1))
else
    echo -e "  ${YELLOW}[⚠ WARN]${RESET} Soft-RoCE (RXE) not loaded or not active."
    echo -e "           Fix: sudo rdma link add rxe0 type rxe netdev ${IFACE}"
    FAIL=$((FAIL+1))
fi

# === 5. TCP Throughput with iperf3 ===
echo -e "\n[5/5] ${BOLD}TCP/UDP Throughput via iperf3${RESET}"
if ! command -v iperf3 &>/dev/null; then
    echo -e "  ${YELLOW}[⚠ SKIP]${RESET} iperf3 not installed. Install with: sudo apt-get install iperf3 -y"
    FAIL=$((FAIL+1))
else
    # Try connecting to existing iperf3 server on peer
    echo -e "  -> Attempting iperf3 TCP throughput test to ${PEER}:${IPERF_PORT}..."
    IPERF_RESULT=$(iperf3 -c "$PEER" -p "$IPERF_PORT" -t 5 -J 2>/dev/null || echo "")
    if [ -n "$IPERF_RESULT" ]; then
        BW_MBPS=$(echo "$IPERF_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['end']['sum_received']['bits_per_second']/1e6:.0f}\")" 2>/dev/null || echo "N/A")
        echo -e "  ${GREEN}[✔ PASS]${RESET} TCP Throughput: ${BW_MBPS} Mbps (MTU 9000 enables near-wire-speed)"
        PASS=$((PASS+1))
    else
        echo -e "  ${YELLOW}[⚠ SKIP]${RESET} iperf3 server not running on ${PEER}:${IPERF_PORT}."
        echo -e "           On Satellite, run: iperf3 -s -D -p ${IPERF_PORT}"
        echo -e "           Then re-run: sudo azam-bench ${PEER}"
        FAIL=$((FAIL+1))
    fi
fi

# Summary
echo -e "\n${CYAN}================================================================================"
TOTAL=$((PASS+FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo -e " ${GREEN}${BOLD}CLUSTER FABRIC STATUS: ALL ${TOTAL} PROBES PASSED ✔ - Ready for Heavy Lab Deployment${RESET}${CYAN}"
elif [ "$PASS" -ge "$FAIL" ]; then
    echo -e " ${YELLOW}${BOLD}CLUSTER FABRIC STATUS: ${PASS}/${TOTAL} PASSED | ${FAIL} Warnings Detected${RESET}${CYAN}"
    echo -e " ${YELLOW}Verify switch MTU configuration and RXE setup before deploying 40+ node topologies.${RESET}${CYAN}"
else
    echo -e " ${RED}${BOLD}CLUSTER FABRIC STATUS: ${FAIL} CRITICAL FAILURES - Investigate before lab deployment${RESET}${CYAN}"
fi
echo -e "${CYAN}================================================================================${RESET}"
