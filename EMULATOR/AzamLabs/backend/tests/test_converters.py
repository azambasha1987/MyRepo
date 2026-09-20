"""
Comprehensive Unit Tests for AzamLabs Universal Multi-Platform Converters
Verifies Containerlab, Cisco CML 2.x, EVE-NG / PNETLab, GNS3, P2V, and AZAML Bundle conversions.
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport

from azamlabs.core.schema import AzamTopology, AzamNode, AzamLink, DeviceType, DriverType, ImpairmentProfile
from azamlabs.converters.containerlab import ContainerlabConverter
from azamlabs.converters.cml import CmlConverter
from azamlabs.converters.eve import EveConverter
from azamlabs.converters.gns3 import Gns3Converter
from azamlabs.converters.p2v import P2VConverter
from azamlabs.converters.bundle import LabBundleManager
from azamlabs.converters.universal import UniversalConverter
from azamlabs.main import app


# ==========================================
# 1. Containerlab (.clab.yml) Tests
# ==========================================

SAMPLE_CLAB_YAML = """
name: datacenter-fabric
mgmt:
  network: custom-mgmt
  ipv4-subnet: 172.20.20.0/24
topology:
  kinds:
    srl:
      image: ghcr.io/nokia/srlinux:24.3.1
    ceos:
      image: ceos:4.30.0F
  nodes:
    spine1:
      kind: srl
      mgmt-ipv4: 172.20.20.11
    leaf1:
      kind: ceos
      mgmt-ipv4: 172.20.20.12
  links:
    - endpoints: ["spine1:e1-1", "leaf1:eth1"]
"""

def test_containerlab_import_and_export():
    topo = ContainerlabConverter.clab_to_azam(SAMPLE_CLAB_YAML)

    assert topo.name == "datacenter-fabric"
    assert len(topo.nodes) == 2
    assert len(topo.links) == 1
    assert len(topo.networks) == 1
    assert topo.networks[0].subnet == "172.20.20.0/24"

    s1 = topo.get_node("spine1")
    assert s1 is not None
    assert s1.driver == DriverType.DOCKER
    assert s1.image == "ghcr.io/nokia/srlinux:24.3.1"
    assert s1.get_interface("eth0").ip_address == "172.20.20.11"

    link = topo.links[0]
    assert link.source_node == "spine1"
    assert link.source_interface == "e1-1"
    assert link.target_node == "leaf1"
    assert link.target_interface == "eth1"

    # Export back to Containerlab
    clab_exported = ContainerlabConverter.azam_to_clab(topo)
    assert "datacenter-fabric" in clab_exported
    assert "spine1:e1-1" in clab_exported
    assert "leaf1:eth1" in clab_exported


# ==========================================
# 2. Cisco Modeling Labs (CML 2.x) Tests
# ==========================================

SAMPLE_CML_YAML = """
lab:
  title: CCNA Core Lab
  description: Multi-vendor routing lab
  notes: Cisco CML 2.x Test
nodes:
  - id: n0
    label: Core-R1
    node_definition: iosv
    x: 100
    y: 150
    cpus: 1
    ram: 1024
    configuration: |
      hostname Core-R1
      !
    interfaces:
      - id: i0
        label: GigabitEthernet0/0
  - id: n1
    label: Edge-SW1
    node_definition: iosvl2
    x: 350
    y: 150
    interfaces:
      - id: i0
        label: GigabitEthernet0/1
links:
  - id: l0
    n1: n0
    i1: i0
    n2: n1
    i2: i0
    conditioning:
      latency: 45.5
      jitter: 5.0
      loss: 1.5
      bandwidth: 10000
