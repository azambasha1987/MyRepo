"""
AzamLabs Live Packet Capture Engine
Runs non-intrusive wire-level tcpdump packet sniffers, produces standard .pcap captures,
and streams real-time packet headers directly to the in-browser Web Wireshark interface.
"""

import os
import struct
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from azamlabs.config import settings

logger = logging.getLogger("azamlabs.capture")


class PacketCaptureManager:
    """Manages active tcpdump sniffer processes and PCAP file generation."""

    def __init__(self):
        self._active_captures: Dict[str, Dict[str, Any]] = {}
        self.pcap_dir = settings.DATA_DIR / "captures"
        self.pcap_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_pcap_header() -> bytes:
        """Generates standard Libpcap 24-byte Global File Header (Ethernet DLT=1)."""
        # magic (0xa1b2c3d4), ver_major (2), ver_minor (4), thiszone (0), sigfigs (0), snaplen (65535), network (1)
        return struct.pack("!IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)

    async def start_capture(self, lab_id: str, link_id: str, iface_name: str) -> str:
        """Starts a live packet sniffer on a specified interface or virtual wire."""
        capture_id = f"cap_{lab_id[:6]}_{link_id[:6]}"
        pcap_file = self.pcap_dir / f"{capture_id}.pcap"

        # Initialize file with standard PCAP header
        pcap_file.write_bytes(self.create_pcap_header())

        tcpdump_bin = shutil.which("tcpdump")
        proc = None

        if tcpdump_bin and os.name != "nt":
            cmd = [
                tcpdump_bin, "-i", iface_name,
                "-s", "0",
                "-U",
                "-w", str(pcap_file.resolve()),
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except Exception as e:
                logger.warning(f"tcpdump failed to start on {iface_name}: {e}")

        self._active_captures[capture_id] = {
            "capture_id": capture_id,
            "lab_id": lab_id,
            "link_id": link_id,
            "interface": iface_name,
            "pcap_file": pcap_file,
            "proc": proc,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "capturing",
        }
        logger.info(f"Started packet capture {capture_id} on {iface_name}")
        return capture_id

    async def stop_capture(self, capture_id: str) -> Optional[Path]:
        """Terminates active sniffer and finalizes the PCAP file."""
        entry = self._active_captures.get(capture_id)
        if not entry:
            return None

        proc = entry.get("proc")
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await proc.wait()
            except Exception:
                pass

        entry["status"] = "stopped"
        entry["stopped_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Stopped packet capture {capture_id}")
        return entry["pcap_file"]

    def get_capture_path(self, capture_id: str) -> Optional[Path]:
        """Returns the filesystem path of the captured PCAP."""
        entry = self._active_captures.get(capture_id)
        if entry and entry["pcap_file"].exists():
            return entry["pcap_file"]
        return None

    def list_captures(self, lab_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns metadata for active and completed captures."""
        results = []
        for cap in self._active_captures.values():
            if lab_id and cap.get("lab_id") != lab_id:
                continue
            pcap = cap["pcap_file"]
            size = pcap.stat().st_size if pcap.exists() else 0
            results.append({
                "capture_id": cap["capture_id"],
                "lab_id": cap["lab_id"],
                "link_id": cap["link_id"],
                "interface": cap["interface"],
                "status": cap["status"],
                "started_at": cap["started_at"],
                "size_bytes": size,
            })
        return results


# Global Packet Capture Manager
capture_manager = PacketCaptureManager()
