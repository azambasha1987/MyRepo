"""
Unit Tests for AzamLabs Central Engine & API
"""

import pytest
from httpx import AsyncClient, ASGITransport

from azamlabs.main import app
from azamlabs.core.schema import AzamTopology, AzamNode, DeviceType, DriverType, NodeStatus
from azamlabs.core.engine import engine
from azamlabs.core.ksm import KsmManager
from azamlabs.core.cluster import cluster_manager


@pytest.mark.asyncio
async def test_engine_lifecycle():
    topo = AzamTopology(name="Engine Test Lab")
    r1 = AzamNode(name="TestR1", device_type=DeviceType.ROUTER, driver=DriverType.DOCKER, image="frr:latest")
    topo.add_node(r1)

    created = engine.create_lab(topo)
    assert created.id == topo.id

    # Start single node
    started = await engine.start_node(topo.id, r1.id)
    assert started is True
    status = engine.get_lab_status(topo.id)
    assert status["running_nodes"] == 1

    # Stop single node
    stopped = await engine.stop_node(topo.id, r1.id)
    assert stopped is True
    status = engine.get_lab_status(topo.id)
    assert status["running_nodes"] == 0

    # Start all
    start_results = await engine.start_all_nodes(topo.id)
    assert start_results[r1.id] is True

    # Wipe all
    wiped = await engine.wipe_all_nodes(topo.id)
    assert wiped is True


@pytest.mark.asyncio
async def test_fastapi_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert "AzamLabs" in data["platform"]

        # Create Lab via REST API
        new_lab = {
            "name": "REST API Test Lab",
            "description": "Created via FastAPI",
            "nodes": [
                {
                    "name": "API-R1",
                    "device_type": "router",
                    "driver": "docker",
                    "image": "frr:latest",
                }
            ],
            "links": []
        }
        create_resp = await client.post("/api/v1/labs", json=new_lab)
        assert create_resp.status_code == 200
        lab_data = create_resp.json()
        lab_id = lab_data["id"]

        # List Labs
        list_resp = await client.get("/api/v1/labs")
        assert list_resp.status_code == 200
        assert any(l["id"] == lab_id for l in list_resp.json())

        # Start All
        start_resp = await client.post(f"/api/v1/labs/{lab_id}/start")
        assert start_resp.status_code == 200

        # Lab Status
        status_resp = await client.get(f"/api/v1/labs/{lab_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["running_nodes"] == 1

        # Delete Lab
        del_resp = await client.delete(f"/api/v1/labs/{lab_id}")
        assert del_resp.status_code == 200


def test_ksm_and_cluster():
    telemetry = KsmManager.get_telemetry()
    assert "saved_ram_mb" in telemetry

    satellites = cluster_manager.list_satellites()
    assert len(satellites) >= 1
    assert satellites[0].id == "master"

    placement = cluster_manager.schedule_placement(1024)
    assert placement == "master"
