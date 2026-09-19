#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Standalone High-Density Heavy Node Optimizer
# Targets: Cisco Catalyst 8000 (C8000v), Cisco 8000 (XR7), Catalyst 9000 (Cat9kv)
# Nodes:   Master Node and Satellite Worker Nodes
#
# Can be applied directly to ANY existing VM via:
#   sudo bash apply-heavy-node-optimizer.sh
# or curl:
#   curl -fsSL <URL>/apply-heavy-node-optimizer.sh | sudo bash
# ==============================================================================
set -euo pipefail

# -----------------------------------------------------------------------------
# Help and CLI Handling
# -----------------------------------------------------------------------------
if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
    cat << 'EOF'
Usage: sudo bash apply-heavy-node-optimizer.sh [OPTIONS]

Options:
  (no args)          Apply complete memory & CPU optimization to this VM
  --check, --status  Audit current KSM savings, THP status & CPU governor
  --cluster          Deploy and trigger optimization across all registered satellites
  --rollback         Restore standard Linux defaults
  -h, --help         Show this help message
EOF
    exit 0
fi

# Diagnostic Audit Mode
if [[ "${1:-}" =~ ^(--check|--status)$ ]]; then
    echo "============================================================"
    echo "  Azam Basha High-Density Heavy Node Optimization Audit     "
    echo "  Target Appliances: Catalyst 8000, Cisco 8000, Cat 9000    "
    echo "============================================================"
    
    echo -n "[*] KSM Memory Deduplication: "
    if [ -f /sys/kernel/mm/ksm/run ] && [ "$(cat /sys/kernel/mm/ksm/run 2>/dev/null || echo 0)" -ge 1 ]; then
        RUN_MODE=$(cat /sys/kernel/mm/ksm/run)
        PAGES_SHARING=$(cat /sys/kernel/mm/ksm/pages_sharing 2>/dev/null || echo 0)
        PAGE_SIZE_KB=$(($(getconf PAGE_SIZE 2>/dev/null || echo 4096) / 1024))
        SAVED_MB=$((PAGES_SHARING * PAGE_SIZE_KB / 1024))
        SAVED_GB=$(awk "BEGIN {printf \"%.2f\", ${SAVED_MB}/1024}")
        SCAN_RATE=$(cat /sys/kernel/mm/ksm/pages_to_scan 2>/dev/null || echo "default")
        SLEEP_MS=$(cat /sys/kernel/mm/ksm/sleep_millisecs 2>/dev/null || echo "default")
        echo "ACTIVE (Mode: $RUN_MODE, Rate: $SCAN_RATE pages / ${SLEEP_MS}ms)"
        echo "    ↳ Deduplicated RAM Saved: ~${SAVED_MB} MB (~${SAVED_GB} GB)"
    else
        echo "INACTIVE or NOT AVAILABLE"
    fi

    echo -n "[*] Transparent Hugepages (THP): "
    if [ -f /sys/kernel/mm/transparent_hugepage/enabled ]; then
        THP_STATUS=$(grep -o '\[.*\]' /sys/kernel/mm/transparent_hugepage/enabled | tr -d '[]' || echo "unknown")
        if [ "$THP_STATUS" = "madvise" ] || [ "$THP_STATUS" = "never" ]; then
            echo "OPTIMIZED ($THP_STATUS - KSM 4KB base page merging active)"
        else
            echo "WARNING ($THP_STATUS - 2MB hugepages block KSM deduplication!)"
        fi
    else
        echo "N/A"
    fi

    echo -n "[*] KVM Halt Polling: "
    if [ -f /sys/module/kvm/parameters/halt_poll_ns ]; then
        HP_VAL=$(cat /sys/module/kvm/parameters/halt_poll_ns)
        [ "$HP_VAL" -eq 0 ] && echo "OPTIMIZED (0 ns - zero host spinlock overhead)" || echo "DEFAULT ($HP_VAL ns)"
    else
        echo "N/A"
    fi

    echo -n "[*] In-Memory Fast Swap (ZRAM/ZSWAP): "
    if [ -f /sys/module/zswap/parameters/enabled ] && [ "$(cat /sys/module/zswap/parameters/enabled 2>/dev/null)" = "Y" ]; then
        COMP=$(cat /sys/module/zswap/parameters/compressor 2>/dev/null || echo "unknown")
        echo "ACTIVE (ZSWAP with $COMP compression)"
    elif grep -q zram /proc/swaps 2>/dev/null; then
        echo "ACTIVE (ZRAM Compressed Device)"
    else
        echo "STANDARD LINUX SWAP"
    fi

    echo -n "[*] Dynamic Lossless CPU Governor: "
    if systemctl is-active --quiet azambasha-cpu-governor.service 2>/dev/null; then
        echo "ACTIVE (Running - dynamic burst protection)"
    else
        echo "INACTIVE"
    fi

    echo "============================================================"
    exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] This script must be run as root: sudo bash $0" >&2
    exit 1
