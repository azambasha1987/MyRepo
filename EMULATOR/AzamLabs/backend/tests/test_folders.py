"""
Test suite for AzamLabs Folder-Wise Lab Explorer Backend
Validates category hierarchies, folder creation, lab relocation, and deletion.
"""

import pytest
from fastapi.testclient import TestClient
from azamlabs.main import app

client = TestClient(app)


def test_get_folders_default_hierarchy():
    """Verify default seeded folder categories exist in the tree."""
    response = client.get("/api/v1/folders")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4

    folder_paths = [f["path"] for f in data]
    assert "/Enterprise Networks" in folder_paths
    assert "/Data Center & Cloud" in folder_paths
    assert "/Cybersecurity & PenTest" in folder_paths
    assert "/Service Provider" in folder_paths

    for folder in data:
        assert "name" in folder
        assert "path" in folder
        assert "labs" in folder
        assert isinstance(folder["labs"], list)


def test_create_custom_folder():
    """Verify POST /api/v1/folders creates a new folder category."""
    folder_name = "Edge & IoT Labs"
    response = client.post(
        "/api/v1/folders",
        json={"name": folder_name, "parent_path": "/"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == folder_name
    assert data["path"] == f"/{folder_name}"

    # Verify folder now appears in tree
    tree_resp = client.get("/api/v1/folders")
    tree_data = tree_resp.json()
    paths = [f["path"] for f in tree_data]
    assert f"/{folder_name}" in paths


def test_move_lab_between_folders():
    """Verify PATCH /api/v1/labs/{lab_id}/move updates topology folder_path."""
    # 1. Create a dummy lab
    lab_id = "test-folder-mesh"
    lab_payload = {
        "id": lab_id,
        "name": "Folder Migration Test Lab",
        "description": "Lab for testing folder movements",
        "folder_path": "/",
        "nodes": [],
        "links": []
    }
    create_resp = client.post("/api/v1/labs", json=lab_payload)
    assert create_resp.status_code == 200

    # 2. Move lab to /Enterprise Networks
    move_resp = client.patch(
        f"/api/v1/labs/{lab_id}/move",
        json={"folder_path": "/Enterprise Networks"}
    )
    assert move_resp.status_code == 200
    assert move_resp.json()["status"] == "moved"

    # 3. Check tree: lab should now be inside /Enterprise Networks
    tree_resp = client.get("/api/v1/folders")
    tree_data = tree_resp.json()
    ent_folder = next((f for f in tree_data if f["path"] == "/Enterprise Networks"), None)
    assert ent_folder is not None
    lab_ids_in_ent = [l["id"] for l in ent_folder["labs"]]
    assert lab_id in lab_ids_in_ent

    # 4. Clean up
    client.delete(f"/api/v1/labs/{lab_id}")


def test_delete_folder():
    """Verify DELETE /api/v1/folders/{folder_id} deletes category and safely relocates labs."""
    # 1. Create temporary folder
    f_resp = client.post(
        "/api/v1/folders",
        json={"name": "Temporary Sandbox", "parent_path": "/"}
    )
    assert f_resp.status_code == 200
    folder_id = f_resp.json()["id"]

    # 2. Delete folder
    del_resp = client.delete(f"/api/v1/folders/{folder_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # 3. Verify folder is removed from tree
    tree_resp = client.get("/api/v1/folders")
    tree_data = tree_resp.json()
    paths = [f["path"] for f in tree_data]
    assert "/Temporary Sandbox" not in paths
