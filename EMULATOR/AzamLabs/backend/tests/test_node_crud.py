"""
Unit Tests for Node & Link Lifecycle CRUD Endpoints
"""

import pytest
from fastapi.testclient import TestClient

from azamlabs.main import app

client = TestClient(app)


@pytest.fixture
def sample_lab():
    """Create a temporary lab topology for CRUD testing."""
    response = client.post(
        "/api/v1/labs",
        json={"name": "CRUD Test Lab", "description": "Testing node and link CRUD lifecycle"},
    )
    assert response.status_code == 200
    lab = response.json()
    yield lab["id"]
    # Teardown
    client.delete(f"/api/v1/labs/{lab['id']}")


def test_add_single_node(sample_lab):
    """Test creating a single node with template parameters."""
    payload = {
        "name": "R1",
        "device_type": "router",
        "driver": "iol",
        "image": "L3-ADVENTERPRISE9-M-15.5-2T.bin",
        "template_id": "cisco_iol_l3",
        "vcpus": 1,
        "ram_mb": 512,
        "x": 200.0,
        "y": 150.0,
        "count": 1,
    }
    response = client.post(f"/api/v1/labs/{sample_lab}/nodes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    node = data[0]
    assert node["name"] == "R1"
    assert node["console_port"] >= 30000
    assert len(node["interfaces"]) >= 4

    # Verify topology persisted in DB
    lab_resp = client.get(f"/api/v1/labs/{sample_lab}")
    assert lab_resp.status_code == 200
    topo = lab_resp.json()
    assert any(n["name"] == "R1" for n in topo["nodes"])


def test_add_batch_nodes_auto_increment(sample_lab):
    """Test creating batch nodes with auto-incrementing names and staggered coordinates."""
    payload = {
        "name": "Switch",
        "device_type": "switch",
        "driver": "iol",
        "image": "L2-ADVENTERPRISE9-M-15.2-MAY-2018.bin",
        "template_id": "cisco_iol_l2",
        "vcpus": 1,
        "ram_mb": 512,
        "x": 100.0,
        "y": 100.0,
        "count": 3,
    }
    response = client.post(f"/api/v1/labs/{sample_lab}/nodes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    names = [n["name"] for n in data]
    assert names == ["Switch1", "Switch2", "Switch3"]

    # Verify distinct console ports and coordinates
    ports = [n["console_port"] for n in data]
    assert len(set(ports)) == 3
    x_coords = [n["pos_x"] for n in data]
    assert x_coords[1] > x_coords[0]


def test_clone_node(sample_lab):
    """Test cloning a node with offset and new console port."""
    add_resp = client.post(
        f"/api/v1/labs/{sample_lab}/nodes",
        json={"name": "CoreRouter", "device_type": "router", "driver": "qemu", "count": 1, "x": 100, "y": 100},
    )
    node_id = add_resp.json()[0]["id"]

    # Clone it
    clone_resp = client.post(f"/api/v1/labs/{sample_lab}/nodes/{node_id}/clone")
    assert clone_resp.status_code == 200
    cloned = clone_resp.json()
    assert cloned["name"] in ("CoreRouter2", "CoreRouter_clone")
    assert cloned["id"] != node_id
    assert cloned["pos_x"] == 150.0
    assert cloned["pos_y"] == 150.0


def test_wipe_and_isolate_node(sample_lab):
    """Test wipe and isolate endpoints on node."""
    add_resp = client.post(
        f"/api/v1/labs/{sample_lab}/nodes",
        json={"name": "TestNode", "device_type": "router", "driver": "iol", "count": 1},
    )
    node_id = add_resp.json()[0]["id"]

    # Test wipe
    wipe_resp = client.post(f"/api/v1/labs/{sample_lab}/nodes/{node_id}/wipe")
    assert wipe_resp.status_code == 200
    assert wipe_resp.json()["status"] == "wiped"

    # Test isolate
    isolate_resp = client.post(f"/api/v1/labs/{sample_lab}/nodes/{node_id}/isolate?isolate=true")
    assert isolate_resp.status_code == 200
    assert isolate_resp.json()["isolated"] is True


def test_delete_node_cascades_links(sample_lab):
    """Test that deleting a node also deletes associated links."""
    n1_resp = client.post(f"/api/v1/labs/{sample_lab}/nodes", json={"name": "N1", "device_type": "router", "count": 1})
    n2_resp = client.post(f"/api/v1/labs/{sample_lab}/nodes", json={"name": "N2", "device_type": "router", "count": 1})
    n1_id = n1_resp.json()[0]["id"]
    n2_id = n2_resp.json()[0]["id"]

    # Connect them
    connect_resp = client.post(
        f"/api/v1/labs/{sample_lab}/connect",
        json={
            "source_node": n1_id,
            "source_interface": "eth0",
            "target_node": n2_id,
            "target_interface": "eth0",
        },
    )
    assert connect_resp.status_code == 200

    # Delete N1
    del_resp = client.delete(f"/api/v1/labs/{sample_lab}/nodes/{n1_id}")
    assert del_resp.status_code == 200

    # Verify N1 and the link are removed from topology
    lab_resp = client.get(f"/api/v1/labs/{sample_lab}")
    topo = lab_resp.json()
    assert not any(n["id"] == n1_id for n in topo["nodes"])
    assert len(topo["links"]) == 0


def test_batch_delete_nodes(sample_lab):
    """Test batch deleting multiple nodes."""
    res = client.post(f"/api/v1/labs/{sample_lab}/nodes", json={"name": "Batch", "device_type": "router", "count": 3})
    node_ids = [n["id"] for n in res.json()]

    del_res = client.post(f"/api/v1/labs/{sample_lab}/nodes/batch-delete", json={"node_ids": node_ids[:2]})
    assert del_res.status_code == 200
    assert len(del_res.json()["deleted_nodes"]) == 2

    # Verify only 1 remains
    lab_resp = client.get(f"/api/v1/labs/{sample_lab}")
    assert len(lab_resp.json()["nodes"]) == 1


def test_add_virtual_network_cloud(sample_lab):
    """Test creating a virtual network cloud (Management / NAT / Isolated)."""
    payload = {
        "name": "MGMT-CLOUD",
        "network_type": "management",
        "bridge_name": "azam0",
        "x": 300.0,
        "y": 80.0,
    }
    response = client.post(f"/api/v1/labs/{sample_lab}/networks", json=payload)
    assert response.status_code == 200
    cloud = response.json()
    assert cloud["name"] == "MGMT-CLOUD"
    assert cloud["net_type"] == "management"


def test_link_suspend_and_impairment(sample_lab):
    """Test link cable cut (suspend) and NetEm impairment endpoints."""
    n1_resp = client.post(f"/api/v1/labs/{sample_lab}/nodes", json={"name": "A", "device_type": "router", "count": 1})
    n2_resp = client.post(f"/api/v1/labs/{sample_lab}/nodes", json={"name": "B", "device_type": "router", "count": 1})
    n1_id = n1_resp.json()[0]["id"]
    n2_id = n2_resp.json()[0]["id"]

    connect_resp = client.post(
        f"/api/v1/labs/{sample_lab}/connect",
        json={
            "source_node": n1_id,
            "source_interface": "eth0",
            "target_node": n2_id,
            "target_interface": "eth0",
        },
    )
    link = connect_resp.json()["link"]
    link_id = link["id"]

    # Test link suspend
    suspend_resp = client.post(f"/api/v1/labs/{sample_lab}/links/{link_id}/suspend")
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["suspended"] is True

    # Test link unsuspend
    unsuspend_resp = client.post(f"/api/v1/labs/{sample_lab}/links/{link_id}/suspend")
    assert unsuspend_resp.status_code == 200
    assert unsuspend_resp.json()["suspended"] is False

    # Test link impairment
    impair_payload = {
        "latency_ms": 25.0,
        "jitter_ms": 5.0,
        "loss_percent": 1.5,
        "rate_kbps": 100000,
    }
    impair_resp = client.post(f"/api/v1/labs/{sample_lab}/links/{link_id}/impairment", json=impair_payload)
    assert impair_resp.status_code == 200
    assert impair_resp.json()["profile"]["delay_ms"] == 25.0

    # Test link deletion
    del_link_resp = client.delete(f"/api/v1/labs/{sample_lab}/links/{link_id}")
    assert del_link_resp.status_code == 200
    lab_resp = client.get(f"/api/v1/labs/{sample_lab}")
    assert len(lab_resp.json()["links"]) == 0