"""

def test_cml_import_and_export():
    topo = CmlConverter.cml_to_azam(SAMPLE_CML_YAML)

    assert topo.name == "CCNA Core Lab"
    assert len(topo.nodes) == 2
    assert len(topo.links) == 1

    r1 = topo.get_node("Core-R1")
    assert r1 is not None
    assert r1.driver == DriverType.QEMU
    assert "hostname Core-R1" in r1.startup_config

    sw1 = topo.get_node("Edge-SW1")
    assert sw1 is not None
    assert sw1.device_type == DeviceType.SWITCH

    # Check Impairment Conditioning
    link = topo.links[0]
    assert link.impairment is not None
    assert link.impairment.delay_ms == 45.5
    assert link.impairment.loss_percent == 1.5
    assert link.impairment.rate_limit_kbps == 10000

    # Export back to CML
    cml_exported = CmlConverter.azam_to_cml(topo)
    assert "CCNA Core Lab" in cml_exported
    assert "iosv" in cml_exported
    assert "conditioning:" in cml_exported


# ==========================================
# 3. EVE-NG / PNETLab (.unl) Tests
# ==========================================

SAMPLE_EVE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<lab name="EVE_BGP_Lab" version="1" scripttimeout="300">
  <description>EVE-NG Exported Lab</description>
  <topology>
    <nodes>
      <node id="1" name="R1-IOL" type="iol" template="iol" image="cisco-iol-l3.bin" ram="1024" cpu="1" left="150" top="200">
        <interface id="0" name="Ethernet0/0" type="ethernet" network_id="1"/>
      </node>
      <node id="2" name="R2-QEMU" type="qemu" template="c8000v" image="c8000v-17.09.03" ram="4096" cpu="2" left="450" top="200">
        <interface id="0" name="GigabitEthernet1" type="ethernet" network_id="1"/>
      </node>
    </nodes>
    <networks>
      <network id="1" type="bridge" name="Net-R1_if0" left="300" top="200"/>
    </networks>
  </topology>
</lab>
"""

def test_eve_import_and_export():
    topo = EveConverter.eve_to_azam(SAMPLE_EVE_XML)

    assert topo.name == "EVE_BGP_Lab"
    assert len(topo.nodes) == 2
    assert len(topo.links) == 1

    r1 = topo.get_node("R1-IOL")
    assert r1 is not None
    assert r1.driver == DriverType.IOL
    assert r1.image == "cisco-iol-l3.bin"

    r2 = topo.get_node("R2-QEMU")
    assert r2 is not None
    assert r2.driver == DriverType.QEMU
    assert r2.ram_mb == 4096

    link = topo.links[0]
    assert link.source_node == "R1-IOL"
    assert link.source_interface == "Ethernet0/0"
    assert link.target_node == "R2-QEMU"
    assert link.target_interface == "GigabitEthernet1"

    # Export back to EVE XML
    eve_exported = EveConverter.azam_to_eve(topo)
    assert "<lab name=" in eve_exported
    assert "R1-IOL" in eve_exported
    assert "network_id=" in eve_exported


# ==========================================
# 4. GNS3 (.gns3) Tests
# ==========================================

SAMPLE_GNS3_JSON = """{
  "name": "GNS3 SD-WAN",
  "project_id": "993a4bc1-1111-2222-3333-444455556666",
  "topology": {
    "nodes": [
      {
        "name": "Edge1",
        "node_id": "aaaa-1111",
        "node_type": "qemu",
        "x": 100,
        "y": 120,
        "properties": {
          "hda_disk_image": "c8000v.qcow2",
          "ram": 2048,
          "cpus": 2
        }
      },
      {
        "name": "Host1",
        "node_id": "bbbb-2222",
        "node_type": "vpcs",
        "x": 100,
        "y": 300,
        "properties": {}
      }
    ],
    "links": [
      {
        "link_id": "link-101",
        "nodes": [
          {"node_id": "aaaa-1111", "label": {"text": "GigabitEthernet1"}},
          {"node_id": "bbbb-2222", "label": {"text": "eth0"}}
        ]
      }
    ]
  }
}"""

def test_gns3_import_and_export():
    topo = Gns3Converter.gns3_to_azam(SAMPLE_GNS3_JSON)

    assert topo.name == "GNS3 SD-WAN"
    assert len(topo.nodes) == 2
    assert len(topo.links) == 1

    edge = topo.get_node("Edge1")
    assert edge is not None
    assert edge.driver == DriverType.QEMU

    host = topo.get_node("Host1")
    assert host is not None
    assert host.driver == DriverType.VPCS

    link = topo.links[0]
    assert link.source_node == "Edge1"
    assert link.source_interface == "GigabitEthernet1"
    assert link.target_node == "Host1"
    assert link.target_interface == "eth0"

    # Export back to GNS3
    gns3_exported = Gns3Converter.azam_to_gns3(topo)
    assert "GNS3 SD-WAN" in gns3_exported
    assert "topology" in gns3_exported


# ==========================================
# 5. Physical-to-Virtual (P2V) Config Importer
# ==========================================

SAMPLE_P2V_CONFIGS = """
! --- Device: Spine-01 ---
hostname Spine-01
!
interface GigabitEthernet0/1
 description Link to Leaf-01
 ip address 10.100.1.1 255.255.255.252
 no shutdown
!
interface Loopback0
 ip address 1.1.1.1 255.255.255.255
!
! --- Device: Leaf-01 ---
hostname Leaf-01
!
interface GigabitEthernet0/1
 description Link to Spine-01
 ip address 10.100.1.2 255.255.255.252
 no shutdown
!
interface Loopback0
 ip address 2.2.2.2 255.255.255.255
!
"""

