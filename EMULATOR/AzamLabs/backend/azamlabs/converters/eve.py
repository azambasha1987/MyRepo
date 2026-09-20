"""
AzamLabs EVE-NG & PNETLab (.unl) Bidirectional XML Converter
Provides clean, high-fidelity conversion between EVE-NG / PNETLab XML (.unl) files and AzamTopology.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from collections import defaultdict

from azamlabs.core.schema import (
    AzamTopology,
    AzamNode,
    AzamLink,
    AzamNetwork,
    DeviceType,
    DriverType,
)


class EveConverter:
    """Handles bidirectional conversion between EVE-NG / PNETLab XML (.unl) and AzamTopology."""

    # EVE-NG node type to AzamLabs DriverType
    TYPE_DRIVER_MAP = {
        "iol": DriverType.IOL,
        "iou": DriverType.IOL,
        "qemu": DriverType.QEMU,
        "docker": DriverType.DOCKER,
        "vpcs": DriverType.VPCS,
        "dynamips": DriverType.QEMU,
    }

    @classmethod
    def eve_to_azam(cls, content: str) -> AzamTopology:
        """Converts an EVE-NG / PNETLab XML (.unl) string into an AzamTopology."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid EVE-NG XML specification: {e}")

        lab_name = root.attrib.get("name", "eve-imported-lab")
        desc_elem = root.find("description")
        description = desc_elem.text if desc_elem is not None and desc_elem.text else "Imported from EVE-NG / PNETLab (.unl)"

        azam_topo = AzamTopology(
            name=lab_name,
            description=description,
            author=root.attrib.get("version", "EVE-NG Importer"),
        )

        topo_elem = root.find("topology")
        if topo_elem is None:
            return azam_topo

        # 1. Parse Networks
        networks_elem = topo_elem.find("networks")
        network_map: Dict[str, Dict[str, Any]] = {}
        if networks_elem is not None:
            for net_node in networks_elem.findall("network"):
                net_id = net_node.attrib.get("id", "")
                net_type = net_node.attrib.get("type", "bridge")
                net_name = net_node.attrib.get("name", f"Net-{net_id}")
                network_map[net_id] = {
                    "id": net_id,
                    "type": net_type,
                    "name": net_name,
                    "left": float(net_node.attrib.get("left", 0)),
                    "top": float(net_node.attrib.get("top", 0)),
                }

        # 2. Parse Nodes & Record Interface-to-Network Mappings
        nodes_elem = topo_elem.find("nodes")
        net_to_endpoints: Dict[str, List[tuple]] = defaultdict(list)  # net_id -> [(node_name, iface_name)]
        node_id_map: Dict[str, AzamNode] = {}

        if nodes_elem is not None:
            for n_elem in nodes_elem.findall("node"):
                node_id = n_elem.attrib.get("id", "")
                node_name = n_elem.attrib.get("name", f"Node-{node_id}")
                raw_type = n_elem.attrib.get("type", "qemu").lower()
                template = n_elem.attrib.get("template", "").lower()
                image = n_elem.attrib.get("image", template)

                driver_type = cls.TYPE_DRIVER_MAP.get(raw_type, DriverType.QEMU)

                # Determine DeviceType
                if "l2" in template or "switch" in template or "layer2" in template:
                    dev_type = DeviceType.SWITCH
                elif "firewall" in template or "asa" in template or "forti" in template or "palo" in template:
                    dev_type = DeviceType.FIREWALL
                elif "vpcs" in raw_type or "host" in template or "win" in template or "ubuntu" in template:
                    dev_type = DeviceType.HOST
                else:
                    dev_type = DeviceType.ROUTER

                pos_x = float(n_elem.attrib.get("left", 100))
                pos_y = float(n_elem.attrib.get("top", 100))
                ram = int(n_elem.attrib.get("ram", 1024))
                cpu = int(n_elem.attrib.get("cpu", 1))

                azam_node = AzamNode(
                    name=node_name,
                    device_type=dev_type,
                    driver=driver_type,
                    image=image,
                    cpu=cpu,
                    ram_mb=ram,
                    pos_x=pos_x,
                    pos_y=pos_y,
                    metadata={"eve_id": node_id, "eve_type": raw_type, "template": template},
                )

                # Parse Interfaces
                for iface_elem in n_elem.findall("interface"):
                    iface_id = iface_elem.attrib.get("id", "0")
                    iface_name = iface_elem.attrib.get("name", f"eth{iface_id}")
                    net_id = iface_elem.attrib.get("network_id", "0")

                    azam_node.add_interface(iface_name)
                    if net_id and net_id != "0":
                        net_to_endpoints[net_id].append((node_name, iface_name))

                azam_topo.add_node(azam_node)
                node_id_map[node_id] = azam_node

        # 3. Stitch Links and Cloud Networks
        for net_id, endpoints in net_to_endpoints.items():
            net_info = network_map.get(net_id, {"type": "bridge", "name": f"Net-{net_id}"})
            net_type = net_info.get("type", "bridge")

            # If it's a point-to-point bridge connecting exactly 2 interfaces:
            if len(endpoints) == 2 and (net_type == "bridge" or net_type.startswith("net")):
                ep1, ep2 = endpoints[0], endpoints[1]
                azam_link = AzamLink(
                    source_node=ep1[0],
                    source_interface=ep1[1],
                    target_node=ep2[0],
                    target_interface=ep2[1],
                    metadata={"eve_net_id": net_id},
                )
                azam_topo.links.append(azam_link)
            else:
                # Multi-access cloud or external bridge (e.g. pnet0, management cloud)
                cloud_net = AzamNetwork(
                    name=net_info.get("name", f"Cloud-{net_id}"),
                    net_type="mgmt" if "pnet0" in net_type or "mgmt" in net_info.get("name", "").lower() else "bridge",
                    bridge_name=net_type,
                )
                azam_topo.networks.append(cloud_net)

                # Connect each endpoint to this virtual network
                for ep in endpoints:
                    azam_link = AzamLink(
                        source_node=ep[0],
                        source_interface=ep[1],
                        target_node=cloud_net.name,
                        target_interface="port",
                        metadata={"connected_to_network": cloud_net.name},
                    )
                    azam_topo.links.append(azam_link)

        return azam_topo

    @classmethod
    def azam_to_eve(cls, topology: AzamTopology) -> str:
        """Exports an AzamTopology into an EVE-NG / PNETLab XML (.unl) string."""
        root = ET.Element("lab", {
            "name": topology.name.replace(" ", "_"),
            "version": "1",
            "scripttimeout": "300",
            "lock": "0",
        })

        desc_elem = ET.SubElement(root, "description")
        desc_elem.text = topology.description or "Exported from AzamLabs"

        ET.SubElement(root, "body")
        topo_elem = ET.SubElement(root, "topology")
        nodes_elem = ET.SubElement(topo_elem, "nodes")
        networks_elem = ET.SubElement(topo_elem, "networks")

        # Track network ID assignments for links
        link_net_map: Dict[str, str] = {}
        net_counter = 1

        for link in topology.links:
            net_id = str(net_counter)
            net_counter += 1
            link_net_map[link.id] = net_id

            # Create synthetic network node for EVE-NG bridge
            ET.SubElement(networks_elem, "network", {
                "id": net_id,
                "type": "bridge",
                "name": f"Net-{link.source_node}_{link.source_interface}",
                "left": "0",
                "top": "0",
                "visibility": "0",
            })

        # Node index map
        for n_idx, node in enumerate(topology.nodes, start=1):
            raw_type = "qemu"
            if node.driver == DriverType.IOL:
                raw_type = "iol"
            elif node.driver == DriverType.VPCS:
                raw_type = "vpcs"
            elif node.driver == DriverType.DOCKER:
                raw_type = "docker"

            template = node.metadata.get("template", node.image.split(":")[0])

            node_elem = ET.SubElement(nodes_elem, "node", {
                "id": str(n_idx),
                "name": node.name,
                "type": raw_type,
                "template": template,
                "image": node.image,
                "cpu": str(node.cpu),
                "ram": str(node.ram_mb),
                "left": str(int(node.pos_x)),
                "top": str(int(node.pos_y)),
            })

            # Add interfaces
            for i_idx, iface in enumerate(node.interfaces):
                # Find connected network_id
                assigned_net_id = "0"
                for link in topology.links:
                    if (link.source_node == node.name and link.source_interface == iface.name) or \
                       (link.target_node == node.name and link.target_interface == iface.name):
                        assigned_net_id = link_net_map.get(link.id, "0")
                        break

                ET.SubElement(node_elem, "interface", {
                    "id": str(i_idx),
                    "name": iface.name,
                    "type": "ethernet",
                    "network_id": assigned_net_id,
                })

        # Pretty indent XML
        try:
            ET.indent(root, space="  ")
        except AttributeError:
            pass  # Fallback for older python if ever needed

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
