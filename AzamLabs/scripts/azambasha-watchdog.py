#!/usr/bin/env python3
"""
==============================================================================
Azam Basha Node Failure Detection & Auto-Recovery Watchdog (azam-watchdog)
==============================================================================
A systemd-compatible daemon that monitors every active QEMU/IOL process,
detects silent crashes, auto-recovers nodes via PNetLab REST API,
and dispatches WhatsApp alerts when a node fails and is recovered.
==============================================================================
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import ssl

WATCHDOG_LOG = "/opt/azambasha/logs/watchdog.log"
PID_FILE = "/var/run/azam-watchdog.pid"
NOTIFY_SCRIPT = "/opt/azambasha/scripts/azambasha-notify.py"
NOTIFY_CONF = "/etc/pnetlab/azambasha-notify.conf"
POLL_INTERVAL = 30  # seconds between health checks


def setup_logging(log_file=WATCHDOG_LOG):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_running_qemu_pids():
    """Return dict of {pid: cmdline} for all active qemu-system processes."""
    pids = {}
    try:
        result = subprocess.run(
            ["pgrep", "-a", "-f", "qemu-system"],
            capture_output=True, text=True
        )
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) >= 1:
                try:
                    pid = int(parts[0])
                    cmd = parts[1] if len(parts) > 1 else ""
                    pids[pid] = cmd
                except ValueError:
                    continue
    except Exception:
        pass
    return pids


def get_running_iol_pids():
    """Return dict of {pid: cmdline} for all active IOL processes."""
    pids = {}
    try:
        result = subprocess.run(
            ["pgrep", "-a", "-f", r"iol.*\.bin"],
            capture_output=True, text=True
        )
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) >= 1:
                try:
                    pid = int(parts[0])
                    cmd = parts[1] if len(parts) > 1 else ""
                    pids[pid] = cmd
                except ValueError:
                    continue
    except Exception:
        pass
    return pids


def pid_alive(pid: int) -> bool:
    """Check if a PID is still alive."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def extract_node_info(cmdline: str) -> dict:
    """Parse QEMU cmdline to extract lab session, tenant, node ID."""
    info = {"session": None, "tenant": None, "node_id": None, "lab": None, "name": None}
    # Parse UNetLab-style naming from cmdline: -name "pnet_<tenant>@<session>_<nodeid>"
    import re
    m = re.search(r'-name\s+"?pnet_(\d+)@(\d+)_(\d+)"?', cmdline)
    if m:
        info["tenant"] = m.group(1)
        info["session"] = m.group(2)
        info["node_id"] = m.group(3)
    # Try to extract lab path from pidfile or socket path
    m2 = re.search(r'/opt/unetlab/tmp/(\d+)/([^/]+)/(\d+)', cmdline)
    if m2:
        info["tenant"] = m2.group(1)
        info["session"] = m2.group(2)
        info["node_id"] = m2.group(3)
    return info


def send_alert(title: str, message: str):
    """Send WhatsApp/webhook alert via azambasha-notify.py if configured."""
    if not os.path.isfile(NOTIFY_SCRIPT):
        return
    if not os.path.isfile(NOTIFY_CONF):
        return
    try:
        subprocess.run(
            [sys.executable, NOTIFY_SCRIPT, "--title", title, "--message", message],
            timeout=30, check=False
        )
    except Exception as e:
        logging.warning(f"Alert dispatch failed: {e}")


