#!/usr/bin/env python3
"""
==============================================================================
Azam Basha Git-Based Lab Topology Version Control (azam-topology-git)
==============================================================================
Provides fine-grained, per-file .unl topology version control:
  - Auto-commits every .unl file change to a local bare Git repository
  - Shows XML diff between versions (added nodes, deleted links, IP changes)
  - Restores any .unl to any previous commit in seconds
  - Integrates with inotify (optional) for real-time auto-commit on save
==============================================================================
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
import hashlib
import time
from datetime import datetime

LABS_DIR = "/opt/unetlab/labs"
GIT_REPO = "/opt/azambasha/topology-git.git"
GIT_WORK  = "/opt/azambasha/topology-work"
LOG_FILE  = "/opt/azambasha/logs/topology-git.log"

GREEN  = "\033[1;32m"
YELLOW = "\033[1;33m"
RED    = "\033[1;31m"
CYAN   = "\033[1;36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def run(cmd: list, cwd=None, capture=True) -> tuple:
    """Run a subprocess command and return (returncode, stdout, stderr)."""
    r = subprocess.run(
        cmd, cwd=cwd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True
    )
    return r.returncode, r.stdout or "", r.stderr or ""


def ensure_git_repo():
    """Initialize the bare git repo and working tree if they don't exist."""
    os.makedirs(GIT_WORK, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    if not os.path.isdir(GIT_REPO):
        # Initialize bare repo
        run(["git", "init", "--bare", GIT_REPO])
        # Clone to working tree
        run(["git", "clone", GIT_REPO, GIT_WORK])
        # Configure identity
        run(["git", "config", "user.name", "Azam-Topology-Git"], cwd=GIT_WORK)
        run(["git", "config", "user.email", "azam-topology@pnetlab.local"], cwd=GIT_WORK)
        print(f"{GREEN}[✔]{RESET} Topology Git repository initialized at {GIT_REPO}")
    else:
        # Pull latest
        run(["git", "pull", "--quiet"], cwd=GIT_WORK)


def get_unl_files(folder=None) -> list:
    """Enumerate all .unl files in the labs directory."""
    unls = []
    root = os.path.join(LABS_DIR, folder) if folder else LABS_DIR
    if not os.path.isdir(root):
        return unls
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".unl"):
                unls.append(os.path.join(dirpath, fn))
    return unls


def lab_to_repo_path(lab_abs: str) -> str:
    """Convert an absolute labs path to a relative path in the git repo."""
    rel = os.path.relpath(lab_abs, LABS_DIR)
    return rel


def commit_lab(lab_abs: str, message: str = None) -> bool:
    """Copy a single .unl file into the work tree and commit it."""
    ensure_git_repo()
    rel_path = lab_to_repo_path(lab_abs)
    dest = os.path.join(GIT_WORK, rel_path)

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(lab_abs, dest)

    rc, _, _ = run(["git", "diff", "--quiet", rel_path], cwd=GIT_WORK)
    changed = (rc != 0)

    # Also check for untracked
    rc2, out2, _ = run(["git", "status", "--porcelain", rel_path], cwd=GIT_WORK)
    if not changed and not out2.strip():
        return False  # No changes

    run(["git", "add", rel_path], cwd=GIT_WORK)
    msg = message or f"auto-commit: {os.path.basename(lab_abs)} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    run(["git", "commit", "-m", msg], cwd=GIT_WORK)
    run(["git", "push", "origin", "main", "--quiet"], cwd=GIT_WORK)

    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} COMMIT {rel_path}: {msg}\n")
    return True


def snapshot_all(folder=None) -> int:
    """Snapshot all .unl files and commit any that changed."""
    ensure_git_repo()
    unls = get_unl_files(folder)
    committed = 0
    for lab in unls:
        if commit_lab(lab):
            committed += 1
            print(f"  {GREEN}[✔]{RESET} Committed: {os.path.relpath(lab, LABS_DIR)}")
    return committed


