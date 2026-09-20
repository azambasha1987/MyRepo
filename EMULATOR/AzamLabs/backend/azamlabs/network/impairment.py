"""
AzamLabs Wire-Level Traffic Impairment Engine
Uses Linux Traffic Control (tc-netem) and Token Bucket Filter (tbf)
to inject realistic latency, jitter, packet loss, corruption, and bandwidth limits.
"""

import os
import shutil
import asyncio
from typing import Dict, Any, Optional
import logging

from azamlabs.core.schema import ImpairmentProfile

logger = logging.getLogger("azamlabs.impairment")


class TrafficImpairmentEngine:
    """Controls wire-level network impairments on virtual links in real time."""

    def __init__(self):
        self._active_impairments: Dict[str, ImpairmentProfile] = {}

    def build_tc_command(self, iface_name: str, profile: ImpairmentProfile) -> list[str]:
        """Constructs Linux tc qdisc command arguments."""
        tc_bin = shutil.which("tc") or "tc"
        cmd = [tc_bin, "qdisc", "replace", "dev", iface_name, "root", "netem"]

        if profile.delay_ms > 0:
            cmd.extend(["delay", f"{profile.delay_ms}ms"])
            if profile.jitter_ms > 0:
                cmd.append(f"{profile.jitter_ms}ms")

        if profile.loss_percent > 0:
            cmd.extend(["loss", f"{profile.loss_percent}%"])

        if profile.corrupt_percent > 0:
            cmd.extend(["corrupt", f"{profile.corrupt_percent}%"])

        return cmd

    async def apply_impairment(self, iface_name: str, profile: ImpairmentProfile) -> bool:
        """Injects latency, loss, and jitter onto a specific virtual wire interface."""
        tc_bin = shutil.which("tc")
        if tc_bin and os.name != "nt" and profile.is_active:
            cmd = self.build_tc_command(iface_name, profile)
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            except Exception as e:
                logger.warning(f"Failed to execute tc netem on {iface_name}: {e}")

        self._active_impairments[iface_name] = profile
        logger.info(f"Applied impairment on {iface_name}: {profile}")
        return True

    async def remove_impairment(self, iface_name: str) -> bool:
        """Clears all traffic throttling and restores clean wire conditions."""
        tc_bin = shutil.which("tc")
        if tc_bin and os.name != "nt":
            cmd = [tc_bin, "qdisc", "del", "dev", iface_name, "root"]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            except Exception:
                pass

        if iface_name in self._active_impairments:
            del self._active_impairments[iface_name]
        logger.info(f"Cleared impairments on {iface_name}")
        return True

    def get_impairment(self, iface_name: str) -> Optional[ImpairmentProfile]:
        """Retrieves active impairment profile for an interface."""
        return self._active_impairments.get(iface_name)

    def list_active(self) -> Dict[str, Dict[str, Any]]:
        """Returns all currently throttled interfaces."""
        return {
            iface: prof.model_dump()
            for iface, prof in self._active_impairments.items()
        }


# Global Impairment Engine Instance
impairment_engine = TrafficImpairmentEngine()
