"""
AzamLabs GNS3 (.gns3) Bidirectional JSON Converter
Provides seamless bidirectional translation between GNS3 project topologies and AzamTopology.
"""

import json
import uuid
from typing import Dict, Any, Union

from azamlabs.core.schema import (
    AzamTopology,
    AzamNode,
    AzamLink,
    DeviceType,
    DriverType,
)


class Gns3Converter:
    """Handles parsing and generating GNS3 project JSON (.gns3) topologies."""

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
    def gns3_to_azam(cls, content: Union[str, Dict[str, Any]]) -> AzamTopology:
        """Converts a GNS3 JSON string or dictionary into an AzamTopology."""
        if isinstance(content, str):
            data = json.loads(content)
        else:
            data = content

        if not isinstance(data, dict):
            raise ValueError("Invalid GNS3 specification: root must be a JSON dictionary.")

        project_name = data.get("name", "gns3-imported-lab")
        topo_def = data.get("topology", {})
        gns3_nodes = topo_def.get("nodes", [])
        gns3_links = topo_def.get("links", [])

        azam_topo = AzamTopology(
            name=project_name,
            description=f"Imported from GNS3 project '{project_name}'",
            author="GNS3 Importer",
        )

        node_id_to_node: Dict[str, AzamNode] = {}

        # 1. Parse Nodes
        for n_def in gns3_nodes:
            g_nid = n_def.get("node_id", str(uuid.uuid4()))
            name = n_def.get("name", f"Node-{g_nid[:6]}")
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