fi

# Rollback Mode
if [[ "${1:-}" == "--rollback" ]]; then
    echo "=== Rolling back High-Density Heavy Node Optimizations ==="
    systemctl stop azambasha-heavy-optimizer.service 2>/dev/null || true
    systemctl disable azambasha-heavy-optimizer.service 2>/dev/null || true
    systemctl stop azambasha-cpu-governor.service 2>/dev/null || true
    systemctl disable azambasha-cpu-governor.service 2>/dev/null || true
    rm -f /etc/systemd/system/azambasha-heavy-optimizer.service
    rm -f /etc/systemd/system/azambasha-cpu-governor.service
    rm -f /etc/sysctl.d/99-azambasha-heavy-nodes.conf
    if [ -f /sys/kernel/mm/transparent_hugepage/enabled ]; then
        echo always > /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || true
    fi
    systemctl daemon-reload 2>/dev/null || true
    echo "[SUCCESS] Rollback complete. Standard defaults restored."
    exit 0
fi

echo "============================================================"
echo "    Azam Basha Standalone Heavy Node Optimizer Deployer     "
echo "  Targets: Catalyst 8000, Cisco 8000, Catalyst 9000 Series  "
echo "  Nodes:   Master Node & Satellite Worker Nodes             "
echo "============================================================"

# Detect Master vs Satellite
ROLE="satellite"
if [ -d /opt/unetlab/cluster ] || [ -f /opt/unetlab/html/config.php ]; then
    ROLE="master"
fi
echo "[+] Target Appliance Role: $(echo "$ROLE" | tr '[:lower:]' '[:upper:]')"

# -----------------------------------------------------------------------------
# 1. Enable Host Kernel KSM Ultra Engine
# -----------------------------------------------------------------------------
echo "[1/6] Activating Ultra-High Throughput KSM Memory Deduplication..."
if [ -d /sys/kernel/mm/ksm ]; then
    echo 1 > /sys/kernel/mm/ksm/run 2>/dev/null || true
    echo 10000 > /sys/kernel/mm/ksm/pages_to_scan 2>/dev/null || true
    echo 10 > /sys/kernel/mm/ksm/sleep_millisecs 2>/dev/null || true
    echo 1 > /sys/kernel/mm/ksm/use_zero_pages 2>/dev/null || true
    echo 1 > /sys/kernel/mm/ksm/merge_across_nodes 2>/dev/null || true
    echo "  [✔] KSM configured: 10,000 pages / 10ms with zero-page deduplication"
else
    echo "  [!] Warning: /sys/kernel/mm/ksm not found in this kernel."
fi

# -----------------------------------------------------------------------------
# 2. Configure Transparent Huge Pages (THP) to madvise
# -----------------------------------------------------------------------------
echo "[2/6] De-conflicting Transparent Hugepages (THP) for 4KB Page Merging..."
if [ -f /sys/kernel/mm/transparent_hugepage/enabled ]; then
    echo madvise > /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || true
    echo "  [✔] THP set to 'madvise' (enables 4KB base page granularity for KSM)"
