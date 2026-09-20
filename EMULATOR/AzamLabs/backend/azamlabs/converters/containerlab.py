"""
AzamLabs Containerlab (.clab.yml) Bidirectional Converter
Provides high-fidelity conversion between Containerlab YAML topologies and AzamTopology.
"""

from typing import Dict, Any, Union
import yaml

from azamlabs.core.schema import (
    AzamTopology,
    AzamNode,
    AzamLink,
    AzamNetwork,
    DeviceType,
    DriverType,
)


class ContainerlabConverter:
    """Handles parsing and generating Containerlab YAML topologies."""

    # Kind to DeviceType and DriverType mapping
    KIND_MAP = {
        "srl": (DeviceType.ROUTER, DriverType.DOCKER, "ghcr.io/nokia/srlinux:latest"),
        "ceos": (DeviceType.SWITCH, DriverType.DOCKER, "ceos:latest"),
        "cisco_xrd": (DeviceType.ROUTER, DriverType.DOCKER, "cisco/xrd:latest"),
        "cisco_xrv": (DeviceType.ROUTER, DriverType.QEMU, "cisco-xrv:latest"),
        "cisco_xrv9k": (DeviceType.ROUTER, DriverType.QEMU, "cisco-xrv9k:latest"),
        "cisco_c8000v": (DeviceType.ROUTER, DriverType.QEMU, "c8000v:latest"),
        "arista_veos": (DeviceType.SWITCH, DriverType.QEMU, "veos:latest"),
        "juniper_vrr": (DeviceType.ROUTER, DriverType.QEMU, "vrr:latest"),
        "vr-sros": (DeviceType.ROUTER, DriverType.QEMU, "vr-sros:latest"),
        "vr-pan": (DeviceType.FIREWALL, DriverType.QEMU, "vr-pan:latest"),
        "vr-vmx": (DeviceType.ROUTER, DriverType.QEMU, "vr-vmx:latest"),
        "linux": (DeviceType.HOST, DriverType.DOCKER, "alpine:latest"),
        "mysocketio": (DeviceType.CLOUD, DriverType.DOCKER, "mysocketio:latest"),
        "bridge": (DeviceType.SWITCH, DriverType.DOCKER, ""),
        "ovs-bridge": (DeviceType.SWITCH, DriverType.DOCKER, ""),
    }

    @classmethod
    def clab_to_azam(cls, content: Union[str, Dict[str, Any]]) -> AzamTopology:
        """Converts a Containerlab YAML string or dictionary into an AzamTopology."""
        if isinstance(content, str):
            data = yaml.safe_load(content)
        else:
            data = content

        if not isinstance(data, dict):
            raise ValueError("Invalid Containerlab specification: root must be a YAML dictionary.")

        lab_name = data.get("name", "clab-imported-topology")
        topo_def = data.get("topology", {})
        kinds_def = topo_def.get("kinds", {})
        defaults_def = topo_def.get("defaults", {})
        nodes_def = topo_def.get("nodes", {})
        links_def = topo_def.get("links", [])
        mgmt_def = data.get("mgmt", {})

        azam_topo = AzamTopology(
            name=lab_name,
            description=f"Imported from Containerlab '{lab_name}'",
            author="Containerlab Importer",
        )

        # Management network
        if mgmt_def:
            net_name = mgmt_def.get("network", f"{lab_name}-mgmt")
            subnet = mgmt_def.get("ipv4-subnet")
            mgmt_net = AzamNetwork(
                name=net_name,
                net_type="mgmt",
                subnet=subnet,
                bridge_name=mgmt_def.get("bridge"),
            )
            azam_topo.networks.append(mgmt_net)

        # Parse Nodes
        grid_x = 100.0
        grid_y = 100.0

        for node_name, node_info in nodes_def.items():
            kind = node_info.get("kind", defaults_def.get("kind", "linux"))
            dev_type, driver_type, default_img = cls.KIND_MAP.get(
                kind.lower(), (DeviceType.ROUTER, DriverType.DOCKER, "alpine:latest")
            )

            image = (
                node_info.get("image")
                or kinds_def.get(kind, {}).get("image")
                or defaults_def.get("image")
                or default_img
            )

            # Node labels for positions
            labels = node_info.get("labels", {})
            pos_x = float(labels.get("graph-posX", labels.get("pos_x", grid_x)))
            pos_y = float(labels.get("graph-posY", labels.get("pos_y", grid_y)))
            grid_x += 180.0
            if grid_x > 800.0:
                grid_x = 100.0
                grid_y += 150.0

            azam_node = AzamNode(
                name=node_name,
                device_type=dev_type,
                driver=driver_type,
                image=image,
                pos_x=pos_x,
                pos_y=pos_y,
                env=node_info.get("env", {}),
                binds=node_info.get("binds", []),
                startup_config=node_info.get("startup-config"),
                metadata={"clab_kind": kind, "labels": labels},
            )

            # Management interface if specified
            mgmt_ip = node_info.get("mgmt-ipv4")
            if mgmt_ip:
                mgmt_iface = azam_node.add_interface("eth0", is_mgmt=True)
                mgmt_iface.ip_address = mgmt_ip

            azam_topo.add_node(azam_node)

        # Parse Links
        for link_info in links_def:
            endpoints = link_info.get("endpoints", [])
            if len(endpoints) == 2:
                cls._process_endpoint_pair(azam_topo, endpoints[0], endpoints[1], link_info)

        return azam_topo

    @classmethod
    def _process_endpoint_pair(
        cls,
        topo: AzamTopology,
        ep1: str,
        ep2: str,
        link_info: Dict[str, Any]
    ) -> None:
        """Parses a pair of endpoints ('node:interface') and links them in topology."""
        def parse_ep(ep: str):
            parts = ep.split(":", 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
            return parts[0].strip(), "eth1"

        node_a_name, iface_a_name = parse_ep(ep1)
        node_b_name, iface_b_name = parse_ep(ep2)

        node_a = topo.get_node(node_a_name)
        node_b = topo.get_node(node_b_name)

        if node_a:
            node_a.add_interface(iface_a_name)
        if node_b:
            node_b.add_interface(iface_b_name)

        azam_link = AzamLink(
            source_node=node_a_name,
            source_interface=iface_a_name,
            target_node=node_b_name,
            target_interface=iface_b_name,
            metadata=link_info.get("vars", {}),
        )
        topo.links.append(azam_link)

    @classmethod
    def azam_to_clab(cls, topology: AzamTopology) -> str:
        """Exports an AzamTopology into a valid Containerlab YAML configuration string."""
        clab_dict: Dict[str, Any] = {
            "name": topology.name.lower().replace(" ", "-"),
            "topology": {
                "nodes": {},
                "links": [],
            }
        }

        # Find mgmt network
        for net in topology.networks:
            if net.net_type == "mgmt":
                clab_dict["mgmt"] = {
                    "network": net.name,
                    "ipv4-subnet": net.subnet or "172.20.20.0/24",
                }
                break

        # Export Nodes
        for node in topology.nodes:
            kind = node.metadata.get("clab_kind")
            if not kind:
                if node.driver == DriverType.DOCKER:
                    kind = "linux" if node.device_type == DeviceType.HOST else "ceos"
                elif node.driver == DriverType.QEMU:
                    kind = "cisco_c8000v"
                else:
                    kind = "linux"

            node_entry: Dict[str, Any] = {
                "kind": kind,
                "image": node.image,
                "labels": {
                    "graph-posX": str(int(node.pos_x)),
                    "graph-posY": str(int(node.pos_y)),
                }
            }

            if node.env:
                node_entry["env"] = node.env
            if node.binds:
                node_entry["binds"] = node.binds
            if node.startup_config:
                node_entry["startup-config"] = node.startup_config

            # Mgmt IP
            for iface in node.interfaces:
                if iface.is_management and iface.ip_address:
                    node_entry["mgmt-ipv4"] = iface.ip_address.split("/")[0]

            clab_dict["topology"]["nodes"][node.name] = node_entry

        # Export Links
        for link in topology.links:
            clab_dict["topology"]["links"].append({
                "endpoints": [
                    f"{link.source_node}:{link.source_interface}",
                    f"{link.target_node}:{link.target_interface}",
                ]
            })

        return yaml.dump(clab_dict, sort_keys=False)
