"""
AzamLabs Cisco Modeling Labs (CML 2.x) Bidirectional Converter
Provides full-fidelity conversion between CML 2.x YAML topologies and AzamTopology.
"""

from typing import Dict, Any, Union, List
import yaml

from azamlabs.core.schema import (
    AzamTopology,
    AzamNode,
    AzamInterface,
    AzamLink,
    ImpairmentProfile,
    DeviceType,
    DriverType,
)


class CmlConverter:
    """Handles parsing and generating Cisco Modeling Labs (CML 2.x) YAML topologies."""

    CML_DEFINITION_MAP = {
        "iosv": (DeviceType.ROUTER, DriverType.QEMU, "cisco-iosv:latest"),
        "iosvl2": (DeviceType.SWITCH, DriverType.QEMU, "cisco-iosvl2:latest"),
        "csr1000v": (DeviceType.ROUTER, DriverType.QEMU, "cisco-csr1000v:latest"),
        "cat8000v": (DeviceType.ROUTER, DriverType.QEMU, "cisco-cat8000v:latest"),
        "nxosv9000": (DeviceType.SWITCH, DriverType.QEMU, "cisco-nxosv9000:latest"),
        "asav": (DeviceType.FIREWALL, DriverType.QEMU, "cisco-asav:latest"),
        "ftdv": (DeviceType.FIREWALL, DriverType.QEMU, "cisco-ftdv:latest"),
        "server": (DeviceType.SERVER, DriverType.DOCKER, "ubuntu:latest"),
        "desktop": (DeviceType.HOST, DriverType.DOCKER, "alpine:latest"),
        "ext-conn": (DeviceType.CLOUD, DriverType.PHYSICAL, ""),
        "wan-emulator": (DeviceType.ROUTER, DriverType.DOCKER, "alpine:latest"),
    }

    @classmethod
    def cml_to_azam(cls, content: Union[str, Dict[str, Any]]) -> AzamTopology:
        """Converts a CML 2.x YAML string or dictionary into an AzamTopology."""
        if isinstance(content, str):
            data = yaml.safe_load(content)
        else:
            data = content

        if not isinstance(data, dict):
            raise ValueError("Invalid CML specification: root must be a YAML dictionary.")

        lab_info = data.get("lab", {})
        title = lab_info.get("title", "CML-Imported-Lab")
        description = lab_info.get("description", "Imported from Cisco Modeling Labs (CML 2.x)")

        azam_topo = AzamTopology(
            name=title,
            description=description,
            author=lab_info.get("notes", "CML Importer"),
        )

        # Lookup table: node_id -> AzamNode, and (node_id, iface_id) -> iface_name
        cml_nodes = data.get("nodes", [])
        node_id_map: Dict[str, AzamNode] = {}
        iface_id_map: Dict[tuple, str] = {}  # (node_id, iface_id) -> label

        for n_def in cml_nodes:
            cml_nid = n_def.get("id", "")
            label = n_def.get("label", f"Node-{cml_nid}")
            node_def = n_def.get("node_definition", "iosv").lower()

            dev_type, driver_type, default_img = cls.CML_DEFINITION_MAP.get(
                node_def, (DeviceType.ROUTER, DriverType.QEMU, "cisco-iosv:latest")
            )

            # Coordinates (CML can have negative offsets; normalize gracefully)
            raw_x = float(n_def.get("x", 100))
            raw_y = float(n_def.get("y", 100))
            pos_x = raw_x + 500.0 if raw_x < 0 else raw_x
            pos_y = raw_y + 500.0 if raw_y < 0 else raw_y

            node = AzamNode(
                name=label,
                device_type=dev_type,
                driver=driver_type,
                image=n_def.get("image", default_img),
                cpu=int(n_def.get("cpus", 1)),
                ram_mb=int(n_def.get("ram", 1024)),
                pos_x=pos_x,
                pos_y=pos_y,
                startup_config=n_def.get("configuration"),
                metadata={"cml_id": cml_nid, "cml_definition": node_def},
            )

            # Interfaces
            for i_def in n_def.get("interfaces", []):
                cml_iid = i_def.get("id", "")
                i_label = i_def.get("label", f"eth{cml_iid}")
                node.add_interface(i_label)
                iface_id_map[(cml_nid, cml_iid)] = i_label

            azam_topo.add_node(node)
            node_id_map[cml_nid] = node

        # Links
        cml_links = data.get("links", [])
        for l_def in cml_links:
            n1_id = l_def.get("n1", "")
            i1_id = l_def.get("i1", "")
            n2_id = l_def.get("n2", "")
            i2_id = l_def.get("i2", "")

            node_a = node_id_map.get(n1_id)
            node_b = node_id_map.get(n2_id)

            if not node_a or not node_b:
                continue

            iface_a = iface_id_map.get((n1_id, i1_id), f"iface_{i1_id}")
            iface_b = iface_id_map.get((n2_id, i2_id), f"iface_{i2_id}")

            # Ensure interfaces exist on nodes
            node_a.add_interface(iface_a)
            node_b.add_interface(iface_b)

            # Impairment / Conditioning
            impairment = None
            cond = l_def.get("conditioning")
            if cond:
                impairment = ImpairmentProfile(
                    delay_ms=float(cond.get("latency", 0.0)),
                    jitter_ms=float(cond.get("jitter", 0.0)),
                    loss_percent=float(cond.get("loss", 0.0)),
                    rate_limit_kbps=int(cond.get("bandwidth", 0)),
                )

            azam_link = AzamLink(
                source_node=node_a.name,
                source_interface=iface_a,
                target_node=node_b.name,
                target_interface=iface_b,
                impairment=impairment,
                metadata={"cml_link_id": l_def.get("id")},
            )
            azam_topo.links.append(azam_link)

        return azam_topo

    @classmethod
    def azam_to_cml(cls, topology: AzamTopology) -> str:
        """Exports an AzamTopology into a valid CML 2.x YAML configuration string."""
        cml_dict: Dict[str, Any] = {
            "lab": {
                "title": topology.name,
                "description": topology.description or "Exported from AzamLabs",
                "notes": f"Author: {topology.author}",
            },
            "nodes": [],
            "links": [],
        }

        node_to_nid: Dict[str, str] = {}
        iface_to_iid: Dict[tuple, str] = {}  # (node_name, iface_name) -> iid

        for idx, node in enumerate(topology.nodes):
            nid = f"n{idx}"
            node_to_nid[node.name] = nid

            node_def = node.metadata.get("cml_definition")
            if not node_def:
                if node.device_type == DeviceType.SWITCH:
                    node_def = "iosvl2"
                elif node.device_type == DeviceType.FIREWALL:
                    node_def = "asav"
                elif node.device_type == DeviceType.SERVER:
                    node_def = "server"
                else:
                    node_def = "iosv"

            cml_interfaces = []
            for i_idx, iface in enumerate(node.interfaces):
                iid = f"i{i_idx}"
                iface_to_iid[(node.name, iface.name)] = iid
                cml_interfaces.append({
                    "id": iid,
                    "label": iface.name,
                    "slot": i_idx,
                })

            node_entry: Dict[str, Any] = {
                "id": nid,
                "label": node.name,
                "node_definition": node_def,
                "x": int(node.pos_x),
                "y": int(node.pos_y),
                "cpus": node.cpu,
                "ram": node.ram_mb,
                "interfaces": cml_interfaces,
            }

            if node.startup_config:
                node_entry["configuration"] = node.startup_config

            cml_dict["nodes"].append(node_entry)

        for l_idx, link in enumerate(topology.links):
            n1_id = node_to_nid.get(link.source_node)
            n2_id = node_to_nid.get(link.target_node)
            i1_id = iface_to_iid.get((link.source_node, link.source_interface))
            i2_id = iface_to_iid.get((link.target_node, link.target_interface))

            if n1_id and n2_id and i1_id and i2_id:
                link_entry: Dict[str, Any] = {
                    "id": f"l{l_idx}",
                    "n1": n1_id,
                    "i1": i1_id,
                    "n2": n2_id,
                    "i2": i2_id,
                }
                if link.impairment and link.impairment.is_active:
                    link_entry["conditioning"] = {
                        "latency": link.impairment.delay_ms,
                        "jitter": link.impairment.jitter_ms,
                        "loss": link.impairment.loss_percent,
                        "bandwidth": link.impairment.rate_limit_kbps,
                    }
                cml_dict["links"].append(link_entry)

        return yaml.dump(cml_dict, sort_keys=False)