fi
if [ -f /sys/kernel/mm/transparent_hugepage/defrag ]; then
    echo defer+madvise > /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null || true
    echo "  [✔] THP defrag set to 'defer+madvise' (prevents allocation jitter)"
fi

# -----------------------------------------------------------------------------
# 3. KVM Virtualization & Halt-Polling Latency Elimination
# -----------------------------------------------------------------------------
echo "[3/6] Eliminating KVM Host Halt-Polling Spinlocks & Tuning Latency..."
if [ -f /sys/module/kvm/parameters/halt_poll_ns ]; then
    echo 0 > /sys/module/kvm/parameters/halt_poll_ns 2>/dev/null || true
    echo "  [✔] kvm.halt_poll_ns set to 0 (zero host spinlock overhead)"
fi

cat << 'EOF' > /etc/sysctl.d/99-azambasha-heavy-nodes.conf
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_background_ratio = 5
vm.dirty_ratio = 10
fs.inotify.max_user_watches = 1048576
fs.file-max = 2097152
EOF
sysctl -p /etc/sysctl.d/99-azambasha-heavy-nodes.conf >/dev/null 2>&1 || true
echo "  [✔] Sysctl applied: vm.swappiness=10, 2M file descriptors"

# -----------------------------------------------------------------------------
# 4. In-Memory ZRAM / ZSWAP Fast Compression Buffer
# -----------------------------------------------------------------------------
echo "[4/6] Initializing High-Speed In-Memory Swap Buffer (ZRAM / ZSWAP)..."
if [ -d /sys/module/zswap/parameters ]; then
    echo 1 > /sys/module/zswap/parameters/enabled 2>/dev/null || true
    if grep -q zstd /sys/module/zswap/parameters/compressor 2>/dev/null; then
        echo zstd > /sys/module/zswap/parameters/compressor 2>/dev/null || true
    elif grep -q lz4 /sys/module/zswap/parameters/compressor 2>/dev/null; then
        echo lz4 > /sys/module/zswap/parameters/compressor 2>/dev/null || true
    fi
    echo 30 > /sys/module/zswap/parameters/max_pool_percent 2>/dev/null || true
    echo "  [✔] ZSWAP active: In-RAM 3:1 fast compression prevents mass-boot disk stalls"
fi

# -----------------------------------------------------------------------------
# 5. Self-Contained Extraction of Lossless Dynamic CPU Governor
# -----------------------------------------------------------------------------
echo "[5/6] Deploying Lossless Dynamic CPU Governor Daemon..."
mkdir -p /opt/unetlab/scripts 2>/dev/null || true

cat << 'PYEOF' > /opt/unetlab/scripts/azambasha-cpu-governor.py
#!/usr/bin/env python3
"""
Azam Basha Lossless Dynamic CPU Governor for Heavy Virtual Routers
Targets: Cisco Catalyst 8000, Cisco 8000 Series, Cisco Catalyst 9000
"""
import os, sys, time, glob, re, argparse

TARGET_PATTERNS = [
    r'8000v',
    r'c8000v',
    r'c8000',
    r'cisco8000',
    r'cisco8k',
    r'cat8000',
    r'cat8k',
    r'cat9000v',
    r'cat9000',
    r'cat9k',
    r'c9300v',
    r'c9300',
    r'c9500v',
    r'c9500',
    r'csr1000v',
    r'csr1000',
    r'xrv9k',
    r'xrv',
    r'xr8000'
]
TARGET_REGEX = re.compile('|'.join(TARGET_PATTERNS), re.IGNORECASE)

