#!/usr/bin/env python3
"""
AzamLabs Database & Services Integration Test Suite (test_database_and_services.py)
Validates the backend subsystem:
1. SQL Schema integrity in schema/azamlabs_db.sql.
2. Systemd service definitions (azamlabs-brokerd, azamlabs-mcp, azamlabs-network-engine).
3. Broker daemon verb registration and IPC socket specification.
4. Administrative toolchain and credential standardization.
"""

import os
import re
import sys
import unittest

# Safe utf-8 reconfigure for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT_DIR, "schema")
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")

class TestDatabaseAndServices(unittest.TestCase):

    def test_database_schema_file(self):
        """Verify schema/azamlabs_db.sql exists, is non-empty, and contains core tables."""
        schema_file = os.path.join(SCHEMA_DIR, "azamlabs_db.sql")
        self.assertTrue(os.path.isfile(schema_file), "schema/azamlabs_db.sql must exist")

        with open(schema_file, "r", encoding="utf-8") as f:
            sql = f.read()

        self.assertIn("CREATE TABLE `control`", sql, "control table must exist in schema")
        self.assertIn("CREATE TABLE `schema_version`", sql, "schema_version table must exist in schema")
        self.assertIn("CREATE TABLE `users`", sql, "users table must exist in schema")
        self.assertIn("CREATE TABLE `lab_sessions`", sql, "lab_sessions table must exist in schema")

    def test_broker_daemon_verbs_and_socket(self):
        """Verify azamlabs-brokerd.py registers essential verbs and binds to /run/azamlabs/broker.sock."""
        broker_file = os.path.join(SCRIPTS_DIR, "azamlabs-brokerd.py")
        self.assertTrue(os.path.isfile(broker_file), "azamlabs-brokerd.py must exist")

        with open(broker_file, "r", encoding="utf-8") as f:
            code = f.read()

        # Check socket definition
        self.assertIn('SOCK_PATH = "/run/azamlabs/broker.sock"', code)
        self.assertIn('SOCK_GROUP = "www-data"', code)

        # Check critical allowlisted verbs
        essential_verbs = [
            "ping", "wrapper", "qemu_cpu_scope", "qemu_cpu_policy",
            "session_cleanup", "linkwatch_start", "nodestats"
        ]
        for v in essential_verbs:
            self.assertIn(f'"{v}"', code, f"Verb {v} must be defined in broker verbs")

    def test_systemd_service_syntax(self):
        """Verify systemd service units have correct structure and point to azamlabs executables."""
        mcp_svc = os.path.join(SCRIPTS_DIR, "mcp", "azamlabs-mcp.service")
        self.assertTrue(os.path.isfile(mcp_svc), "azamlabs-mcp.service must exist")

        with open(mcp_svc, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Description=AzamLabs MCP server", content)
        self.assertIn("ExecStart=/usr/bin/python3 /opt/unetlab/scripts/mcp/azamlabs-mcp.py", content)
        self.assertIn("User=azamlabs-mcp", content)

    def test_install_script_database_and_user_grants(self):
        """Verify install.sh provisions azamlabs_db and azamlabs MySQL user."""
        install_sh = os.path.join(ROOT_DIR, "install.sh")
        with open(install_sh, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("CREATE DATABASE IF NOT EXISTS azamlabs_db", code)
        self.assertIn("CREATE USER IF NOT EXISTS 'azamlabs'@'localhost'", code)
        self.assertIn("GRANT ALL PRIVILEGES ON azamlabs_db.* TO 'azamlabs'@'localhost'", code)
        self.assertIn("schema/azamlabs_db.sql", code)

if __name__ == "__main__":
    unittest.main()
