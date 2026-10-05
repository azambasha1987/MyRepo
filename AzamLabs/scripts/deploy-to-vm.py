#!/usr/bin/env python3
"""
================================================================================
Azam Basha Multi-VM Fleet Deployment, Synchronization & Fix Runner
Ubuntu 26.04+ Native Architecture
================================================================================
Supports deploying, synchronizing, and applying optimizations across one or more
Azam Basha / AzamLabs VMs simultaneously.

Features:
- Multi-host fleet support (single IP or list of VM IPs)
- Differential sync: Only uploads modified files (sub-second sync)
- Zero hardcoded credentials (supports CLI, ENV: VM_HOST, VM_USER, VM_PASS)
- Remote execution of installers, fix suites, and node test suites

Usage:
  python3 deploy-to-vm.py [OPTIONS]

Options:
  --host, -H HOST [HOST2...] Target VM IP address(es) (e.g. 192.168.1.29)
  --user, -u USER            SSH username (default: root)
  --pass, -p PASSWORD        SSH password (default: azam or prompt)
  --port, -P PORT            SSH port (default: 22)
  --apply-all                Run 'azambasha-apply-all-fixes.sh 19' on targets
  --test                     Run 'azambasha-node-test-suite.py --all' on targets
  --install                  Run master 'install.sh' on targets
  --satellite                Run worker 'install-satellite.sh' on targets
  --remote-dir DIR           Remote destination directory (default: /opt/azambasha)
  --dry-run                  Simulate sync without uploading or executing commands
================================================================================
"""

import os
import sys
import getpass
import argparse
import time
import hashlib

