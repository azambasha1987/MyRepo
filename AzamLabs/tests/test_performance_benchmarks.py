#!/usr/bin/env python3
"""
AzamLabs Hyper-Performance & Optimization Benchmark Test Suite (test_performance_benchmarks.py)
Validates the speed, RAM saving, and CPU reduction subsystems:
1. Ultra-KSM memory deduplication parameters and service units.
2. Cisco IOL 100:1 CPU idle governor & memory deduplication shim C code.
3. Silicon Dataplane Fast-Path Netfilter bypass & MTU 9000 configs.
4. Cgroups v2 dynamic CFS burst scheduling & loss-less priority transitions.
5. Anti-Bootstorm multi-tier queue classification (Heavy, Medium, Light).
6. PHP 8.4/8.5 OPcache bytecode acceleration & JIT tracing settings.
"""

import os
import re
import sys
import unittest
import importlib.util

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")

class TestPerformanceBenchmarks(unittest.TestCase):

    def test_ksm_service_configuration(self):
        """Verify KSM service tunes pages_to_scan, sleep_millisecs, and THP madvise."""
        speed_opt_sh = os.path.join(SCRIPTS_DIR, "azambasha-speed-optimizer.sh")
        self.assertTrue(os.path.isfile(speed_opt_sh), "azambasha-speed-optimizer.sh must exist")

        with open(speed_opt_sh, "r", encoding="utf-8") as f:
            content = f.read()

        # Check aggressive deduplication tunings
        self.assertIn("10000 > /sys/kernel/mm/ksm/pages_to_scan", content)
        self.assertIn("10 > /sys/kernel/mm/ksm/sleep_millisecs", content)
        self.assertIn("1 > /sys/kernel/mm/ksm/use_zero_pages", content)
        self.assertIn("madvise > /sys/kernel/mm/transparent_hugepage/enabled", content)

    def test_iol_shim_source_integrity(self):
        """Verify azam-iol-shim.c contains LD_PRELOAD interceptors and memory merge hooks."""
        shim_c = os.path.join(SCRIPTS_DIR, "azam-iol-shim.c")
        self.assertTrue(os.path.isfile(shim_c), "azam-iol-shim.c must exist")

        with open(shim_c, "r", encoding="utf-8") as f:
            code = f.read()

        # Check key functions and constants
        self.assertIn("PR_SET_MEMORY_MERGE", code)
        self.assertIn("MADV_MERGEABLE", code)
        self.assertIn("sched_yield()", code)
        self.assertIn("mark_memory_mergeable", code)
        self.assertIn("int select(", code)
        self.assertIn("int usleep(", code)
        self.assertIn("int nanosleep(", code)
        self.assertIn("g_idle_ticks", code)

    def test_dataplane_netfilter_bypass_and_mtu(self):
        """Verify Silicon Dataplane Engine configures netfilter bypass and MTU 9000."""
        dataplane_sh = os.path.join(SCRIPTS_DIR, "azambasha-dataplane-engine.sh")
        self.assertTrue(os.path.isfile(dataplane_sh), "azambasha-dataplane-engine.sh must exist")

        with open(dataplane_sh, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("net.bridge.bridge-nf-call-iptables = 0", content)
        self.assertIn("net.bridge.bridge-nf-call-ip6tables = 0", content)
        self.assertIn("net.bridge.bridge-nf-call-arptables = 0", content)
        self.assertIn("txqueuelen 10000", content)
        self.assertIn("mtu 9000", content)

    def test_cgroups_governor_logic(self):
        """Test the CPU Governor decision engine and classification patterns."""
        gov_path = os.path.join(SCRIPTS_DIR, "azambasha-cpu-governor.py")
        self.assertTrue(os.path.isfile(gov_path), "azambasha-cpu-governor.py must exist")

        # Import governor dynamically
        spec = importlib.util.spec_from_file_location("azambasha_cpu_gov", gov_path)
        gov_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gov_mod)

        governor = gov_mod.HeavyNodeGovernor()
        self.assertEqual(governor.check_interval, 2.0)
        self.assertEqual(governor.hysteresis_sec, 5.0)

        # Check that heavy routers are detected by TARGET_REGEX
        test_routers = ["c8000v", "cat9000v", "xrv9k", "csr1000v", "vios", "viosl2"]
        for rtr in test_routers:
            self.assertIsNotNone(
                gov_mod.TARGET_REGEX.search(f"/opt/qemu/bin/qemu-system-x86_64 -name {rtr}-1"),
                f"Router {rtr} must match governor target regex"
            )

    def test_anti_bootstorm_node_classification(self):
        """Test Anti-Bootstorm weight classification across Heavy, Medium, and Light nodes."""
        bootstorm_path = os.path.join(SCRIPTS_DIR, "azambasha-bootstorm.py")
        self.assertTrue(os.path.isfile(bootstorm_path), "azambasha-bootstorm.py must exist")

        spec = importlib.util.spec_from_file_location("azambasha_bootstorm", bootstorm_path)
        bs_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bs_mod)

        # 1. Heavy Nodes
        for h in ["c8000v", "cat9k", "xrv9k", "win11", "vmx", "nxosv9k"]:
            node = {"template": h, "name": f"R_{h}", "type": "qemu"}
            weight, _ = bs_mod.classify_node(node)
            self.assertEqual(weight, "heavy", f"Node {h} must be classified as heavy")

        # 2. Medium Nodes
        for m in ["csr1000v", "veos", "viosl2", "fortigate", "pfsense", "arista"]:
            node = {"template": m, "name": f"SW_{m}", "type": "qemu"}
            weight, _ = bs_mod.classify_node(node)
            self.assertEqual(weight, "medium", f"Node {m} must be classified as medium")

        # 3. Light Nodes
        for l in ["iol", "vpcs", "alpine", "docker", "dynamips"]:
            node = {"template": l, "name": f"PC_{l}", "type": l}
            weight, _ = bs_mod.classify_node(node)
            self.assertEqual(weight, "light", f"Node {l} must be classified as light")

    def test_anti_bootstorm_session_token_reuse_and_features(self):
        """Verify Anti-Bootstorm session token preservation, console readiness probing, and KSM."""
        bootstorm_path = os.path.join(SCRIPTS_DIR, "azambasha-bootstorm.py")
        self.assertTrue(os.path.isfile(bootstorm_path), "azambasha-bootstorm.py must exist")

        spec = importlib.util.spec_from_file_location("azambasha_bootstorm", bootstorm_path)
        bs_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bs_mod)

        # 1. Verify function availability
        self.assertTrue(callable(getattr(bs_mod, "get_active_db_token", None)))
        self.assertTrue(callable(getattr(bs_mod, "get_active_db_lab", None)))
        self.assertTrue(callable(getattr(bs_mod, "probe_console_port", None)))
        self.assertTrue(callable(getattr(bs_mod, "activate_ksm_deduplication", None)))
        self.assertTrue(callable(getattr(bs_mod, "resolve_lab_disk_path", None)))

        # 2. Verify signature compatibility
        import inspect
        sig_cs = inspect.signature(bs_mod.create_session)
        self.assertIn("token", sig_cs.parameters, "create_session must accept token parameter")

        sig_rb = inspect.signature(bs_mod.run_bootstorm)
        self.assertIn("token", sig_rb.parameters, "run_bootstorm must accept token parameter")
        self.assertIn("probe_console", sig_rb.parameters, "run_bootstorm must accept probe_console parameter")
        self.assertIn("ksm", sig_rb.parameters, "run_bootstorm must accept ksm parameter")

        # 3. Test console probe on invalid / empty port returns gracefully
        ok, msg = bs_mod.probe_console_port("127.0.0.1", "")
        self.assertTrue(ok)
        self.assertEqual(msg, "No console port")

        # 4. Test KSM function returns boolean status tuple
        ksm_ok, ksm_msg = bs_mod.activate_ksm_deduplication()
        self.assertIsInstance(ksm_ok, bool)
        self.assertIsInstance(ksm_msg, str)

        # 5. Test create_session with token on local host preserves token without POST /api/auth
        os.environ["AZAM_LOCAL"] = "1"
        try:
            cj, ctx, proto, opener = bs_mod.create_session("127.0.0.1", token="test_active_session_token_123")
            self.assertIsNotNone(cj)
            self.assertEqual(getattr(opener, "session_token", None), "test_active_session_token_123")

            # 6. Test create_session without token falls back gracefully to file on local host if API unreachable
            cj2, ctx2, proto2, opener2 = bs_mod.create_session("127.0.0.1", token=None)
            self.assertIsNotNone(cj2)
            self.assertIn(proto2, ("https", "http", "file"))
        finally:
            os.environ.pop("AZAM_LOCAL", None)

        # 7. Test resolve_lab_disk_path with placeholder returns non-empty string ending with .unl
        resolved = bs_mod.resolve_lab_disk_path("/Admin/active_lab.unl")
        self.assertTrue(resolved.endswith(".unl"))

    def test_php_opcache_and_jit_configuration(self):
        """Verify PHP OPcache bytecode accelerator and JIT tracing configs."""
        speed_opt_sh = os.path.join(SCRIPTS_DIR, "azambasha-speed-optimizer.sh")
        with open(speed_opt_sh, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("opcache.enable = 1", content)
        self.assertIn("opcache.memory_consumption = 256", content)
        self.assertIn("opcache.jit = tracing", content)
        self.assertIn("opcache.jit_buffer_size = 64M", content)
        self.assertIn("realpath_cache_size = 4096K", content)

    def test_sequenced_console_dispatcher_integrity(self):
        """Verify Sequenced Console Engine in azamlabs-features.js and azamlabs-sequenced-console.js."""
        feat_js = os.path.join(ROOT_DIR, "html", "azam-ops", "azamlabs-features.js")
        seq_js = os.path.join(ROOT_DIR, "html", "azam-ops", "azamlabs-sequenced-console.js")

        self.assertTrue(os.path.isfile(feat_js), "azamlabs-features.js must exist")
        self.assertTrue(os.path.isfile(seq_js), "azamlabs-sequenced-console.js must exist")

        with open(feat_js, "r", encoding="utf-8") as f:
            feat_code = f.read()
        with open(seq_js, "r", encoding="utf-8") as f:
            seq_code = f.read()

        for code in (feat_code, seq_code):
            self.assertIn("window.azamSequencedConsole", code)
            self.assertIn("naturalSort", code)
            self.assertIn("compareNatural", code)
            self.assertIn("getCategory", code)
            self.assertIn("getNodeDisplayName", code)
            self.assertIn("openSingle", code)
            self.assertIn("showHud", code)
            self.assertIn("pnq-seq-console-hud", code)
            # Verify Server, Sever typo tolerance, and VPC regexes
            self.assertIn("SERVER|SEVER", code)
            self.assertIn("VPC|VPCS|PC", code)
            self.assertIn("vpcs-first", code)
            self.assertIn("servers-first", code)
            # Verify SecureCRT 250ms and HTML5 180ms timings
            self.assertIn("180 : 250", code)
            self.assertIn("SecureCRT", code)
            self.assertIn("action-nodesconsole", code)

    def test_setup_windows_securecrt_powershell_script(self):
        """Verify Windows 1-Click SecureCRT Protocol Integrator & tab-naming wrapper."""
        ps1_path = os.path.join(SCRIPTS_DIR, "setup-windows-securecrt.ps1")
        self.assertTrue(os.path.isfile(ps1_path), "setup-windows-securecrt.ps1 must exist")

        with open(ps1_path, "r", encoding="utf-8") as f:
            ps1_code = f.read()

        self.assertIn("SecureCRT.exe", ps1_code)
        self.assertIn("HKEY_CLASSES_ROOT\\telnet", ps1_code)
        self.assertIn("/T /N", ps1_code)
        self.assertIn("azamlabs-securecrt.bat", ps1_code)

    def test_python_natural_sort_logic_simulation(self):
        """Simulate and verify the Natural Alphanumeric Sorting logic for device names."""
        import re

        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s) if text]

        def get_category(name):
            name_u = name.upper()
            if re.match(r'^(VPC|VPCS|PC|CLIENT)', name_u):
                return 'vpcs'
            if re.match(r'^(SERVER|SEVER|SRV|SVR|HOST|NODE|LINUX|WIN)', name_u):
                return 'servers'
            if re.match(r'^(SW|SWITCH|LEAF|SPINE)', name_u):
                return 'switches'
            if re.match(r'^(R|ROUTER|CORE|EDGE|GW)', name_u):
                return 'routers'
            return 'others'

        nodes = [
            {"id": 1, "name": "R10"},
            {"id": 2, "name": "R1"},
            {"id": 3, "name": "R2"},
            {"id": 4, "name": "SW10"},
            {"id": 5, "name": "SW2"},
            {"id": 6, "name": "SW1"},
            {"id": 7, "name": "Server-10"},
            {"id": 8, "name": "Server-1"},
            {"id": 9, "name": "Server-2"},
            {"id": 10, "name": "Sever-1"},
            {"id": 11, "name": "Sever-2"},
            {"id": 12, "name": "VPC-10"},
            {"id": 13, "name": "VPC-1"},
            {"id": 14, "name": "VPC-2"},
        ]

        # Pure Natural sort
        sorted_nodes = sorted(nodes, key=lambda n: natural_sort_key(n["name"]))
        sorted_names = [n["name"] for n in sorted_nodes]

        # Verify Server-1 < Server-2 < Server-10
        srv_idx_1 = sorted_names.index("Server-1")
        srv_idx_2 = sorted_names.index("Server-2")
        srv_idx_10 = sorted_names.index("Server-10")
        self.assertTrue(srv_idx_1 < srv_idx_2 < srv_idx_10, "Server-1 must come before Server-2 and Server-10")

        # Verify Sever-1 < Sever-2 (typo tolerance)
        svr_idx_1 = sorted_names.index("Sever-1")
        svr_idx_2 = sorted_names.index("Sever-2")
        self.assertTrue(svr_idx_1 < svr_idx_2, "Sever-1 must come before Sever-2")

        # Verify VPC-1 < VPC-2 < VPC-10
        vpc_idx_1 = sorted_names.index("VPC-1")
        vpc_idx_2 = sorted_names.index("VPC-2")
        vpc_idx_10 = sorted_names.index("VPC-10")
        self.assertTrue(vpc_idx_1 < vpc_idx_2 < vpc_idx_10, "VPC-1 must come before VPC-2 and VPC-10")

        # Category mapping verification
        self.assertEqual(get_category("Server-1"), "servers")
        self.assertEqual(get_category("Sever-2"), "servers")
        self.assertEqual(get_category("VPC-1"), "vpcs")
        self.assertEqual(get_category("R1"), "routers")
        self.assertEqual(get_category("SW1"), "switches")

        # Logical Hierarchy: Routers -> Switches -> Servers -> VPCs
        by_cat = {"routers": [], "switches": [], "servers": [], "vpcs": [], "others": []}
        for n in sorted_nodes:
            by_cat[get_category(n["name"])].append(n["name"])

        logical_order = by_cat["routers"] + by_cat["switches"] + by_cat["servers"] + by_cat["vpcs"]
        self.assertEqual(
            logical_order,
            [
                "R1", "R2", "R10",
                "SW1", "SW2", "SW10",
                "Server-1", "Server-2", "Server-10", "Sever-1", "Sever-2",
                "VPC-1", "VPC-2", "VPC-10"
            ]
        )

        # VPCs First: VPCs -> Servers -> Routers -> Switches
        vpcs_first_order = by_cat["vpcs"] + by_cat["servers"] + by_cat["routers"] + by_cat["switches"]
        self.assertEqual(
            vpcs_first_order,
            [
                "VPC-1", "VPC-2", "VPC-10",
                "Server-1", "Server-2", "Server-10", "Sever-1", "Sever-2",
                "R1", "R2", "R10",
                "SW1", "SW2", "SW10"
            ]
        )

        # Servers First: Servers -> VPCs -> Routers -> Switches
        servers_first_order = by_cat["servers"] + by_cat["vpcs"] + by_cat["routers"] + by_cat["switches"]
        self.assertEqual(
            servers_first_order,
            [
                "Server-1", "Server-2", "Server-10", "Sever-1", "Sever-2",
                "VPC-1", "VPC-2", "VPC-10",
                "R1", "R2", "R10",
                "SW1", "SW2", "SW10"
            ]
        )

if __name__ == "__main__":
    unittest.main()

