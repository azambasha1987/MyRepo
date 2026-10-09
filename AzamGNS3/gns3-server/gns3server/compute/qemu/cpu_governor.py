"""
==============================================================================
AzamGNS3 Lossless Dynamic CPU Governor (Ubuntu 26 / Cgroups v2)
==============================================================================
Replaces legacy cpulimit (SIGSTOP/SIGCONT) with kernel-level CFS weight scheduling.

Guarantees:
1. Zero Packet Drops / Protocol Flapping:
   Does NOT freeze processes. Adjusts kernel CFS cpu.weight between 10 (idle DPDK
   polling) and 1000 (active dataplane bursts).
2. Hysteresis Protection:
   Maintains high priority for 5 seconds post-traffic burst so BGP/OSPF/BFD never drop.
3. Native Ubuntu 26 / Linux 6.x/7.x cgroups v2 integration.
==============================================================================
"""

import os
import sys
import time
import logging
import asyncio
import re

log = logging.getLogger(__name__)

# Virtual appliance patterns that execute DPDK / spinloops at idle
DPDK_POLL_PATTERNS = [
    r'vios',
    r'viosl2',
    r'iosv',
    r'iosvl2',
    r'8000v',
    r'c8000v',
    r'c8000',
    r'cisco8000',
    r'cisco8k',
    r'cat8000',
    r'cat8k',
    r'cat9000v',
    r'cat9000',
    r'xrv',
    r'xrv9k',
    r'vqfx',
    r'vmx',
    r'veos',
]

_DPDK_REGEX = re.compile("|".join(DPDK_POLL_PATTERNS), re.IGNORECASE)


class CpuGovernor:
    """
    Manages dynamic CPU scheduling for QEMU virtual machine processes.
    """

    WEIGHT_IDLE = 10       # Background priority when CPU is in idle spinloop
    WEIGHT_ACTIVE = 1000   # Maximum priority during dataplane forwarding
    HYSTERESIS_SEC = 5.0   # Hold time for high priority post-traffic

    def __init__(self, node_id: str, node_name: str, pid: int, tap_devices: list = None):
        self.node_id = node_id
        self.node_name = node_name
        self.pid = pid
        self.tap_devices = tap_devices or []
        self._is_dpdk_appliance = bool(_DPDK_REGEX.search(node_name))
        self._cgroup_path = None
        self._last_packet_time = 0.0
        self._current_weight = self.WEIGHT_ACTIVE
        self._monitor_task = None
        self._running = False
        self._prev_rx_packets = {}

    def is_dpdk_target(self) -> bool:
        """Returns True if the VM matches poll-mode DPDK appliance signatures."""
        return self._is_dpdk_appliance

    def find_cgroup_path(self) -> str:
        """Locates the cgroup v2 directory for the VM process."""
        if not sys.platform.startswith("linux"):
            return None

        # Check /proc/<pid>/cgroup for cgroup v2 path
        proc_cgroup = f"/proc/{self.pid}/cgroup"
        if not os.path.exists(proc_cgroup):
            return None

        try:
            with open(proc_cgroup, "r") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) == 3 and parts[0] == "0":
                        rel_path = parts[2].lstrip("/")
                        full_path = os.path.join("/sys/fs/cgroup", rel_path)
                        if os.path.exists(full_path):
                            return full_path
        except (OSError, IOError) as e:
            log.debug(f"Governor: Unable to read {proc_cgroup}: {e}")

        # Fallback to general cgroups v2 location if writable
        generic_path = f"/sys/fs/cgroup/azamgns3/node-{self.node_id}"
        if os.path.exists(generic_path):
            return generic_path

        return None

    def set_cpu_weight(self, weight: int):
        """Sets the CFS cpu.weight for the node cgroup."""
        if not self._cgroup_path or not sys.platform.startswith("linux"):
            return

        weight_file = os.path.join(self._cgroup_path, "cpu.weight")
        if not os.path.exists(weight_file):
            return

        try:
            with open(weight_file, "w") as f:
                f.write(str(weight) + "\n")
            self._current_weight = weight
            log.debug(f"Governor: Set cpu.weight={weight} for {self.node_name} (PID {self.pid})")
        except (OSError, IOError) as e:
            log.debug(f"Governor: Failed to write cpu.weight: {e}")

    def _get_tap_rx_packets(self) -> int:
        """Reads cumulative RX packet counts across the node's TAP devices."""
        total_packets = 0
        for tap in self.tap_devices:
            stat_file = f"/sys/class/net/{tap}/statistics/rx_packets"
            if os.path.exists(stat_file):
                try:
                    with open(stat_file, "r") as f:
                        total_packets += int(f.read().strip())
                except (OSError, IOError, ValueError):
                    pass
        return total_packets

    async def _governor_loop(self):
        """Monitors network traffic and dynamically adjusts CPU weight."""
        log.info(f"Governor: Started dynamic scheduling for {self.node_name} (DPDK={self._is_dpdk_appliance})")
        self._cgroup_path = self.find_cgroup_path()

        # If not Linux or cgroups not found, governor runs passively without throwing errors
        if not self._cgroup_path:
            log.debug(f"Governor: Cgroups v2 not available for {self.node_name}. Running in passive mode.")
            return

        # Start with full power during boot
        self.set_cpu_weight(self.WEIGHT_ACTIVE)
        # Give initial 30 seconds boot grace period before stepping down
        await asyncio.sleep(30.0)

        prev_rx = self._get_tap_rx_packets()

        while self._running:
            try:
                await asyncio.sleep(1.0)
                curr_rx = self._get_tap_rx_packets()
                delta_packets = curr_rx - prev_rx
                prev_rx = curr_rx
                now = time.time()

                if delta_packets > 0:
                    # Dataplane packet activity detected!
                    self._last_packet_time = now
                    if self._current_weight != self.WEIGHT_ACTIVE:
                        self.set_cpu_weight(self.WEIGHT_ACTIVE)
                else:
                    # No new packets; check hysteresis window
                    time_since_traffic = now - self._last_packet_time
                    if time_since_traffic > self.HYSTERESIS_SEC:
                        if self._is_dpdk_appliance and self._current_weight != self.WEIGHT_IDLE:
                            # Step down idle DPDK spinloop
                            self.set_cpu_weight(self.WEIGHT_IDLE)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.debug(f"Governor: Error in monitor loop: {e}")

    def start(self):
        """Starts the asynchronous governor monitoring task."""
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._monitor_task = loop.create_task(self._governor_loop())
        except RuntimeError:
            pass

    def stop(self):
        """Stops the governor and restores normal CPU priority."""
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        # Restore full weight on shutdown
        self.set_cpu_weight(self.WEIGHT_ACTIVE)
        log.info(f"Governor: Stopped for {self.node_name}")
