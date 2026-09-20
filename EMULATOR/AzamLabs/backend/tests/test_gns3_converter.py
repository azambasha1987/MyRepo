"""
Tests for Gns3Converter:
- Portable .gns3project ZIP archive unpacking
- Startup config extraction (startup.vpc, .cfg)
- Drawing extraction into AzamAnnotation
- Bidirectional export
"""

import io
import json
import zipfile
import pytest

from azamlabs.converters.gns3 import Gns3Converter
from azamlabs.converters.universal import UniversalConverter
from azamlabs.core.schema import AzamTopology, DriverType


def create_mock_gns3project_bytes() -> bytes:
    """Constructs an in-memory .gns3project ZIP archive with project.gns3 and Day-0 startup configs."""
    buf = io.BytesIO()

    project_data = {
        "name": "Portable-Campus-Core",
        "project_id": "11111111-2222-3333-4444-555555555555",
        "topology": {
            "nodes": [
                {
                    "node_id": "aaaa-1111",
                    "name": "Border-GW",
                    "node_type": "qemu",
                    "x": 120,
                    "y": 180,
                    "properties": {"cpus": 2, "ram": 2048, "hda_disk_image": "c8000v.qcow2"}
                },
                {
                    "node_id": "bbbb-2222",
                    "name": "BORDER-GW",  # Case collision
                    "node_type": "vpcs",
                    "x": 300,
                    "y": 180,
                    "properties": {}
                }
            ],
            "links": [
                {
                    "link_id": "link-1",
                    "nodes": [
                        {"node_id": "aaaa-1111", "adapter_number": 0, "port_number": 0},
                        {"node_id": "bbbb-2222", "adapter_number": 0, "port_number": 0}
                    ]
                }
            ],
            "drawings": [
                {
                    "drawing_id": "draw-1",
                    "x": 100,
                    "y": 100,
                    "svg": '<rect width="300" height="200" fill="#001a2c" stroke="#00f2fe" stroke-width="2"/>'
                }
            ]
        }
    }

    startup_vpc_content = """# VPCS Startup Script
set pcname VPC-Client
ip 192.168.1.10/24 192.168.1.1
"""

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zp:
        zp.writestr("project.gns3", json.dumps(project_data))
        zp.writestr("project-files/vpcs/bbbb-2222/startup.vpc", startup_vpc_content)

    buf.seek(0)
    return buf.getvalue()


def test_gns3project_unpacking_and_config_extraction():
    """Verifies that .gns3project ZIP archives unpack, extract configs, and resolve name collisions."""
    mock_zip = create_mock_gns3project_bytes()
    topo = Gns3Converter.gns3project_to_azam(mock_zip)

    assert isinstance(topo, AzamTopology)
    assert topo.name == "Portable-Campus-Core"
    assert len(topo.nodes) == 2

    # Verify case collision resolution
    names = [n.name.lower() for n in topo.nodes]
    assert len(set(names)) == 2

    # Verify Day-0 startup config extraction for VPCS node
    vpcs_node = [n for n in topo.nodes if n.driver == DriverType.VPCS][0]
    assert vpcs_node.startup_config is not None
    assert "192.168.1.10/24" in vpcs_node.startup_config

    # Verify drawing extraction into AzamAnnotation
    assert len(topo.annotations) == 1
    assert topo.annotations[0].pos_x == 100.0
    assert topo.annotations[0].width == 300.0
    assert topo.annotations[0].height == 200.0


def test_universal_converter_gns3project_auto_detection():
    """Verifies UniversalConverter auto-detects and imports .gns3project files seamlessly."""
    mock_zip = create_mock_gns3project_bytes()
    topo = UniversalConverter.import_lab(mock_zip, filename="campus.gns3project")

    assert isinstance(topo, AzamTopology)
    assert topo.name == "Portable-Campus-Core"
    assert len(topo.nodes) == 2
