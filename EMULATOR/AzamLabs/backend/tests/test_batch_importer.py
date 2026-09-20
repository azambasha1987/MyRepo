"""
Integration and Unit Tests for BatchLabImporter, Cascading Deletion, and Folder Tree Operations.
All tests run against isolated mock/temporary databases to guarantee zero production pollution.
"""

import io
import json
import zipfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from azamlabs.converters.batch import BatchLabImporter
from azamlabs.core.database import DatabaseManager
from azamlabs.core.schema import AzamTopology, AzamNode, AzamLink, DriverType
from azamlabs.main import app


SAMPLE_UNL = """<?xml version="1.0" encoding="UTF-8"?>
<lab name="Branch-Office" version="1">
  <topology>
    <nodes>
      <node id="1" name="R1" type="qemu" template="c8000v" image="c8000v.qcow2" cpu="1" ram="1024"/>
      <node id="2" name="R2" type="iol" template="iol" image="cisco-iol.bin" cpu="1" ram="256"/>
    </nodes>
  </topology>
</lab>"""

SAMPLE_CLAB = """name: DC-Fabric
topology:
  nodes:
    spine1:
      kind: nokia_srlinux
      image: ghcr.io/nokia/srlinux:latest
    leaf1:
      kind: arista_ceos
      image: ceos:latest
  links:
    - endpoints: ["spine1:e1-1", "leaf1:eth1"]
"""


def create_multi_lab_zip_bytes() -> bytes:
    """Builds an in-memory ZIP archive containing multiple labs across subdirectories."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zp:
        zp.writestr("Enterprise/Branch/branch.unl", SAMPLE_UNL)
        zp.writestr("DataCenter/Fabric/dc.clab.yml", SAMPLE_CLAB)
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Creates an isolated temporary database for test execution."""
    test_db_path = tmp_path / "test_azamlabs.db"
    test_db = DatabaseManager(db_path=test_db_path)
    test_db.init_db()

    # Monkeypatch global db in database module and batch importer
    monkeypatch.setattr("azamlabs.core.database.db", test_db)
    monkeypatch.setattr("azamlabs.core.folders.db", test_db)
    monkeypatch.setattr("azamlabs.core.engine.db", test_db)
    monkeypatch.setattr("azamlabs.converters.batch.db", test_db)

    return test_db


def test_batch_importer_dry_run(tmp_path, isolated_db):
    """Verifies that dry_run=True returns parsed stats without touching the database."""
    zip_bytes = create_multi_lab_zip_bytes()

    results = BatchLabImporter.import_zip(zip_bytes, target_folder="/Imported", dry_run=True)

    assert results["total_found"] == 2
    assert results["imported_count"] == 2
    assert results["failed_count"] == 0
    assert len(results["imported_labs"]) == 2

    # Database must remain empty
    topos = isolated_db.list_topologies()
    assert len(topos) == 0


def test_batch_importer_preserves_folder_hierarchy(isolated_db):
    """Verifies that batch importing creates folders and assigns labs correctly."""
    zip_bytes = create_multi_lab_zip_bytes()

    results = BatchLabImporter.import_zip(zip_bytes, target_folder="/Imported", dry_run=False)

    assert results["imported_count"] == 2
    topos = isolated_db.list_topologies()
    assert len(topos) == 2

    # Verify folders exist in database
    folders = {f["path"]: f for f in isolated_db.list_folders()}
    assert "/Imported/Enterprise/Branch" in folders
    assert "/Imported/DataCenter/Fabric" in folders


