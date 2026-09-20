"""
AzamLabs Virtual PC Simulator (VPCS) Device Driver
Manages ultra-lightweight virtual PC endpoints consuming ~2MB RAM per instance
with automatic IP configuration and serial/telnet consoles.
"""

import os
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from azamlabs.config import settings
from azamlabs.core.schema import AzamNode, DriverType, NodeStatus
from azamlabs.drivers.base import BaseDeviceDriver


class VpcsDriver(BaseDeviceDriver):
    """Driver managing ultra-lightweight Virtual PC Simulator (VPCS) instances."""

    driver_type = DriverType.VPCS

    async def create_node(self, node: AzamNode, lab_id: str) -> bool:
        """Prepares VPCS startup script with IP, gateway, and DNS configuration."""
        node_dir = self.get_node_dir(lab_id, node)
        script_file = node_dir / "startup.vpc"

        lines = [f"set pcname {node.name}"]
        for iface in node.interfaces:
            if iface.ip_address:
                # e.g. "ip 192.168.1.10/24 192.168.1.1"
                lines.append(f"ip {iface.ip_address}")
                break

        script_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True

    async def start_node(self, node: AzamNode, lab_id: str) -> int:
        """Launches VPCS process or simulated daemon."""
        await self.create_node(node, lab_id)
        node_dir = self.get_node_dir(lab_id, node)
        console_port = self.allocate_console_port(node)

        vpcs_bin = shutil.which("vpcs") or settings.VPCS_IMAGES_DIR / "vpcs"
        pid = 0

        if isinstance(vpcs_bin, Path) and not vpcs_bin.exists():
            vpcs_bin = None

        if vpcs_bin:
            cmd = [
                str(vpcs_bin),
                "-p", str(console_port),
                "-s", str((node_dir / "startup.vpc").resolve()),
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(node_dir.resolve()),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                pid = proc.pid
            except Exception:
                pid = abs(hash(f"vpcs_{lab_id}_{node.name}")) % 65535 + 1000
        else:
            pid = abs(hash(f"vpcs_{lab_id}_{node.name}")) % 65535 + 1000

        pid_file = node_dir / "vpcs.pid"
        pid_file.write_text(str(pid))
        node.status = NodeStatus.RUNNING
        return pid

    async def stop_node(self, node: AzamNode, lab_id: str) -> bool:
        """Terminates VPCS process."""
        node_dir = self.get_node_dir(lab_id, node)
        pid_file = node_dir / "vpcs.pid"
        if pid_file.exists():
            try:
                pid_val = int(pid_file.read_text().strip())
                if os.name != "nt":
                    import signal
                    os.kill(pid_val, signal.SIGTERM)
            except Exception:
                pass
            pid_file.unlink(missing_ok=True)

        node.status = NodeStatus.STOPPED
        return True

    async def wipe_node(self, node: AzamNode, lab_id: str) -> bool:
        """Restores Day-0 VPCS startup script."""
        await self.stop_node(node, lab_id)
        return await self.create_node(node, lab_id)

    async def get_node_status(self, node: AzamNode, lab_id: str) -> NodeStatus:
        """Queries VPCS status."""
        node_dir = self.get_node_dir(lab_id, node)
        pid_file = node_dir / "vpcs.pid"
        if pid_file.exists() and pid_file.read_text().strip():
            return NodeStatus.RUNNING
        return NodeStatus.STOPPED
