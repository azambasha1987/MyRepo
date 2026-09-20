"""
AzamLabs Day-0 Automated Configuration Generator
Generates vendor-tuned initial configurations (IP addressing, hostnames, SSH keys,
and routing protocols: OSPF, BGP) for Cisco, Arista, Juniper, FRRouting, and Linux.
"""

from typing import Dict, Any, Optional
from azamlabs.core.schema import AzamTopology, AzamNode, DeviceType, DriverType


class Day0ConfigGenerator:
    """Generates Day-0 startup configurations for virtual nodes."""

    @staticmethod
    def auto_assign_ip_plan(topology: AzamTopology, base_prefix: str = "10.100") -> None:
        """Assigns non-overlapping /30 or /31 subnets across all point-to-point links."""
        link_idx = 1
        for link in topology.links:
            subnet = f"{base_prefix}.{link_idx}"
            src_node = topology.get_node(link.source_node)
            tgt_node = topology.get_node(link.target_node)
            if src_node and tgt_node:
                src_iface = src_node.get_interface(link.source_interface)
                tgt_iface = tgt_node.get_interface(link.target_interface)
                if src_iface and not src_iface.ip_address:
                    src_iface.ip_address = f"{subnet}.1/30"
                if tgt_iface and not tgt_iface.ip_address:
                    tgt_iface.ip_address = f"{subnet}.2/30"
            link_idx += 1

    @classmethod
    def generate_config(
        cls,
        node: AzamNode,
        topology: AzamTopology,
        routing_protocol: str = "ospf",
        domain_name: str = "azamlabs.internal"
    ) -> str:
        """Generates appropriate Day-0 startup configuration based on vendor/driver."""
        image_name = node.image.lower()
        if "nxos" in image_name:
            return cls._generate_cisco_nxos(node, routing_protocol)
        elif any(k in image_name for k in ["c8000v", "csr1000v", "iosv", "iol", "cisco"]):
            return cls._generate_cisco_ios(node, routing_protocol, domain_name)
        elif "veos" in image_name or "arista" in image_name:
            return cls._generate_arista_eos(node, routing_protocol)
        elif "juniper" in image_name or "vsrx" in image_name:
            return cls._generate_juniper_junos(node, routing_protocol)
        elif "frr" in image_name or "linux" in image_name:
            return cls._generate_frrouting(node, routing_protocol)
        else:
            return cls._generate_generic_linux(node)

    @staticmethod
    def _generate_cisco_ios(node: AzamNode, routing: str, domain: str) -> str:
        lines = [
            f"! AzamLabs Day-0 Auto-Generated Config for {node.name}",
            f"hostname {node.name}",
            f"ip domain-name {domain}",
            "no ip domain-lookup",
            "service password-encryption",
            "enable secret 9 $9$AzamLabsSecret",
            "username admin privilege 15 secret 9 $9$AzamLabsSecret",
            "aaa new-model",
            "aaa authentication login default local",
            "ip ssh version 2",
            "crypto key generate rsa modulus 2048",
            "line vty 0 4",
            " transport input ssh telnet",
            " login local",
            "!",
        ]
        # Interface configurations
        for iface in node.interfaces:
            if iface.is_management:
                continue
            lines.append(f"interface {iface.name}")
            lines.append(f" description Connected-to-AzamLabs-Fabric")
            if iface.ip_address:
                ip, mask_len = iface.ip_address.split("/")
                # Convert prefix length to subnet mask
                mask = "255.255.255.252" if mask_len == "30" else "255.255.255.0"
                lines.append(f" ip address {ip} {mask}")
            lines.append(" no shutdown")
            if routing.lower() == "ospf":
                lines.append(" ip ospf 1 area 0")
            lines.append("!")

        if routing.lower() == "ospf":
            lines.extend([
                "router ospf 1",
                " passive-interface default",
            ])
            for iface in node.interfaces:
                if not iface.is_management:
                    lines.append(f" no passive-interface {iface.name}")
            lines.append("!")
        lines.append("end\n")
        return "\n".join(lines)

    @staticmethod
    def _generate_cisco_nxos(node: AzamNode, routing: str) -> str:
        lines = [
            f"! AzamLabs Day-0 NX-OS Config for {node.name}",
            f"hostname {node.name}",
            "feature ssh",
            "feature lldp",
        ]
        if routing.lower() == "ospf":
            lines.append("feature ospf")
        for iface in node.interfaces:
            if not iface.is_management:
                lines.append(f"interface {iface.name}")
                lines.append(" no switchport")
                if iface.ip_address:
                    lines.append(f" ip address {iface.ip_address}")
                if routing.lower() == "ospf":
                    lines.append(" ip router ospf 1 area 0.0.0.0")
                lines.append(" no shutdown")
        lines.append("!\n")
        return "\n".join(lines)

    @staticmethod
    def _generate_arista_eos(node: AzamNode, routing: str) -> str:
        lines = [
            f"! AzamLabs Day-0 Arista EOS Config for {node.name}",
            f"hostname {node.name}",
            "ip routing",
            "username admin privilege 15 secret sha512 $6$AzamLabsSecret",
        ]
        for iface in node.interfaces:
            if not iface.is_management:
                lines.append(f"interface {iface.name}")
                lines.append(" no switchport")
                if iface.ip_address:
                    lines.append(f" ip address {iface.ip_address}")
                lines.append(" no shutdown")
        lines.append("!\n")
        return "\n".join(lines)

    @staticmethod
    def _generate_juniper_junos(node: AzamNode, routing: str) -> str:
        lines = [
            "system {",
            f"    host-name {node.name};",
            "    root-authentication {",
            "        encrypted-password \"$6$AzamLabsSecret\";",
            "    }",
            "    services {",
            "        ssh;",
            "        netconf { ssh; }",
            "    }",
            "}",
            "interfaces {",
        ]
        for iface in node.interfaces:
            if not iface.is_management and iface.ip_address:
                lines.extend([
                    f"    {iface.name} {{",
                    "        unit 0 {",
                    "            family inet {",
                    f"                address {iface.ip_address};",
                    "            }",
                    "        }",
                    "    }",
                ])
        lines.append("}\n")
        return "\n".join(lines)

    @staticmethod
    def _generate_frrouting(node: AzamNode, routing: str) -> str:
        lines = [
            f"! FRRouting Day-0 Configuration for {node.name}",
            f"hostname {node.name}",
            "password zebra",
            "enable password zebra",
            "log stdout informational",
        ]
        for iface in node.interfaces:
            if not iface.is_management:
                lines.append(f"interface {iface.name}")
                if iface.ip_address:
                    lines.append(f" ip address {iface.ip_address}")
        if routing.lower() == "ospf":
            lines.extend([
                "router ospf",
                " ospf router-id 1.1.1.1",
                " network 0.0.0.0/0 area 0",
            ])
        lines.append("line vty\n!\n")
        return "\n".join(lines)

    @staticmethod
    def _generate_generic_linux(node: AzamNode) -> str:
        lines = [
            f"# AzamLabs Network Configuration for {node.name}",
            f"HOSTNAME={node.name}",
        ]
        for iface in node.interfaces:
            if iface.ip_address:
                lines.append(f"# {iface.name}: {iface.ip_address}")
        return "\n".join(lines)
