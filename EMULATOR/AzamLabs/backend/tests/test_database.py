"""
Unit Tests for AzamLabs Database Manager
"""

import tempfile
from pathlib import Path
import pytest

from azamlabs.core.database import DatabaseManager
from azamlabs.core.schema import AzamTopology, AzamNode, DeviceType, DriverType, NodeStatus


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_azamlabs.db"
        manager = DatabaseManager(db_file)
        manager.init_db()
        yield manager


def test_save_and_get_topology(temp_db):
    topo = AzamTopology(name="Production BGP Mesh", description="Test topology")
    r1 = AzamNode(name="R1", device_type=DeviceType.ROUTER, driver=DriverType.DOCKER, image="frrouting/frr:latest")
    topo.add_node(r1)

    temp_db.save_topology(topo)
    retrieved = temp_db.get_topology(topo.id)

    assert retrieved is not None
    assert retrieved.name == "Production BGP Mesh"
    assert len(retrieved.nodes) == 1
    assert retrieved.nodes[0].name == "R1"


def test_update_node_status(temp_db):
    topo = AzamTopology(name="State Lab")
    node = AzamNode(name="Core1", device_type=DeviceType.SWITCH, driver=DriverType.DOCKER, image="ceos:4.30.0F")
    topo.add_node(node)
    temp_db.save_topology(topo)

    temp_db.update_node_status(topo.id, node.id, NodeStatus.RUNNING, pid=12345, console_port=32768)
    updated_topo = temp_db.get_topology(topo.id)

    target_node = updated_topo.get_node(node.name)
    assert target_node.status == NodeStatus.RUNNING
    assert target_node.console_port == 32768


def test_delete_topology(temp_db):
    topo = AzamTopology(name="Transient Lab")
    temp_db.save_topology(topo)

    assert temp_db.get_topology(topo.id) is not None
    deleted = temp_db.delete_topology(topo.id)
    assert deleted is True
    assert temp_db.get_topology(topo.id) is None
