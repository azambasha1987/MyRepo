"""
AzamLabs Abstract Base Device Driver
Defines the unified lifecycle interface for all virtual device execution engines:
Containerlab / Docker, QEMU / KVM, Cisco IOL, and VPCS.
"""

from abc import ABC, abstractmethod
import socket
from pathlib import Path
from typing import Dict, Any, Optional

from azamlabs.config import settings
from azamlabs.core.schema import AzamNode, DriverType, NodeStatus


class BaseDeviceDriver(ABC):
    """Abstract base class that all node execution drivers must implement."""

    driver_type: DriverType

    def get_node_dir(self, lab_id: str, node: AzamNode) -> Path:
        """Returns the isolated ephemeral runtime directory for this node."""
        node_dir = settings.LABS_DIR / lab_id / node.name
        node_dir.mkdir(parents=True, exist_ok=True)
        return node_dir

    def allocate_console_port(self, node: AzamNode) -> int:
        """Allocates an available TCP port for serial/telnet console access."""
        if node.console_port and self._is_port_free(node.console_port):
            return node.console_port

        # Search in standard pool 30000 - 45000
        start_port = 30000 + (hash(node.name) % 10000)
        for port in range(start_port, start_port + 1000):
            if self._is_port_free(port):
                node.console_port = port
                return port

        # Fallback to ephemeral OS assigned port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            node.console_port = s.getsockname()[1]
            return node.console_port

    def _is_port_free(self, port: int) -> bool:
        """Checks if a TCP port is currently free on localhost."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                s.bind(("0.0.0.0", port))
                return True
        except OSError:
            return False

    @abstractmethod
    async def create_node(self, node: AzamNode, lab_id: str) -> bool:
        """Prepares node disk overlays, configs, and directory structures."""
        pass

    @abstractmethod
    async def start_node(self, node: AzamNode, lab_id: str) -> int:
        """Launches the node process or container and returns its PID / process ID."""
        pass

    @abstractmethod
    async def stop_node(self, node: AzamNode, lab_id: str) -> bool:
        """Terminates the running process or stops the container."""
        pass

    @abstractmethod
    async def wipe_node(self, node: AzamNode, lab_id: str) -> bool:
        """Deletes ephemeral copy-on-write disk overlays and restores Day-0 pristine state."""
        pass

    @abstractmethod
    async def get_node_status(self, node: AzamNode, lab_id: str) -> NodeStatus:
        """Checks whether the process or container is currently running."""
        pass

    def get_console_info(self, node: AzamNode, lab_id: str) -> Dict[str, Any]:
        """Returns connection coordinates for browser Web Terminal and external Telnet clients."""
        return {
            "node_name": node.name,
            "host": settings.HOST if settings.HOST != "0.0.0.0" else "127.0.0.1",
            "port": node.console_port,
            "type": node.console_type,
            "uri": f"{node.console_type}://{settings.HOST if settings.HOST != '0.0.0.0' else '127.0.0.1'}:{node.console_port}",
        }