def test_p2v_config_importer_and_auto_link_stitching():
    topo = P2VConverter.p2v_to_azam(SAMPLE_P2V_CONFIGS)

    assert len(topo.nodes) == 2
    spine = topo.get_node("Spine-01")
    leaf = topo.get_node("Leaf-01")

    assert spine is not None
    assert leaf is not None

    assert spine.get_interface("GigabitEthernet0/1").ip_address == "10.100.1.1/30"
    assert leaf.get_interface("GigabitEthernet0/1").ip_address == "10.100.1.2/30"

    # Verify that the link was automatically stitched based on 10.100.1.0/30 subnet!
    assert len(topo.links) == 1
    link = topo.links[0]
    assert (link.source_node == "Spine-01" and link.target_node == "Leaf-01") or \
           (link.source_node == "Leaf-01" and link.target_node == "Spine-01")
    assert link.source_interface == "GigabitEthernet0/1"
    assert link.target_interface == "GigabitEthernet0/1"


# ==========================================
# 6. Universal .azaml Bundle Tests
# ==========================================

def test_azaml_bundle_packaging():
    topo = AzamTopology(name="Production Security Grid", description="SecOps Lab")
    n1 = AzamNode(name="Firewall1", device_type=DeviceType.FIREWALL, driver=DriverType.QEMU, image="asav:latest")
    n1.startup_config = "hostname Firewall1\ninterface mgmt\n"
    topo.add_node(n1)

    bundle_bytes = LabBundleManager.export_azaml_bytes(topo)
    assert len(bundle_bytes) > 50

    # Unpack
    restored_topo = LabBundleManager.import_azaml_archive(bundle_bytes)
    assert restored_topo.name == "Production Security Grid"
    assert len(restored_topo.nodes) == 1
    restored_fw = restored_topo.get_node("Firewall1")
    assert restored_fw is not None
    assert restored_fw.startup_config == "hostname Firewall1\ninterface mgmt\n"


# ==========================================
# 7. Universal Auto-Detector & Master Importer
# ==========================================

def test_universal_converter_auto_detect():
    assert UniversalConverter.auto_detect_format(SAMPLE_CLAB_YAML) == "clab"
    assert UniversalConverter.auto_detect_format(SAMPLE_CML_YAML) == "cml"
    assert UniversalConverter.auto_detect_format(SAMPLE_EVE_XML) == "eve"
    assert UniversalConverter.auto_detect_format(SAMPLE_GNS3_JSON) == "gns3"
    assert UniversalConverter.auto_detect_format(SAMPLE_P2V_CONFIGS) == "p2v"

    # Direct Universal Import
    imported_clab = UniversalConverter.import_lab(SAMPLE_CLAB_YAML)
    assert imported_clab.name == "datacenter-fabric"

    imported_eve = UniversalConverter.import_lab(SAMPLE_EVE_XML)
    assert imported_eve.name == "EVE_BGP_Lab"

    # Multi-Format Export
    clab_out = UniversalConverter.export_lab(imported_clab, "clab")
    assert isinstance(clab_out, str)
    assert "datacenter-fabric" in clab_out

    cml_out = UniversalConverter.export_lab(imported_clab, "cml")
    assert isinstance(cml_out, str)
    assert "datacenter-fabric" in cml_out

    azaml_out = UniversalConverter.export_lab(imported_clab, "azaml")
    assert isinstance(azaml_out, bytes)


# ==========================================
# 8. FastAPI Conversion REST Endpoints
# ==========================================

@pytest.mark.asyncio
async def test_fastapi_conversion_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Import Containerlab via JSON payload
        import_resp = await client.post(
            "/api/v1/convert/import",
            json={
                "content": SAMPLE_CLAB_YAML,
                "filename": "datacenter.clab.yml"
            }
        )
        assert import_resp.status_code == 200
        imported_topo = import_resp.json()
        assert imported_topo["name"] == "datacenter-fabric"
        lab_id = imported_topo["id"]

        # Export to CML format
        export_cml_resp = await client.get(f"/api/v1/convert/export/{lab_id}/cml")
        assert export_cml_resp.status_code == 200
        assert "datacenter-fabric" in export_cml_resp.text

        # Export to .azaml archive
        export_azaml_resp = await client.get(f"/api/v1/convert/export/{lab_id}/azaml")
        assert export_azaml_resp.status_code == 200
        assert len(export_azaml_resp.content) > 50
