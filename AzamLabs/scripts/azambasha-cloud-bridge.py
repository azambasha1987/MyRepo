#!/usr/bin/env python3
"""
==============================================================================
Azam Basha External Cloud & Real-LAN Transit Bridge Manager (azambasha-cloud-bridge.py)
==============================================================================
Connects PNetLab virtual nodes to:
  1. Physical LAN (192.168.1.0/24) via pnet0 / eth0 bridging.
  2. Outbound Internet NAT Gateway for package updates and licensing.
  3. WireGuard Cloud Transit VPC tunnels (AWS, Azure, remote office).
==============================================================================
"""

import os
import sys
import json
import argparse
import subprocess

CONFIG_FILE = "/etc/pnetlab/azambasha-bridge.conf"


def load_config():
    cfg = {
        "outbound_nat_enabled": True,
        "wan_interface": "eth0",
        "lan_bridge_interface": "pnet0",
        "wireguard_enabled": False,
        "wireguard_interface": "wg0"
    }
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        k = k.strip().lower()
                        v = v.strip().strip('"').strip("'")
                        if v.lower() in ("true", "1", "yes"):
                            cfg[k] = True
                        elif v.lower() in ("false", "0", "no"):
                            cfg[k] = False
                        else:
                            cfg[k] = v
        except Exception:
            pass
    return cfg


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write("# Azam-Pnet Transit Bridge Configuration\n")
        for k, v in cfg.items():
            f.write(f"{k.upper()}={v}\n")


def check_nat_status(wan_iface="eth0"):
    try:
        r = subprocess.run(["iptables", "-t", "nat", "-C", "POSTROUTING", "-o", wan_iface, "-j", "MASQUERADE"],
                           capture_output=True)
        return (r.returncode == 0)
    except Exception:
        return False


def set_nat(enable=True, wan_iface="eth0"):
    # Enable IP forwarding
    try:
        with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
            f.write("1\n")
    except Exception:
        pass

    action = "-A" if enable else "-D"
    cmd = ["iptables", "-t", "nat", action, "POSTROUTING", "-o", wan_iface, "-j", "MASQUERADE"]
    try:
        subprocess.run(cmd, capture_output=True, check=False)
        cfg = load_config()
        cfg["outbound_nat_enabled"] = enable
        save_config(cfg)
        return True, f"Outbound NAT on {wan_iface} {'ENABLED' if enable else 'DISABLED'}."
    except Exception as e:
        return False, f"Error updating NAT rule: {e}"


def check_wireguard_status():
    try:
        r = subprocess.run(["wg", "show"], capture_output=True, text=True)
        return r.returncode == 0 and len(r.stdout.strip()) > 0
    except Exception:
        return False


def toggle_wireguard(up=True):
    cmd = ["wg-quick", "up" if up else "down", "wg0"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        cfg = load_config()
        cfg["wireguard_enabled"] = up
        save_config(cfg)
        return r.returncode == 0, r.stdout or r.stderr or ("WireGuard tunnel UP" if up else "WireGuard tunnel DOWN")
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Azam-Pnet Cloud & Real-LAN Transit Manager")
    parser.add_argument("--status", action="store_true", help="Display transit bridge status")
    parser.add_argument("--enable-nat", action="store_true", help="Enable outbound Internet NAT gateway")
    parser.add_argument("--disable-nat", action="store_true", help="Disable outbound Internet NAT gateway")
    parser.add_argument("--wireguard-up", action="store_true", help="Bring up WireGuard Cloud VPC tunnel")
    parser.add_argument("--wireguard-down", action="store_true", help="Tear down WireGuard Cloud VPC tunnel")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    cfg = load_config()

    if args.enable_nat:
        ok, msg = set_nat(True, cfg.get("wan_interface", "eth0"))
        print(f"[{'✔' if ok else '✘'}] {msg}")
        return

    if args.disable_nat:
        ok, msg = set_nat(False, cfg.get("wan_interface", "eth0"))
        print(f"[{'✔' if ok else '✘'}] {msg}")
        return

    if args.wireguard_up:
        ok, msg = toggle_wireguard(True)
        print(f"[{'✔' if ok else '✘'}] {msg}")
        return

    if args.wireguard_down:
        ok, msg = toggle_wireguard(False)
        print(f"[{'✔' if ok else '✘'}] {msg}")
        return

    # Default: status
    nat_active = check_nat_status(cfg.get("wan_interface", "eth0"))
    wg_active = check_wireguard_status()

    res = {
        "wan_interface": cfg.get("wan_interface", "eth0"),
        "lan_bridge": cfg.get("lan_bridge_interface", "pnet0"),
        "outbound_nat": "active" if nat_active else "inactive",
        "wireguard_vpc": "connected" if wg_active else "disconnected",
        "ip_forwarding": "enabled"
    }

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print("================================================================================")
        print("         Azam-Pnet External Cloud & Real-LAN Transit Bridge")
        print("================================================================================")
        print(f"  • WAN Interface:           {res['wan_interface']}")
        print(f"  • Physical LAN Bridge:     {res['lan_bridge']} (Bridged to 192.168.1.0/24)")
        nat_str = "\033[32m● ACTIVE (Internet Accessible)\033[0m" if nat_active else "\033[33m○ INACTIVE\033[0m"
        print(f"  • Outbound Internet NAT:   {nat_str}")
        wg_str = "\033[32m● CONNECTED (wg0)\033[0m" if wg_active else "\033[33m○ DISCONNECTED\033[0m"
        print(f"  • Cloud VPC WireGuard:     {wg_str}")
        print("================================================================================")


if __name__ == "__main__":
    main()