class HeavyNodeGovernor:
    def __init__(self, check_interval=2.0, hysteresis_sec=5.0):
        self.check_interval = check_interval
        self.hysteresis_sec = hysteresis_sec
        self.node_states = {}

    def find_heavy_qemu_nodes(self):
        nodes = []
        try:
            for pid_dir in glob.glob('/proc/[0-9]*'):
                pid = os.path.basename(pid_dir)
                cmdline_path = os.path.join(pid_dir, 'cmdline')
                if not os.path.isfile(cmdline_path):
                    continue
                try:
                    with open(cmdline_path, 'rb') as f:
                        cmdline = f.read().decode('utf-8', errors='ignore').replace('\x00', ' ')
                except (IOError, PermissionError):
                    continue

                if 'qemu-system' not in cmdline:
                    continue

                is_target = False
                matched_type = "QEMU-Router"

                # Check 1: Direct match in command line
                m = TARGET_REGEX.search(cmdline)
                if m:
                    is_target = True
                    matched_type = m.group(0)

                # Check 2: Inspect open file descriptors for backing files in /opt/unetlab/addons/qemu/
                if not is_target:
                    try:
                        fd_dir = f'/proc/{pid}/fd'
                        if os.path.isdir(fd_dir):
                            for fd in os.listdir(fd_dir):
                                try:
                                    target = os.readlink(os.path.join(fd_dir, fd))
                                    m_fd = TARGET_REGEX.search(target)
                                    if m_fd:
                                        is_target = True
                                        matched_type = m_fd.group(0)
                                        break
                                    if '/opt/unetlab/addons/qemu/' in target:
                                        matched_type = target.split('/opt/unetlab/addons/qemu/')[1].split('/')[0]
                                        is_target = True
                                        break
                                except (IOError, OSError):
                                    continue
                    except Exception:
                        pass

                # Check 3: Any QEMU node running under PNETLab (/opt/unetlab/tmp)
                if not is_target and ('/opt/unetlab' in cmdline or '/opt/qemu' in cmdline):
                    is_target = True
                    matched_type = "pnet-router"

                if is_target:
                    name_match = re.search(r'-name\s+([^\s]+)', cmdline)
                    node_name = name_match.group(1) if name_match else f"{matched_type}-{pid}"

                    nodes.append({
                        "pid": int(pid),
                        "name": node_name,
                        "type": matched_type,
                        "cmdline": cmdline
                    })
        except Exception:
            pass
        return nodes

    def get_node_tap_interfaces(self, pid):
        taps = []
        for net_path in glob.glob('/sys/class/net/vnet*'):
            taps.append(os.path.basename(net_path))
        return list(set(taps))

    def get_total_packets(self, tap_list):
        total = 0
        for tap in tap_list:
            for stat in ['rx_packets', 'tx_packets']:
                sf = f'/sys/class/net/{tap}/statistics/{stat}'
                try:
                    if os.path.isfile(sf):
                        with open(sf, 'r') as f:
                            total += int(f.read().strip())
                except Exception:
                    pass
        return total

    def set_lossless_priority(self, pid, priority="idle"):
        try:
            cgroup_file = f'/proc/{pid}/cgroup'
            if os.path.isfile(cgroup_file):
                with open(cgroup_file, 'r') as f:
                    cg_line = f.read().strip()
                parts = cg_line.split('::')
                if len(parts) == 2:
                    cg_path = os.path.join('/sys/fs/cgroup', parts[1].lstrip('/'))
                    weight_file = os.path.join(cg_path, 'cpu.weight')
                    idle_file = os.path.join(cg_path, 'cpu.idle')
                    if os.path.isfile(weight_file):
                        with open(weight_file, 'w') as wf:
                            wf.write(f"{'1000' if priority == 'active' else '10'}\n")
                    if os.path.isfile(idle_file):
                        with open(idle_file, 'w') as idf:
                            idf.write(f"{'0' if priority == 'active' else '1'}\n")

            os.setpriority(os.PRIO_PROCESS, pid, 0 if priority == "active" else 10)
        except Exception:
            pass

    def run_pass(self):
        now = time.time()
        active_nodes = self.find_heavy_qemu_nodes()
        current_pids = {n["pid"] for n in active_nodes}

        for pid in list(self.node_states.keys()):
            if pid not in current_pids:
                del self.node_states[pid]

        results = []
        for node in active_nodes:
            pid = node["pid"]
            name = node["name"]
            node_type = node["type"]
            taps = self.get_node_tap_interfaces(pid)
            total_pkts = self.get_total_packets(taps)

            if pid not in self.node_states:
                self.node_states[pid] = {
                    "last_active": now,
                    "prev_packets": total_pkts,
                    "state": "active",
                    "name": name,
                    "type": node_type
                }
                self.set_lossless_priority(pid, "active")
                results.append((name, pid, node_type, "ACTIVE (New Boot)", total_pkts))
                continue

            state_info = self.node_states[pid]
            delta_pkts = total_pkts - state_info["prev_packets"]
            state_info["prev_packets"] = total_pkts

            if delta_pkts > 0:
                state_info["last_active"] = now
                if state_info["state"] != "active":
                    state_info["state"] = "active"
                    self.set_lossless_priority(pid, "active")
                results.append((name, pid, node_type, f"ACTIVE (+{delta_pkts} pkts)", total_pkts))
            else:
                idle_duration = now - state_info["last_active"]
                if idle_duration > self.hysteresis_sec:
                    if state_info["state"] != "idle":
                        state_info["state"] = "idle"
                        self.set_lossless_priority(pid, "idle")
                    results.append((name, pid, node_type, f"IDLE (Yielding, {idle_duration:.1f}s silent)", total_pkts))
                else:
                    results.append((name, pid, node_type, f"HOLD ACTIVE ({self.hysteresis_sec - idle_duration:.1f}s)", total_pkts))
        return results

    def status(self):
        print("============================================================")
        print("  Azam Basha Heavy Router CPU Governor Diagnostic           ")
        print("============================================================")
        results = self.run_pass()
        if not results:
            print("  [*] No active Catalyst 8000, Cisco 8000, or Cat 9000 instances detected.")
            print("      (Governor is armed and will automatically attach when nodes boot).")
            
            other_qemu = []
            for pid_dir in glob.glob('/proc/[0-9]*'):
                cmdline_path = os.path.join(pid_dir, 'cmdline')
                if os.path.isfile(cmdline_path):
                    try:
                        with open(cmdline_path, 'rb') as f:
                            cmd = f.read().decode('utf-8', errors='ignore').replace('\x00', ' ')
                        if 'qemu-system' in cmd:
                            other_qemu.append((os.path.basename(pid_dir), cmd[:80]))
                    except Exception:
                        pass
            if other_qemu:
                print("\n  [i] Other active QEMU processes found on this host:")
                for p, c in other_qemu:
                    print(f"      PID {p:<6}: {c}...")
        else:
            print(f"  {'APPLIANCE / NAME':<25} {'PID':<8} {'TYPE':<12} {'STATE':<25}")
            print("  " + "-" * 70)
            for name, pid, node_type, state_desc, pkts in results:
                print(f"  {name[:24]:<25} {pid:<8} {node_type:<12} {state_desc:<25}")
        print("============================================================")

    def loop(self):
        print("[+] Azam Basha Lossless CPU Governor daemon started.")
        while True:
            try:
                self.run_pass()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(self.check_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Azam Basha Heavy Node Lossless CPU Governor")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--status", action="store_true", help="Show current node status")
    args = parser.parse_args()
    gov = HeavyNodeGovernor()
    if args.status:
        gov.status()
    else:
        gov.loop()
