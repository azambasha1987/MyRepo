"""
Unit Tests for AzamLabs Device Execution Drivers
Verifies Docker, QEMU (QCOW2 Overlays), Cisco IOL (License & 100:1 Throttle), and VPCS Drivers.
"""

import pytest
from pathlib import Path

from azamlabs.core.schema import AzamNode, DeviceType, DriverType, NodeStatus
from azamlabs.drivers.factory import DriverFactory
from azamlabs.drivers.docker import DockerDriver
from azamlabs.drivers.qemu import QemuDriver
from azamlabs.drivers.iol import IolDriver
from azamlabs.drivers.vpcs import VpcsDriver


@pytest.mark.asyncio
async def test_driver_factory():
    d_driver = DriverFactory.get_driver(DriverType.DOCKER)
    assert isinstance(d_driver, DockerDriver)

    q_driver = DriverFactory.get_driver(DriverType.QEMU)
    assert isinstance(q_driver, QemuDriver)

    i_driver = DriverFactory.get_driver(DriverType.IOL)
    assert isinstance(i_driver, IolDriver)

    v_driver = DriverFactory.get_driver(DriverType.VPCS)
    assert isinstance(v_driver, VpcsDriver)


@pytest.mark.asyncio
async def test_docker_driver_lifecycle(tmp_path):
    driver = DockerDriver()
    node = AzamNode(
        name="Test-FRR",
        device_type=DeviceType.ROUTER,
        driver=DriverType.DOCKER,
        image="frr:latest",
        startup_config="hostname Test-FRR\nrouter ospf\n",
    )
    lab_id = "test_lab_docker"

    # 1. Create
    created = await driver.create_node(node, lab_id)
    assert created is True
    node_dir = driver.get_node_dir(lab_id, node)
    assert (node_dir / "startup-config").exists()
    assert "router ospf" in (node_dir / "startup-config").read_text()

    # 2. Start
    pid = await driver.start_node(node, lab_id)
    assert pid > 0
    assert node.status == NodeStatus.RUNNING
    assert node.console_port is not None
    assert (node_dir / "docker.pid").exists()

    # 3. Status
    status = await driver.get_node_status(node, lab_id)
    assert status == NodeStatus.RUNNING

    # 4. Console info
    info = driver.get_console_info(node, lab_id)
    assert info["node_name"] == "Test-FRR"
    assert info["port"] == node.console_port

    # 5. Stop
    stopped = await driver.stop_node(node, lab_id)
    assert stopped is True
    assert node.status == NodeStatus.STOPPED

    # 6. Wipe
    wiped = await driver.wipe_node(node, lab_id)
    assert wiped is True


@pytest.mark.asyncio
async def test_qemu_driver_lifecycle(tmp_path):
    driver = QemuDriver()
    node = AzamNode(
        name="Core-C8000v",
        device_type=DeviceType.ROUTER,
        driver=DriverType.QEMU,
        image="c8000v.qcow2",
        cpu=2,
        ram_mb=4096,
        startup_config="hostname Core-C8000v\n",
    )
    lab_id = "test_lab_qemu"

    # 1. Create (creates disposable overlay)
    created = await driver.create_node(node, lab_id)
    assert created is True
    node_dir = driver.get_node_dir(lab_id, node)
    assert (node_dir / "overlay.qcow2").exists()

    # 2. Start
    pid = await driver.start_node(node, lab_id)
    assert pid > 0
    assert node.status == NodeStatus.RUNNING
    assert (node_dir / "qemu.pid").exists()

    # 3. Stop
    stopped = await driver.stop_node(node, lab_id)
    assert stopped is True
    assert node.status == NodeStatus.STOPPED

    # 4. Wipe (restores Day-0 overlay)
    wiped = await driver.wipe_node(node, lab_id)
    assert wiped is True
    assert (node_dir / "overlay.qcow2").exists()


@pytest.mark.asyncio
async def test_iol_driver_license_and_lifecycle():
    driver = IolDriver()
    # Test built-in automated iourc keygen
    license_text = IolDriver.generate_iourc()
    assert "[license]" in license_text
    assert " = " in license_text
    assert ";" in license_text

    node = AzamNode(
        name="IOL-Switch1",
        device_type=DeviceType.SWITCH,
        driver=DriverType.IOL,
        image="cisco-iol-l2.bin",
        startup_config="hostname IOL-Switch1\n",
    )
    lab_id = "test_lab_iol"

    # 1. Create
    created = await driver.create_node(node, lab_id)
    assert created is True
    node_dir = driver.get_node_dir(lab_id, node)
    assert (node_dir / "iourc").exists()
    assert (node_dir / "startup-config").exists()

    # 2. Start
    pid = await driver.start_node(node, lab_id)
    assert pid > 0
    assert node.status == NodeStatus.RUNNING
    assert (node_dir / "iol.pid").exists()

    # 3. Stop
    stopped = await driver.stop_node(node, lab_id)
    assert stopped is True
    assert node.status == NodeStatus.STOPPED


@pytest.mark.asyncio
async def test_vpcs_driver_lifecycle():
    driver = VpcsDriver()
    node = AzamNode(
        name="PC-1",
        device_type=DeviceType.HOST,
        driver=DriverType.VPCS,
        image="vpcs",
    )
    iface = node.add_interface("eth0")
    iface.ip_address = "192.168.1.50/24 192.168.1.1"

    lab_id = "test_lab_vpcs"

    # 1. Create (generates startup.vpc script)
    created = await driver.create_node(node, lab_id)
    assert created is True
    node_dir = driver.get_node_dir(lab_id, node)
    script_file = node_dir / "startup.vpc"
    assert script_file.exists()
    content = script_file.read_text()
    assert "set pcname PC-1" in content
    assert "ip 192.168.1.50/24 192.168.1.1" in content

    # 2. Start
    pid = await driver.start_node(node, lab_id)
    assert pid > 0
    assert node.status == NodeStatus.RUNNING

    # 3. Stop
    stopped = await driver.stop_node(node, lab_id)
    assert stopped is True
    assert node.status == NodeStatus.STOPPED