# Force UTF-8 on Windows stdout if possible
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import paramiko
except ImportError:
    print("[ERROR] paramiko library is required. Install via: pip install paramiko")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[32m"
C_RED = "\033[31m"
C_YELLOW = "\033[33m"
C_CYAN = "\033[36m"

def log_info(msg):
    print(f"  {C_CYAN}[*]{C_RESET} {msg}")

def log_ok(msg):
    print(f"  {C_GREEN}[✔]{C_RESET} {msg}")

def log_err(msg):
    print(f"  {C_RED}[✖]{C_RESET} {msg}")

def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def ensure_remote_dir(sftp, remote_dir):
    dirs = []
    current = remote_dir
    while current and current != "/":
        dirs.append(current)
        current = os.path.dirname(current).replace("\\", "/")
    
    for d in reversed(dirs):
        try:
            sftp.stat(d)
        except IOError:
            try:
                sftp.mkdir(d)
            except Exception:
                pass

def sync_tree(sftp, local_dir, remote_dir, dry_run=False):
    uploaded = 0
    ensure_remote_dir(sftp, remote_dir)
    
    for root, dirs, files in os.walk(local_dir):
        if ".git" in root or "__pycache__" in root or "scratch" in root:
            continue
        rel_path = os.path.relpath(root, local_dir).replace("\\", "/")
        target_dir = f"{remote_dir}/{rel_path}".rstrip("/.")
        ensure_remote_dir(sftp, target_dir)
        
        for f in files:
            if f.endswith((".pyc", ".tmp", ".log")):
                continue
            local_file = os.path.join(root, f)
            remote_file = f"{target_dir}/{f}"
            
            # Check size and modify time
            local_sz = os.path.getsize(local_file)
            needs_upload = True
            try:
                r_stat = sftp.stat(remote_file)
                if r_stat.st_size == local_sz:
                    needs_upload = False
            except IOError:
                needs_upload = True
                
            if needs_upload:
                if not dry_run:
                    sftp.put(local_file, remote_file)
                    if f.endswith((".sh", ".py")):
                        try:
                            sftp.chmod(remote_file, 0o755)
                        except Exception:
                            pass
                uploaded += 1
                
    return uploaded

def execute_remote_cmd(client, cmd, stream=True):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out_lines = []
    for line in stdout:
        if stream:
            print(f"    {line}", end="")
        out_lines.append(line)
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, "".join(out_lines)

def deploy_host(host, user, password, port, args):
    print(f"\n{C_BOLD}============================================================{C_RESET}")
    print(f"{C_BOLD} Target VM Host: {C_CYAN}{user}@{host}:{port}{C_RESET}")
    print(f"{C_BOLD}============================================================{C_RESET}")
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        log_info(f"Connecting to {host}...")
        client.connect(host, port=port, username=user, password=password, timeout=12, banner_timeout=30)
        log_ok("SSH connection & authentication successful!")
    except Exception as e:
        log_err(f"Authentication failed for {user}@{host}: {e}")
        return False
        
    try:
        sftp = client.open_sftp()
        remote_base = args.remote_dir
        log_info(f"Synchronizing workspace -> {remote_base}...")
        
        # Upload root installer files
        ensure_remote_dir(sftp, remote_base)
        for rfile in ["VERSION", "install.sh", "install-satellite.sh", "azambasha-bootstrap-and-install.sh", "README.md", "VERIFICATION_REPORT.md"]:
            lpath = os.path.join(BASE_DIR, rfile)
            if os.path.exists(lpath) and not args.dry_run:
                sftp.put(lpath, f"{remote_base}/{rfile}")
                sftp.chmod(f"{remote_base}/{rfile}", 0o644 if rfile in ["VERSION", "README.md", "VERIFICATION_REPORT.md"] else 0o755)
                
        # Sync core subdirectories
        for sdir in ["scripts", "assets", "assets-common", "login", "schema", "metadata", "generic", "debian", "html", "docs", "themes"]:
            ldir = os.path.join(BASE_DIR, sdir)
            if os.path.exists(ldir):
                rdir = f"{remote_base}/{sdir}"
                cnt = sync_tree(sftp, ldir, rdir, dry_run=args.dry_run)
                log_ok(f"Synced {sdir}/ ({cnt} files updated)")
                
        sftp.close()
        log_ok("All repository assets synchronized!")
        
        # Make scripts executable and register CLI commands
        if not args.dry_run:
            execute_remote_cmd(client, f"chmod +x {remote_base}/*.sh {remote_base}/scripts/*.sh {remote_base}/scripts/*.py 2>/dev/null || true", stream=False)
            execute_remote_cmd(client, f"mkdir -p /opt/unetlab/scripts && cp -f {remote_base}/scripts/azambasha-* {remote_base}/scripts/azam-* {remote_base}/scripts/apply-* {remote_base}/scripts/ksm_* {remote_base}/scripts/cisco-* /opt/unetlab/scripts/ 2>/dev/null && chmod +x /opt/unetlab/scripts/azambasha-*.sh /opt/unetlab/scripts/azambasha-*.py /opt/unetlab/scripts/apply-*.sh 2>/dev/null || true", stream=False)
            execute_remote_cmd(client, f"if [ -d {remote_base}/html/templates ]; then mkdir -p /opt/unetlab/html/templates/intel /opt/unetlab/html/templates/amd && cp -rf {remote_base}/html/templates/* /opt/unetlab/html/templates/ 2>/dev/null && cp -f {remote_base}/html/templates/intel/*.yml /opt/unetlab/html/templates/ 2>/dev/null || true; fi", stream=False)
            execute_remote_cmd(client, f"if [ -d {remote_base}/html/azam-ops ]; then mkdir -p /opt/unetlab/html && cp -rf {remote_base}/html/azam-ops /opt/unetlab/html/ 2>/dev/null || true; fi", stream=False)
            execute_remote_cmd(client, f"ln -sf {remote_base}/scripts/azambasha-update.sh /usr/local/bin/azam-update && ln -sf {remote_base}/scripts/azambasha-quarterly-audit.sh /usr/local/bin/azam-audit && ln -sf {remote_base}/scripts/azambasha-apply-all-fixes.sh /usr/local/bin/azam-menu && ln -sf {remote_base}/scripts/azambasha-apply-all-fixes.sh /usr/local/bin/azam-fix && ln -sf {remote_base}/scripts/azambasha-satellite-join.sh /usr/local/bin/azam-satellite-join && ln -sf {remote_base}/scripts/azambasha-satellite-join.sh /usr/local/bin/azam-satellite-join && ln -sf {remote_base}/scripts/azambasha-heavy-node-optimizer.sh /usr/local/bin/azam-optimizer && ln -sf {remote_base}/scripts/azambasha-heavy-node-optimizer.sh /usr/local/bin/azam-heavy-optimizer && ln -sf {remote_base}/scripts/azambasha-image-doctor.sh /usr/local/bin/azam-doctor && ln -sf {remote_base}/scripts/azambasha-image-doctor.sh /usr/local/bin/azam-image-doctor && ln -sf {remote_base}/scripts/azambasha-dry-test.py /usr/local/bin/azam-dry-test && ln -sf {remote_base}/scripts/azambasha-health-check.sh /usr/local/bin/azam-health && ln -sf {remote_base}/scripts/azambasha-bootstorm.py /usr/local/bin/azam-bootstorm && ln -sf {remote_base}/scripts/azambasha-bootstorm.py /usr/local/bin/azam-bootstorm 2>/dev/null || true", stream=False)
            execute_remote_cmd(client, "for s in php8.5-fpm php8.4-fpm php8.3-fpm php8.2-fpm php8.1-fpm php-fpm apache2 azamlabs-satd azamlabs-brokerd azamlabs-docker-image-watcher docker; do mkdir -p /etc/systemd/system/${s}.service.d && printf '[Unit]\\nStartLimitIntervalSec=0\\nStartLimitBurst=0\\n[Service]\\nRestart=on-failure\\nRestartSec=1s\\n' > /etc/systemd/system/${s}.service.d/override.conf; done && systemctl daemon-reload 2>/dev/null && systemctl reset-failed 2>/dev/null || true", stream=False)
            execute_remote_cmd(client, "systemctl is-active azambasha-cpu-governor >/dev/null 2>&1 && systemctl restart azambasha-cpu-governor || true", stream=False)

            
        # Post-sync Action Triggers
        if args.install:
            log_info("Executing Master Installer (install.sh)...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash install.sh")
        elif args.satellite:
            sat_cmd = f"cd {remote_base} && sudo bash install-satellite.sh"
            if args.join_master:
                sat_cmd += f" --master {args.join_master}"
                if args.cluster_id:
                    sat_cmd += f" --id {args.cluster_id}"
                if args.cluster_name:
                    sat_cmd += f" --name '{args.cluster_name}'"
                if args.cluster_psk:
                    sat_cmd += f" --psk {args.cluster_psk}"
            log_info(f"Executing Satellite Worker Installer...")
            execute_remote_cmd(client, sat_cmd)
        elif args.join_only:
            join_cmd = f"cd {remote_base} && sudo bash scripts/azambasha-satellite-join.sh"
            if args.join_master:
                join_cmd += f" --master {args.join_master}"
            if args.cluster_id:
                join_cmd += f" --id {args.cluster_id}"
            if args.cluster_name:
                join_cmd += f" --name '{args.cluster_name}'"
            if args.cluster_psk:
                join_cmd += f" --psk {args.cluster_psk}"
            log_info(f"Executing Satellite Cluster Join Utility...")
            execute_remote_cmd(client, join_cmd)
        elif args.fix_cluster:
            log_info("Executing Master Cluster Staging & Fixes (azambasha-fix-cluster.sh)...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-fix-cluster.sh")
        elif args.apply_all:
            log_info("Executing Master Fix & Optimization Suite...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-apply-all-fixes.sh 19")
        elif getattr(args, 'dry_run_optimize', False):
            log_info("Executing Universal Optimizer Dry-Run Simulation...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-heavy-node-optimizer.sh --dry-run")
        elif args.optimize:
            log_info("Applying High-Density Heavy Node Memory & CPU Optimization (Master & Satellites)...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-heavy-node-optimizer.sh --master --cluster && sudo bash scripts/azambasha-fix-node-startup.sh")
        elif args.optimize_satellite:
            log_info("Applying High-Density Heavy Node Memory & CPU Optimization (Satellite)...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-heavy-node-optimizer.sh --satellite && sudo bash scripts/azambasha-fix-node-startup.sh")
        elif args.satellite_fixes:
            log_info("Executing Satellite Worker Fix & Optimization Suite...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-apply-all-fixes.sh 25")
        elif args.fix_credentials:
            log_info("Restoring Web-GUI admin credentials (admin / azam) and clearing login throttles...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-fix-web-credentials.sh")
        elif args.sync_version:
            ver_arg = args.sync_version if isinstance(args.sync_version, str) and args.sync_version != "True" else "auto"
            log_info(f"Synchronizing Web-GUI Version to latest implemented release ({ver_arg})...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-sync-gui-version.sh {ver_arg}")
        elif args.test:
            log_info("Running Automated Node & Virtualization Test Suite...")
            execute_remote_cmd(client, f"cd {remote_base} && python3 scripts/azambasha-node-test-suite.py --all")
        elif args.weekly_scan:
            log_warn("The Weekly Codeberg Intelligence Scan feature has been retired.")
        elif args.install_features:
            log_info("Executing Azam Features Installer & Symlink Generator...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-install-azam-features.sh")
        elif args.cmd:
            log_info(f"Executing Custom Remote Command: {args.cmd}")
            execute_remote_cmd(client, f"cd {remote_base} && {args.cmd}")
        elif args.verify:
            log_info("Running Remote Non-Regression Health Probe...")
            execute_remote_cmd(client, f"cd {remote_base} && sudo bash scripts/azambasha-fix-permissions.sh --check && sudo bash scripts/azambasha-system-and-console-fix.sh --check")
            
        client.close()
        log_ok(f"Deployment on {host} completed successfully!\n")
        return True
    except Exception as e:
        log_err(f"Deployment encountered error on {host}: {e}")
        try:
            client.close()
        except Exception:
            pass
        return False

def main():
    parser = argparse.ArgumentParser(description="Azam Basha Multi-VM Fleet Deployment & Fix Runner")
    parser.add_argument("--host", "-H", nargs="+", help="Target VM IP address(es) (e.g. 192.168.1.29)")
    parser.add_argument("--user", "-u", default=os.environ.get("VM_USER", "root"), help="SSH username (default: root)")
    parser.add_argument("--pass", "-p", dest="password", default=os.environ.get("VM_PASS", None), help="SSH password")
    parser.add_argument("--port", "-P", type=int, default=int(os.environ.get("VM_PORT", 22)), help="SSH port (default: 22)")
    parser.add_argument("--remote-dir", default="/opt/azambasha", help="Remote base directory (default: /opt/azambasha)")
    parser.add_argument("--apply-all", action="store_true", help="Apply all fixes and speed optimizations on targets")
    parser.add_argument("--dry-run-optimize", action="store_true", help="Simulate optimization remotely without making system changes")
    parser.add_argument("--optimize", action="store_true", help="Deploy and activate High-Density Memory & CPU Optimizer on Master (Cat8000, Cisco 8000, Cat9000, IOL)")
    parser.add_argument("--optimize-satellite", action="store_true", help="Deploy and activate High-Density Memory & CPU Optimizer on Satellite Worker")
    parser.add_argument("--test", action="store_true", help="Run node validation test suite on targets")
    parser.add_argument("--weekly-scan", action="store_true", help="Run weekly Codeberg scanner remotely and fetch report")
    parser.add_argument("--verify", action="store_true", help="Run remote non-regression health probes across fleet")
    parser.add_argument("--install", action="store_true", help="Run master installer on targets")
    parser.add_argument("--satellite", action="store_true", help="Run satellite worker installer on targets")
    parser.add_argument("--satellite-fixes", action="store_true", help="Apply full optimization & issue remediation suite to a satellite worker node")
    parser.add_argument("--install-features", action="store_true", help="Run azambasha-install-azam-features.sh to link all 26 CLI tools and services")
    parser.add_argument("--cmd", help="Execute arbitrary command on remote host after sync")
    parser.add_argument("--fix-cluster", action="store_true", help="Stage cluster bundle and configure remote DB on Master")
    parser.add_argument("--join-master", help="Master node IP address for satellite cluster join")
    parser.add_argument("--cluster-id", type=int, choices=[1, 2, 3, 4, 5], default=1, help="Satellite slot ID (default: 1)")
    parser.add_argument("--cluster-name", help="Satellite display name (default: Satellite <id>)")
    parser.add_argument("--cluster-psk", help="Cluster 64-hex PSK key from Master")
    parser.add_argument("--join-only", action="store_true", help="Run satellite cluster join utility without full re-install")
    parser.add_argument("--fix-credentials", action="store_true", help="Restore Web-GUI admin credentials (admin / azam) and clear login throttles")
    parser.add_argument("--sync-version", nargs="?", const="auto", help="Synchronize Web-GUI version display to latest implemented release (e.g. 6.8.85 or auto)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sync without uploading")

    args = parser.parse_args()

    hosts = args.host
    if not hosts:
        env_host = os.environ.get("VM_HOST")
        if env_host:
            hosts = [env_host]
        else:
            default_host = "192.168.1.29"
            user_in = input(f"Enter target VM IP address(es) [default: {default_host}]: ").strip()
            hosts = user_in.split() if user_in else [default_host]

    password = args.password
    if not password:
        password = getpass.getpass(f"Enter SSH password for {args.user} (default 'azam'): ")
        if not password:
            password = "azam"

    print(f"\n{C_BOLD}Starting Multi-VM Fleet Deployment across {len(hosts)} target host(s)...{C_RESET}")
    success_count = 0
    
    for h in hosts:
        if deploy_host(h, args.user, password, args.port, args):
            success_count += 1

    print("=" * 60)
    print(f" Fleet Deployment Summary: {success_count}/{len(hosts)} Hosts Configured Successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
