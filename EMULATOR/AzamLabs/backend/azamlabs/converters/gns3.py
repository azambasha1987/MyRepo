"""
AzamLabs GNS3 (.gns3) Bidirectional JSON Converter
Provides seamless bidirectional translation between GNS3 project topologies and AzamTopology.
"""

import io
import json
import uuid
import zipfile
import re
from typing import Dict, Any, Union

from azamlabs.core.schema import (
    AzamTopology,
    AzamNode,
    AzamLink,
    AzamAnnotation,
    DeviceType,
    DriverType,
)


class Gns3Converter:
    """Handles parsing and generating GNS3 project JSON (.gns3) and portable archives (.gns3project)."""

    TYPE_DRIVER_MAP = {
        "qemu": DriverType.QEMU,
        "iou": DriverType.IOL,
        "docker": DriverType.DOCKER,
        "vpcs": DriverType.VPCS,
        "dynamips": DriverType.QEMU,
        "ethernet_switch": DriverType.DOCKER,
        "ethernet_hub": DriverType.DOCKER,
        "cloud": DriverType.PHYSICAL,
        "nat": DriverType.DOCKER,
    }

    @classmethod
    def gns3project_to_azam(cls, content: Union[bytes, str]) -> AzamTopology:
        """Unpacks a portable .gns3project ZIP archive and parses the enclosed topology and configs."""
        if isinstance(content, str):
            content_bytes = content.encode("latin1")
        else:
            content_bytes = content

        with zipfile.ZipFile(io.BytesIO(content_bytes), "r") as zp:
            gns3_files = [x for x in zp.namelist() if x.endswith(".gns3")]
            if not gns3_files:
                raise ValueError("No .gns3 JSON file found inside .gns3project archive.")

            raw_json = zp.read(gns3_files[0]).decode("utf-8", errors="ignore")
            data = json.loads(raw_json)

            # Extract any startup configs from project-files/
            configs_by_node_id = {}
            node_ids = [n.get("node_id") for n in data.get("topology", {}).get("nodes", []) if n.get("node_id")]
            for name in zp.namelist():
                if "startup.vpc" in name or "startup-config" in name or name.endswith(".cfg"):
                    for nid in node_ids:
                        if nid in name:
                            configs_by_node_id[nid] = zp.read(name).decode("utf-8", errors="ignore")

            topo = cls.gns3_to_azam(data)

            # Attach Day-0 configs
            for node in topo.nodes:
                nid = node.metadata.get("gns3_id")
                if nid and nid in configs_by_node_id:
                    node.startup_config = configs_by_node_id[nid]
                    node.metadata["startup_config"] = configs_by_node_id[nid]

            return topo

    @classmethod
    def gns3_to_azam(cls, content: Union[str, bytes, Dict[str, Any]]) -> AzamTopology:
        """Converts a GNS3 JSON string, dictionary, or .gns3project archive into an AzamTopology."""
        if isinstance(content, (bytes, bytearray)):
            # Check for ZIP archive magic bytes (PK\x03\x04)
            if len(content) > 4 and content[:4] == b"PK\x03\x04":
                return cls.gns3project_to_azam(content)
            content_str = content.decode("utf-8", errors="ignore")
            data = json.loads(content_str)
        elif isinstance(content, str):
            data = json.loads(content)
        else:
            data = content

        if not isinstance(data, dict):
            raise ValueError("Invalid GNS3 specification: root must be a JSON dictionary.")

        project_name = data.get("name", "gns3-imported-lab")
        topo_def = data.get("topology", {})
        gns3_nodes = topo_def.get("nodes", [])
        gns3_links = topo_def.get("links", [])
        gns3_drawings = topo_def.get("drawings", [])

        azam_topo = AzamTopology(
            name=project_name,
            description=f"Imported from GNS3 project '{project_name}'",
            author="GNS3 Importer",
        )

        node_id_to_node: Dict[str, AzamNode] = {}
        seen_names_lower: Dict[str, int] = {}

        # 1. Parse Nodes
        for n_def in gns3_nodes:
            g_nid = n_def.get("node_id", str(uuid.uuid4()))
            raw_name = n_def.get("name", f"Node-{g_nid[:6]}").strip()
            if not raw_name:
                raw_name = f"Node-{g_nid[:6]}"

            name_lower = raw_name.lower()
            if name_lower in seen_names_lower:
                seen_names_lower[name_lower] += 1
                name = f"{raw_name}-{seen_names_lower[name_lower]}"
            else:
                seen_names_lower[name_lower] = 1
                name = raw_name
            node_type = n_def.get("node_type", "qemu").lower()
            props = n_def.get("properties", {})

            driver_type = cls.TYPE_DRIVER_MAP.get(node_type, DriverType.QEMU)

            # Determine DeviceType
            if node_type in ("ethernet_switch", "ethernet_hub"):
                dev_type = DeviceType.SWITCH
            elif node_type == "vpcs":
                dev_type = DeviceType.HOST
            elif node_type in ("cloud", "nat"):
                dev_type = DeviceType.CLOUD
            else:
                dev_type = DeviceType.ROUTER

            # Extract image
            image = (
                props.get("hda_disk_image")
                or props.get("path")
                or props.get("image")
                or props.get("qemu_path", "c8000v.qcow2")
            )

            # Coordinates
            pos_x = float(n_def.get("x", 100))
            pos_y = float(n_def.get("y", 100))
            # Shift positive if negative
            if pos_x < 0:
                pos_x += 600
            if pos_y < 0:
                pos_y += 600

            ram = int(props.get("ram", 1024))
            cpus = int(props.get("cpus", 1))

            azam_node = AzamNode(
                name=name,
                device_type=dev_type,
                driver=driver_type,
                image=image,
                cpu=cpus,
                ram_mb=ram,
                pos_x=pos_x,
                pos_y=pos_y,
                metadata={"gns3_id": g_nid, "gns3_type": node_type, "properties": props},
            )

            azam_topo.add_node(azam_node)
            node_id_to_node[g_nid] = azam_node

        # 2. Parse Links
        for l_def in gns3_links:
            end_nodes = l_def.get("nodes", [])
            if len(end_nodes) < 2:
                continue

            ep1, ep2 = end_nodes[0], end_nodes[1]
            n1 = node_id_to_node.get(ep1.get("node_id"))
            n2 = node_id_to_node.get(ep2.get("node_id"))

            if not n1 or not n2:
                continue

            # Resolve interface names
            def resolve_iface_name(ep):
                label = ep.get("label", {}).get("text")
                if label:
                    return label
                adapter = ep.get("adapter_number", 0)
                port = ep.get("port_number", 0)
                return f"eth{adapter}/{port}"

            iface1_name = resolve_iface_name(ep1)
            iface2_name = resolve_iface_name(ep2)

            n1.add_interface(iface1_name)
            n2.add_interface(iface2_name)

            azam_link = AzamLink(
                source_node=n1.name,
                source_interface=iface1_name,
                target_node=n2.name,
                target_interface=iface2_name,
                metadata={"gns3_link_id": l_def.get("link_id")},
            )
            azam_topo.links.append(azam_link)

        # 3. Parse Drawings & Architectural Annotations
        for d_def in gns3_drawings:
            d_id = d_def.get("drawing_id", str(uuid.uuid4())[:8])
            d_x = float(d_def.get("x", 0))
            d_y = float(d_def.get("y", 0))
            if d_x < 0:
                d_x += 600
            if d_y < 0:
                d_y += 600

            svg = d_def.get("svg", "")
            is_zone = "<rect" in svg or "<polygon" in svg or "<path" in svg
            label = ""
            if "<text" in svg:
                m = re.search(r">([^<]+)<", svg)
                if m:
                    label = m.group(1).strip()

            w_match = re.search(r'width="([0-9.]+)"', svg)
            h_match = re.search(r'height="([0-9.]+)"', svg)
            stroke_match = re.search(r'stroke="([^"]+)"', svg)

            width = float(w_match.group(1)) if w_match else 220.0
            height = float(h_match.group(1)) if h_match else 130.0
            color = stroke_match.group(1) if stroke_match else "#00f2fe"

            azam_topo.annotations.append(AzamAnnotation(
                id=d_id,
                type="zone" if is_zone else "text",
                label=label or "Zone",
                pos_x=d_x,
                pos_y=d_y,
                width=width,
                height=height,
                color=color,
            ))

        return azam_topo

    @classmethod
    def azam_to_gns3(cls, topology: AzamTopology) -> str:
        """Exports an AzamTopology into a valid GNS3 project JSON (.gns3) string."""
        project_id = str(uuid.uuid4())
        gns3_dict: Dict[str, Any] = {
            "name": topology.name,
            "project_id": project_id,
            "type": "topology",
            "version": "2.2.46",
            "topology": {
                "nodes": [],
                "links": [],
            }
        }

        node_id_map: Dict[str, str] = {}

        for idx, node in enumerate(topology.nodes):
            g_nid = node.metadata.get("gns3_id", str(uuid.uuid4()))
            node_id_map[node.name] = g_nid

            g_type = "qemu"
            if node.driver == DriverType.IOL:
                g_type = "iou"
            elif node.driver == DriverType.VPCS:
                g_type = "vpcs"
            elif node.driver == DriverType.DOCKER:
                g_type = "docker"

            node_entry: Dict[str, Any] = {
                "name": node.name,
                "node_id": g_nid,
                "node_type": g_type,
                "x": int(node.pos_x),
                "y": int(node.pos_y),
                "properties": {
                    "hda_disk_image": node.image,
                    "ram": node.ram_mb,
                    "cpus": node.cpu,
                }
            }
            gns3_dict["topology"]["nodes"].append(node_entry)

        for link in topology.links:
            n1_id = node_id_map.get(link.source_node)
            n2_id = node_id_map.get(link.target_node)

            if n1_id and n2_id:
                link_entry: Dict[str, Any] = {
                    "link_id": str(uuid.uuid4()),
                    "nodes": [
                        {
                            "node_id": n1_id,
                            "adapter_number": 0,
                            "port_number": 0,
                            "label": {"text": link.source_interface},
                        },
                        {
                            "node_id": n2_id,
                            "adapter_number": 0,
                            "port_number": 0,
                            "label": {"text": link.target_interface},
                        }
                    ]
                }
                gns3_dict["topology"]["links"].append(link_entry)

        return json.dumps(gns3_dict, indent=2)
