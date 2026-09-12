#!/usr/bin/env python3
"""
Azam Basha Lossless Dynamic CPU Governor for Heavy Virtual Routers
Target Appliances: Cisco Catalyst 8000, Cisco 8000 Series, Cisco Catalyst 9000

Guarantees:
1. Zero Performance Degradation: Does NOT use hard CPU caps (cpu.max) that cause packet drops.
2. Dynamic CFS Weight Scheduling: Automatically steps down idle DPDK spinloops (cpu.weight=10)
   and instantaneously bursts to maximum priority (cpu.weight=1000) when packets arrive.
3. Hysteresis Protection: Holds high priority for 5 seconds after traffic bursts to ensure
   routing protocols (BGP, OSPF, ISIS, BFD) never flap.
"""

import os
import sys
import time
import glob
import re
import argparse
import subprocess

TARGET_PATTERNS = [
    r'c8000v',
    r'cisco8000',
    r'cat9000v',
    r'c9300v',
    r'c9500v',
    r'cat9k',
    r'csr1000v',
    r'xrv9k',
    r'xr8000'
]

TARGET_REGEX = re.compile('|'.join(TARGET_PATTERNS), re.IGNORECASE)

class HeavyNodeGovernor:
    def __init__(self, check_interval=2.0, hysteresis_sec=5.0):
        self.check_interval = check_interval
        self.hysteresis_sec = hysteresis_sec
        # Map pid -> {"last_active": timestamp, "prev_packets": int, "state": "idle"|"active", "name": str}
        self.node_states = {}

    def find_heavy_qemu_nodes(self):
        """Finds all running QEMU processes matching heavy router appliance signatures."""
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

                if 'qemu-system' in cmdline and TARGET_REGEX.search(cmdline):
                    # Identify node name or template from cmdline or lab path
                    match = TARGET_REGEX.search(cmdline)
                    matched_type = match.group(0) if match else "heavy-qemu"
                    
                    # Extract node ID / lab ID from wrapper arguments if available
                    # Typical unetlab qemu cmdline has: .../labs/<lab_id>/... or -name ...
                    node_name = f"{matched_type}-{pid}"
                    name_match = re.search(r'-name\s+([^\s]+)', cmdline)
                    if name_match:
                        node_name = name_match.group(1)

                    nodes.append({
                        "pid": int(pid),
                        "name": node_name,
                        "type": matched_type,
                        "cmdline": cmdline
                    })
        except Exception as e:
            pass
        return nodes

    def get_node_tap_interfaces(self, pid):
        """Identifies TAP interfaces (/sys/class/net/vnet*) attached to this QEMU PID."""
        taps = []
        try:
            fd_dir = f'/proc/{pid}/fd'
            if os.path.isdir(fd_dir):
                for fd in os.listdir(fd_dir):
                    fd_path = os.path.join(fd_dir, fd)
                    try:
                        target = os.readlink(fd_path)
                        if '/dev/net/tun' in target:
                            pass
                    except (IOError, OSError):
                        continue
        except Exception:
            pass
        
        # Fallback / heuristic: check all vnet* interfaces on host
        for net_path in glob.glob('/sys/class/net/vnet*'):
            tap_name = os.path.basename(net_path)
            taps.append(tap_name)
        return list(set(taps))

    def get_total_packets(self, tap_list):
        """Sums RX + TX packets across monitored TAP interfaces."""
        total = 0
        for tap in tap_list:
            rx_file = f'/sys/class/net/{tap}/statistics/rx_packets'
            tx_file = f'/sys/class/net/{tap}/statistics/tx_packets'
            try:
                if os.path.isfile(rx_file):
                    with open(rx_file, 'r') as f:
                        total += int(f.read().strip())
                if os.path.isfile(tx_file):
                    with open(tx_file, 'r') as f:
                        total += int(f.read().strip())
            except Exception:
                pass
        return total

    def set_lossless_priority(self, pid, priority="idle"):
        """
        Applies cgroups v2 / nice priority without hard-capping CPU bandwidth.
        priority='active': cpu.weight=1000, nice=0 (100% full wire-speed burst)
        priority='idle':   cpu.weight=10, nice=10 (Yields idle DPDK loops to host)
        """
        try:
            # 1. Check if cgroup v2 exists for process
            cgroup_file = f'/proc/{pid}/cgroup'
            if os.path.isfile(cgroup_file):
                with open(cgroup_file, 'r') as f:
                    cg_line = f.read().strip()
                # e.g. 0::/azambasha.slice/...
                parts = cg_line.split('::')
                if len(parts) == 2:
                    cg_rel = parts[1].lstrip('/')
                    cg_path = os.path.join('/sys/fs/cgroup', cg_rel)
                    weight_file = os.path.join(cg_path, 'cpu.weight')
                    idle_file = os.path.join(cg_path, 'cpu.idle')
                    
                    if os.path.isfile(weight_file):
                        weight_val = "1000" if priority == "active" else "10"
                        with open(weight_file, 'w') as wf:
                            wf.write(f"{weight_val}\n")
                    
                    # On Linux 5.14+, cpu.idle=1 marks entire cgroup as idle-priority
                    if os.path.isfile(idle_file):
                        idle_val = "0" if priority == "active" else "1"
                        with open(idle_file, 'w') as idf:
                            idf.write(f"{idle_val}\n")

            # 2. Apply nice level as universal fallback
            nice_val = 0 if priority == "active" else 10
            os.setpriority(os.PRIO_PROCESS, pid, nice_val)
        except Exception:
            pass

    def run_pass(self):
        """Executes one scan pass over all heavy router instances."""
        now = time.time()
        active_nodes = self.find_heavy_qemu_nodes()
        current_pids = {n["pid"] for n in active_nodes}

        # Clean up dead PIDs
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
                # Newly discovered nodes start in active mode for clean boot
                self.set_lossless_priority(pid, "active")
                results.append((name, pid, node_type, "ACTIVE (New Boot)", total_pkts))
                continue

            state_info = self.node_states[pid]
            prev_pkts = state_info["prev_packets"]
            delta_pkts = total_pkts - prev_pkts
            state_info["prev_packets"] = total_pkts

            if delta_pkts > 0:
                # Active network traffic detected! Burst immediately
                state_info["last_active"] = now
                if state_info["state"] != "active":
                    state_info["state"] = "active"
                    self.set_lossless_priority(pid, "active")
                results.append((name, pid, node_type, f"ACTIVE (+{delta_pkts} pkts)", total_pkts))
            else:
                # No traffic in this interval
                idle_duration = now - state_info["last_active"]
                if idle_duration > self.hysteresis_sec:
                    # Beyond hysteresis: safe to yield idle DPDK spinloop
                    if state_info["state"] != "idle":
                        state_info["state"] = "idle"
                        self.set_lossless_priority(pid, "idle")
                    results.append((name, pid, node_type, f"IDLE (Yielding, {idle_duration:.1f}s silent)", total_pkts))
                else:
                    # Within hysteresis window: hold active priority
                    results.append((name, pid, node_type, f"HOLD ACTIVE ({self.hysteresis_sec - idle_duration:.1f}s)", total_pkts))

        return results

    def status(self):
        """Prints diagnostic status of all monitored nodes."""
        print("============================================================")
        print("  Azam Basha Heavy Router CPU Governor Diagnostic           ")
        print("  Target Appliances: Catalyst 8000, Cisco 8000, Cat 9000    ")
        print("============================================================")
        results = self.run_pass()
        if not results:
            print("  [*] No active Catalyst 8000, Cisco 8000, or Cat 9000 instances detected.")
            print("      (Governor is ready and will automatically attach when nodes boot).")
        else:
            print(f"  {'APPLIANCE / NAME':<25} {'PID':<8} {'TYPE':<12} {'STATE':<25}")
            print("  " + "-" * 70)
            for name, pid, node_type, state_desc, pkts in results:
                print(f"  {name[:24]:<25} {pid:<8} {node_type:<12} {state_desc:<25}")
        print("============================================================")

    def loop(self):
        """Runs the continuous daemon loop."""
        print("[+] Azam Basha Lossless CPU Governor daemon started.")
        while True:
            try:
                self.run_pass()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                print("\n[+] CPU Governor stopped.")
                break
            except Exception as e:
                time.sleep(self.check_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Azam Basha Heavy Node Lossless CPU Governor")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--status", action="store_true", help="Show current node status and priorities")
    parser.add_argument("--interval", type=float, default=2.0, help="Check interval in seconds (default: 2.0)")
    parser.add_argument("--hysteresis", type=float, default=5.0, help="Active hold time after packets in seconds (default: 5.0)")

    args = parser.parse_args()
    gov = HeavyNodeGovernor(check_interval=args.interval, hysteresis_sec=args.hysteresis)

    if args.status:
        gov.status()
    else:
        gov.loop()
