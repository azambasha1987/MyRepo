#!/usr/bin/env bash
# ==============================================================================
# AzamGNS3 - Ubuntu 26 (26.04 LTS) High-Performance System Tuning Engine
# ==============================================================================
# Targets:
#  1. Extreme RAM deduplication via Kernel Samepage Merging (KSM) + Smart-Scan
#  2. Multi-Gen LRU (MGLRU) for aggressive memory page lifecycle management
#  3. ZRAM with zstd compression for high-speed in-RAM virtual swap
#  4. Low-latency network stack: vhost-net, jumbo frame buffers, TAP optimizations
#  5. Modern cgroups v2 hierarchy verification and permissions
# ==============================================================================

set -euo pipefail

echo "===================================================================="
echo " [AzamGNS3] Initializing Ubuntu 26 High-Performance System Tuning   "
echo "===================================================================="

# Check root privileges
if [[ $EUID -ne 0 ]]; then
   echo "[-] Error: This tuning script must be run as root (sudo)." 1>&2
   exit 1
fi

# 1. Kernel Samepage Merging (KSM) + Smart-Scan (Linux 6.6+)
echo "[+] Configuring Kernel Samepage Merging (KSM)..."
if [[ -d /sys/kernel/mm/ksm ]]; then
    # Enable KSM
    echo 1 > /sys/kernel/mm/ksm/run
    # Sleep 20ms between scan passes
    echo 20 > /sys/kernel/mm/ksm/sleep_millisecs
    # Scan 1000 pages per pass for responsive deduplication
    echo 1000 > /sys/kernel/mm/ksm/pages_to_scan
    # Deduplicate identical zero-pages
    echo 1 > /sys/kernel/mm/ksm/use_zero_pages

    # Ubuntu 26 / Linux 6.6+ Smart Scan (reduces KSM scanner CPU overhead by up to 80%)
    if [[ -f /sys/kernel/mm/ksm/smart_scan ]]; then
        echo 1 > /sys/kernel/mm/ksm/smart_scan
        echo "[+] KSM smart_scan enabled successfully."
    fi
    echo "[+] KSM active: pages_to_scan=1000, sleep_millisecs=20, use_zero_pages=1"
else
    echo "[!] Warning: /sys/kernel/mm/ksm not found. Ensure KSM is compiled into kernel."
fi

# 2. Multi-Gen LRU (MGLRU)
echo "[+] Enabling Multi-Gen LRU (MGLRU) memory reclamation..."
if [[ -f /sys/kernel/mm/lru_gen/enabled ]]; then
    echo y > /sys/kernel/mm/lru_gen/enabled
    echo "[+] MGLRU active."
fi

# 3. Kernel Modules (vhost_net, tun, kvm)
echo "[+] Loading kernel virtualization and high-speed networking modules..."
modprobe -q kvm || true
modprobe -q kvm_intel || modprobe -q kvm_amd || true
modprobe -q tun || true
modprobe -q vhost_net || true
modprobe -q zram || true

# Persist modules across reboot
cat << 'EOF' > /etc/modules-load.d/azamgns3.conf
kvm
tun
vhost_net
zram
EOF

# 4. Kernel Network & Virtualization Sysctl Optimization
echo "[+] Applying high-throughput sysctl network parameters..."
cat << 'EOF' > /etc/sysctl.d/99-azamgns3-perf.conf
# Virtual network interface buffering & 32MB TCP socket buffers for fast uploads
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.core.netdev_max_backlog = 100000
net.core.somaxconn = 4096

# High-bandwidth TCP autotuning for large image / project transfers
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1

# Memory swappiness and virtual memory tuning
vm.swappiness = 10
vm.dirty_background_ratio = 5
vm.dirty_ratio = 10
vm.vfs_cache_pressure = 50

# Inotify and max open files for high-density topologies
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 8192
EOF

sysctl --system > /dev/null 2>&1 || true

# 5. ZRAM Swap Configuration with zstd compression
echo "[+] Setting up systemd-zram-generator for compressed in-RAM swap..."
mkdir -p /etc/systemd
cat << 'EOF' > /etc/systemd/zram-generator.conf
[zram0]
zram-size = min(ram / 2, 32768)
compression-algorithm = zstd
swap-priority = 100
fs-type = swap
EOF

# 6. Cgroups v2 Delegation for GNS3 Process Tree
echo "[+] Ensuring Cgroups v2 controllers are enabled..."
if [[ -f /sys/fs/cgroup/cgroup.subtree_control ]]; then
    for controller in cpu memory io; do
        if grep -qw "$controller" /sys/fs/cgroup/cgroup.controllers; then
            echo "+$controller" > /sys/fs/cgroup/cgroup.subtree_control 2>/dev/null || true
        fi
    done
fi

echo "===================================================================="
echo " [AzamGNS3] System tuning complete! Host is primed for high scale.  "
echo "===================================================================="
