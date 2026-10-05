#!/usr/bin/env python3
"""
AzamLabs Zero-Trace Rebranding Engine (azamlabs-rebrand-zero-trace.py)
Replaces all occurrences of 'pnetlab' / 'PNETLab' / 'pnet' branding
with 'AzamLabs' / 'azamlabs', while strictly excluding cloud bridge
interface names (pnet0 through pnet9).
"""

import os
import sys
import re

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
THIS_SCRIPT = os.path.abspath(__file__)

# Extensions to process as text
TEXT_EXTS = {
    ".py", ".sh", ".bash", ".js", ".html", ".htm", ".css",
    ".md", ".txt", ".json", ".sql", ".conf", ".ini", ".service",
    ".yml", ".yaml", ".c", ".h", ".ps1", ".bat", ".tsv"
}

# Explicit filenames to process (even if no extension)
TEXT_FILENAMES = {
    "VERSION", "inventory.tsv", "COMPLETE",
    "binary-amd64-Packages", "binary-all-Packages"
}

# Directories to skip
SKIP_DIRS = {
    ".git", "__pycache__", "debian", "snapshots"
}

# Binary / archive file extensions to skip
SKIP_EXTS = {
    ".deb", ".tar", ".gz", ".zst", ".png", ".ico", ".pdf", ".pyc", ".sig"
}

