"""
Unit Tests for AzamLabs Virtual Dataplane & Network Engineering
Verifies Fabric Live Cabling, Anti-DHCP Leak Sandbox, Traffic Impairment, Packet Capture, and Chaos Flapper.
"""

import pytest
import asyncio
from pathlib import Path

from azamlabs.core.schema import AzamLink, ImpairmentProfile, LinkStatus
from azamlabs.network.fabric import fabric
from azamlabs.network.sandbox import sandbox
from azamlabs.network.impairment import impairment_engine
from azamlabs.network.capture import capture_manager
from azamlabs.network.chaos import chaos_flapper


@pytest.mark.asyncio
async def test_fabric_live_cabling():
    link = AzamLink(
        source_node="Router1",
        source_interface="Gi0/1",
        target_node="Switch1",
        target_interface="Gi0/1",
    )
    lab_id = "test_fabric_lab"

    # Connect link
    connected = await fabric.connect_link(link, lab_id)
    assert connected is True
    assert link.status == LinkStatus.UP

    active_links = fabric.list_active_links(lab_id)
    assert len(active_links) == 1
    assert active_links[0]["source"] == "Router1:Gi0/1"
    assert active_links[0]["target"] == "Switch1:Gi0/1"

    # Disconnect live link
    disconnected = await fabric.disconnect_link(link, lab_id)
    assert disconnected is True
    assert link.status == LinkStatus.DOWN


@pytest.mark.asyncio
async def test_anti_dhcp_leak_sandbox():
    bridge_name = "azam_test0"

    # Apply sandbox
    applied = await sandbox.apply_sandbox(bridge_name)
    assert applied is True

    status = sandbox.get_status()
    assert status["sandbox_active"] is True
    assert bridge_name in status["protected_bridges"]

    # Remove sandbox
    removed = await sandbox.remove_sandbox(bridge_name)
    assert removed is True
    assert bridge_name not in sandbox.get_status()["protected_bridges"]


@pytest.mark.asyncio
async def test_traffic_impairment_engine():
    profile = ImpairmentProfile(
        delay_ms=30.0,
        jitter_ms=5.0,
        loss_percent=2.5,
        corrupt_percent=0.1,
    )
    iface = "veth_test_wire"

    # Build and verify tc command
    cmd = impairment_engine.build_tc_command(iface, profile)
    assert "netem" in cmd
    assert "delay" in cmd
    assert "30.0ms" in cmd
    assert "5.0ms" in cmd
    assert "loss" in cmd
    assert "2.5%" in cmd

    # Apply impairment
    applied = await impairment_engine.apply_impairment(iface, profile)
    assert applied is True
    retrieved = impairment_engine.get_impairment(iface)
    assert retrieved is not None
    assert retrieved.delay_ms == 30.0

    # Remove impairment
    cleared = await impairment_engine.remove_impairment(iface)
    assert cleared is True
    assert impairment_engine.get_impairment(iface) is None


@pytest.mark.asyncio
async def test_packet_capture_manager():
    lab_id = "test_cap_lab"
    link_id = "link_101"
    iface = "veth_test_wire"

    # 1. Verify PCAP header generation
    header = capture_manager.create_pcap_header()
    assert len(header) == 24
    # Magic number 0xa1b2c3d4
    assert header[:4] == b"\xa1\xb2\xc3\xd4"

    # 2. Start Capture
    cap_id = await capture_manager.start_capture(lab_id, link_id, iface)
    assert cap_id.startswith("cap_")

    captures = capture_manager.list_captures(lab_id)
    assert len(captures) == 1
    assert captures[0]["capture_id"] == cap_id
    assert captures[0]["status"] == "capturing"

    # 3. Stop Capture
    pcap_path = await capture_manager.stop_capture(cap_id)
    assert pcap_path is not None
    assert pcap_path.exists()
    assert pcap_path.stat().st_size >= 24


@pytest.mark.asyncio
async def test_chaos_link_flapper():
    link = AzamLink(
        source_node="Edge-A",
        source_interface="eth1",
        target_node="Edge-B",
        target_interface="eth1",
    )
    lab_id = "chaos_test_lab"

    # Start short flap cycle (0.05s up, 0.05s down, 2 cycles)
    task_id = chaos_flapper.start_flap(link, lab_id, up_sec=0.05, down_sec=0.05, cycles=2)
    assert task_id.startswith("chaos_")

    active = chaos_flapper.list_active()
    assert any(t["task_id"] == task_id for t in active)

    # Let the cycle run
    await asyncio.sleep(0.3)

    # Confirm completion or stop
    chaos_flapper.stop_flap(task_id)
