"""
Unit and benchmark tests for AzamGNS3 performance optimizations.
"""

import sys
import os
import unittest
import asyncio

# Ensure gns3-server is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "gns3-server"))

from gns3server.controller.bootstorm import BootstormEngine, classify_node_weight
from gns3server.compute.qemu.cpu_governor import CpuGovernor


class DummyNode:
    def __init__(self, name, node_type="qemu"):
        self.name = name
        self.node_type = node_type
        self.status = "stopped"
        self.started_at = None

    async def start(self):
        self.status = "started"
        self.started_at = asyncio.get_event_loop().time()


class TestBootstormEngine(unittest.TestCase):
    def test_node_classification(self):
        # Heavy nodes
        c8k = DummyNode("C8000v-Edge-Router-1")
        xrv = DummyNode("XRv9k-Core-1")
        win = DummyNode("Windows11-Host")
        self.assertEqual(classify_node_weight(c8k), 3)
        self.assertEqual(classify_node_weight(xrv), 3)
        self.assertEqual(classify_node_weight(win), 3)

        # Medium nodes
        veos = DummyNode("vEOS-Leaf-1")
        iosv = DummyNode("IOSv-Switch-1")
        csr = DummyNode("CSR1000v-GW")
        self.assertEqual(classify_node_weight(veos), 2)
        self.assertEqual(classify_node_weight(iosv), 2)
        self.assertEqual(classify_node_weight(csr), 2)

        # Light nodes
        vpcs = DummyNode("PC-1", node_type="vpcs")
        alpine = DummyNode("Alpine-Server", node_type="docker")
        self.assertEqual(classify_node_weight(vpcs), 1)
        self.assertEqual(classify_node_weight(alpine), 1)

    def test_staggered_execution_order(self):
        async def run_test():
            nodes = [
                DummyNode("PC-1", "vpcs"),
                DummyNode("C8000v-1"),
                DummyNode("IOSv-1"),
                DummyNode("Alpine-1", "docker"),
            ]
            # Fast test: run staggered
            await BootstormEngine.start_nodes_staggered(nodes)
            for n in nodes:
                self.assertEqual(n.status, "started")

        asyncio.run(run_test())


class TestCpuGovernor(unittest.TestCase):
    def test_dpdk_signature_detection(self):
        gov1 = CpuGovernor("node1", "C8000v-Edge", 12345)
        self.assertTrue(gov1.is_dpdk_target())

        gov2 = CpuGovernor("node2", "XRv9k-PE1", 12346)
        self.assertTrue(gov2.is_dpdk_target())

        gov3 = CpuGovernor("node3", "vIOS-L2-Switch", 12347)
        self.assertTrue(gov3.is_dpdk_target())

        gov4 = CpuGovernor("node4", "Ubuntu-Desktop", 12348)
        self.assertFalse(gov4.is_dpdk_target())


if __name__ == "__main__":
    unittest.main()
