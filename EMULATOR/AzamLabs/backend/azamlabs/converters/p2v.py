"""
AzamLabs Physical-to-Virtual (P2V) Configuration Importer
Parses production router and switch configurations (Cisco IOS, NX-OS, Arista EOS, Juniper)
and automatically reconstructs the virtual network topology, interfaces, subnets, and links.
"""

import re
import ipaddress
from typing import Dict, List, Optional, Union, Any
from collections import defaultdict

from azamlabs.core.schema import (
    AzamTopology,
    AzamNode,
    AzamInterface,
    AzamLink,
    DeviceType,
    DriverType,
)


class P2VConverter:
    """Ingests running-config files and reconstructs virtual network topologies."""

    @classmethod
    def p2v_to_azam(
        cls,
        configs: Union[str, Dict[str, str], List[str]],
        lab_name: str = "P2V-Imported-Topology"
    ) -> AzamTopology:
        """Parses config text or dictionary of configs and returns an AzamTopology."""
        config_blocks: List[str] = []

        if isinstance(configs, dict):
            config_blocks = list(configs.values())
        elif isinstance(configs, list):
            config_blocks = configs
        elif isinstance(configs, str):
            # Split single string into device blocks if multiple hostnames are found
            config_blocks = cls._split_multi_device_text(configs)

        azam_topo = AzamTopology(
            name=lab_name,
            description="Reconstructed from physical production configurations via P2V Importer",
            author="AzamLabs P2V Engine",
        )

        grid_x = 120.0
        grid_y = 120.0

        # Map: IPv4Network -> List[(node_name, iface_name, ip)]
        subnet_map: Dict[ipaddress.IPv4Network, List[tuple]] = defaultdict(list)

        for raw_cfg in config_blocks:
            if not raw_cfg.strip():
                continue

            node_data = cls._parse_single_device(raw_cfg)
            hostname = node_data["hostname"]
            dev_type = node_data["device_type"]
            driver = node_data["driver"]
            image = node_data["image"]

            azam_node = AzamNode(
                name=hostname,
                device_type=dev_type,
                driver=driver,
                image=image,
                pos_x=grid_x,
                pos_y=grid_y,
                startup_config=raw_cfg.strip(),
            )

            grid_x += 220.0
            if grid_x > 900.0:
                grid_x = 120.0
                grid_y += 180.0

            # Add interfaces
            for iface_dict in node_data["interfaces"]:
                iface_name = iface_dict["name"]
                ip_str = iface_dict.get("ip")
                is_loopback = "loopback" in iface_name.lower()

                iface = azam_node.add_interface(iface_name)
                if ip_str:
                    iface.ip_address = ip_str
                    # Subnet matching (ignore loopbacks and host /32 routes for links)
                    if not is_loopback:
                        try:
                            iface_obj = ipaddress.IPv4Interface(ip_str)
                            if iface_obj.network.prefixlen < 32:
                                subnet_map[iface_obj.network].append((hostname, iface_name, str(iface_obj.ip)))
                        except ValueError:
                            pass

            azam_topo.add_node(azam_node)

        # Reconstruct Links via Subnet Intersection
        created_pairs = set()
        for subnet, endpoints in subnet_map.items():
            if len(endpoints) == 2:
                ep1, ep2 = endpoints[0], endpoints[1]
                pair_key = tuple(sorted([f"{ep1[0]}:{ep1[1]}", f"{ep2[0]}:{ep2[1]}"]))
                if pair_key not in created_pairs:
                    created_pairs.add(pair_key)
                    azam_link = AzamLink(
                        source_node=ep1[0],
                        source_interface=ep1[1],
                        target_node=ep2[0],
                        target_interface=ep2[1],
                        metadata={"inferred_subnet": str(subnet)},
                    )
                    azam_topo.links.append(azam_link)

        return azam_topo

    @classmethod
    def _split_multi_device_text(cls, text: str) -> List[str]:
        """Splits multi-config text files separated by headers or multiple hostname lines."""
        # Check for explicit boundary comments
        if "! --- Device:" in text or "# --- Device:" in text:
            chunks = re.split(r"[!#]\s*---\s*Device:[^\n]+---\s*", text)
            return [c.strip() for c in chunks if c.strip()]

        # Check for multiple 'hostname' commands
        host_matches = list(re.finditer(r"^\s*(?:hostname|sysname)\s+([A-Za-z0-9_\-\.]+)", text, re.MULTILINE))
        if len(host_matches) <= 1:
            return [text]

        chunks = []
        for idx, match in enumerate(host_matches):
            start = match.start()
            end = host_matches[idx + 1].start() if idx + 1 < len(host_matches) else len(text)
            chunks.append(text[start:end].strip())

        return chunks

    @classmethod
    def _parse_single_device(cls, config_text: str) -> Dict[str, Any]:
        """Extracts hostname, hardware type, and interfaces from a single device config."""
        # 1. Hostname
        host_match = re.search(r"^\s*(?:hostname|sysname)\s+([A-Za-z0-9_\-\.]+)", config_text, re.MULTILINE | re.IGNORECASE)
        hostname = host_match.group(1).strip() if host_match else "Device-Auto"

        # 2. Operating System & Device Type Detection
        lower_cfg = config_text.lower()
        if "nexus" in lower_cfg or "nx-os" in lower_cfg or "feature nxapi" in lower_cfg:
            dev_type = DeviceType.SWITCH
            driver = DriverType.QEMU
            image = "cisco-nxosv9000:latest"
        elif "arista" in lower_cfg or "eos" in lower_cfg or "transceiver qsfp" in lower_cfg:
            dev_type = DeviceType.SWITCH
            driver = DriverType.DOCKER
            image = "ceos:latest"
        elif "juniper" in lower_cfg or "junos" in lower_cfg:
            dev_type = DeviceType.ROUTER
            driver = DriverType.QEMU
            image = "juniper-vrr:latest"
        elif "asa" in lower_cfg or "firepower" in lower_cfg or "names" in lower_cfg:
            dev_type = DeviceType.FIREWALL
            driver = DriverType.QEMU
            image = "cisco-asav:latest"
        elif "spanning-tree" in lower_cfg or "vlan " in lower_cfg:
            dev_type = DeviceType.SWITCH
            driver = DriverType.IOL
            image = "cisco-iol-l2.bin"
        else:
            dev_type = DeviceType.ROUTER
            driver = DriverType.IOL
            image = "cisco-iol-l3.bin"

        # 3. Parse Interfaces line-by-line
        raw_ifaces = []
        current_iface = None
        current_lines = []

        for line in config_text.splitlines():
            stripped = line.strip()
            if re.match(r"^interface\s+", stripped, re.IGNORECASE):
                if current_iface:
                    raw_ifaces.append((current_iface, "\n".join(current_lines)))
                current_iface = re.sub(r"^interface\s+", "", stripped, flags=re.IGNORECASE).strip()
                current_lines = []
            elif current_iface:
                if stripped.startswith("!") or stripped.startswith("#") or stripped in ("exit", "end"):
                    raw_ifaces.append((current_iface, "\n".join(current_lines)))
                    current_iface = None
                    current_lines = []
                else:
                    current_lines.append(stripped)

        if current_iface:
            raw_ifaces.append((current_iface, "\n".join(current_lines)))

        interfaces = []
        for iface_name, block in raw_ifaces:
            ip_val = None

            # Subnet mask format: ip address 10.100.1.1 255.255.255.252
            ip_mask_match = re.search(
                r"ip\s+address\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})",
                block,
                re.IGNORECASE,
            )
            if ip_mask_match:
                ip_str = ip_mask_match.group(1)
                mask_str = ip_mask_match.group(2)
                try:
                    iface_obj = ipaddress.IPv4Interface(f"{ip_str}/{mask_str}")
                    ip_val = f"{iface_obj.ip}/{iface_obj.network.prefixlen}"
                except ValueError:
                    ip_val = ip_str
            else:
                cidr_match = re.search(
                    r"ip\s+address\s+(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})",
                    block,
                    re.IGNORECASE,
                )
                if cidr_match:
                    ip_val = cidr_match.group(1)

            interfaces.append({
                "name": iface_name,
                "ip": ip_val,
            })

        return {
            "hostname": hostname,
            "device_type": dev_type,
            "driver": driver,
            "image": image,
            "interfaces": interfaces,
        }
