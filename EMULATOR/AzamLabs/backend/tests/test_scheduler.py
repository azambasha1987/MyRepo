"""
Unit Tests for AzamLabs Anti-Bootstorm Scheduler & Eco-Mode
"""

import asyncio
import pytest
from azamlabs.core.schema import AzamNode, DeviceType, DriverType, NodeStatus
from azamlabs.core.scheduler import AntiBootstormScheduler, BootTier, EcoModeGovernor


def test_boot_tier_classification():
    sw = AzamNode(name="SW1", device_type=DeviceType.SWITCH, driver=DriverType.DOCKER, image="ceos")
    rtr = AzamNode(name="R1", device_type=DeviceType.ROUTER, driver=DriverType.QEMU, image="c8000v")
    fw = AzamNode(name="FW1", device_type=DeviceType.FIREWALL, driver=DriverType.QEMU, image="fortigate")
    host = AzamNode(name="H1", device_type=DeviceType.HOST, driver=DriverType.DOCKER, image="alpine")

    assert BootTier.classify(sw) == BootTier.INFRASTRUCTURE
    assert BootTier.classify(rtr) == BootTier.CORE_ROUTING
    assert BootTier.classify(fw) == BootTier.SECURITY_EDGE
    assert BootTier.classify(host) == BootTier.WORKLOADS

    scheduler = AntiBootstormScheduler()
    sequence = scheduler.plan_boot_sequence([host, rtr, sw, fw])
    # Verify proper order: Switch first, then Router, then Firewall, then Host
    assert sequence[0].name == "SW1"
    assert sequence[1].name == "R1"
    assert sequence[2].name == "FW1"
    assert sequence[3].name == "H1"


@pytest.mark.asyncio
async def test_staggered_startup():
    scheduler = AntiBootstormScheduler(stagger_delay=0.05, max_concurrent_boots=2)
    n1 = AzamNode(name="N1", device_type=DeviceType.SWITCH, driver=DriverType.DOCKER, image="test")
    n2 = AzamNode(name="N2", device_type=DeviceType.ROUTER, driver=DriverType.DOCKER, image="test")

    booted = []

    async def _mock_boot(node: AzamNode) -> bool:
        booted.append(node.name)
        return True

    results = await scheduler.execute_staggered_startup([n1, n2], _mock_boot)
    assert len(booted) == 2
    assert results[n1.id] is True
    assert results[n2.id] is True


def test_eco_mode_governor():
    governor = EcoModeGovernor(timeout_minutes=15)
    node_id = "node-101"

    # Initially inactive/idle
    assert governor.is_idle(node_id) is False

    # Record activity
    governor.record_activity(node_id)
    assert governor.is_idle(node_id) is False
