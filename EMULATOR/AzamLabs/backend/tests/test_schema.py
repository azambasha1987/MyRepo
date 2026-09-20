"""
Unit Tests for AzamLabs Universal Schema
"""

import pytest
from azamlabs.core.schema import (
    AzamTopology,
    AzamNode,
    AzamInterface,
    AzamLink,
    AzamNetwork,
    ImpairmentProfile,
    DeviceType,
    DriverType,
    NodeStatus,
    LinkStatus,
)


def test_create_topology():
    topo = AzamTopology(name="Test Core Fabric", description="2-Router Core")
    r1 = AzamNode(name="R1", device_type=DeviceType.ROUTER, driver=DriverType.QEMU, image="cisco-c8000v-17.09.03a")
    r2 = AzamNode(name="R2", device_type=DeviceType.ROUTER, driver=DriverType.QEMU, image="cisco-c8000v-17.09.03a")

    topo.add_node(r1)
    topo.add_node(r2)
    link = topo.add_link("R1", "GigabitEthernet1", "R2", "GigabitEthernet1")

    assert len(topo.nodes) == 2
    assert len(topo.links) == 1
    assert topo.get_node("R1") is not None
    assert topo.get_node("R2") is not None
    assert link.source_node == "R1"
    assert link.target_node == "R2"


def test_topology_yaml_serialization():
    topo = AzamTopology(name="YAML Export Test")
    sw1 = AzamNode(name="SW1", device_type=DeviceType.SWITCH, driver=DriverType.DOCKER, image="ceos:4.30.0F")
    topo.add_node(sw1)

    yaml_str = topo.to_yaml()
    assert "YAML Export Test" in yaml_str
    assert "SW1" in yaml_str

    deserialized = AzamTopology.from_yaml(yaml_str)
    assert deserialized.name == "YAML Export Test"
    assert len(deserialized.nodes) == 1
    assert deserialized.nodes[0].name == "SW1"


def test_link_impairment_profile():
    profile = ImpairmentProfile(delay_ms=25.0, jitter_ms=5.0, loss_percent=1.5)
    assert profile.is_active is True
    assert profile.delay_ms == 25.0
    assert profile.loss_percent == 1.5

    clean_profile = ImpairmentProfile()
    assert clean_profile.is_active is False
