"""
Unit Tests for AzamLabs Universal Device Catalog Service and Endpoints
"""

import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from azamlabs.main import app
from azamlabs.core.catalog import DeviceCatalogService, HardwareApplianceTemplate, ApplianceTemplate

client = TestClient(app)


def test_catalog_service_defaults():
    """Verify default hardware templates are generated with rich metadata."""
    service = DeviceCatalogService()
    catalog = service.get_catalog()
    assert len(catalog) >= 10

    # Verify key templates exist
    template_ids = [item["id"] for item in catalog]
    assert "cisco_iol_l3" in template_ids
    assert "cisco_iol_l2" in template_ids
    assert "arista_veos" in template_ids
    assert "endpoint_linux" in template_ids
    assert "endpoint_vpcs" in template_ids

    # Check template structure
    iol_l3 = next(item for item in catalog if item["id"] == "cisco_iol_l3")
    assert iol_l3["vendor"] == "Cisco"
    assert iol_l3["category"] == "Routers"
    assert iol_l3["driver"] == "iol"
    assert iol_l3["default_ram_mb"] >= 512
    assert iol_l3["default_cpu"] >= 1
    assert len(iol_l3["default_interfaces"]) >= 4


def test_catalog_service_scan_directory():
    """Verify that catalog detects installed images in mock image directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        iol_bin = tmp_path / "iol" / "bin"
        iol_bin.mkdir(parents=True)
        qemu_dir = tmp_path / "qemu"
        qemu_dir.mkdir(parents=True)

        # Create dummy IOL bin and QEMU image
        dummy_iol = iol_bin / "L3-ADVENTERPRISE9-M-15.5-2T.bin"
        dummy_iol.touch()

        dummy_qemu = qemu_dir / "veos-4.28.0F"
        dummy_qemu.mkdir()
        (dummy_qemu / "hda.qcow2").touch()

        service = DeviceCatalogService()
        catalog = service.get_catalog(extra_iol_dirs=[iol_bin], extra_qemu_dirs=[qemu_dir])

        iol_l3 = next(item for item in catalog if item["id"] == "cisco_iol_l3")
        assert iol_l3["is_installed"] is True
        assert "L3-ADVENTERPRISE9-M-15.5-2T.bin" in iol_l3["installed_images"]

        veos = next(item for item in catalog if item["id"] == "arista_veos")
        assert veos["is_installed"] is True
        assert "veos-4.28.0F" in veos["installed_images"]


def test_api_devices_catalog():
    """Verify GET /api/v1/devices/catalog returns list of catalog items with vendor categories."""
    response = client.get("/api/v1/devices/catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 10
    vendors = {item["vendor"] for item in data}
    categories = {item["category"] for item in data}
    assert "Cisco" in vendors
    assert "Routers" in categories
