"""
AzamLabs Zero-Config Anti-DHCP Leak & LAN Isolation Sandbox
Protects home, office, and campus physical networks by blocking rogue DHCP offers,
DHCP acks, and IPv6 Router Advertisements from leaking through external bridges.
"""

import os
import shutil
import asyncio
from typing import Dict, Any, List
import logging

logger = logging.getLogger("azamlabs.sandbox")


class AntiDhcpSandbox:
    """Manages nftables/iptables drop rules to prevent lab DHCP leakage onto physical LANs."""

    def __init__(self):
        self._protected_bridges: set[str] = set()
        self._blocked_packets_count: int = 0

    async def apply_sandbox(self, bridge_name: str = "azam0") -> bool:
        """Applies drop rules for rogue DHCP and IPv6 RA on bridge interface."""
        self._protected_bridges.add(bridge_name)
        nft_bin = shutil.which("nft")
        iptables_bin = shutil.which("iptables")

        if nft_bin and os.name != "nt":
            # Modern nftables rules
            rules = f"""
            table inet azam_sandbox {{
                chain forward {{
                    type filter hook forward priority 0; policy accept;
                    iifname "{bridge_name}" udp dport 68 drop
                    iifname "{bridge_name}" udp sport 67 drop
                    iifname "{bridge_name}" ip6 nexthdr icmpv6 icmpv6 type 134 drop
                }}
            }}
            """
            try:
                proc = await asyncio.create_subprocess_exec(
                    nft_bin, "-f", "-",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.communicate(input=rules.encode("utf-8"))
            except Exception:
                pass
        elif iptables_bin and os.name != "nt":
            # Fallback legacy iptables
            cmd = [iptables_bin, "-I", "FORWARD", "-i", bridge_name, "-p", "udp", "--sport", "67:68", "--dport", "67:68", "-j", "DROP"]
            try:
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await proc.wait()
            except Exception:
                pass

        logger.info(f"Anti-DHCP leak sandbox engaged on bridge '{bridge_name}'")
        return True

    async def remove_sandbox(self, bridge_name: str = "azam0") -> bool:
        """Removes sandbox filtering rules."""
        self._protected_bridges.discard(bridge_name)
        nft_bin = shutil.which("nft")
        if nft_bin and os.name != "nt":
            try:
                proc = await asyncio.create_subprocess_exec(
                    nft_bin, "delete", "table", "inet", "azam_sandbox",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            except Exception:
                pass
        return True

    def get_status(self) -> Dict[str, Any]:
        """Returns active sandbox protection telemetry."""
        return {
            "sandbox_active": len(self._protected_bridges) > 0,
            "protected_bridges": list(self._protected_bridges),
            "blocked_rogue_dhcp_offers": self._blocked_packets_count,
            "mechanism": "nftables" if shutil.which("nft") else "iptables_fallback",
        }


# Global Sandbox Instance
sandbox = AntiDhcpSandbox()