def test_batch_importer_iol_licensing_and_port_collision():
    """Verifies dynamic port collision resolution and Cisco IOL auto-licensing."""
    topo = AzamTopology(name="IOL-Test")
    n1 = AzamNode(name="Core-IOL", driver=DriverType.IOL, image="cisco-iol.bin")
    n2 = AzamNode(name="Peer-Router", driver=DriverType.QEMU, image="c8000v.qcow2")

    topo.add_node(n1)
    topo.add_node(n2)

    # Force port collision on n1
    topo.add_link("Core-IOL", "eth0", "Peer-Router", "eth0")
    topo.add_link("Core-IOL", "eth0", "Peer-Router", "eth1")  # Collision on Core-IOL eth0

    BatchLabImporter.resolve_port_collisions(topo)
    BatchLabImporter.apply_iol_auto_licensing(topo)

    # Core-IOL interfaces must be unique
    n1_ifaces = [i.name for i in n1.interfaces]
    assert len(set(n1_ifaces)) == 2
    assert "eth0" in n1_ifaces
    assert "eth0_2" in n1_ifaces

    # IOL licensing environment variables must be injected
    assert n1.env.get("IOURC") == "/etc/opt/iou/iourc"
    assert n1.env.get("CISCO_IOL_LICENSED") == "true"


def test_cascading_folder_deletion(isolated_db):
    """Verifies that delete_contents=True deletes a folder AND all nested labs."""
    # Create folder and save a topology inside it
    folder = isolated_db.get_or_create_folder_by_path("/Testing/Subcategory")
    topo = AzamTopology(name="Nested-Lab")
    topo.folder_path = "/Testing/Subcategory"
    isolated_db.save_topology(topo)

    assert len(isolated_db.list_topologies()) == 1

    # Cascading delete of parent folder /Testing
    parent_folder = isolated_db.get_or_create_folder_by_path("/Testing")
    success = isolated_db.delete_folder(parent_folder["id"], delete_topologies=True)

    assert success is True
    # Contained lab must be deleted
    assert len(isolated_db.list_topologies()) == 0


def test_lab_duplication_clone(isolated_db):
    """Verifies lab cloning generates an independent copy with a new ID."""
    original = AzamTopology(name="Original-Lab")
    original.add_node(AzamNode(name="R1", driver=DriverType.DOCKER))
    isolated_db.save_topology(original)

    cloned = isolated_db.duplicate_topology(original.id, new_name="Cloned-Lab")

    assert cloned is not None
    assert cloned["id"] != original.id
    assert cloned["name"] == "Cloned-Lab"
    assert len(isolated_db.list_topologies()) == 2


def test_api_batch_import_and_folder_export(isolated_db, monkeypatch):
    """Verifies HTTP API endpoints for batch import, folder export, and clone."""
    client = TestClient(app)

    # 1. Test POST /api/v1/convert/upload-archive
    zip_bytes = create_multi_lab_zip_bytes()
    resp = client.post(
        "/api/v1/convert/upload-archive",
        files={"file": ("test_labs.zip", zip_bytes, "application/zip")},
        data={"target_folder": "/TestAPI"}
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["imported_count"] == 2

    # 2. Test GET /api/v1/folders
    folders_resp = client.get("/api/v1/folders")
    assert folders_resp.status_code == 200
    folders_tree = folders_resp.json()
    assert len(folders_tree) > 0

    # 3. Test GET /api/v1/folders/{id}/export
    target_folder = [f for f in folders_tree if f["path"] == "/TestAPI/Enterprise/Branch"][0]
    export_resp = client.get(f"/api/v1/folders/{target_folder['id']}/export")
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/zip"

    # 4. Test POST /api/v1/labs/{id}/clone
    lab_id = res_data["imported_labs"][0]["id"]
    clone_resp = client.post(f"/api/v1/labs/{lab_id}/clone", json={"new_name": "API-Cloned-Lab"})
    assert clone_resp.status_code == 200
    assert clone_resp.json()["name"] == "API-Cloned-Lab"

    # 5. Test DELETE /api/v1/folders/{id}?delete_contents=true
    del_resp = client.delete(f"/api/v1/folders/{target_folder['id']}?delete_contents=true")
    assert del_resp.status_code == 200
    assert del_resp.json()["cascaded"] is True
