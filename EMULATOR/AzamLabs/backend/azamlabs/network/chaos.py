"""
AzamLabs Chaos Engineering & Link Flap Generator
Simulates intermittent physical fiber cuts, dirty optical connections,
and recurring link flapping to validate BGP/OSPF convergence, BFD, and STP resilience.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from azamlabs.core.schema import AzamLink
from azamlabs.network.fabric import fabric

logger = logging.getLogger("azamlabs.chaos")


class ChaosLinkFlapper:
    """Manages background link flap sequences and jitter chaos schedules."""

    def __init__(self):
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_metadata: Dict[str, Dict[str, Any]] = {}

    async def _flap_worker(
        self,
        task_id: str,
        link: AzamLink,
        lab_id: str,
        up_sec: float,
        down_sec: float,
        cycles: int
    ):
        """Asynchronous loop toggling link state between UP and DOWN."""
        try:
            iteration = 0
            while cycles == 0 or iteration < cycles:
                # 1. Bring Down
                await fabric.disconnect_link(link, lab_id)
                self._task_metadata[task_id]["current_state"] = "down"
                self._task_metadata[task_id]["flaps_completed"] = iteration + 1
                logger.info(f"Chaos Flapper [{task_id}]: Link {link.endpoints_display} -> DOWN")
                await asyncio.sleep(down_sec)

                # 2. Bring Up
                await fabric.connect_link(link, lab_id)
                self._task_metadata[task_id]["current_state"] = "up"
                logger.info(f"Chaos Flapper [{task_id}]: Link {link.endpoints_display} -> UP")
                await asyncio.sleep(up_sec)

                iteration += 1

            self._task_metadata[task_id]["status"] = "completed"
        except asyncio.CancelledError:
            # Ensure link is restored to UP when task is cancelled
            await fabric.connect_link(link, lab_id)
            self._task_metadata[task_id]["status"] = "cancelled"
            logger.info(f"Chaos Flapper [{task_id}] cancelled, link restored to UP.")

    def start_flap(
        self,
        link: AzamLink,
        lab_id: str,
        up_sec: float = 10.0,
        down_sec: float = 5.0,
        cycles: int = 5
    ) -> str:
        """Schedules automated link flapping."""
        task_id = f"chaos_{link.id[:6]}"
        if task_id in self._active_tasks and not self._active_tasks[task_id].done():
            self._active_tasks[task_id].cancel()

        self._task_metadata[task_id] = {
            "task_id": task_id,
            "link_id": link.id,
            "endpoints": link.endpoints_display,
            "up_sec": up_sec,
            "down_sec": down_sec,
            "target_cycles": cycles,
            "flaps_completed": 0,
            "status": "running",
            "current_state": "up",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        task = asyncio.create_task(
            self._flap_worker(task_id, link, lab_id, up_sec, down_sec, cycles)
        )
        self._active_tasks[task_id] = task
        return task_id

    def stop_flap(self, task_id: str) -> bool:
        """Cancels an ongoing link flap cycle."""
        task = self._active_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def list_active(self) -> List[Dict[str, Any]]:
        """Returns metadata for all chaos schedules."""
        return list(self._task_metadata.values())


# Global Chaos Flapper Instance
chaos_flapper = ChaosLinkFlapper()