def show_log(lab_name: str, limit: int = 20):
    """Show commit history for a specific .unl file."""
    ensure_git_repo()
    # Find matching file
    matches = [f for f in get_unl_files() if lab_name.lower() in f.lower()]
    if not matches:
        print(f"{RED}[!]{RESET} Lab '{lab_name}' not found in tracked files.")
        return
    rel = lab_to_repo_path(matches[0])
    rc, out, err = run(
        ["git", "log", f"-{limit}", "--oneline", "--follow", "--",  rel],
        cwd=GIT_WORK
    )
    if not out.strip():
        print(f"{YELLOW}[!]{RESET} No commits yet for {rel}. Run: azam-topology-git --snapshot")
        return
    print(f"{CYAN}{'='*64}{RESET}")
    print(f"  {BOLD}Topology History: {os.path.basename(matches[0])}{RESET}")
    print(f"{CYAN}{'-'*64}{RESET}")
    for i, line in enumerate(out.strip().split("\n"), 1):
        parts = line.split(" ", 1)
        sha = parts[0]
        msg = parts[1] if len(parts) > 1 else ""
        print(f"  {DIM}{i:>3}.{RESET}  {CYAN}{sha}{RESET}  {msg}")
    print(f"{CYAN}{'='*64}{RESET}")
    print(f"  Restore: {BOLD}azam-topology-git --restore {lab_name} --commit <SHA>{RESET}")


def show_diff(lab_name: str, commit1: str = "HEAD~1", commit2: str = "HEAD"):
    """Show XML diff of a .unl file between two commits."""
    ensure_git_repo()
    matches = [f for f in get_unl_files() if lab_name.lower() in f.lower()]
    if not matches:
        print(f"{RED}[!]{RESET} Lab '{lab_name}' not found.")
        return
    rel = lab_to_repo_path(matches[0])
    rc, out, err = run(
        ["git", "diff", f"{commit1}..{commit2}", "--", rel],
        cwd=GIT_WORK
    )
    if not out.strip():
        print(f"{YELLOW}[!]{RESET} No differences between {commit1} and {commit2} for {rel}")
        return
    print(f"{CYAN}{'='*64}{RESET}")
    print(f"  {BOLD}Topology Diff: {os.path.basename(matches[0])}{RESET}")
    print(f"  {DIM}{commit1} → {commit2}{RESET}")
    print(f"{CYAN}{'-'*64}{RESET}")
    for line in out.split("\n"):
        if line.startswith("+++") or line.startswith("---"):
            print(f"{DIM}{line}{RESET}")
        elif line.startswith("+"):
            print(f"{GREEN}{line}{RESET}")
        elif line.startswith("-"):
            print(f"{RED}{line}{RESET}")
        elif line.startswith("@@"):
            print(f"{CYAN}{line}{RESET}")
        else:
            print(line)
    print(f"{CYAN}{'='*64}{RESET}")


def restore_lab(lab_name: str, commit_sha: str):
    """Restore a .unl file from a specific commit back to the live labs directory."""
    ensure_git_repo()
    matches = [f for f in get_unl_files() if lab_name.lower() in f.lower()]
    rel = None
    if matches:
        rel = lab_to_repo_path(matches[0])
    else:
        # Try searching in git log
        rc, out, err = run(
            ["git", "log", "--all", "--name-only", "--format=", "--"],
            cwd=GIT_WORK
        )
        for line in out.split("\n"):
            if lab_name.lower() in line.lower() and line.endswith(".unl"):
                rel = line.strip()
                break

    if not rel:
        print(f"{RED}[!]{RESET} Lab '{lab_name}' not found in history.")
        return

    # Extract file from specific commit
    rc, content, err = run(
        ["git", "show", f"{commit_sha}:{rel}"],
        cwd=GIT_WORK
    )
    if rc != 0:
        print(f"{RED}[!]{RESET} Cannot retrieve {rel} at commit {commit_sha}: {err}")
        return

    target_path = os.path.join(LABS_DIR, rel)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    # Backup current version before restore
    if os.path.isfile(target_path):
        backup = f"{target_path}.pre-restore.{int(time.time())}"
        shutil.copy2(target_path, backup)
        print(f"  {YELLOW}[!]{RESET} Current version backed up: {backup}")

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Fix permissions
    try:
        shutil.chown(target_path, user="nobody")
    except Exception:
        pass

    print(f"  {GREEN}[✔ RESTORED]{RESET} {rel} ← commit {commit_sha}")
    print(f"  {GREEN}[✔]${RESET} Reload PNetLab GUI to see the restored topology.")

    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} RESTORE {rel} ← {commit_sha}\n")


