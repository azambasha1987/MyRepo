#!/usr/bin/env python3
"""
==============================================================================
Azam-Pnet Operations Dashboard Backend API (azam-ops-api.py)
Runs on port 8889, proxied by Apache at /azam-ops/api/
Provides secure whitelisted execution of azam-* CLI tools
and streams real-time output via Server-Sent Events (SSE).
==============================================================================
"""
import os, sys, json, subprocess, threading, queue, time, signal, shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 8889
PID_FILE = "/var/run/azam-ops-api.pid"

# ──────────────────────────────────────────────────────────────────────────────
# Whitelisted commands (name → real command)
# ──────────────────────────────────────────────────────────────────────────────
COMMANDS = {
    # Health & Monitoring
    "fleet":         ["bash", "/usr/local/bin/azam-fleet"],
    "capacity":      ["python3", "/usr/local/bin/azam-capacity"],
    "doctor":        ["bash", "/usr/local/bin/azam-doctor", "--check"],
    "doctor-compress":["bash", "/usr/local/bin/azam-doctor", "--compress"],
    "perf":          ["python3", "/usr/local/bin/azam-perf", "--once"],
    "watchdog-status":["python3", "/usr/local/bin/azam-watchdog", "--status"],
    "watchdog-install":["python3", "/usr/local/bin/azam-watchdog", "--install"],

    # Backup & Restore
    "backup":        ["bash", "/usr/local/bin/azam-backup", "--backup"],
    "backup-list":   ["bash", "/usr/local/bin/azam-backup", "--list"],

    # Network & Dataplane
    "bench":         None,   # requires SATELLITE_IP param
    "console-fix":   ["bash", "/usr/local/bin/azam-console-fix", "--fix"],
    "console-check": ["bash", "/usr/local/bin/azam-console-fix", "--check"],

    # Security & SSL
    "ssl-status":    ["bash", "/usr/local/bin/azam-ssl", "--status"],
    "ssl-generate":  ["bash", "/usr/local/bin/azam-ssl", "--generate"],

    # Templates
    "templates-list":["bash", "/usr/local/bin/azam-templates", "list"],

    # Topology Git
    "topology-snapshot": ["python3", "/usr/local/bin/azam-topology-git", "--snapshot"],

    # Scanner
    "scanner":       ["python3", "/opt/azambasha/scripts/azambasha-weekly-codeberg-scanner.py"],

    # Notifications
    "notify-test":   ["python3", "/usr/local/bin/azam-notify", "--test"],
    "notify-send":   None,

    # AI Lab Copilot
    "ai-generate":        None,
    "ai-diagnose":        None,
    "ai-templates":       ["python3", "/opt/azambasha/scripts/azambasha-ai-copilot.py", "--list-templates"],

    # Config Diff & Rollback
    "config-snapshot":    ["python3", "/opt/azambasha/scripts/azambasha-config-diff.py", "--snapshot"],
    "config-nodes":       ["python3", "/opt/azambasha/scripts/azambasha-config-diff.py", "--nodes"],
    "config-diff":        None,
    "config-rollback":    None,

    # Ping Mesh & Traffic Gen
    "mesh-sweep":         ["python3", "/opt/azambasha/scripts/azambasha-ping-mesh.py", "--sweep"],
    "mesh-traffic":       None,

    # Scheduler & Quotas
    "scheduler-status":   ["python3", "/opt/azambasha/scripts/azambasha-scheduler.py", "--status"],
    "scheduler-check":    ["python3", "/opt/azambasha/scripts/azambasha-scheduler.py", "--check"],
    "scheduler-stop-idle":["python3", "/opt/azambasha/scripts/azambasha-scheduler.py", "--stop-idle"],
    "scheduler-install":  ["python3", "/opt/azambasha/scripts/azambasha-scheduler.py", "--install"],

    # Cloud & Offsite Backup
    "cloud-status":       ["python3", "/opt/azambasha/scripts/azambasha-cloud-backup.py", "--status"],
    "cloud-sync":         ["python3", "/opt/azambasha/scripts/azambasha-cloud-backup.py", "--sync"],
    "cloud-list":         ["python3", "/opt/azambasha/scripts/azambasha-cloud-backup.py", "--list-remote"],
}

