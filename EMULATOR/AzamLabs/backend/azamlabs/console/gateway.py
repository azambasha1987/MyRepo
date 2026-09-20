"""
AzamLabs Multi-Protocol Console Gateway
Provides bi-directional bridging between WebSocket connections (for xterm.js Web Terminal)
and local device serial/Telnet TCP sockets.
"""

import asyncio
from typing import Dict, Any, Optional
import logging

from fastapi import WebSocket, WebSocketDisconnect
from azamlabs.core.database import db
from azamlabs.core.schema import NodeStatus

logger = logging.getLogger("azamlabs.console")


class ConsoleGateway:
    """Bridges browser WebSockets to device TCP serial/telnet console sockets."""

    @classmethod
    async def bridge_websocket_to_tcp(
        cls,
        websocket: WebSocket,
        lab_id: str,
        node_id_or_name: str
    ) -> None:
        """Handles bi-directional communication between xterm.js WebSocket and device serial console."""
        await websocket.accept()

        topo = db.get_topology(lab_id)
        if not topo:
            await websocket.send_text(f"\r\n\x1b[31m[AzamLabs] Lab '{lab_id}' not found.\x1b[0m\r\n")
            await websocket.close()
            return

        node = topo.get_node(node_id_or_name)
        if not node:
            await websocket.send_text(f"\r\n\x1b[31m[AzamLabs] Node '{node_id_or_name}' not found.\x1b[0m\r\n")
            await websocket.close()
            return

        if node.status != NodeStatus.RUNNING or not node.console_port:
            await websocket.send_text(
                f"\r\n\x1b[33m[AzamLabs] Node '{node.name}' is currently {node.status.value.upper()}.\r\n"
                f"Start the node from the Studio canvas to access its interactive console.\x1b[0m\r\n"
            )
            # Keep socket open and wait or close
            await asyncio.sleep(1.0)
            return

        host = "127.0.0.1"
        port = node.console_port

        await websocket.send_text(
            f"\r\n\x1b[36m[AzamLabs Console Gateway] Connecting to {node.name} on port {port}...\x1b[0m\r\n"
        )

        tcp_reader = None
        tcp_writer = None
        # Attempt connection with retries (if node is booting)
        for attempt in range(5):
            try:
                tcp_reader, tcp_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=2.0
                )
                break
            except Exception:
                await asyncio.sleep(0.5)

        if not tcp_writer:
            await websocket.send_text(
                f"\r\n\x1b[33m[AzamLabs] Console port {port} is not responding yet. Node might still be booting.\x1b[0m\r\n"
            )
            return

        await websocket.send_text(
            f"\x1b[32m[AzamLabs] Connected to {node.name} console ({node.console_type.upper()}).\x1b[0m\r\n\r\n"
        )

        # Forwarders
        async def forward_tcp_to_ws():
            try:
                while True:
                    data = await tcp_reader.read(4096)
                    if not data:
                        break
                    # Send decoded text or bytes
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
            except (asyncio.CancelledError, WebSocketDisconnect):
                pass
            except Exception as e:
                logger.debug(f"TCP to WS stream closed: {e}")

        async def forward_ws_to_tcp():
            try:
                while True:
                    msg = await websocket.receive_text()
                    tcp_writer.write(msg.encode("utf-8"))
                    await tcp_writer.drain()
            except (asyncio.CancelledError, WebSocketDisconnect):
                pass
            except Exception as e:
                logger.debug(f"WS to TCP stream closed: {e}")

        task_tcp_to_ws = asyncio.create_task(forward_tcp_to_ws())
        task_ws_to_tcp = asyncio.create_task(forward_ws_to_tcp())

        done, pending = await asyncio.wait(
            [task_tcp_to_ws, task_ws_to_tcp],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        try:
            tcp_writer.close()
            await tcp_writer.wait_closed()
        except Exception:
            pass

    @classmethod
    async def send_command_to_node(
        cls,
        port: int,
        command: str,
        timeout: float = 3.0,
        host: str = "127.0.0.1"
    ) -> str:
        """Sends a single CLI command over Telnet/serial socket and returns the response."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
        except Exception as e:
            return f"Error: Unable to connect to console port {port}: {e}"

        try:
            # Wake up prompt with newline
            writer.write(b"\r\n")
            await writer.drain()
            await asyncio.sleep(0.1)

            # Send command
            writer.write(f"{command}\r\n".encode("utf-8"))
            await writer.drain()

            output = []
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    chunk = await asyncio.wait_for(reader.read(2048), timeout=0.5)
                    if not chunk:
                        break
                    output.append(chunk.decode("utf-8", errors="replace"))
                except asyncio.TimeoutError:
                    if output:
                        break

            writer.close()
            await writer.wait_closed()
            return "".join(output)
        except Exception as e:
            try:
                writer.close()
            except Exception:
                pass
            return f"Error executing command: {e}"


# Global Gateway Instance
gateway = ConsoleGateway()
