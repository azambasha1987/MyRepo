"""
AzamLabs Flow-Controlled Bulk Configuration Paster
Prevents CLI buffer overruns and dropped characters when injecting massive multi-vendor
configurations into router and switch terminals.
"""

import re
import asyncio
from typing import Dict, Any, List, Optional, Callable
import logging

logger = logging.getLogger("azamlabs.paster")


class FlowControlledPaster:
    """Injects multi-line configurations with line pacing, prompt acknowledgment, and syntax error detection."""

    ERROR_PATTERNS = [
        re.compile(r"%\s*Invalid input detected", re.IGNORECASE),
        re.compile(r"%\s*Incomplete command", re.IGNORECASE),
        re.compile(r"%\s*Ambiguous command", re.IGNORECASE),
        re.compile(r"%\s*Error", re.IGNORECASE),
        re.compile(r"%\s*Bad IP address", re.IGNORECASE),
        re.compile(r"Syntax error:", re.IGNORECASE),
        re.compile(r"unknown command", re.IGNORECASE),
        re.compile(r"error:\s*syntax error", re.IGNORECASE),
    ]

    @classmethod
    def check_for_errors(cls, response: str) -> Optional[str]:
        """Checks if a terminal response contains known CLI syntax error signatures."""
        for pattern in cls.ERROR_PATTERNS:
            match = pattern.search(response)
            if match:
                return match.group(0)
        return None

    @classmethod
    async def paste_configuration(
        cls,
        host: str,
        port: int,
        config_text: str,
        inter_line_delay_ms: int = 50,
        stop_on_error: bool = False,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Paces configuration lines into a serial/Telnet socket with syntax feedback."""
        lines = [l for l in config_text.splitlines() if l.strip() and not l.strip().startswith("!")]
        total_lines = len(lines)

        results: Dict[str, Any] = {
            "total_lines": total_lines,
            "applied_lines": 0,
            "success": True,
            "errors": [],
            "log": [],
        }

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
        except Exception as e:
            results["success"] = False
            results["errors"].append({"line_number": 0, "command": "CONNECT", "error": str(e)})
            return results

        try:
            # Wake terminal prompt
            writer.write(b"\r\n")
            await writer.drain()
            await asyncio.sleep(0.1)

            # Drain any initial greeting or prompt
            try:
                await asyncio.wait_for(reader.read(1024), timeout=0.2)
            except asyncio.TimeoutError:
                pass

            delay_sec = max(0.01, inter_line_delay_ms / 1000.0)

            for idx, line in enumerate(lines, start=1):
                clean_line = line.strip()
                writer.write(f"{clean_line}\r\n".encode("utf-8"))
                await writer.drain()

                # Read line response
                response = ""
                try:
                    chunk = await asyncio.wait_for(reader.read(2048), timeout=0.3)
                    if chunk:
                        response = chunk.decode("utf-8", errors="replace")
                except asyncio.TimeoutError:
                    pass

                results["applied_lines"] = idx
                results["log"].append({"line": idx, "cmd": clean_line, "output": response})

                err = cls.check_for_errors(response)
                if err:
                    results["errors"].append({
                        "line_number": idx,
                        "command": clean_line,
                        "error_signature": err,
                        "output": response.strip(),
                    })
                    if stop_on_error:
                        results["success"] = False
                        logger.warning(f"Flow Paster halted on line {idx}: {err}")
                        break

                await asyncio.sleep(delay_sec)

            if results["errors"]:
                results["success"] = False

            writer.close()
            await writer.wait_closed()
        except Exception as e:
            try:
                writer.close()
            except Exception:
                pass
            results["success"] = False
            results["errors"].append({"line_number": results["applied_lines"], "command": "STREAM", "error": str(e)})

        return results


# Global Flow Paster Instance
flow_paster = FlowControlledPaster()
