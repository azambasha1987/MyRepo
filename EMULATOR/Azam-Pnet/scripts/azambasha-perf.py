#!/usr/bin/env python3
"""
==============================================================================
Azam Basha Live Lab Performance Profiler & Hot-Node Detector (azam-perf)
==============================================================================
Reads /proc/<PID>/stat for every active QEMU/IOL process and displays a
live color-coded ranking table of nodes sorted by CPU%, RAM, and I/O.
--kill-hot flag pauses (SIGSTOP) the top CPU offender temporarily.
==============================================================================
"""

import os
import sys
import time
import argparse
import subprocess
import re

# ANSI colors
GREEN  = "\033[1;32m"
YELLOW = "\033[1;33m"
RED    = "\033[1;31m"
CYAN   = "\033[1;36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

CPU_WARN  = 40.0   # % above which a node is flagged as HOT
CPU_CRIT  = 80.0   # % above which a node is CRITICAL
MEM_WARN  = 2048   # MB resident above which node is flagged

TICK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def get_node_procs():
    """
    Scan /proc for QEMU and IOL processes.
    Returns list of dicts: {pid, name, cmd, utime, stime, rss_mb}.
    """
    procs = []
    try:
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmd = f.read().replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
                if not ("qemu-system" in cmd or (re.search(r'iol.*\.bin', cmd) and ".bin" in cmd)):
                    continue

                with open(f"/proc/{pid}/stat", "r") as f:
                    stat = f.read().split()
                utime = int(stat[13])    # user mode jiffies
                stime = int(stat[14])    # kernel mode jiffies
                rss   = int(stat[23])    # RSS in pages

                name = extract_node_name(cmd)
                procs.append({
                    "pid": pid,
                    "name": name,
                    "cmd": cmd,
                    "utime": utime,
                    "stime": stime,
                    "rss_mb": (rss * PAGE) // (1024 * 1024),
                    "total_jiffies": utime + stime,
                    "cpu_pct": 0.0,
                })
            except (FileNotFoundError, IndexError, ValueError):
                continue
    except PermissionError:
        pass
    return procs


def compute_cpu(sample1: list, sample2: list, elapsed: float) -> list:
    """
    Compute CPU% for each process between two samples.
    CPU% = (delta_jiffies / TICK) / elapsed * 100 * num_cpus
    """
    num_cpus = os.cpu_count() or 1
    pid_map = {p["pid"]: p for p in sample1}
    results = []
    for p2 in sample2:
        p1 = pid_map.get(p2["pid"])
        if p1:
            delta = p2["total_jiffies"] - p1["total_jiffies"]
            cpu_pct = (delta / TICK) / elapsed * 100.0
            p2["cpu_pct"] = min(cpu_pct, num_cpus * 100.0)
        results.append(p2)
    return sorted(results, key=lambda x: x["cpu_pct"], reverse=True)


def extract_node_name(cmdline: str) -> str:
    """Parse a human-readable node name from QEMU cmdline."""
    m = re.search(r'-name\s+"?([^"\s]+)"?', cmdline)
    if m:
        return m.group(1)[:24]
    m2 = re.search(r'(qemu-system-\w+)', cmdline)
    if m2:
        return m2.group(1)
    m3 = re.search(r'(\w+\.bin)', cmdline)
    if m3:
        return m3.group(1)[:24]
    return "unknown"


def get_mem_info() -> dict:
    """Read /proc/meminfo for cluster-wide memory stats."""
    info = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k.strip()] = int(v.strip().split()[0])
    except Exception:
        pass
    return info


def get_disk_io(pid: int) -> dict:
    """Read /proc/<pid>/io for process-level disk I/O."""
    io = {"read_mb": 0.0, "write_mb": 0.0}
    try:
        with open(f"/proc/{pid}/io", "r") as f:
            for line in f:
                if line.startswith("read_bytes:"):
                    io["read_mb"] = int(line.split(":")[1]) / (1024 * 1024)
                elif line.startswith("write_bytes:"):
                    io["write_mb"] = int(line.split(":")[1]) / (1024 * 1024)
    except (FileNotFoundError, PermissionError):
        pass
    return io


def color_cpu(pct: float) -> str:
    val = f"{pct:6.1f}%"
    if pct >= CPU_CRIT:
        return f"{RED}{BOLD}{val}{RESET}"
    if pct >= CPU_WARN:
        return f"{YELLOW}{val}{RESET}"
    return f"{GREEN}{val}{RESET}"


def color_mem(mb: int) -> str:
    val = f"{mb:6} MB"
    if mb >= MEM_WARN * 2:
        return f"{RED}{BOLD}{val}{RESET}"
    if mb >= MEM_WARN:
        return f"{YELLOW}{val}{RESET}"
    return f"{GREEN}{val}{RESET}"