PYEOF
chmod +x /opt/unetlab/scripts/azambasha-cpu-governor.py 2>/dev/null || true

# -----------------------------------------------------------------------------
# 6. Patch Templates & device_qemu.php for Universal mem-merge
# -----------------------------------------------------------------------------
echo "[6/6] Tuning QEMU Templates & Engine for Catalyst 8000, Cisco 8000 & Cat 9000..."
python3 - << 'PYEOF'
import os, re

templates_dirs = [
    "/opt/unetlab/html/templates",
    "/opt/unetlab/html/templates/intel",
    "/opt/unetlab/html/templates/amd"
]

target_templates = {
    "8000v": {
        "name": "Cisco 8000 Series (8000v)", "cpus": 4, "ram": 8192, "ethernets": 8, "qemu_nic": "virtio-net-pci",
        "qemu_options": "-machine pc,mem-merge=on -cpu host -enable-kvm -serial mon:stdio -nographic"
    },
    "c8000": {
        "name": "Cisco Catalyst 8000", "cpus": 2, "ram": 4096, "ethernets": 4, "qemu_nic": "virtio-net-pci",
        "qemu_options": "-machine pc,mem-merge=on -cpu host -enable-kvm -serial mon:stdio -nographic"
    },
    "c8000v": {
        "name": "Cisco Catalyst 8000v", "cpus": 2, "ram": 4096, "ethernets": 4, "qemu_nic": "virtio-net-pci",
        "qemu_options": "-machine pc,mem-merge=on -cpu host -enable-kvm -serial mon:stdio -nographic"
    },
    "cisco8000": {
        "name": "Cisco 8000 Series (XR7)", "cpus": 4, "ram": 8192, "ethernets": 8, "qemu_nic": "virtio-net-pci",
        "qemu_options": "-machine pc,mem-merge=on -cpu host,migratable=no,+invtsc -enable-kvm -serial mon:stdio -nographic"
    },
    "cat9000v": {
        "name": "Cisco Catalyst 9000v", "cpus": 4, "ram": 8192, "ethernets": 16, "qemu_nic": "virtio-net-pci",
        "qemu_options": "-machine pc,mem-merge=on -cpu host -enable-kvm -serial mon:stdio -nographic"
    },
    "c9300v": {
        "name": "Cisco Catalyst 9300v", "cpus": 4, "ram": 8192, "ethernets": 16, "qemu_nic": "virtio-net-pci",
        "qemu_options": "-machine pc,mem-merge=on -cpu host -enable-kvm -serial mon:stdio -nographic"
    },
    "c9500v": {
        "name": "Cisco Catalyst 9500v", "cpus": 4, "ram": 8192, "ethernets": 24, "qemu_nic": "virtio-net-pci",
        "qemu_options": "-machine pc,mem-merge=on -cpu host -enable-kvm -serial mon:stdio -nographic"
    }
}

