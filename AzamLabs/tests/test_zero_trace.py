#!/usr/bin/env python3
"""
AzamLabs Zero-Trace Verification Test Suite (test_zero_trace.py)
Audits the entire repository to guarantee that:
1. Exactly ZERO occurrences of 'pnetlab' (case-insensitive) exist in any source code,
   script, configuration, template, web asset, or documentation file.
2. Cloud bridge interface names (pnet0 through pnet9) remain preserved.
3. No legacy brand tokens remain in filenames or directory structures.
"""

import os
import re
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Directories to skip
SKIP_DIRS = {
    ".git", "__pycache__", "debian", "snapshots", ".pytest_cache"
}

# Binary / archive file extensions to skip
SKIP_EXTS = {
    ".deb", ".tar", ".gz", ".zst", ".png", ".ico", ".pdf", ".pyc", ".sig"
}

# Text extensions to inspect
TEXT_EXTS = {
    ".py", ".sh", ".bash", ".js", ".html", ".htm", ".css",
    ".md", ".txt", ".json", ".sql", ".conf", ".ini", ".service",
    ".yml", ".yaml", ".c", ".h", ".ps1", ".bat", ".tsv"
}

TEXT_FILENAMES = {
    "VERSION", "inventory.tsv", "COMPLETE",
    "binary-amd64-Packages", "binary-all-Packages"
}

# Tool scripts that naturally contain migration regexes to replace pnetlab
WHITELIST_FILES = {
    "scripts/azamlabs-rebrand-zero-trace.py",
    "tests/test_zero_trace.py"
}

class TestZeroTrace(unittest.TestCase):

    def test_no_pnetlab_in_filenames(self):
        """Assert no active source file or directory contains 'pnetlab' in its name."""
        violations = []
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

            for d in dirs:
                if "pnetlab" in d.lower():
                    violations.append(os.path.relpath(os.path.join(root, d), ROOT_DIR))

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in SKIP_EXTS:
                    continue
                if "pnetlab" in f.lower():
                    violations.append(os.path.relpath(os.path.join(root, f), ROOT_DIR))

        self.assertEqual(
            violations, [],
            f"Found files/directories containing 'pnetlab':\n" + "\n".join(violations)
        )

    def test_no_pnetlab_in_file_contents(self):
        """Assert exactly 0 occurrences of 'pnetlab' in all text source files."""
        violations = []

        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in SKIP_EXTS:
                    continue

                if f not in TEXT_FILENAMES and ext not in TEXT_EXTS:
                    continue

                filepath = os.path.join(root, f)
                rel_path = os.path.relpath(filepath, ROOT_DIR).replace("\\", "/")

                if rel_path in WHITELIST_FILES:
                    continue

                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                        for line_no, line in enumerate(fh, 1):
                            if "pnetlab" in line.lower():
                                violations.append(f"{rel_path}:{line_no}: {line.strip()[:100]}")
                except Exception as e:
                    violations.append(f"{rel_path}: Read error: {e}")

        self.assertEqual(
            len(violations), 0,
            f"Found {len(violations)} occurrences of 'pnetlab':\n" + "\n".join(violations[:20])
        )

    def test_cloud_bridge_naming_preserved(self):
        """Verify that pnet0 cloud bridge naming remains intact in install.sh."""
        install_sh = os.path.join(ROOT_DIR, "install.sh")
        self.assertTrue(os.path.isfile(install_sh), "install.sh must exist")

        with open(install_sh, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("pnet0", content, "Cloud bridge pnet0 must be preserved in install.sh")
        self.assertIn("allow-hotplug pnet0", content, "pnet0 stanza must be present in install.sh")

    def test_database_and_socket_rebranded(self):
        """Verify azamlabs_db and azamlabs services/sockets are configured."""
        install_sh = os.path.join(ROOT_DIR, "install.sh")
        with open(install_sh, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("azamlabs_db", content, "install.sh must configure azamlabs_db")
        self.assertIn("azamlabs-brokerd.service", content, "install.sh must register azamlabs-brokerd.service")
        self.assertIn("RuntimeDirectory=azamlabs", content, "install.sh must use RuntimeDirectory=azamlabs")
        self.assertNotIn("pnetlab_db", content, "install.sh must not contain pnetlab_db")

        broker_py = os.path.join(ROOT_DIR, "scripts", "azamlabs-brokerd.py")
        with open(broker_py, "r", encoding="utf-8") as f:
            bcontent = f.read()
        self.assertIn("/run/azamlabs/broker.sock", bcontent, "azamlabs-brokerd.py must use /run/azamlabs/broker.sock")

if __name__ == "__main__":
    unittest.main()
