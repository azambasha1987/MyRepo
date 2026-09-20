"""
Unit Tests for AzamLabs Model Context Protocol (MCP) Server
Verifies JSON-RPC 2.0 protocol adherence, tool enumeration, tool execution, and resource retrieval.
"""

import pytest
import json
from httpx import AsyncClient, ASGITransport

from azamlabs.core.schema import AzamTopology, AzamNode, DeviceType, DriverType
from azamlabs.core.engine import engine
from azamlabs.mcp.server import mcp_server
from azamlabs.main import app


@pytest.mark.asyncio
async def test_mcp_initialize():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    resp = await mcp_server.process_json_rpc(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "serverInfo" in resp["result"]
    assert resp["result"]["serverInfo"]["name"] == "azamlabs-mcp"


@pytest.mark.asyncio
async def test_mcp_tools_list():
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    resp = await mcp_server.process_json_rpc(req)
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "azam_list_labs" in tool_names
    assert "azam_start_node" in tool_names
    assert "azam_stop_node" in tool_names
    assert "azam_send_command" in tool_names
    assert "azam_inject_impairment" in tool_names
    assert "azam_get_telemetry" in tool_names


@pytest.mark.asyncio
async def test_mcp_resources_list_and_read():
    # 1. List resources
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "resources/list",
        "params": {}
    }
    resp = await mcp_server.process_json_rpc(req)
    resources = resp["result"]["resources"]
    uris = [r["uri"] for r in resources]
    assert "azam://labs" in uris
    assert "azam://telemetry" in uris

    # 2. Read resource
    read_req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "resources/read",
        "params": {"uri": "azam://telemetry"}
    }
    read_resp = await mcp_server.process_json_rpc(read_req)
    contents = read_resp["result"]["contents"]
    assert len(contents) == 1
    assert "ksm" in json.loads(contents[0]["text"])


@pytest.mark.asyncio
async def test_mcp_tool_execution_and_http_endpoint():
    topo = AzamTopology(name="MCP Lab Test")
    n1 = AzamNode(name="Router-MCP", driver=DriverType.DOCKER, image="alpine:latest")
    topo.add_node(n1)
    engine.create_lab(topo)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Call azam_list_labs via HTTP POST /mcp
        call_req = {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {
                "name": "azam_list_labs",
                "arguments": {}
            }
        }
        http_resp = await client.post("/mcp", json=call_req)
        assert http_resp.status_code == 200
        data = http_resp.json()
        assert data["id"] == 100
        content_text = data["result"]["content"][0]["text"]
        assert "labs" in json.loads(content_text)

        # Call azam_start_node
        start_req = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "azam_start_node",
                "arguments": {
                    "lab_id": topo.id,
                    "node_id": n1.id
                }
            }
        }
        start_resp = await client.post("/mcp", json=start_req)
        assert start_resp.status_code == 200
        start_result = json.loads(start_resp.json()["result"]["content"][0]["text"])
        assert start_result["status"] == "started"

        # Call azam_stop_node
        stop_req = {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/call",
            "params": {
                "name": "azam_stop_node",
                "arguments": {
                    "lab_id": topo.id,
                    "node_id": n1.id
                }
            }
        }
        stop_resp = await client.post("/mcp", json=stop_req)
        assert stop_resp.status_code == 200
        stop_result = json.loads(stop_resp.json()["result"]["content"][0]["text"])
        assert stop_result["status"] == "stopped"