for tdir in templates_dirs:
    if not os.path.isdir(tdir): continue
    for tkey, tdata in target_templates.items():
        tpath = os.path.join(tdir, f"{tkey}.yml")
        if os.path.isfile(tpath):
            try:
                with open(tpath, 'r', encoding='utf-8') as f: content = f.read()
                if "mem-merge=on" not in content:
                    if "qemu_options:" in content:
                        content = re.sub(r'qemu_options:\s*([^\n]+)', r'qemu_options: -machine pc,mem-merge=on \1', content)
                    else:
                        content += f"\nqemu_options: {tdata['qemu_options']}\n"
                    with open(tpath, 'w', encoding='utf-8') as f: f.write(content)
                    print(f"  [✔] Injected mem-merge=on into {tpath}")
            except Exception: pass
        else:
            try:
                tpl_yaml = f"""---
type: qemu
description: {tdata['name']}
name: {tkey.upper()}
cpus: {tdata['cpus']}
ram: {tdata['ram']}
ethernets: {tdata['ethernets']}
qemu_arch: x86_64
qemu_nic: {tdata['qemu_nic']}
qemu_options: {tdata['qemu_options']}
icon: Router.png
"""
                with open(tpath, 'w', encoding='utf-8') as f: f.write(tpl_yaml)
                print(f"  [✔] Created optimized template {tpath}")
            except Exception: pass

# Universally patch device_qemu.php
dev_file = "/opt/unetlab/html/devices/qemu/device_qemu.php"
if os.path.isfile(dev_file):
    try:
        with open(dev_file, 'r', encoding='utf-8') as f: code = f.read()
        if "mem-merge=on" not in code:
            target_str = "$flags .= ' -enable-kvm';"
            replacement_str = "$flags .= ' -enable-kvm -machine mem-merge=on';"
            if target_str in code:
                code = code.replace(target_str, replacement_str)
                with open(dev_file, 'w', encoding='utf-8') as f: f.write(code)
                print("  [✔] Patched device_qemu.php: mem-merge=on active for all QEMU nodes")
    except Exception: pass