def render_table(procs: list, iteration: int):
    os.system("clear")
    print(f"{CYAN}{'='*84}{RESET}")
    print(f"{BOLD}  Azam-Pnet Live Lab Performance Profiler — Hot Node Detector  "
          f"(refresh #{iteration}){RESET}")
    print(f"{CYAN}{'='*84}{RESET}")

    mem = get_mem_info()
    total_mb = mem.get("MemTotal", 0) // 1024
    avail_mb = mem.get("MemAvailable", 0) // 1024
    used_mb  = total_mb - avail_mb
    mem_bar_pct = (used_mb / total_mb * 100) if total_mb else 0

    print(f"  Cluster RAM:  {used_mb:,} / {total_mb:,} MB used  ({mem_bar_pct:.1f}%)")
    print(f"  Node procs:   {len(procs)} QEMU/IOL processes active")
    print(f"  Time:         {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{CYAN}{'-'*84}{RESET}")

    header = f"{'#':>3}  {'Node Name':<26} {'PID':>7}  {'CPU%':>7}  {'RAM':>9}  {'DiskR':>8}  {'DiskW':>8}  Status"
    print(f"{BOLD}{header}{RESET}")
    print(f"{DIM}{'-'*84}{RESET}")

    hot_count = 0
    for i, p in enumerate(procs[:20], start=1):
        io = get_disk_io(p["pid"])
        status = ""
        if p["cpu_pct"] >= CPU_CRIT:
            status = f"{RED}● CRITICAL{RESET}"
            hot_count += 1
        elif p["cpu_pct"] >= CPU_WARN:
            status = f"{YELLOW}● HOT{RESET}"
            hot_count += 1
        else:
            status = f"{GREEN}● OK{RESET}"

        row = (
            f"{i:>3}. "
            f"{p['name']:<26} "
            f"{p['pid']:>7}  "
            f"{color_cpu(p['cpu_pct']):>7}  "
            f"{color_mem(p['rss_mb']):>9}  "
            f"{io['read_mb']:>7.1f}M  "
            f"{io['write_mb']:>7.1f}M  "
            f"{status}"
        )
        print(row)

    print(f"{CYAN}{'='*84}{RESET}")
    if hot_count > 0:
        print(f"  {YELLOW}{BOLD}⚠  {hot_count} node(s) running HOT — "
              f"consider suspending or migrating.{RESET}")
        print(f"  Kill top offender: {BOLD}azam-perf --kill-hot{RESET}")
    else:
        print(f"  {GREEN}All nodes within normal operating parameters.{RESET}")
    print(f"{CYAN}{'='*84}{RESET}")
    print(f"  {DIM}Press Ctrl+C to exit | --once for single snapshot | "
          f"--interval N for refresh rate{RESET}")


def kill_hot(procs: list, dry_run: bool = False):
    if not procs:
        print("[!] No node processes found.")
        return
    top = procs[0]
    print(f"[*] Top CPU offender: {top['name']} (PID {top['pid']}) at {top['cpu_pct']:.1f}% CPU")
    if dry_run:
        print(f"[DRY-RUN] Would send SIGSTOP to PID {top['pid']}")
        return
    try:
        import signal as _sig
        os.kill(top["pid"], _sig.SIGSTOP)
        print(f"[✔] Sent SIGSTOP to PID {top['pid']} — node paused.")
        print(f"    Resume with: sudo kill -CONT {top['pid']}")
    except PermissionError:
        print("[!] Permission denied. Run as root: sudo azam-perf --kill-hot")
    except ProcessLookupError:
        print("[!] Process no longer exists.")


def install_symlink():
    if sys.platform != "win32":
        try:
            target = "/usr/local/bin/azam-perf"
            source = os.path.realpath(__file__)
            if not os.path.exists(target) or os.path.realpath(target) != source:
                if os.path.exists(target):
                    os.remove(target)
                os.symlink(source, target)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Azam-Pnet Live Lab Performance Profiler & Hot-Node Detector"
    )
    parser.add_argument("--interval", "-i", type=int, default=3,
                        help="Refresh interval in seconds (default: 3)")
    parser.add_argument("--once", action="store_true",
                        help="Print one snapshot and exit (non-interactive)")
    parser.add_argument("--kill-hot", action="store_true",
                        help="Send SIGSTOP to the top CPU offender (requires root)")
    parser.add_argument("--resume", type=int, metavar="PID",
                        help="Resume a SIGSTOP-paused node by PID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate --kill-hot without actually sending signal")
    args = parser.parse_args()

    install_symlink()

    if args.resume:
        import signal as _sig
        try:
            os.kill(args.resume, _sig.SIGCONT)
            print(f"[✔] Sent SIGCONT to PID {args.resume} — node resumed.")
        except Exception as e:
            print(f"[!] Could not resume PID {args.resume}: {e}")
        return

    # Take two samples to compute CPU delta
    print("[*] Sampling CPU usage (1 second)...")
    s1 = get_node_procs()
    time.sleep(1.0)
    s2 = get_node_procs()
    procs = compute_cpu(s1, s2, 1.0)

    if args.kill_hot:
        kill_hot(procs, dry_run=args.dry_run)
        return

    if args.once:
        render_table(procs, 1)
        return

    # Live refresh loop
    iteration = 1
    try:
        while True:
            render_table(procs, iteration)
            time.sleep(args.interval)
            s1 = s2
            s2 = get_node_procs()
            procs = compute_cpu(s1, s2, float(args.interval))
            iteration += 1
    except KeyboardInterrupt:
        print(f"\n{RESET}[*] azam-perf exited.")


if __name__ == "__main__":
    main()
