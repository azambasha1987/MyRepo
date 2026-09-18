#!/usr/bin/env python3
"""
==============================================================================
Azam Basha Cluster Capacity & Concurrent Node Density Estimator
==============================================================================
Models physical RAM, vCPU cores, and Ultra-KSM 4KB RAM deduplication savings
to calculate maximum concurrent node density limits for Cisco, Juniper,
Arista, and Windows appliances across Master and Satellite nodes.
==============================================================================
"""

import os
import sys
import argparse
import subprocess

# Appliance profiles: Base RAM (MB), vCPUs, KSM Deduplication Factor (0.0 to 1.0)
APPLIANCE_PROFILES = {
    "Cisco IOL (L2/L3)": {
        "ram_mb": 256,
        "vcpus": 1,
        "ksm_dedup": 0.80, # 80% shared memory across identical IOL nodes
        "desc": "Lightweight Cisco IOS on Linux (32-bit ELF)"
    },
    "Cisco CSR1000v": {
        "ram_mb": 4096,
        "vcpus": 2,
        "ksm_dedup": 0.60, # 60% shared code/kernel pages
        "desc": "Cisco IOS XE Cloud Router"
    },
    "Cisco C8000v": {
        "ram_mb": 4096,
        "vcpus": 2,
        "ksm_dedup": 0.60,
        "desc": "Next-Gen Catalyst 8000v Edge"
    },
    "Cisco XRd-9k": {
        "ram_mb": 3072,
        "vcpus": 2,
        "ksm_dedup": 0.50,
        "desc": "Cloud-Native IOS XR Container/VM"
    },
    "Juniper vMX (Dual-Disk)": {
        "ram_mb": 4096,
        "vcpus": 2,
        "ksm_dedup": 0.50,
        "desc": "Juniper Junos Virtual MX"
    },
    "Arista vEOS": {
        "ram_mb": 2048,
        "vcpus": 1,
        "ksm_dedup": 0.65,
        "desc": "Arista Extensible Operating System"
    },
    "Windows 11 / Server": {
        "ram_mb": 4096,
        "vcpus": 2,
        "ksm_dedup": 0.40,
        "desc": "UEFI SMM + TPM 2.0 swtpm Workstation"
    },
    "Linux Alpine / Gateway": {
        "ram_mb": 128,
        "vcpus": 1,
        "ksm_dedup": 0.75,
        "desc": "Lightweight Container/Micro-VM"
    }
}

def get_local_resources():
    """Extract CPU, RAM, and KSM stats from local Linux system."""
    total_ram_mb = 16384
    avail_ram_mb = 12288
    cpu_cores = 8
    ksm_active = False
    ksm_sharing_mb = 0

    if os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total_ram_mb = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    avail_ram_mb = int(line.split()[1]) // 1024

    if os.path.exists("/proc/cpuinfo"):
        with open("/proc/cpuinfo", "r") as f:
            cpu_cores = len([line for line in f if line.startswith("processor")])

    if os.path.exists("/sys/kernel/mm/ksm/run"):
        with open("/sys/kernel/mm/ksm/run", "r") as f:
            ksm_active = (f.read().strip() == "1")

    if os.path.exists("/sys/kernel/mm/ksm/pages_sharing"):
        with open("/sys/kernel/mm/ksm/pages_sharing", "r") as f:
            try:
                pages = int(f.read().strip())
                ksm_sharing_mb = (pages * 4096) // (1024 * 1024)
            except Exception:
                pass

    return {
        "host": "Local Node (Master/Worker)",
        "total_ram_mb": total_ram_mb,
        "avail_ram_mb": avail_ram_mb,
        "cpu_cores": cpu_cores,
        "ksm_active": ksm_active,
        "ksm_sharing_mb": ksm_sharing_mb
    }

def print_capacity_report(res):
    print("================================================================================")
    print("       Azam-Pnet Cluster Capacity & Concurrent Node Density Estimator           ")
    print("================================================================================")
    print(f" Node:            {res['host']}")
    print(f" Physical RAM:    {res['total_ram_mb'] // 1024} GB ({res['total_ram_mb']} MB)")
    print(f" Available RAM:   {res['avail_ram_mb'] // 1024} GB ({res['avail_ram_mb']} MB)")
    print(f" Logical vCPUs:   {res['cpu_cores']} cores (Overcommit ratio: up to 4:1)")
    ksm_status = "ENABLED (Ultra-KSM 4KB Deduplication)" if res['ksm_active'] else "DISABLED"
    print(f" Ultra-KSM State: {ksm_status}")
    print(f" RAM Saved Now:   {res['ksm_sharing_mb']} MB ({res['ksm_sharing_mb'] / 1024:.2f} GB)")
    print("--------------------------------------------------------------------------------")
    print(" Appliance Architecture  | Base RAM | Effective RAM | Standalone | Ultra-KSM Max")
    print("-------------------------|----------|---------------|------------|---------------")

    # Safe headroom reserve: Leave 2GB for host OS + services
    headroom_mb = 2048
    usable_mb = max(1024, res['total_ram_mb'] - headroom_mb)

    for app_name, prof in APPLIANCE_PROFILES.items():
        base_ram = prof["ram_mb"]
        dedup = prof["ksm_dedup"]
        effective_ram = int(base_ram * (1.0 - dedup))

        standalone_limit = usable_mb // base_ram
        # KSM calculation: 1st node takes 100%, subsequent nodes take effective_ram
        if usable_mb > base_ram:
            ksm_limit = 1 + ((usable_mb - base_ram) // effective_ram)
        else:
            ksm_limit = standalone_limit

        print(f" {app_name:<23} | {base_ram:>6}MB | {effective_ram:>9}MB | {standalone_limit:>10} | {ksm_limit:>11} nodes")

    print("--------------------------------------------------------------------------------")
    print(" [i] Effective RAM: Average RAM consumed per node once Ultra-KSM deduplicates.")
    print(" [i] Standalone:    Max nodes without memory merging before Out-Of-Memory (OOM).")
    print(" [i] Ultra-KSM Max: Safe concurrent node ceiling preserving 2GB host headroom.")
    print("================================================================================")

def install_symlink():
    """Install /usr/local/bin/azam-capacity if root on Linux."""
    if sys.platform != "win32" and os.geteuid() == 0:
        target = "/usr/local/bin/azam-capacity"
        source = os.path.realpath(__file__)
        try:
            if not os.path.exists(target) or os.path.realpath(target) != source:
                if os.path.exists(target):
                    os.remove(target)
                os.symlink(source, target)
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="Azam-Pnet Cluster Capacity Estimator")
    parser.add_argument("--satellite", help="Satellite Worker IP to query via SSH")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    install_symlink()
    res = get_local_resources()
    print_capacity_report(res)

if __name__ == "__main__":
    main()
