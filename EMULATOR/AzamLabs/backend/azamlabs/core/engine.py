"""
AzamLabs Central Lifecycle Engine
Coordinates lab creation, node lifecycle (start/stop/wipe), anti-bootstorm scheduling,
and status telemetry reporting.
"""

import logging
from typing import Dict, List, Optional, Any

from azamlabs.core.schema import AzamTopology, AzamNode, NodeStatus
from azamlabs.core.database import db
from azamlabs.core.scheduler import AntiBootstormScheduler, EcoModeGovernor
from azamlabs.core.ksm import KsmManager
from azamlabs.core.governor import cpu_governor
from azamlabs.drivers.factory import DriverFactory
from azamlabs.network.fabric import fabric
from azamlabs.network.sandbox import sandbox

logger = logging.getLogger("azamlabs.engine")


class LabLifecycleEngine:
    """Master controller managing the lifecycle of virtual labs and devices."""

    def __init__(self):
        self.scheduler = AntiBootstormScheduler()
        self.eco_governor = EcoModeGovernor()

    def create_lab(self, topology: AzamTopology) -> AzamTopology:
        """Stores a new topology in the persistent database."""
        db.save_topology(topology)
        logger.info(f"Created lab '{topology.name}' (ID: {topology.id}) with {len(topology.nodes)} nodes.")
        return topology

    def get_lab(self, lab_id: str) -> Optional[AzamTopology]:
        """Retrieves an existing lab topology with live node statuses by ID or exact name."""
        topo = db.get_topology(lab_id)
        if topo:
            return topo
        for item in db.list_topologies():
            if item.get("name") == lab_id or item.get("id") == lab_id:
                return db.get_topology(item["id"])
        return None

    def list_labs(self) -> List[Dict[str, Any]]:
        """Returns summary list of all available labs."""
        return db.list_topologies()

    async def delete_lab(self, lab_id: str) -> bool:
        """Stops any running nodes and deletes lab from database."""
        await self.stop_all_nodes(lab_id)
        return db.delete_topology(lab_id)

    async def start_node(self, lab_id: str, node_id_or_name: str) -> bool:
        """Starts a specific node within a lab using its registered driver."""
        topo = db.get_topology(lab_id)
        if not topo:
            raise ValueError(f"Lab '{lab_id}' not found.")
        node = topo.get_node(node_id_or_name)
        if not node:
            raise ValueError(f"Node '{node_id_or_name}' not found in lab.")

        db.update_node_status(lab_id, node.id, NodeStatus.STARTING)
        logger.info(f"Booting node '{node.name}' ({node.driver.value}) in lab '{topo.name}'...")

        driver = DriverFactory.get_driver(node.driver)
        pid = await driver.start_node(node, lab_id)

        # Update to running
        db.update_node_status(lab_id, node.id, NodeStatus.RUNNING, pid=pid, console_port=node.console_port)
        self.eco_governor.record_activity(node.id)
        return True

    async def stop_node(self, lab_id: str, node_id_or_name: str) -> bool:
        """Stops a specific node within a lab."""
        topo = db.get_topology(lab_id)
        if not topo:
            raise ValueError(f"Lab '{lab_id}' not found.")
        node = topo.get_node(node_id_or_name)
        if not node:
            raise ValueError(f"Node '{node_id_or_name}' not found in lab.")

        db.update_node_status(lab_id, node.id, NodeStatus.STOPPING)
        logger.info(f"Stopping node '{node.name}' in lab '{topo.name}'...")

        driver = DriverFactory.get_driver(node.driver)
        await driver.stop_node(node, lab_id)

        db.update_node_status(lab_id, node.id, NodeStatus.STOPPED)
        cpu_governor.unregister_node(node.id)
        return True

    async def start_all_nodes(self, lab_id: str) -> Dict[str, bool]:
        """Starts all nodes in lab using anti-bootstorm staggered scheduling and establishes fabric."""
        topo = db.get_topology(lab_id)
        if not topo:
            raise ValueError(f"Lab '{lab_id}' not found.")

        # 1. Engage Anti-DHCP leak sandbox if management networks are declared
        for net in topo.networks:
            if net.net_type == "mgmt":
                await sandbox.apply_sandbox(net.bridge_name or "azam0")

        # 2. Wire virtual dataplane links
        for link in topo.links:
            await fabric.connect_link(link, lab_id)

        async def _boot_callback(node: AzamNode) -> bool:
            return await self.start_node(lab_id, node.id)

        async def _on_progress(node: AzamNode, status: NodeStatus) -> None:
            db.update_node_status(lab_id, node.id, status)

        # 3. Enable KSM memory deduplication before bulk launch
        KsmManager.enable_proactive_deduplication()

        results = await self.scheduler.execute_staggered_startup(
            nodes=topo.nodes,
            boot_callback=_boot_callback,
            on_progress=_on_progress
        )
        return results

    async def stop_all_nodes(self, lab_id: str) -> Dict[str, bool]:
        """Gracefully stops all nodes in a lab and tears down links."""
        topo = db.get_topology(lab_id)
        if not topo:
            return {}

        results = {}
        for node in topo.nodes:
            results[node.id] = await self.stop_node(lab_id, node.id)

        for link in topo.links:
            await fabric.disconnect_link(link, lab_id)

        return results

    async def wipe_all_nodes(self, lab_id: str) -> bool:
        """Stops all nodes and resets ephemeral overlays back to Day-0 state."""
        await self.stop_all_nodes(lab_id)
        topo = db.get_topology(lab_id)
        if topo:
            for node in topo.nodes:
                driver = DriverFactory.get_driver(node.driver)
                await driver.wipe_node(node, lab_id)
                node.running_config = None
                db.update_node_status(lab_id, node.id, NodeStatus.STOPPED)
        return True

    def get_lab_status(self, lab_id: str) -> Dict[str, Any]:
        """Returns comprehensive real-time status and telemetry for a lab."""
        topo = db.get_topology(lab_id)
        if not topo:
            raise ValueError(f"Lab '{lab_id}' not found.")

        total_nodes = len(topo.nodes)
        running_nodes = sum(1 for n in topo.nodes if n.status == NodeStatus.RUNNING)
        ksm_stats = KsmManager.get_telemetry()
        cpu_stats = cpu_governor.get_status()

        return {
            "lab_id": topo.id,
            "name": topo.name,
            "total_nodes": total_nodes,
            "running_nodes": running_nodes,
            "stopped_nodes": total_nodes - running_nodes,
            "ksm_deduplication": ksm_stats,
            "cpu_governor": cpu_stats,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "device_type": n.device_type.value,
                    "driver": n.driver.value,
                    "status": n.status.value,
                    "console_port": n.console_port,
                    "console_type": n.console_type,
                    "interfaces_count": len(n.interfaces)
                }
                for n in topo.nodes
            ]
        }


# Global Engine Instance
engine = LabLifecycleEngine()
