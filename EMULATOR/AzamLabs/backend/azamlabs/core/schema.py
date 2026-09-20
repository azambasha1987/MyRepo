"""
AzamLabs Universal Data Schema
Defines canonical Pydantic models for topologies, nodes, interfaces, links, and networks.
Provides unified abstraction over Containerlab, CML2, EVE-NG, and GNS3 representations.
"""

from __future__ import annotations
import uuid
import yaml
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    PAUSED = "paused"


class LinkStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    IMPAIRED = "impaired"


class DeviceType(str, Enum):
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    SERVER = "server"
    HOST = "host"
    CLOUD = "cloud"
    CONTAINER = "container"
    ATTACKER = "attacker"
    CUSTOM = "custom"


class DriverType(str, Enum):
    DOCKER = "docker"
    QEMU = "qemu"
    IOL = "iol"
    VPCS = "vpcs"
    K8S = "k8s"
    PHYSICAL = "physical"


class ImpairmentProfile(BaseModel):
    """Network Link Impairment Profile (tc-netem parameterization)."""
    delay_ms: float = Field(default=0.0, description="One-way latency in milliseconds")
    jitter_ms: float = Field(default=0.0, description="Latency variation (jitter) in milliseconds")
    loss_percent: float = Field(default=0.0, description="Packet loss probability (0.0 - 100.0%)")
    rate_limit_kbps: int = Field(default=0, description="Bandwidth throttling limit in kbps (0 = unlimited)")
    corrupt_percent: float = Field(default=0.0, description="Packet corruption percentage (0.0 - 100.0%)")

    @property
    def is_active(self) -> bool:
        return any([
            self.delay_ms > 0,
            self.loss_percent > 0,
            self.rate_limit_kbps > 0,
            self.corrupt_percent > 0,
        ])


class AzamInterface(BaseModel):
    """Canonical Network Interface Model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(description="Interface identifier, e.g. eth0, Gi0/1")
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    is_management: bool = False
    status: LinkStatus = LinkStatus.DOWN
    peer_link_id: Optional[str] = None


class AzamNode(BaseModel):
    """Canonical Network Node Model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    device_type: DeviceType = DeviceType.ROUTER
    driver: DriverType = DriverType.DOCKER
    image: str = Field(default="alpine:latest", description="Image path, QCOW2 filename, or Docker container tag")
    cpu: int = Field(default=1, ge=1)
    ram_mb: int = Field(default=1024, ge=64)
    status: NodeStatus = NodeStatus.STOPPED
    interfaces: List[AzamInterface] = Field(default_factory=list)
    startup_config: Optional[str] = None
    running_config: Optional[str] = None
    pos_x: float = Field(default=100.0)
    pos_y: float = Field(default=100.0)
    console_port: Optional[int] = None
    console_type: str = "telnet"  # telnet, ssh, serial, vnc
    env: Dict[str, str] = Field(default_factory=dict)
    binds: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_interface(self, iface_name: str) -> Optional[AzamInterface]:
        for iface in self.interfaces:
            if iface.name.lower() == iface_name.lower():
                return iface
        return None

    def add_interface(self, iface_name: str, is_mgmt: bool = False) -> AzamInterface:
        existing = self.get_interface(iface_name)
        if existing:
            return existing
        new_iface = AzamInterface(name=iface_name, is_management=is_mgmt)
        self.interfaces.append(new_iface)
        return new_iface


class AzamLink(BaseModel):
    """Canonical Point-to-Point Virtual Wire / Link Model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_node: str
    source_interface: str
    target_node: str
    target_interface: str
    status: LinkStatus = LinkStatus.UP
    impairment: Optional[ImpairmentProfile] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def endpoints_display(self) -> str:
        return f"{self.source_node}:{self.source_interface} <-> {self.target_node}:{self.target_interface}"


class AzamNetwork(BaseModel):
    """Virtual Network / Bridge / Cloud Transit Domain Model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    net_type: str = "bridge"  # mgmt, nat, isolated, passthrough, wireguard
    subnet: Optional[str] = None
    bridge_name: Optional[str] = None
    vlan_id: Optional[int] = None


class AzamAnnotation(BaseModel):
    """Canvas Visual Annotation (Zone, Shape, or Sticky Note)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "zone"  # zone, text, box, cloud, icon
    label: str = ""
    pos_x: float = 0.0
    pos_y: float = 0.0
    width: float = 200.0
    height: float = 150.0
    color: str = "#00f2fe"
    background_color: str = "rgba(0, 242, 254, 0.08)"


class AzamTopology(BaseModel):
    """Master Canonical Topology Model for AzamLabs."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = "AzamLabs Architect"
    folder_path: str = "/"
    nodes: List[AzamNode] = Field(default_factory=list)
    links: List[AzamLink] = Field(default_factory=list)
    networks: List[AzamNetwork] = Field(default_factory=list)
    annotations: List[AzamAnnotation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_node(self, node_id_or_name: str) -> Optional[AzamNode]:
        for node in self.nodes:
            if node.id == node_id_or_name or node.name.lower() == node_id_or_name.lower():
                return node
        return None

    def get_link(self, link_id: str) -> Optional[AzamLink]:
        for link in self.links:
            if link.id == link_id:
                return link
        return None

    def add_node(self, node: AzamNode) -> AzamNode:
        existing = self.get_node(node.name)
        if existing:
            raise ValueError(f"Node with name '{node.name}' already exists in topology.")
        self.nodes.append(node)
        return node

    def add_link(self, source_node: str, source_iface: str, target_node: str, target_iface: str) -> AzamLink:
        s_node = self.get_node(source_node)
        t_node = self.get_node(target_node)
        if not s_node:
            raise ValueError(f"Source node '{source_node}' not found.")
        if not t_node:
            raise ValueError(f"Target node '{target_node}' not found.")

        s_iface = s_node.add_interface(source_iface)
        t_iface = t_node.add_interface(target_iface)

        link = AzamLink(
            source_node=s_node.name,
            source_interface=s_iface.name,
            target_node=t_node.name,
            target_interface=t_iface.name,
        )
        s_iface.peer_link_id = link.id
        t_iface.peer_link_id = link.id
        self.links.append(link)
        return link

    def to_yaml(self) -> str:
        """Serializes topology to standardized AzamLabs YAML format."""
        return yaml.dump(self.model_dump(mode="json"), sort_keys=False, indent=2)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> AzamTopology:
        """Deserializes topology from standardized AzamLabs YAML format."""
        data = yaml.safe_load(yaml_content)
        return cls(**data)
