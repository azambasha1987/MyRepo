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
        self.assertTrue(callable(getattr(bs_mod, "probe_console_port", None)))
        self.assertTrue(callable(getattr(bs_mod, "activate_ksm_deduplication", None)))

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

if __name__ == "__main__":
    unittest.main()
