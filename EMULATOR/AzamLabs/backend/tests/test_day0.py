"""
Unit Tests for AzamLabs Day-0 Automated Config Generator
"""

import pytest
from azamlabs.core.schema import AzamTopology, AzamNode, DeviceType, DriverType
from azamlabs.core.day0 import Day0ConfigGenerator


def test_auto_assign_ip_plan():
    topo = AzamTopology(name="Auto IP Lab")
    r1 = AzamNode(name="R1", device_type=DeviceType.ROUTER, driver=DriverType.QEMU, image="cisco-c8000v")
    r2 = AzamNode(name="R2", device_type=DeviceType.ROUTER, driver=DriverType.QEMU, image="cisco-c8000v")
    topo.add_node(r1)
    topo.add_node(r2)
    topo.add_link("R1", "GigabitEthernet1", "R2", "GigabitEthernet1")

    Day0ConfigGenerator.auto_assign_ip_plan(topo, base_prefix="10.50")

    r1_iface = r1.get_interface("GigabitEthernet1")
    r2_iface = r2.get_interface("GigabitEthernet1")

    assert r1_iface.ip_address == "10.50.1.1/30"
    assert r2_iface.ip_address == "10.50.1.2/30"


def test_generate_cisco_ios_day0():
    topo = AzamTopology(name="Cisco Day0")
    r1 = AzamNode(name="Core-RTR-01", device_type=DeviceType.ROUTER, driver=DriverType.QEMU, image="cisco-c8000v-17.09")
    iface = r1.add_interface("GigabitEthernet1")
    iface.ip_address = "10.10.1.1/30"
    topo.add_node(r1)

    cfg = Day0ConfigGenerator.generate_config(r1, topo, routing_protocol="ospf")

    assert "hostname Core-RTR-01" in cfg
    assert "ip domain-name azamlabs.internal" in cfg
    assert "interface GigabitEthernet1" in cfg
    assert "ip address 10.10.1.1 255.255.255.252" in cfg
    assert "router ospf 1" in cfg


def test_generate_arista_eos_day0():
    topo = AzamTopology(name="Arista Day0")
    sw1 = AzamNode(name="Spine-01", device_type=DeviceType.SWITCH, driver=DriverType.DOCKER, image="arista-veos-4.28")
    iface = sw1.add_interface("Ethernet1")
    iface.ip_address = "10.20.1.1/24"
    topo.add_node(sw1)

    cfg = Day0ConfigGenerator.generate_config(sw1, topo)

    assert "hostname Spine-01" in cfg
    assert "ip routing" in cfg
    assert "interface Ethernet1" in cfg