def replace_tokens(text: str, filepath: str) -> tuple[str, int]:
    """
    Perform replacements in text, preserving pnet0..pnet9 cloud bridge interface names.
    Returns (new_text, count_of_changes).
    """
    total_changes = 0

    # Replacement rules in order of specificity
    # Rule tuples: (pattern, replacement, flags)
    rules = [
        # Database name & user
        (r'\bpnetlab_db\b', 'azamlabs_db', re.IGNORECASE),
        (r"'pnetlab'@'", "'azamlabs'@'", 0),
        (r'"pnetlab"@"\'', '"azamlabs"@\'', 0),
        (r'-u pnetlab -ppnetlab', '-u azamlabs -pazam', 0),
        (r'-u pnetlab\b', '-u azamlabs', 0),
        (r'-ppnetlab\b', '-pazam', 0),
        
        # Sockets, paths, configs
        (r'/run/pnetlab/broker\.sock', '/run/azamlabs/broker.sock', 0),
        (r'/run/pnetlab\b', '/run/azamlabs', 0),
        (r'/etc/pnetlab-version\b', '/etc/azamlabs-version', 0),
        (r'/etc/pnetlab-role\b', '/etc/azamlabs-role', 0),
        (r'/etc/pnetlab\b', '/etc/azamlabs', 0),
        (r'/etc/pnet-webconsole\b', '/etc/azam-webconsole', 0),
        (r'/dev/shm/pnet-authfail', '/dev/shm/azamlabs-authfail', 0),
        (r'/tmp/pnet-authfail', '/tmp/azamlabs-authfail', 0),
        (r'/usr/share/plymouth/themes/pnetlab', '/usr/share/plymouth/themes/azamlabs', 0),

        # Netcfg comments and filenames
        (r'pnetlab-netcfg', 'azamlabs-netcfg', 0),
        (r'01-pnetlab-netcfg\.yaml', '01-azamlabs-netcfg.yaml', 0),
        (r'pnet-netcfg-reboot', 'azamlabs-netcfg-reboot', 0),
        (r'pnetlab-network-engine', 'azamlabs-network-engine', 0),

        # Backup & temp names
        (r'pnetlab_backup_', 'azamlabs_backup_', 0),
        (r'_pnetlab_backup', '_azamlabs_backup', 0),
        (r'_pnetlab_restore', '_azamlabs_restore', 0),

        # Specific shell variables & configs
        (r'\bPNETLAB_CONF\b', 'AZAMLABS_CONF', 0),
        (r'\bPNETLAB_SUDO_PASS\b', 'AZAMLABS_SUDO_PASS', 0),
        (r'99pnetlab-held', '99azamlabs-held', 0),
        (r'99pnetlab-credentials', '99azamlabs-credentials', 0),
        (r'99pnetlab-no-auto-upgrade', '99azamlabs-no-auto-upgrade', 0),
        (r'Pnetlabv8', 'AzamLabsv8', 0),
        (r'/tmp/pnetlab_server\.csr', '/tmp/azamlabs_server.csr', 0),
        (r'/tmp/pnetlab_san\.ext', '/tmp/azamlabs_san.ext', 0),
        (r'pnetlab_root_ca\.crt', 'azamlabs_root_ca.crt', 0),
        (r'pnetlab_secret_token', 'azamlabs_secret_token', 0),
        (r'pnetlab_password', 'azam', 0),
        (r'pnetlab_nodes', 'azamlabs_nodes', 0),
        (r'pnetlab_docker_updates', 'azamlabs_docker_updates', 0),
        (r'_set_pnetlab_slice_weight', '_set_azamlabs_slice_weight', 0),
        (r'pnetlab_(rx|tx)_(packets|bytes|drops|errors)_total', r'azamlabs_\1_\2_total', 0),
        (r'PNetLab_Multi_Vendor_Mesh', 'AzamLabs_Multi_Vendor_Mesh', 0),
        (r'create_pnetlab_v8_xml', 'create_azamlabs_v8_xml', 0),
        (r'convert_cml2_yaml_to_pnetlab', 'convert_cml2_yaml_to_azamlabs', 0),

        # Daemons & systemd services
        (r'pnetlab-brokerd\.service', 'azamlabs-brokerd.service', 0),
        (r'pnetlab-brokerd\.py', 'azamlabs-brokerd.py', 0),
        (r'pnetlab-brokerd\b', 'azamlabs-brokerd', 0),
        (r'pnetlab-satd\.service', 'azamlabs-satd.service', 0),
        (r'pnetlab-satd\.py', 'azamlabs-satd.py', 0),
        (r'pnetlab-satd\b', 'azamlabs-satd', 0),
        (r'pnetlab-linkwatchd\.service', 'azamlabs-linkwatchd.service', 0),
        (r'pnetlab-linkwatchd\.py', 'azamlabs-linkwatchd.py', 0),
        (r'pnetlab-linkwatchd\b', 'azamlabs-linkwatchd', 0),
        (r'pnetlab-mcp\.service', 'azamlabs-mcp.service', 0),
        (r'pnetlab-mcp\.py', 'azamlabs-mcp.py', 0),
        (r'pnetlab-mcp\b', 'azamlabs-mcp', 0),
        (r'pnetlab\.slice\b', 'azamlabs.slice', 0),
        (r'ksm-pnetlab\.service', 'ksm-azamlabs.service', 0),
        (r'pnet-guac-lite\.service', 'azam-guac-lite.service', 0),
        (r'pnet-console-mux\.service', 'azam-console-mux.service', 0),
        (r'pnetlab-dataplane\.service', 'azamlabs-dataplane.service', 0),

        # SSL & Web Server
        (r'pnetlab-ca\.(crt|key)', r'azamlabs-ca.\1', 0),
        (r'pnetlab-selfsigned\.(crt|key)', r'azamlabs-selfsigned.\1', 0),
        (r'\bpnetlab\.local\b', 'azamlabs.local', 0),
        (r'sites-available/pnetlab\.conf', 'sites-available/azamlabs.conf', 0),
        (r'sites-available/pnetlab-ssl\.conf', 'sites-available/azamlabs-ssl.conf', 0),
        (r'zz-pnetlab-cluster\.cnf', 'zz-azamlabs-cluster.cnf', 0),
        (r'pnetlab-iol\.conf', 'azamlabs-iol.conf', 0),
        (r'99-pnetlab-forwarding\.conf', '99-azamlabs-forwarding.conf', 0),
        (r'98-pnetlab-dataplane\.conf', '98-azamlabs-dataplane.conf', 0),
        (r'99-pnetlab-performance\.conf', '99-azamlabs-performance.conf', 0),
        (r'modules-load\.d/pnetlab\.conf', 'modules-load.d/azamlabs.conf', 0),
        (r'resolved\.conf\.d/pnetlab\.conf', 'resolved.conf.d/azamlabs.conf', 0),

        # UI & Features JS
        (r'pnetlab-azam-features\.js', 'azamlabs-features.js', 0),
        (r'\.pnetlab-link\b', '.azamlabs-link', 0),
        (r'window\.PNetLabWatcher', 'window.AzamLabsWatcher', 0),
        (r'window\.__pnetKeepaliveActive', 'window.__azamKeepaliveActive', 0),
        (r'pnetlab-urischeme-installer\.bat', 'azamlabs-urischeme-installer.bat', 0),
        (r'pnetlab-client-setup\.sh', 'azamlabs-client-setup.sh', 0),
        (r'pnetlab-api-client\.py', 'azamlabs-api-client.py', 0),
        (r'pnetlab-v8', 'azamlabs-v8', 0),
        (r'pnet-capture-web', 'azam-capture-web', 0),

        # Extracted files
        (r'extracted_pnet-satdeploy\.sh', 'extracted_azam-satdeploy.sh', 0),
        (r'extracted_pnet-satdeploy', 'extracted_azam-satdeploy', 0),

        # CLI command symlinks
        (r'/usr/local/bin/pnet-menu', '/usr/local/bin/azam-menu', 0),
        (r'/usr/local/bin/pnet-fix', '/usr/local/bin/azam-fix', 0),
        (r'/usr/local/bin/pnet-cluster', '/usr/local/bin/azam-cluster', 0),
        (r'/usr/local/bin/pnet-satellite-join', '/usr/local/bin/azam-satellite-join', 0),
        (r'/usr/local/bin/pnet-health', '/usr/local/bin/azam-health', 0),
        (r'/usr/local/bin/pnet-doctor', '/usr/local/bin/azam-doctor', 0),
        (r'/usr/local/bin/pnet-images', '/usr/local/bin/azam-images', 0),
        (r'/usr/local/bin/pnet-bootstorm', '/usr/local/bin/azam-bootstorm', 0),
        (r'/usr/local/bin/pnet-network', '/usr/local/bin/azam-network', 0),
        (r'/usr/local/bin/pnet-backup', '/usr/local/bin/azam-backup', 0),
        (r'/usr/local/bin/pnet-credentials', '/usr/local/bin/azam-credentials', 0),

        # Compound brand references
        (r'\bAzam-Pnet\b', 'AzamLabs', 0),
        (r'\bazam-pnet\b', 'azamlabs', 0),
        (r'/opt/azam-pnet\b', '/opt/azamlabs', 0),
        (r'/opt/pnetlab\b', '/opt/azamlabs', 0),

        # Prefixed variables
        (r'\bPNETLAB_', 'AZAMLABS_', 0),
        (r'\bpnetlab_', 'azamlabs_', 0),
        (r'\bPNetLab_', 'AzamLabs_', 0),

        # General PNetLab brand strings with case variations
        (r'\bPNETLAB\b', 'AZAMLABS', 0),
        (r'\bPNETLab\b', 'AzamLabs', 0),
        (r'\bPNetLab\b', 'AzamLabs', 0),
        (r'\bpnetlab\b', 'azamlabs', 0),
        (r'\bPnetlab\b', 'AzamLabs', 0),
        (r'\bpnetlabs\b', 'azamlabs', 0),
    ]

    new_text = text
    for pat, repl, flags in rules:
        count = len(re.findall(pat, new_text, flags=flags))
        if count > 0:
            new_text = re.sub(pat, repl, new_text, flags=flags)
            total_changes += count

    return new_text, total_changes

