"""
Tests for EveConverter hardening:
- Duplicate node name resolution with automatic link endpoint remapping
- Zero CPU and RAM clamping (PNETLab ram="0", EVE cpu="0")
- Visual text objects (<textobjects>) extraction into AzamAnnotation
"""

import pytest
from azamlabs.converters.eve import EveConverter
from azamlabs.core.schema import AzamTopology, DriverType


SAMPLE_EVE_XML_WITH_COLLISIONS_AND_ZEROS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<lab name="EVE-Hardening-Test" version="1" scripttimeout="300" lock="0">
  <topology>
    <nodes>
      <node id="1" name="Router-A" type="qemu" template="c8000v" image="c8000v-17.09.03a"
            cpu="0" ram="0" ethernet="4" serial="0" left="100" top="150" delay="0"/>
      <!-- Case collision with Router-A -->
      <node id="2" name="ROUTER-A" type="qemu" template="c8000v" image="c8000v-17.09.03a"
            cpu="2" ram="1024" ethernet="4" serial="0" left="300" top="150" delay="0"/>
      <!-- Exact duplicate name with ROUTER-A -->
      <node id="3" name="Router-A" type="iol" template="iol" image="cisco-iol.bin"
            cpu="1" ram="256" ethernet="4" serial="0" left="500" top="150" delay="0"/>
    </nodes>
    <networks>
      <network id="1" type="bridge" name="Net-R1-R2" left="200" top="150" visibility="1"/>
    </networks>
  </topology>
  <objects>
    <textobjects>
      <textobject id="1" name="Core-Zone" type="box" left="80" top="100" width="460" height="200"
                  color="#00f2fe" bg="rgba(0,242,254,0.1)">Core Network Segment</textobject>
    </textobjects>
  </objects>
</lab>
"""


def test_eve_name_collision_and_clamping():
    """Verifies that duplicate and case-colliding node names are deduplicated and resources clamped."""
    topo = EveConverter.eve_to_azam(SAMPLE_EVE_XML_WITH_COLLISIONS_AND_ZEROS)

    assert isinstance(topo, AzamTopology)
    assert topo.name == "EVE-Hardening-Test"
    assert len(topo.nodes) == 3

    node_names = [n.name for n in topo.nodes]
    # Names must be unique
    assert len(set(node_names)) == 3
    # Case-insensitive names must also be unique
    assert len(set(n.lower() for n in node_names)) == 3

    # Clamping checks: cpu="0" -> 1, ram="0" -> 128
    node1 = topo.nodes[0]
    assert node1.cpu >= 1
    assert node1.ram_mb >= 128


def test_eve_annotations_extraction():
    """Verifies that <textobjects> are extracted into AzamAnnotation visual zones."""
    topo = EveConverter.eve_to_azam(SAMPLE_EVE_XML_WITH_COLLISIONS_AND_ZEROS)

    assert len(topo.annotations) == 1
    ann = topo.annotations[0]
    assert ann.label == "Core Network Segment"
    assert ann.pos_x == 80.0
    assert ann.pos_y == 100.0
    assert ann.width == 460.0
    assert ann.height == 200.0
    assert ann.color == "#00f2fe"