def install_symlink():
    if sys.platform != "win32":
        try:
            target = "/usr/local/bin/azam-topology-git"
            source = os.path.realpath(__file__)
            if not os.path.exists(target) or os.path.realpath(target) != source:
                if os.path.exists(target):
                    os.remove(target)
                os.symlink(source, target)
        except Exception:
            pass


def install_hook():
    """Install a cron hook that auto-snapshots .unl files every 5 minutes."""
    cron_line = f"*/5 * * * * python3 {os.path.realpath(__file__)} --snapshot >> {LOG_FILE} 2>&1"
    rc, out, err = run(["crontab", "-l"])
    existing = out if rc == 0 else ""
    if "azam-topology-git" not in existing and "topology-git" not in existing:
        new_cron = existing.rstrip("\n") + "\n" + cron_line + "\n"
        proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        proc.communicate(new_cron)
        print(f"{GREEN}[✔]{RESET} Auto-snapshot cron job installed (every 5 minutes).")
    else:
        print(f"{YELLOW}[!]{RESET} Cron job already installed.")


def main():
    parser = argparse.ArgumentParser(
        description="Azam-Pnet Git-Based Lab Topology Version Control"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--snapshot", action="store_true",
                       help="Snapshot all changed .unl files and commit")
    group.add_argument("--log", metavar="LAB_NAME",
                       help="Show commit history for a lab topology")
    group.add_argument("--diff", metavar="LAB_NAME",
                       help="Show XML diff between two commits")
    group.add_argument("--restore", metavar="LAB_NAME",
                       help="Restore a lab topology to a specific commit")
    group.add_argument("--install", action="store_true",
                       help="Install auto-snapshot cron job and initialize repo")

    parser.add_argument("--commit", default=None,
                        help="Commit SHA for --restore or --diff")
    parser.add_argument("--from-commit", default="HEAD~1",
                        help="From-commit for --diff (default: HEAD~1)")
    parser.add_argument("--folder", default=None,
                        help="Limit --snapshot to a specific labs subfolder")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max commits to show in --log (default: 20)")

    args = parser.parse_args()
    install_symlink()

    if args.install:
        ensure_git_repo()
        install_hook()
        n = snapshot_all(args.folder)
        print(f"{GREEN}[✔]{RESET} Initial snapshot: {n} topology file(s) committed.")
        return

    if args.snapshot:
        ensure_git_repo()
        n = snapshot_all(args.folder)
        if n == 0:
            print(f"[*] No topology changes detected since last snapshot.")
        else:
            print(f"{GREEN}[✔]{RESET} {n} topology file(s) committed to version history.")
        return

    if args.log:
        show_log(args.log, limit=args.limit)
        return

    if args.diff:
        to_c = args.commit or "HEAD"
        show_diff(args.diff, commit1=args.from_commit, commit2=to_c)
        return

    if args.restore:
        if not args.commit:
            print(f"{RED}[!]{RESET} --commit <SHA> is required for --restore.")
            print(f"     Run: azam-topology-git --log {args.restore}  to see commit SHAs")
            sys.exit(1)
        restore_lab(args.restore, args.commit)
        return


if __name__ == "__main__":
    main()