def process_file(filepath: str, dry_run: bool = True) -> int:
    # Do not process this script itself or the zero-trace test suite
    if os.path.abspath(filepath) == THIS_SCRIPT or os.path.basename(filepath) == "test_zero_trace.py":
        return 0

    basename = os.path.basename(filepath)
    ext = os.path.splitext(filepath)[1].lower()

    if basename in TEXT_FILENAMES or ext in TEXT_EXTS:
        pass
    else:
        return 0

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0

    new_content, count = replace_tokens(content, filepath)
    if count > 0:
        rel = os.path.relpath(filepath, ROOT_DIR)
        print(f"[{'DRY-RUN' if dry_run else 'APPLIED'}] {rel}: {count} replacements")
        if not dry_run:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
    return count

def run(dry_run: bool = True):
    print(f"Starting AzamLabs Zero-Trace Rebranding (dry_run={dry_run})...")
    total_files = 0
    total_replacements = 0

    for root, dirs, files in os.walk(ROOT_DIR):
        # Exclude skip dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in SKIP_EXTS:
                continue

            filepath = os.path.join(root, file)
            cnt = process_file(filepath, dry_run=dry_run)
            if cnt > 0:
                total_files += 1
                total_replacements += cnt

    print(f"\nCompleted! Processed {total_files} files with {total_replacements} total replacements.")

if __name__ == "__main__":
    is_dry = "--apply" not in sys.argv
    run(dry_run=is_dry)
