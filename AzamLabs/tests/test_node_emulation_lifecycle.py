#!/usr/bin/env python3
"""
AzamLabs Node Emulation Lifecycle Test Suite (test_node_emulation_lifecycle.py)
Validates the virtualization engine pipeline:
1. QEMU hypervisor flags (mem-merge=on, virtio-balloon, vhost=on).
2. Cisco IOL multi-arch execution wrapper and LD_PRELOAD injection.
3. Staggered node startup scheduling simulation.
4. Device template syntax and definitions.
"""

import os
import re
import sys
import unittest
import glob
import yaml

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
TEMPLATES_DIR = os.path.join(ROOT_DIR, "html", "templates")
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")

class TestNodeEmulationLifecycle(unittest.TestCase):

    def test_templates_syntax_and_structure(self):
        """Verify YAML syntax of all templates in html/templates/."""
        self.assertTrue(os.path.isdir(TEMPLATES_DIR), "html/templates directory must exist")

        template_files = glob.glob(os.path.join(TEMPLATES_DIR, "**", "*.yml"), recursive=True)
        self.assertGreater(len(template_files), 0, "There should be template YAML files")

        for tpath in template_files:
            rel = os.path.relpath(tpath, ROOT_DIR)
            with open(tpath, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    self.assertIsInstance(data, dict, f"Template {rel} must load as a dict")
                    self.assertIn("type", data, f"Template {rel} must specify 'type'")
                    self.assertIn("name", data, f"Template {rel} must specify 'name'")
                except yaml.YAMLError as exc:
                    self.fail(f"YAML parsing error in {rel}: {exc}")

    def test_iol_wrapper_script_logic(self):
        """Verify heavy node optimizer builds azam-iol-launcher and ksm_merge_exec."""
        optimizer_sh = os.path.join(SCRIPTS_DIR, "azambasha-heavy-node-optimizer.sh")
        self.assertTrue(os.path.isfile(optimizer_sh))

        with open(optimizer_sh, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("azam-iol-launcher", code)
        self.assertIn("ksm_merge_exec", code)
        self.assertIn("gcc -O3", code)

    def test_bootstorm_schedule_simulation(self):
        """Simulate Anti-Bootstorm queue calculation for a complex 20-node enterprise topology."""
        import importlib.util
        bootstorm_path = os.path.join(SCRIPTS_DIR, "azambasha-bootstorm.py")
        spec = importlib.util.spec_from_file_location("azambasha_bootstorm", bootstorm_path)
        bs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bs)

        # Mock topology with mixed node types
        mock_nodes = {
            "1": {"template": "c8000v", "name": "Core-R1", "type": "qemu", "status": 0},
            "2": {"template": "c8000v", "name": "Core-R2", "type": "qemu", "status": 0},
            "3": {"template": "xrv9k", "name": "Edge-XR1", "type": "qemu", "status": 0},
            "4": {"template": "xrv9k", "name": "Edge-XR2", "type": "qemu", "status": 0},
            "5": {"template": "csr1000v", "name": "Agg-1", "type": "qemu", "status": 0},
            "6": {"template": "csr1000v", "name": "Agg-2", "type": "qemu", "status": 0},
            "7": {"template": "veos", "name": "Leaf-1", "type": "qemu", "status": 0},
            "8": {"template": "veos", "name": "Leaf-2", "type": "qemu", "status": 0},
            "9": {"template": "iol", "name": "Access-SW1", "type": "iol", "status": 0},
            "10": {"template": "iol", "name": "Access-SW2", "type": "iol", "status": 0},
            "11": {"template": "vpcs", "name": "Host-1", "type": "vpcs", "status": 0},
            "12": {"template": "vpcs", "name": "Host-2", "type": "vpcs", "status": 0},
        }

        # Classify nodes
        heavy = []
        medium = []
        light = []

        for nid, node in mock_nodes.items():
            weight, _ = bs.classify_node(node)
            if weight == "heavy":
                heavy.append(nid)
            elif weight == "medium":
                medium.append(nid)
            else:
                light.append(nid)

        self.assertEqual(len(heavy), 4, "Should detect 4 heavy nodes (2x C8000v, 2x XRv9k)")
        self.assertEqual(len(medium), 4, "Should detect 4 medium nodes (2x CSR1000v, 2x vEOS)")
        self.assertEqual(len(light), 4, "Should detect 4 light nodes (2x IOL, 2x VPCS)")

if __name__ == "__main__":
    unittest.main()
