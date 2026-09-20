"""
AzamLabs Dynamic Hardware & Appliance Catalog Service
Scans host image repositories (IOL binaries, QEMU folders, Docker images)
and maps them to high-performance, pre-tuned appliance templates.
"""

from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from azamlabs.config import settings
from azamlabs.core.schema import DeviceType, DriverType

logger = logging.getLogger("azamlabs.catalog")


class ApplianceTemplate(BaseModel):
    """Definition for a network or cyber virtual appliance template."""
    id: str
    name: str
    vendor: str  # Cisco, Arista, Juniper, Security, Linux, Generic
    category: str  # Routers, Switches, Firewalls, Servers, Endpoints
    device_type: DeviceType
    driver: DriverType
    default_cpu: int = 1
    default_ram_mb: int = 1024
    default_interfaces: List[str] = Field(default_factory=list)
    icon: str = "router"
    console_type: str = "telnet"
    is_installed: bool = False
    installed_images: List[str] = Field(default_factory=list)
    description: str = ""


# Master Pre-Configured Template Definitions
BASE_TEMPLATES: List[Dict[str, Any]] = [
    # --- Cisco Systems ---
    {
        "id": "cisco_iol_l3",
        "name": "Cisco IOL Router (Layer 3)",
        "vendor": "Cisco",
        "category": "Routers",
        "device_type": DeviceType.ROUTER,
        "driver": DriverType.IOL,
        "default_cpu": 1,
        "default_ram_mb": 512,
        "default_interfaces": ["Ethernet0/0", "Ethernet0/1", "Ethernet0/2", "Ethernet0/3"],
        "icon": "router",
        "console_type": "telnet",
        "description": "High-efficiency Cisco IOS on Linux L3 router with ultra-low memory footprint and KSM sharing.",
    },
    {
        "id": "cisco_iol_l2",
        "name": "Cisco IOL Switch (Layer 2)",
        "vendor": "Cisco",
        "category": "Switches",
        "device_type": DeviceType.SWITCH,
        "driver": DriverType.IOL,
        "default_cpu": 1,
        "default_ram_mb": 512,
        "default_interfaces": [
            "Ethernet0/0", "Ethernet0/1", "Ethernet0/2", "Ethernet0/3",
            "Ethernet1/0", "Ethernet1/1", "Ethernet1/2", "Ethernet1/3"
        ],
        "icon": "switch",
        "console_type": "telnet",
        "description": "High-density Cisco IOS on Linux L2 switch supporting 802.1Q, PVST+, EtherChannel, and VTP.",
    },
    {
        "id": "cisco_c8000v",
        "name": "Cisco Catalyst 8000v Edge",
        "vendor": "Cisco",
        "category": "Routers",
        "device_type": DeviceType.ROUTER,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 4096,
        "default_interfaces": ["GigabitEthernet1", "GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
        "icon": "router",
        "console_type": "telnet",
        "description": "Enterprise cloud router running IOS-XE SD-WAN and advanced BGP/MPLS.",
    },
    {
        "id": "cisco_csr1000v",
        "name": "Cisco CSR 1000v Router",
        "vendor": "Cisco",
        "category": "Routers",
        "device_type": DeviceType.ROUTER,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 3072,
        "default_interfaces": ["GigabitEthernet1", "GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
        "icon": "router",
        "console_type": "telnet",
        "description": "Standard Cisco Cloud Services Router running IOS-XE.",
    },
    {
        "id": "cisco_iosv",
        "name": "Cisco IOSv Virtual Router",
        "vendor": "Cisco",
        "category": "Routers",
        "device_type": DeviceType.ROUTER,
        "driver": DriverType.QEMU,
        "default_cpu": 1,
        "default_ram_mb": 512,
        "default_interfaces": ["GigabitEthernet0/0", "GigabitEthernet0/1", "GigabitEthernet0/2", "GigabitEthernet0/3"],
        "icon": "router",
        "console_type": "telnet",
        "description": "Lightweight virtual Cisco IOS router for routing and protocol labs.",
    },
    {
        "id": "cisco_iosvl2",
        "name": "Cisco IOSv Layer 2 Switch",
        "vendor": "Cisco",
        "category": "Switches",
        "device_type": DeviceType.SWITCH,
        "driver": DriverType.QEMU,
        "default_cpu": 1,
        "default_ram_mb": 1024,
        "default_interfaces": ["GigabitEthernet0/0", "GigabitEthernet0/1", "GigabitEthernet0/2", "GigabitEthernet0/3"],
        "icon": "switch",
        "console_type": "telnet",
        "description": "Virtual enterprise L2 switch supporting STP, MST, LACP, and Dot1X.",
    },
    {
        "id": "cisco_asav",
        "name": "Cisco ASAv Firewall",
        "vendor": "Cisco",
        "category": "Firewalls",
        "device_type": DeviceType.FIREWALL,
        "driver": DriverType.QEMU,
        "default_cpu": 1,
        "default_ram_mb": 2048,
        "default_interfaces": ["Management0/0", "GigabitEthernet0/0", "GigabitEthernet0/1", "GigabitEthernet0/2"],
        "icon": "firewall",
        "console_type": "telnet",
        "description": "Adaptive Security Appliance virtual firewall with stateful inspection and VPN.",
    },
    {
        "id": "cisco_nxosv",
        "name": "Cisco Nexus 9000v (NX-OSv)",
        "vendor": "Cisco",
        "category": "Switches",
        "device_type": DeviceType.SWITCH,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 4096,
        "default_interfaces": ["mgmt0", "Ethernet1/1", "Ethernet1/2", "Ethernet1/3", "Ethernet1/4"],
        "icon": "switch",
        "console_type": "telnet",
        "description": "Data center spine/leaf switch running Cisco NX-OS with VXLAN EVPN support.",
    },

    # --- Arista Networks ---
    {
        "id": "arista_veos",
        "name": "Arista vEOS Switch",
        "vendor": "Arista",
        "category": "Switches",
        "device_type": DeviceType.SWITCH,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 2048,
        "default_interfaces": ["Management1", "Ethernet1", "Ethernet2", "Ethernet3", "Ethernet4"],
        "icon": "switch",
        "console_type": "telnet",
        "description": "Arista Extensible Operating System (EOS) for modern cloud and leaf/spine fabrics.",
    },
    {
        "id": "arista_ceos",
        "name": "Arista cEOS Container",
        "vendor": "Arista",
        "category": "Switches",
        "device_type": DeviceType.SWITCH,
        "driver": DriverType.DOCKER,
        "default_cpu": 1,
        "default_ram_mb": 1024,
        "default_interfaces": ["Management0", "Ethernet1", "Ethernet2", "Ethernet3", "Ethernet4"],
        "icon": "switch",
        "console_type": "telnet",
        "description": "Containerized Arista EOS with sub-second boot time and micro-footprint.",
    },

    # --- Juniper Networks ---
    {
        "id": "juniper_vsrx",
        "name": "Juniper vSRX Next-Gen Firewall",
        "vendor": "Juniper",
        "category": "Firewalls",
        "device_type": DeviceType.FIREWALL,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 4096,
        "default_interfaces": ["fxp0", "ge-0/0/0", "ge-0/0/1", "ge-0/0/2", "ge-0/0/3"],
        "icon": "firewall",
        "console_type": "telnet",
        "description": "Virtual security appliance powered by Junos OS with full NGFW security services.",
    },
    {
        "id": "juniper_vmx",
        "name": "Juniper vMX Router",
        "vendor": "Juniper",
        "category": "Routers",
        "device_type": DeviceType.ROUTER,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 4096,
        "default_interfaces": ["fxp0", "ge-0/0/0", "ge-0/0/1", "ge-0/0/2", "ge-0/0/3"],
        "icon": "router",
        "console_type": "telnet",
        "description": "Carrier-grade virtual MX Series router with high-throughput routing engine.",
    },

    # --- Cybersecurity & Range ---
    {
        "id": "sec_kali",
        "name": "Kali Linux Cyber Range Attacker",
        "vendor": "Security",
        "category": "Cyber Range",
        "device_type": DeviceType.ATTACKER,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 2048,
        "default_interfaces": ["eth0", "eth1"],
        "icon": "attacker",
        "console_type": "vnc",
        "description": "Offensive cyber security suite loaded with Metasploit, Nmap, Wireshark, and pen-testing tools.",
    },
    {
        "id": "sec_fortigate",
        "name": "Fortinet FortiGate Firewall",
        "vendor": "Security",
        "category": "Firewalls",
        "device_type": DeviceType.FIREWALL,
        "driver": DriverType.QEMU,
        "default_cpu": 1,
        "default_ram_mb": 1024,
        "default_interfaces": ["port1", "port2", "port3", "port4"],
        "icon": "firewall",
        "console_type": "telnet",
        "description": "Next-generation enterprise firewall running FortiOS with web filtering and SD-WAN.",
    },
    {
        "id": "sec_paloalto",
        "name": "Palo Alto PAN-OS VM",
        "vendor": "Security",
        "category": "Firewalls",
        "device_type": DeviceType.FIREWALL,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 4096,
        "default_interfaces": ["mgmt", "ethernet1/1", "ethernet1/2", "ethernet1/3", "ethernet1/4"],
        "icon": "firewall",
        "console_type": "telnet",
        "description": "Palo Alto Networks virtualized next-gen firewall running PAN-OS with App-ID and Threat Prevention.",
    },

    # --- Linux & Endpoints ---
    {
        "id": "endpoint_linux",
        "name": "Ubuntu / Alpine Linux Server",
        "vendor": "Linux",
        "category": "Endpoints",
        "device_type": DeviceType.SERVER,
        "driver": DriverType.QEMU,
        "default_cpu": 1,
        "default_ram_mb": 512,
        "default_interfaces": ["eth0", "eth1"],
        "icon": "server",
        "console_type": "telnet",
        "description": "Clean Linux server appliance for network testing, DNS, DHCP, Web, and Python scripts.",
    },
    {
        "id": "endpoint_vpcs",
        "name": "Virtual PC Simulator (VPCS)",
        "vendor": "Linux",
        "category": "Endpoints",
        "device_type": DeviceType.HOST,
        "driver": DriverType.VPCS,
        "default_cpu": 1,
        "default_ram_mb": 2,
        "default_interfaces": ["eth0"],
        "icon": "host",
        "console_type": "telnet",
        "description": "Ultra-lightweight micro-PC (2MB RAM) providing ping, traceroute, and DHCP test capabilities.",
    },
    {
        "id": "endpoint_win",
        "name": "Windows Client / Server",
        "vendor": "Linux",
        "category": "Endpoints",
        "device_type": DeviceType.HOST,
        "driver": DriverType.QEMU,
        "default_cpu": 2,
        "default_ram_mb": 4096,
        "default_interfaces": ["Ethernet0"],
        "icon": "host",
        "console_type": "vnc",
        "description": "Windows workstation or server endpoint for Active Directory and end-user simulation.",
    },
]


HardwareApplianceTemplate = ApplianceTemplate


class DeviceCatalogService:
    """Discovers installed images and matches them with pre-configured templates."""

    def __init__(self, iol_dirs: Optional[List[Path]] = None, qemu_dirs: Optional[List[Path]] = None):
        self.iol_dirs = iol_dirs if iol_dirs is not None else [
            Path("/opt/azamlabs/images/iol/bin"),
            Path("/opt/azamlabs/images/iol"),
            settings.IOL_IMAGES_DIR,
        ]
        self.qemu_dirs = qemu_dirs if qemu_dirs is not None else [
            Path("/opt/azamlabs/images/qemu"),
            settings.QEMU_IMAGES_DIR,
        ]

    def scan_iol_images(self, extra_dirs: Optional[List[Path]] = None) -> List[str]:
        """Returns filenames of detected IOL binaries."""
        detected = set()
        dirs = list(self.iol_dirs) + (extra_dirs or [])
        for d in dirs:
            if d.exists() and d.is_dir():
                try:
                    for f in d.iterdir():
                        if f.is_file():
                            name = f.name
                            # Exclude license or temp files
                            if name in ("iourc", "NETMAP", "license.txt", "license"):
                                continue
                            if name.endswith((".bin", ".image")) or os.access(f, os.X_OK) or "adventerprise" in name.lower() or "l2" in name.lower():
                                detected.add(name)
                except Exception as e:
                    logger.warning(f"Error scanning IOL directory {d}: {e}")
        return sorted(detected)

    def scan_qemu_images(self, extra_dirs: Optional[List[Path]] = None) -> List[str]:
        """Returns folder names or disk file paths of detected QEMU images."""
        detected = set()
        dirs = list(self.qemu_dirs) + (extra_dirs or [])
        for d in dirs:
            if d.exists() and d.is_dir():
                try:
                    for item in d.iterdir():
                        if item.is_dir():
                            # Folder containing disk files
                            for f in item.iterdir():
                                if f.suffix.lower() in (".qcow2", ".vmdk", ".img"):
                                    detected.add(item.name)
                                    break
                        elif item.is_file() and item.suffix.lower() in (".qcow2", ".vmdk", ".img"):
                            detected.add(item.name)
                except Exception as e:
                    logger.warning(f"Error scanning QEMU directory {d}: {e}")
        return sorted(detected)

    def get_catalog(self, extra_iol_dirs: Optional[List[Path]] = None, extra_qemu_dirs: Optional[List[Path]] = None) -> List[Dict[str, Any]]:
        """Returns full catalog with dynamic installation flags and image lists."""
        iol_images = self.scan_iol_images(extra_dirs=extra_iol_dirs)
        qemu_images = self.scan_qemu_images(extra_dirs=extra_qemu_dirs)

        catalog: List[Dict[str, Any]] = []

        for base in BASE_TEMPLATES:
            tmpl = dict(base)
            installed_imgs = []

            if tmpl["driver"] == DriverType.IOL:
                # Filter matching IOL images
                if tmpl["device_type"] == DeviceType.SWITCH:
                    installed_imgs = [img for img in iol_images if "l2" in img.lower() or "switch" in img.lower()]
                else:
                    installed_imgs = [img for img in iol_images if "l2" not in img.lower() and "switch" not in img.lower()]
                # If template has no specific match, allow all IOL images as fallback
                if not installed_imgs and iol_images:
                    installed_imgs = iol_images

            elif tmpl["driver"] == DriverType.QEMU:
                # Match folder name prefixes
                tmpl_id = tmpl["id"].lower()
                for qimg in qemu_images:
                    qlower = qimg.lower()
                    if ("c8000" in tmpl_id and "c8000" in qlower) or \
                       ("csr1000" in tmpl_id and "csr1000" in qlower) or \
                       ("iosvl2" in tmpl_id and ("iosvl2" in qlower or "viosl2" in qlower)) or \
                       ("iosv" in tmpl_id and "iosvl2" not in tmpl_id and ("iosv" in qlower or "vios" in qlower) and "l2" not in qlower) or \
                       ("asav" in tmpl_id and "asav" in qlower) or \
                       ("nxos" in tmpl_id and "nxos" in qlower) or \
                       ("veos" in tmpl_id and "veos" in qlower) or \
                       ("vsrx" in tmpl_id and "vsrx" in qlower) or \
                       ("vmx" in tmpl_id and "vmx" in qlower) or \
                       ("kali" in tmpl_id and "kali" in qlower) or \
                       ("forti" in tmpl_id and ("forti" in qlower or "fgt" in qlower)) or \
                       ("palo" in tmpl_id and ("palo" in qlower or "pan" in qlower)) or \
                       ("linux" in tmpl_id and ("linux" in qlower or "ubuntu" in qlower or "alpine" in qlower)) or \
                       ("win" in tmpl_id and ("win" in qlower or "desktop" in qlower)):
                        installed_imgs.append(qimg)

            elif tmpl["driver"] == DriverType.VPCS:
                # VPCS is built-in
                installed_imgs = ["vpcs-builtin"]

            tmpl["is_installed"] = len(installed_imgs) > 0
            tmpl["installed_images"] = installed_imgs
            catalog.append(tmpl)

        # Append any custom detected images that didn't match standard templates
        matched_images = set()
        for t in catalog:
            for img in t["installed_images"]:
                matched_images.add(img)

        custom_iol = [img for img in iol_images if img not in matched_images]
        if custom_iol:
            catalog.append({
                "id": "custom_iol",
                "name": "Custom Cisco IOL Binary",
                "vendor": "Cisco",
                "category": "Routers",
                "device_type": DeviceType.ROUTER,
                "driver": DriverType.IOL,
                "default_cpu": 1,
                "default_ram_mb": 512,
                "default_interfaces": ["Ethernet0/0", "Ethernet0/1", "Ethernet0/2", "Ethernet0/3"],
                "icon": "router",
                "console_type": "telnet",
                "is_installed": True,
                "installed_images": custom_iol,
                "description": "User-supplied Cisco IOL binary image detected on host.",
            })

        custom_qemu = [img for img in qemu_images if img not in matched_images]
        if custom_qemu:
            catalog.append({
                "id": "custom_qemu",
                "name": "Custom QEMU Appliance",
                "vendor": "Generic",
                "category": "Routers",
                "device_type": DeviceType.ROUTER,
                "driver": DriverType.QEMU,
                "default_cpu": 2,
                "default_ram_mb": 2048,
                "default_interfaces": ["eth0", "eth1", "eth2", "eth3"],
                "icon": "router",
                "console_type": "telnet",
                "is_installed": True,
                "installed_images": custom_qemu,
                "description": "User-supplied QEMU image folder detected on host.",
            })

        return catalog


catalog_service = DeviceCatalogService()