def get_cluster_stats():
    stats = {}
    # RAM
    try:
        with open("/proc/meminfo") as f:
            mem = {l.split(":")[0]: int(l.split(":")[1].strip().split()[0]) for l in f}
        stats["ram_total_gb"] = round(mem.get("MemTotal", 0) / 1024 / 1024, 1)
        stats["ram_used_gb"]  = round((mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)) / 1024 / 1024, 1)
        stats["ram_pct"]      = round(stats["ram_used_gb"] / max(stats["ram_total_gb"], 1) * 100, 1)
    except Exception:
        stats.update({"ram_total_gb": 0, "ram_used_gb": 0, "ram_pct": 0})

    # CPU count + load
    try:
        stats["cpus"] = os.cpu_count() or 1
        with open("/proc/loadavg") as f:
            stats["load1"] = float(f.read().split()[0])
    except Exception:
        stats.update({"cpus": 1, "load1": 0})

    # Active QEMU/IOL nodes
    try:
        r = subprocess.run(["pgrep", "-c", "-f", "qemu-system"], capture_output=True, text=True)
        stats["active_nodes"] = int(r.stdout.strip()) if r.returncode == 0 else 0
    except Exception:
        stats["active_nodes"] = 0

    # Watchdog status
    try:
        r = subprocess.run(["systemctl", "is-active", "azam-watchdog.service"], capture_output=True, text=True)
        stats["watchdog"] = r.stdout.strip()
    except Exception:
        stats["watchdog"] = "unknown"

    # SSL cert expiry
    cert = "/etc/ssl/azambasha/azam-pnet.crt"
    if os.path.isfile(cert):
        try:
            r = subprocess.run(["openssl", "x509", "-noout", "-enddate", "-in", cert],
                               capture_output=True, text=True)
            stats["cert_expiry"] = r.stdout.strip().replace("notAfter=", "")
        except Exception:
            stats["cert_expiry"] = "unknown"
    else:
        stats["cert_expiry"] = "No certificate"

    # Disk usage on /
    try:
        st = shutil.disk_usage("/")
        stats["disk_used_gb"] = round(st.used / 1e9, 1)
        stats["disk_total_gb"] = round(st.total / 1e9, 1)
        stats["disk_pct"] = round(st.used / st.total * 100, 1)
    except Exception:
        stats.update({"disk_used_gb": 0, "disk_total_gb": 0, "disk_pct": 0})

    # Backup count
    backup_dir = "/opt/azambasha/backups"
    try:
        stats["backup_count"] = len([f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")])
    except Exception:
        stats["backup_count"] = 0

    return stats


def stream_command(cmd: list, out_queue: queue.Queue):
    """Run cmd in subprocess and push lines to out_queue."""
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, universal_newlines=True
        )
        for line in proc.stdout:
            out_queue.put({"type": "line", "data": line.rstrip()})
        proc.wait()
        out_queue.put({"type": "done", "code": proc.returncode})
    except Exception as e:
        out_queue.put({"type": "error", "data": str(e)})
        out_queue.put({"type": "done", "code": 1})


class AzamOpsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/azam-ops/api/stats":
            self.reply_json(get_cluster_stats())

        elif parsed.path == "/azam-ops/api/backups":
            backup_dir = "/opt/azambasha/backups"
            try:
                files = sorted([
                    {"name": f, "size_kb": round(os.path.getsize(os.path.join(backup_dir, f)) / 1024, 1),
                     "mtime": os.path.getmtime(os.path.join(backup_dir, f))}
                    for f in os.listdir(backup_dir) if f.endswith(".tar.gz")
                ], key=lambda x: x["mtime"], reverse=True)
                self.reply_json({"backups": files})
            except Exception as e:
                self.reply_json({"backups": [], "error": str(e)})

        elif parsed.path == "/azam-ops/api/topology-log":
            lab = params.get("lab", [""])[0]
            cmd = ["python3", "/usr/local/bin/azam-topology-git", "--log", lab] if lab else []
            if not cmd:
                self.reply_json({"error": "lab parameter required"})
                return
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                self.reply_json({"output": r.stdout, "error": r.stderr})
            except Exception as e:
                self.reply_json({"error": str(e)})

        elif parsed.path == "/azam-ops/api/templates":
            try:
                with open("/opt/azambasha/templates/catalog.json") as f:
                    data = json.load(f)
                self.reply_json(data)
            except Exception as e:
                self.reply_json({"templates": [], "error": str(e)})

        elif parsed.path == "/azam-ops/api/notify-config":
            conf = {}
            if os.path.isfile("/etc/pnetlab/azambasha-notify.conf"):
                try:
                    with open("/etc/pnetlab/azambasha-notify.conf") as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                k, v = line.strip().split("=", 1)
                                val = v.strip().strip('"').strip("'")
                                if "apikey" in k.lower() or "token" in k.lower():
                                    conf[k.lower()] = val[:3] + "..." + val[-2:] if len(val) > 5 else "***"
                                else:
                                    conf[k.lower()] = val
                except Exception:
                    pass
            self.reply_json(conf)

        elif parsed.path == "/azam-ops/api/mesh/sweep":
            try:
                r = subprocess.run(["python3", "/opt/azambasha/scripts/azambasha-ping-mesh.py", "--sweep", "--json"],
                                   capture_output=True, text=True, timeout=15)
                self.reply_json(json.loads(r.stdout))
            except Exception as e:
                self.reply_json({"mesh": [], "error": str(e)})

        elif parsed.path == "/azam-ops/api/ai/templates":
            try:
                r = subprocess.run(["python3", "/opt/azambasha/scripts/azambasha-ai-copilot.py", "--list-templates", "--json"],
                                   capture_output=True, text=True, timeout=10)
                self.reply_json(json.loads(r.stdout))
            except Exception as e:
                self.reply_json({"templates": [], "error": str(e)})

        elif parsed.path == "/azam-ops/api/config/nodes":
            try:
                r = subprocess.run(["python3", "/opt/azambasha/scripts/azambasha-config-diff.py", "--nodes", "--json"],
                                   capture_output=True, text=True, timeout=10)
                self.reply_json(json.loads(r.stdout))
            except Exception as e:
                self.reply_json({"nodes": [], "error": str(e)})

        elif parsed.path == "/azam-ops/api/scheduler/status":
            try:
                r = subprocess.run(["python3", "/opt/azambasha/scripts/azambasha-scheduler.py", "--status", "--json"],
                                   capture_output=True, text=True, timeout=10)
                self.reply_json(json.loads(r.stdout))
            except Exception as e:
                self.reply_json({"error": str(e)})

        elif parsed.path == "/azam-ops/api/cloud/status":
            try:
                r = subprocess.run(["python3", "/opt/azambasha/scripts/azambasha-cloud-backup.py", "--status", "--json"],
                                   capture_output=True, text=True, timeout=10)
                self.reply_json(json.loads(r.stdout))
            except Exception as e:
                self.reply_json({"error": str(e)})

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                body = {}

        if parsed.path == "/azam-ops/api/run":
            tool = body.get("tool", "")
            params = body.get("params", {})

            if tool not in COMMANDS:
                self.reply_json({"error": f"Unknown tool: {tool}"}, status=400)
                return

            # Build command
            cmd = COMMANDS.get(tool)
            if cmd is None:
                # Dynamic command construction
                if tool == "bench":
                    sat_ip = params.get("satellite_ip", "")
                    if not sat_ip:
                        self.reply_json({"error": "satellite_ip required"}, status=400)
                        return
                    cmd = ["bash", "/usr/local/bin/azam-bench", sat_ip]
                elif tool == "notify-send":
                    phone = params.get("phone", "").strip()
                    apikey = params.get("apikey", "").strip()
                    title = params.get("title", "Azam-Pnet Notification").strip()
                    msg = params.get("message", "Test alert from Azam-Features Dashboard").strip()
                    cmd = ["python3", "/usr/local/bin/azam-notify", "--title", title, "--message", msg]
                    if phone:
                        cmd.extend(["--whatsapp-phone", phone])
                    if apikey:
                        cmd.extend(["--whatsapp-apikey", apikey])
                    if params.get("save"):
                        cmd.append("--save-config")
                elif tool == "topology-snapshot":
                    lab = params.get("lab", "").strip()
                    msg = params.get("message", "").strip()
                    cmd = ["python3", "/usr/local/bin/azam-topology-git", "--snapshot"]
                    if lab:
                        cmd.extend(["--lab", lab])
                    if msg:
                        cmd.extend(["--message", msg])
                elif tool == "ai-generate":
                    tmpl = params.get("template", "")
                    prompt = params.get("prompt", "")
                    if tmpl:
                        cmd = ["python3", "/opt/azambasha/scripts/azambasha-ai-copilot.py", "--template", tmpl]
                    elif prompt:
                        cmd = ["python3", "/opt/azambasha/scripts/azambasha-ai-copilot.py", "--prompt", prompt]
                    else:
                        cmd = ["python3", "/opt/azambasha/scripts/azambasha-ai-copilot.py", "--template", "cisco_ospf"]
                elif tool == "ai-diagnose":
                    log_txt = params.get("log", "").strip()
                    cmd = ["python3", "/opt/azambasha/scripts/azambasha-ai-copilot.py", "--diagnose", log_txt or "show ip ospf neighbor"]
                elif tool == "config-diff":
                    rev_a = params.get("rev_a", "")
                    rev_b = params.get("rev_b", "")
                    cmd = ["python3", "/opt/azambasha/scripts/azambasha-config-diff.py", "--diff", rev_a, rev_b]
                elif tool == "config-rollback":
                    lab = params.get("lab", "default_lab")
                    node = params.get("node", "R1-Border-Gateway")
                    rev = params.get("revision", "")
                    cmd = ["python3", "/opt/azambasha/scripts/azambasha-config-diff.py", "--lab", lab, "--node", node, "--rollback", rev]
                elif tool == "mesh-traffic":
                    target = params.get("target", "192.168.1.1")
                    rate = str(params.get("rate", "5"))
                    dur = str(params.get("duration", "5"))
                    cmd = ["python3", "/opt/azambasha/scripts/azambasha-ping-mesh.py", "--traffic-gen", "--target", target, "--rate", rate, "--duration", dur]
                else:
                    self.reply_json({"error": "Command not configured"}, status=400)
                    return

            # Append extra params
            if tool == "backup-list" and params.get("restore_file"):
                cmd = ["bash", "/usr/local/bin/azam-restore", params["restore_file"]]
            elif tool == "ssl-generate" and params.get("ip"):
                cmd = ["bash", "/usr/local/bin/azam-ssl", "--generate", params["ip"]]
            elif tool == "templates-list" and params.get("deploy"):
                cmd = ["bash", "/usr/local/bin/azam-templates", "deploy", params["deploy"]]

            # SSE streaming response
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_cors()
            self.end_headers()

            q = queue.Queue()
            t = threading.Thread(target=stream_command, args=(cmd, q), daemon=True)
            t.start()

            try:
                while True:
                    try:
                        item = q.get(timeout=60)
                        data = json.dumps(item)
                        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                        self.wfile.flush()
                        if item.get("type") == "done":
                            break
                    except queue.Empty:
                        self.wfile.write(b"data: {\"type\":\"keepalive\"}\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif parsed.path == "/azam-ops/api/restore":
            fname = body.get("filename", "")
            if not fname or "/" in fname.replace("azam_lab_backup", ""):
                self.reply_json({"error": "Invalid filename"}, status=400)
                return
            full_path = f"/opt/azambasha/backups/{fname}"
            if not os.path.isfile(full_path):
                self.reply_json({"error": "Backup file not found"}, status=404)
                return
            # Run restore
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_cors()
            self.end_headers()
            q = queue.Queue()
            cmd = ["bash", "/usr/local/bin/azam-restore", full_path]
            t = threading.Thread(target=stream_command, args=(cmd, q), daemon=True)
            t.start()
            try:
                while True:
                    item = q.get(timeout=60)
                    self.wfile.write(f"data: {json.dumps(item)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    if item.get("type") == "done":
                        break
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def reply_json(self, data: dict, status: int = 200):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_cors()
        self.end_headers()
        self.wfile.write(payload)


def write_pid():
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def install_service():
    script_path = os.path.realpath(__file__)
    svc = f"""[Unit]
Description=Azam-Pnet Operations Dashboard API Backend
After=network.target apache2.service
Wants=apache2.service

[Service]
Type=simple
ExecStart={sys.executable} {script_path} --daemon
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    svc_path = "/etc/systemd/system/azam-ops-api.service"
    with open(svc_path, "w") as f:
        f.write(svc)
    subprocess.run(["systemctl", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "enable", "--now", "azam-ops-api.service"], check=False)
    print(f"[✔] azam-ops-api service installed and started on port {PORT}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    if args.install:
        install_service()
        return

    write_pid()
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    port = args.port or PORT
    server = HTTPServer(("127.0.0.1", port), AzamOpsHandler)
    print(f"[*] Azam-Ops API listening on 127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopped.")


if __name__ == "__main__":
    main()
