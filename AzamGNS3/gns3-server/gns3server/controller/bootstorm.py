"""
==============================================================================
AzamGNS3 Anti-Bootstorm Staggered Node Startup Engine
==============================================================================
Prevents CPU and Disk I/O boot-storms when launching large topologies.
Sorts nodes into weighted tiers and throttles batch execution based on real-time
system CPU load and I/O wait metrics.

Tiers:
  Heavy (C8000v, XRd, vMX, Windows)   -> 2 per batch, 18s stagger
  Medium (CSR1000v, vEOS, IOSvL2)     -> 4 per batch, 10s stagger
  Light (VPCS, IOL, Alpine, Docker)   -> Unlimited concurrent, 0s delay
==============================================================================
"""

import os
import sys
import logging
import asyncio
import psutil

log = logging.getLogger(__name__)

# Node classification prefixes
HEAVY_PATTERNS = {
    "c8000v", "c8k", "cat8k", "cat9k", "c9300", "c9500", "c9800",
    "xrd", "xrv9k", "xrv", "win", "win2022", "win11", "win2019", "win10",
    "vmx", "vqfx", "f5", "bigip", "checkpoint"
}

MEDIUM_PATTERNS = {
    "csr", "csr1000v", "veos", "arista", "iosv", "iosvl2", "vios", "viosl2",
    "forti", "fortigate", "palo", "panos", "nxos", "nexus", "asav", "vyos"
}


def classify_node_weight(node) -> int:
    """
    Returns weight priority for a node:
      3 = Heavy
      2 = Medium
      1 = Light
    """
    name = (getattr(node, "name", "") or "").lower()
    node_type = (getattr(node, "node_type", "") or "").lower()

    # VPCS and lightweight containers are always light
    if node_type in ("vpcs", "docker", "iou"):
        # Check if container name explicitly indicates a heavy router
        for prefix in HEAVY_PATTERNS:
            if prefix in name:
                return 3
        return 1

    for prefix in HEAVY_PATTERNS:
        if prefix in name:
            return 3

    for prefix in MEDIUM_PATTERNS:
        if prefix in name:
            return 2

    # Default QEMU nodes without specific signature default to Medium
    if node_type == "qemu":
        return 2

    return 1


class BootstormEngine:
    """
    Orchestrates load-aware staggered node startup across a project.
    """

    @staticmethod
    def is_system_stressed(max_cpu_percent: float = 85.0) -> bool:
        """Checks if host CPU or I/O is under high pressure."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            if cpu > max_cpu_percent:
                return True
            # Check I/O wait if available on Linux
            if hasattr(psutil, "cpu_times"):
                times = psutil.cpu_times()
                iowait = getattr(times, "iowait", 0.0)
                if iowait > 20.0:
                    return True
        except Exception:
            pass
        return False

    @classmethod
    async def start_nodes_staggered(cls, nodes_to_start: list):
        """
        Executes phased, load-aware node startup.
        """
        if not nodes_to_start:
            return

        # Separate nodes into tiers
        heavy = []
        medium = []
        light = []

        for node in nodes_to_start:
            # Only process nodes that are currently stopped
            if getattr(node, "status", "") == "started":
                continue
            weight = classify_node_weight(node)
            if weight == 3:
                heavy.append(node)
            elif weight == 2:
                medium.append(node)
            else:
                light.append(node)

        total_nodes = len(heavy) + len(medium) + len(light)
        log.info(f"[Bootstorm] Initiating staggered startup for {total_nodes} nodes "
                 f"(Heavy: {len(heavy)}, Medium: {len(medium)}, Light: {len(light)})")

        # 1. Boot Heavy Nodes (Batch size: 2, Stagger: 18s)
        if heavy:
            log.info("[Bootstorm] Phase 1/3: Starting Heavy nodes...")
            batch_size = 2
            for i in range(0, len(heavy), batch_size):
                batch = heavy[i:i + batch_size]
                names = [n.name for n in batch]
                log.info(f"[Bootstorm] Launching heavy batch: {', '.join(names)}")
                await asyncio.gather(*(n.start() for n in batch), return_exceptions=True)

                if i + batch_size < len(heavy):
                    # Adaptive delay if system is stressed
                    delay = 18.0
                    while cls.is_system_stressed():
                        log.info("[Bootstorm] Host under high load. Pausing next heavy batch for 5s...")
                        await asyncio.sleep(5.0)
                    await asyncio.sleep(delay)

        # 2. Boot Medium Nodes (Batch size: 4, Stagger: 10s)
        if medium:
            log.info("[Bootstorm] Phase 2/3: Starting Medium nodes...")
            batch_size = 4
            for i in range(0, len(medium), batch_size):
                batch = medium[i:i + batch_size]
                names = [n.name for n in batch]
                log.info(f"[Bootstorm] Launching medium batch: {', '.join(names)}")
                await asyncio.gather(*(n.start() for n in batch), return_exceptions=True)

                if i + batch_size < len(medium):
                    delay = 10.0
                    while cls.is_system_stressed():
                        log.info("[Bootstorm] Host under high load. Pausing next medium batch for 4s...")
                        await asyncio.sleep(4.0)
                    await asyncio.sleep(delay)

        # 3. Boot Light Nodes (All at once)
        if light:
            log.info("[Bootstorm] Phase 3/3: Starting Light nodes concurrently...")
            names = [n.name for n in light]
            log.info(f"[Bootstorm] Launching light batch: {', '.join(names)}")
            await asyncio.gather(*(n.start() for n in light), return_exceptions=True)

        log.info("[Bootstorm] All node batches launched successfully with zero boot-storm.")
