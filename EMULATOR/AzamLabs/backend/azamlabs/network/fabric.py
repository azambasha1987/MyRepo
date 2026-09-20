"""
AzamLabs Linux Virtual Dataplane Fabric & Live Cabling Engine
Manages veth pairs, Linux bridges, TAP devices, and live hot-link cable connects/disconnects.
"""

import os
import shutil
import asyncio
from typing import Dict, List, Any, Optional
import logging

from azamlabs.core.schema import AzamLink, LinkStatus
from azamlabs.config import settings

logger = logging.getLogger("azamlabs.dataplane")


class VirtualDataplaneFabric:
    """Manages virtual network wires, Linux network namespaces, and live cabling."""

    def __init__(self):
        self._active_links: Dict[str, Dict[str, Any]] = {}

    def get_veth_names(self, link: AzamLink) -> tuple[str, str]:
        """Generates deterministic, unique interface names (<=15 chars for Linux kernel)."""
        lid = link.id[:6]
        veth_a = f"vth_{lid}_a"
        veth_b = f"vth_{lid}_b"
        return veth_a, veth_b

    async def connect_link(self, link: AzamLink, lab_id: str) -> bool:
        """Establishes a virtual cable between two device interfaces with live hot-plugging."""
        veth_a, veth_b = self.get_veth_names(link)
        ip_bin = shutil.which("ip")

        if ip_bin and os.name != "nt":
            # 1. Create veth pair
            cmd_create = [ip_bin, "link", "add", veth_a, "type", "veth", "peer", "name", veth_b]
            proc = await asyncio.create_subprocess_exec(*cmd_create, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await proc.wait()

            # 2. Bring up interfaces
            await (await asyncio.create_subprocess_exec(ip_bin, "link", "set", veth_a, "up")).wait()
            await (await asyncio.create_subprocess_exec(ip_bin, "link", "set", veth_b, "up")).wait()

            # 3. Move into node network namespaces if running as Docker containers
            await self._inject_into_netns(lab_id, link.source_node, veth_a, link.source_interface)
            await self._inject_into_netns(lab_id, link.target_node, veth_b, link.target_interface)

        link.status = LinkStatus.UP
        self._active_links[link.id] = {
            "link_id": link.id,
            "lab_id": lab_id,
            "veth_a": veth_a,
            "veth_b": veth_b,
            "source": f"{link.source_node}:{link.source_interface}",
            "target": f"{link.target_node}:{link.target_interface}",
            "status": "up",
        }
        logger.info(f"Connected live link {link.endpoints_display}")
        return True

    async def disconnect_link(self, link: AzamLink, lab_id: str) -> bool:
        """Disconnects a live virtual cable instantly without tearing down nodes."""
        veth_a, _ = self.get_veth_names(link)
        ip_bin = shutil.which("ip")

        if ip_bin and os.name != "nt":
            cmd_del = [ip_bin, "link", "del", veth_a]
            try:
                proc = await asyncio.create_subprocess_exec(*cmd_del, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await proc.wait()
            except Exception:
                pass

        link.status = LinkStatus.DOWN
        if link.id in self._active_links:
            self._active_links[link.id]["status"] = "down"
        logger.info(f"Disconnected live link {link.endpoints_display}")
        return True

    async def _inject_into_netns(self, lab_id: str, node_name: str, veth_name: str, target_ifname: str) -> bool:
        """Moves a veth endpoint into the container network namespace."""
        docker_bin = shutil.which("docker")
        ip_bin = shutil.which("ip")
        if not (docker_bin and ip_bin):
            return False

        container_name = f"azam_{lab_id}_{node_name}".replace("-", "_")
        try:
            # Query container PID
            proc = await asyncio.create_subprocess_exec(
                docker_bin, "inspect", "-f", "{{.State.Pid}}", container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            pid_str = stdout.decode().strip()
            if pid_str and pid_str != "0":
                # Move veth into netns
                await (await asyncio.create_subprocess_exec(
                    ip_bin, "link", "set", veth_name, "netns", pid_str, "name", target_ifname
                )).wait()
                # Bring up interface inside namespace via nsenter
                nsenter_bin = shutil.which("nsenter")
                if nsenter_bin:
                    await (await asyncio.create_subprocess_exec(
                        nsenter_bin, "-t", pid_str, "-n", ip_bin, "link", "set", target_ifname, "up"
                    )).wait()
                return True
        except Exception:
            pass
        return False

    def list_active_links(self, lab_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns metadata for all connected virtual wires."""
        if lab_id:
            return [l for l in self._active_links.values() if l.get("lab_id") == lab_id]
        return list(self._active_links.values())


# Global Dataplane Instance
fabric = VirtualDataplaneFabric()