def attempt_node_recovery(node_info: dict, master_ip: str, password: str) -> bool:
    """Attempt to restart a dead node via the PNetLab REST API."""
    tenant = node_info.get("tenant")
    session = node_info.get("session")
    node_id = node_info.get("node_id")

    if not all([tenant, session, node_id]):
        return False

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            urllib.request.HTTPSHandler(context=ctx)
        )

        # Login
        login_data = json.dumps({"username": "admin", "password": password}).encode("utf-8")
        req = urllib.request.Request(
            f"https://{master_ip}/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/json"}
        )
        with opener.open(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("status") != "success":
                return False

        # Attempt node start via session API
        start_req = urllib.request.Request(
            f"https://{master_ip}/api/labs/session/nodes/{node_id}/start",
            headers={"Content-Type": "application/json"}
        )
        with opener.open(start_req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("status") == "success"

    except Exception as e:
        logging.warning(f"Recovery API call failed: {e}")
        return False


def write_pid():
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def remove_pid():
    try:
        os.remove(PID_FILE)
    except Exception:
        pass


RUNNING = True


def handle_signal(signum, frame):
    global RUNNING
    logging.info(f"[watchdog] Received signal {signum}, shutting down gracefully.")
    RUNNING = False


def cleanup_orphaned_interfaces():
    """If no active nodes/emulators are running, prune any orphaned vunl/ser interfaces."""
    try:
        # Extra check: make sure no dynamips processes exist
        res = subprocess.run(["pgrep", "-f", "dynamips"], capture_output=True, text=True)
        if res.stdout.strip():
            return

        res = subprocess.run(["ip", "-o", "link", "show"], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                dev = parts[1].strip().split("@")[0]
                if (dev.startswith("vunl") or dev.startswith("ser")) and "_" in dev:
                    subprocess.run(["ip", "link", "delete", dev], capture_output=True)
                    logging.info(f"[watchdog] Cleaned orphaned interface {dev}")
    except Exception as e:
        logging.debug(f"[watchdog] Interface cleanup exception: {e}")


def run_watchdog(master_ip: str, password: str, poll: int = POLL_INTERVAL):
    """Main watchdog loop."""
    setup_logging()
    write_pid()
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logging.info("=" * 72)
    logging.info("  Azam-Pnet Node Failure Detection & Auto-Recovery Watchdog STARTED")
    logging.info(f"  Master: https://{master_ip} | Poll interval: {poll}s")
    logging.info("=" * 72)

    # Known running PIDs from last cycle: {pid: cmdline}
    known_pids: dict = {}

    while RUNNING:
        current_qemu = get_running_qemu_pids()
        current_iol = get_running_iol_pids()
        current_all = {**current_qemu, **current_iol}

        # Detect new nodes that just appeared (add to tracking)
        for pid, cmd in current_all.items():
            if pid not in known_pids:
                info = extract_node_info(cmd)
                logging.info(f"[watchdog] Tracking new node PID {pid} "
                             f"(node_id={info.get('node_id')}, session={info.get('session')})")
                known_pids[pid] = {"cmd": cmd, "info": info, "crash_count": 0}

        # Detect PIDs that disappeared (potential crash)
        dead_pids = [pid for pid in list(known_pids.keys()) if pid not in current_all]
        for pid in dead_pids:
            entry = known_pids.pop(pid, {})
            info = entry.get("info", {})
            crash_count = entry.get("crash_count", 0) + 1
            node_id = info.get("node_id", "unknown")
            session = info.get("session", "unknown")

            logging.warning(f"[watchdog] CRASH DETECTED! PID {pid} died "
                            f"(node_id={node_id}, session={session}, crash #{crash_count})")

            # Attempt recovery if we have enough info
            if info.get("node_id") and info.get("session"):
                logging.info(f"[watchdog] Attempting auto-recovery for node {node_id}...")
                recovered = attempt_node_recovery(info, master_ip, password)
                if recovered:
                    logging.info(f"[watchdog] Node {node_id} successfully auto-recovered!")
                    send_alert(
                        "Azam-Pnet: Node Auto-Recovered",
                        f"Node ID {node_id} (session {session}) crashed and was automatically restarted.\n"
                        f"Crash count: {crash_count}. Check /opt/azambasha/logs/watchdog.log for details."
                    )
                else:
                    logging.error(f"[watchdog] Auto-recovery FAILED for node {node_id}.")
                    send_alert(
                        "ALERT: Azam-Pnet Node FAILED",
                        f"Node ID {node_id} (session {session}) crashed and auto-recovery FAILED.\n"
                        f"Manual intervention required! Crash count: {crash_count}."
                    )
            else:
                logging.warning(f"[watchdog] Insufficient metadata to attempt recovery for PID {pid}.")

        # Periodic check for orphaned interfaces if no emulators are running
        if not current_all:
            cleanup_orphaned_interfaces()

        time.sleep(poll)

    remove_pid()
    logging.info("[watchdog] Watchdog stopped cleanly.")


def install_systemd_service():
    """Install azam-watchdog as a systemd service."""
    service_content = f"""[Unit]
Description=Azam-Pnet Node Failure Detection & Auto-Recovery Watchdog
After=network.target mysql.service apache2.service
Wants=network.target

[Service]
Type=simple
ExecStart={sys.executable} {os.path.realpath(__file__)} --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    service_path = "/etc/systemd/system/azam-watchdog.service"
    try:
        with open(service_path, "w") as f:
            f.write(service_content)
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "enable", "--now", "azam-watchdog.service"], check=False)
        print(f"[✔] azam-watchdog installed and started as systemd service.")
        print(f"    Status: sudo systemctl status azam-watchdog.service")
        print(f"    Logs:   sudo journalctl -fu azam-watchdog.service")
        print(f"    File:   {WATCHDOG_LOG}")
    except Exception as e:
        print(f"[!] Systemd install failed: {e}")


def install_symlink():
    if sys.platform != "win32":
        try:
            target = "/usr/local/bin/azam-watchdog"
            source = os.path.realpath(__file__)
            if not os.path.exists(target) or os.path.realpath(target) != source:
                if os.path.exists(target):
                    os.remove(target)
                os.symlink(source, target)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Azam-Pnet Node Watchdog")
    parser.add_argument("--host", default="127.0.0.1",
                        help="PNetLab master IP (default: 127.0.0.1 for local)")
    parser.add_argument("--password", default="azam",
                        help="PNetLab admin password (default: azam)")
    parser.add_argument("--poll", type=int, default=POLL_INTERVAL,
                        help=f"Poll interval in seconds (default: {POLL_INTERVAL})")
    parser.add_argument("--install", action="store_true",
                        help="Install as systemd service and start automatically")
    parser.add_argument("--daemon", action="store_true",
                        help="Run as daemon (used by systemd)")
    parser.add_argument("--status", action="store_true",
                        help="Show watchdog status and recent crash log")
    args = parser.parse_args()

    install_symlink()

    if args.install:
        install_systemd_service()
        return

    if args.status:
        print("[*] Azam-Pnet Watchdog Status:")
        subprocess.run(["systemctl", "status", "azam-watchdog.service", "--no-pager"],
                       check=False)
        if os.path.isfile(WATCHDOG_LOG):
            print("\n[*] Last 20 log entries:")
            subprocess.run(["tail", "-n", "20", WATCHDOG_LOG], check=False)
        return

    run_watchdog(master_ip=args.host, password=args.password, poll=args.poll)


if __name__ == "__main__":
    main()
