"""
AzamLabs Anti-Bootstorm Scheduler & Eco-Mode Engine
Prevents CPU/disk saturation during mass node startup by staggering boot sequences
and manages Eco-Mode intelligent auto-suspension for idle nodes.
"""

import asyncio
import logging
from typing import List, Callable, Awaitable, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from azamlabs.config import settings
from azamlabs.core.schema import AzamNode, NodeStatus, DeviceType

logger = logging.getLogger("azamlabs.scheduler")


class BootTier:
    """Classifies nodes into optimal boot ordering tiers."""
    INFRASTRUCTURE = 1   # Switches, bridges, controllers
    CORE_ROUTING = 2     # BGP/OSPF core routers
    SECURITY_EDGE = 3    # Firewalls, edge routers, transits
    WORKLOADS = 4        # Hosts, containers, servers, attackers

    @classmethod
    def classify(cls, node: AzamNode) -> int:
        if node.device_type == DeviceType.SWITCH:
            return cls.INFRASTRUCTURE
        elif node.device_type == DeviceType.ROUTER:
            return cls.CORE_ROUTING
        elif node.device_type == DeviceType.FIREWALL:
            return cls.SECURITY_EDGE
        else:
            return cls.WORKLOADS


class AntiBootstormScheduler:
    """Manages staggered, prioritized node startups to eliminate bootstorms."""

    def __init__(
        self,
        stagger_delay: float = settings.STAGGER_DELAY_SECONDS,
        max_concurrent_boots: int = settings.MAX_CONCURRENT_BOOTS,
    ):
        self.stagger_delay = stagger_delay
        self.max_concurrent_boots = max_concurrent_boots
        self._boot_semaphore = asyncio.Semaphore(max_concurrent_boots)
        self._active_boots: Dict[str, asyncio.Task] = {}

    def plan_boot_sequence(self, nodes: List[AzamNode]) -> List[AzamNode]:
        """Sorts nodes by tier and hardware weight (heavy nodes booted deliberately)."""
        return sorted(
            nodes,
            key=lambda n: (BootTier.classify(n), -(n.ram_mb or 1024), n.name.lower())
        )

    async def execute_staggered_startup(
        self,
        nodes: List[AzamNode],
        boot_callback: Callable[[AzamNode], Awaitable[bool]],
        on_progress: Optional[Callable[[AzamNode, NodeStatus], Awaitable[None]]] = None
    ) -> Dict[str, bool]:
        """Executes staggered node boots with controlled concurrency and delay."""
        ordered_nodes = self.plan_boot_sequence(nodes)
        results: Dict[str, bool] = {}

        async def _boot_single_node(node: AzamNode):
            async with self._boot_semaphore:
                if on_progress:
                    await on_progress(node, NodeStatus.STARTING)
                success = await boot_callback(node)
                results[node.id] = success
                if on_progress:
                    status = NodeStatus.RUNNING if success else NodeStatus.ERROR
                    await on_progress(node, status)
                # Stagger next boot to let disk I/O settle
                await asyncio.sleep(self.stagger_delay)

        tasks = []
        for node in ordered_nodes:
            task = asyncio.create_task(_boot_single_node(node))
            tasks.append(task)
            # Brief launch delay between dispatching queued tasks
            await asyncio.sleep(0.2)

        await asyncio.gather(*tasks, return_exceptions=True)
        return results


class EcoModeGovernor:
    """Monitors lab activity and suspends idle nodes to reclaim 100% CPU."""

    def __init__(self, timeout_minutes: int = settings.ECO_MODE_IDLE_TIMEOUT_MINUTES):
        self.timeout_minutes = timeout_minutes
        self.node_last_active: Dict[str, datetime] = {}

    def record_activity(self, node_id: str) -> None:
        """Records timestamp of terminal keystroke or packet transit."""
        self.node_last_active[node_id] = datetime.now(timezone.utc)

    def is_idle(self, node_id: str) -> bool:
        """Checks if a node has exceeded the idle threshold."""
        if not settings.ECO_MODE_ENABLED:
            return False
        last_active = self.node_last_active.get(node_id)
        if not last_active:
            return False
        idle_duration = datetime.now(timezone.utc) - last_active
        return idle_duration > timedelta(minutes=self.timeout_minutes)
