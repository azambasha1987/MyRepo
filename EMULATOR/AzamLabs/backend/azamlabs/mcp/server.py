"""
AzamLabs Model Context Protocol (MCP) Server
Implements standard JSON-RPC 2.0 MCP interface, exposing lab lifecycles, CLI execution,
traffic impairments, and real-time telemetry to external AI agents (Claude, Gemini, Antigravity).
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
import logging

from azamlabs.core.database import db
from azamlabs.core.engine import engine
from azamlabs.core.ksm import KsmManager
from azamlabs.core.governor import cpu_governor
from azamlabs.console.gateway import gateway
from azamlabs.network.impairment import impairment_engine
from azamlabs.core.schema import ImpairmentProfile

logger = logging.getLogger("azamlabs.mcp")


class AzamMcpServer:
    """JSON-RPC 2.0 Model Context Protocol Server."""

    SERVER_INFO = {
        "name": "azamlabs-mcp",
        "version": "1.0.0",
        "protocolVersion": "2024-11-05",
    }

    TOOLS = [
        {
            "name": "azam_list_labs",
            "description": "Lists all available network lab topologies with node counts and running statuses.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "azam_get_lab",
            "description": "Retrieves the full topology graph (nodes, interfaces, links, IP plan) of a specific lab.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "lab_id": {"type": "string", "description": "ID of the lab topology"},
                },
                "required": ["lab_id"],
            },
        },
        {
            "name": "azam_start_node",
            "description": "Boots a specific virtual router, switch, or firewall node.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "lab_id": {"type": "string", "description": "ID of the lab"},
                    "node_id": {"type": "string", "description": "ID or name of the node"},
                },
                "required": ["lab_id", "node_id"],
            },
        },
        {
            "name": "azam_stop_node",
            "description": "Gracefully stops a specific virtual node.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "lab_id": {"type": "string", "description": "ID of the lab"},
                    "node_id": {"type": "string", "description": "ID or name of the node"},
                },
                "required": ["lab_id", "node_id"],
            },
        },
        {
            "name": "azam_send_command",
            "description": "Sends a CLI command (e.g. 'show ip route', 'show interfaces') to a device terminal and returns its output.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "lab_id": {"type": "string", "description": "ID of the lab"},
                    "node_id": {"type": "string", "description": "ID or name of the node"},
                    "command": {"type": "string", "description": "CLI command string to execute"},
                },
                "required": ["lab_id", "node_id", "command"],
            },
        },
        {
            "name": "azam_inject_impairment",
            "description": "Injects real-time latency, jitter, or packet loss onto a virtual link between two nodes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "interface_name": {"type": "string", "description": "Interface identifier (e.g. vth_1234_a)"},
                    "delay_ms": {"type": "number", "description": "One-way delay in milliseconds", "default": 0.0},
                    "jitter_ms": {"type": "number", "description": "Jitter variation in milliseconds", "default": 0.0},
                    "loss_percent": {"type": "number", "description": "Packet loss percentage (0-100)", "default": 0.0},
                },
                "required": ["interface_name"],
            },
        },
        {
            "name": "azam_get_telemetry",
            "description": "Fetches real-time host CPU governor stats and 100:1 KSM memory deduplication telemetry.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]

    RESOURCES = [
        {
            "uri": "azam://labs",
            "name": "Active Labs Directory",
            "description": "Real-time list of all network topologies and device states",
            "mimeType": "application/json",
        },
        {
            "uri": "azam://telemetry",
            "name": "Host Telemetry",
            "description": "KSM memory savings and CPU governor metrics",
            "mimeType": "application/json",
        },
    ]

    @classmethod
    async def process_json_rpc(cls, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handles incoming JSON-RPC 2.0 MCP request."""
        req_id = request_data.get("id")
        method = request_data.get("method", "")
        params = request_data.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "serverInfo": cls.SERVER_INFO,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False},
                    },
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": cls.TOOLS},
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            tool_result = await cls.execute_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(tool_result, indent=2)}],
                    "isError": "error" in tool_result,
                },
            }

        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"resources": cls.RESOURCES},
            }

        elif method == "resources/read":
            uri = params.get("uri", "")
            content = await cls.read_resource(uri)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(content, indent=2)}]
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }

    @classmethod
    async def execute_tool(cls, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches tool execution."""
        try:
            if name == "azam_list_labs":
                return {"labs": engine.list_labs()}

            elif name == "azam_get_lab":
                topo = engine.get_lab(args["lab_id"])
                if not topo:
                    return {"error": f"Lab '{args['lab_id']}' not found."}
                return topo.model_dump(mode="json")

            elif name == "azam_start_node":
                success = await engine.start_node(args["lab_id"], args["node_id"])
                return {"status": "started" if success else "failed", "node_id": args["node_id"]}

            elif name == "azam_stop_node":
                success = await engine.stop_node(args["lab_id"], args["node_id"])
                return {"status": "stopped" if success else "failed", "node_id": args["node_id"]}

            elif name == "azam_send_command":
                topo = engine.get_lab(args["lab_id"])
                if not topo:
                    return {"error": f"Lab '{args['lab_id']}' not found."}
                node = topo.get_node(args["node_id"])
                if not node or not node.console_port:
                    return {"error": f"Node '{args['node_id']}' has no active console port."}
                output = await gateway.send_command_to_node(node.console_port, args["command"])
                return {"output": output}

            elif name == "azam_inject_impairment":
                profile = ImpairmentProfile(
                    delay_ms=float(args.get("delay_ms", 0.0)),
                    jitter_ms=float(args.get("jitter_ms", 0.0)),
                    loss_percent=float(args.get("loss_percent", 0.0)),
                )
                success = await impairment_engine.apply_impairment(args["interface_name"], profile)
                return {"status": "applied" if success else "failed", "profile": profile.model_dump()}

            elif name == "azam_get_telemetry":
                return {
                    "ksm_telemetry": KsmManager.get_telemetry(),
                    "cpu_governor": cpu_governor.get_status(),
                }

            return {"error": f"Unknown tool '{name}'"}
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    async def read_resource(cls, uri: str) -> Dict[str, Any]:
        """Reads MCP resource data."""
        if uri == "azam://labs":
            return {"labs": engine.list_labs()}
        elif uri == "azam://telemetry":
            return {
                "ksm": KsmManager.get_telemetry(),
                "cpu": cpu_governor.get_status(),
            }
        return {"error": f"Resource '{uri}' not found"}


# Global MCP Server Instance
mcp_server = AzamMcpServer()