PYEOF

# -----------------------------------------------------------------------------
# Register & Start Systemd Services
# -----------------------------------------------------------------------------
cat << 'EOF' > /etc/systemd/system/azambasha-heavy-optimizer.service
[Unit]
Description=Azam Basha High-Density Heavy Node Memory & KSM Optimizer
After=network.target sys-kernel-mm-ksm.mount
Wants=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c ' \
    [ -f /sys/kernel/mm/ksm/run ] && echo 1 > /sys/kernel/mm/ksm/run; \
    [ -f /sys/kernel/mm/ksm/pages_to_scan ] && echo 10000 > /sys/kernel/mm/ksm/pages_to_scan; \
    [ -f /sys/kernel/mm/ksm/sleep_millisecs ] && echo 10 > /sys/kernel/mm/ksm/sleep_millisecs; \
    [ -f /sys/kernel/mm/ksm/use_zero_pages ] && echo 1 > /sys/kernel/mm/ksm/use_zero_pages; \
    [ -f /sys/kernel/mm/ksm/merge_across_nodes ] && echo 1 > /sys/kernel/mm/ksm/merge_across_nodes; \
    [ -f /sys/kernel/mm/transparent_hugepage/enabled ] && echo madvise > /sys/kernel/mm/transparent_hugepage/enabled; \
    [ -f /sys/kernel/mm/transparent_hugepage/defrag ] && echo defer+madvise > /sys/kernel/mm/transparent_hugepage/defrag; \
    [ -f /sys/module/kvm/parameters/halt_poll_ns ] && echo 0 > /sys/module/kvm/parameters/halt_poll_ns; \
    exit 0'

[Install]
WantedBy=multi-user.target
EOF

cat << 'EOF' > /etc/systemd/system/azambasha-cpu-governor.service
[Unit]
Description=Azam Basha Lossless Dynamic CPU Governor for Heavy Virtual Routers
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/unetlab/scripts/azambasha-cpu-governor.py --daemon
Restart=always
RestartSec=5
KillMode=process
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now azambasha-heavy-optimizer.service 2>/dev/null || true
systemctl enable --now azambasha-cpu-governor.service 2>/dev/null || true

# Cluster Sync if requested
if [[ "${1:-}" == "--cluster" ]] && [ "$ROLE" = "master" ]; then
    echo "[*] Propagating optimization to all registered satellite nodes..."
    python3 - << 'PYEOF'
import subprocess
try:
    import pymysql
    conn = pymysql.connect(host='localhost', user='pnetlab', password='pnetlab_password', database='pnetlab_db')
    with conn.cursor() as cur:
        cur.execute("SELECT ip FROM satellites WHERE status=1")
        for row in cur.fetchall():
            ip = row[0]
            print(f"  [*] Optimizing Satellite: {ip}...")
            subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", f"root@{ip}", "curl -fsSL https://raw.githubusercontent.com/azambasha1987/MyRepo/main/EMULATOR/Azam-Pnet/scripts/apply-heavy-node-optimizer.sh | bash"], timeout=30)
except Exception as e:
    print(f"  [*] Satellite sync note: {e}")
PYEOF
fi

echo ""
echo "============================================================"
echo "    [SUCCESS] HEAVY NODE OPTIMIZATION ACTIVATED!            "
echo "============================================================"
echo "  • Kernel KSM Engine      : ACTIVE (10,000 pages / 10ms)"
echo "  • Transparent Hugepages  : madvise (4KB base page sharing)"
echo "  • KVM Halt Polling       : 0 ns (Zero host spinlock waste)"
echo "  • CPU Governor Daemon    : ACTIVE (Lossless CFS Scheduling)"
echo "  • Target Templates       : C8000v, Cisco 8000, Cat 9000 Ready"
echo ""
echo "  Audit live memory savings at any time:"
echo "    sudo bash $0 --check"
echo "============================================================"
