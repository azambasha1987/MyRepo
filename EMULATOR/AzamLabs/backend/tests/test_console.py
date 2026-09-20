"""
Unit Tests for AzamLabs Console Tools
Verifies Flow-Controlled Bulk Config Paster, Error Detection, Desktop URIs, and Script Launchers.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from azamlabs.core.schema import AzamTopology, AzamNode, DeviceType, DriverType
from azamlabs.core.engine import engine
from azamlabs.console.paster import FlowControlledPaster
from azamlabs.console.uris import TerminalLauncherManager
from azamlabs.main import app


def test_flow_paster_syntax_error_detection():
    assert FlowControlledPaster.check_for_errors("% Invalid input detected at '^' marker.") is not None
    assert FlowControlledPaster.check_for_errors("% Incomplete command.") is not None
    assert FlowControlledPaster.check_for_errors("% Ambiguous command:  \"sh ip\"") is not None
    assert FlowControlledPaster.check_for_errors("Syntax error: line 4") is not None
    assert FlowControlledPaster.check_for_errors("Router(config)# interface Gi0/1") is None
    assert FlowControlledPaster.check_for_errors("Router# show ip route") is None


def test_desktop_uri_generation():
    node = AzamNode(name="R1", device_type=DeviceType.ROUTER, console_port=32768, console_type="telnet")
    uri = TerminalLauncherManager.get_node_uri(node, host="127.0.0.1")
    assert uri == "telnet://127.0.0.1:32768"


def test_terminal_script_generation():
    nodes = [
        AzamNode(name="Core-R1", console_port=30001),
        AzamNode(name="Dist-SW1", console_port=30002),
    ]

    # Windows Terminal
    wt_script = TerminalLauncherManager.generate_windows_terminal_script("Enterprise Lab", nodes)
    assert "wt.exe" in wt_script
    assert "Core-R1" in wt_script
    assert "30001" in wt_script
    assert "Dist-SW1" in wt_script

    # SecureCRT
    crt_script = TerminalLauncherManager.generate_securecrt_script("Enterprise Lab", nodes)
    assert "ConnectInTab" in crt_script
    assert "Core-R1" in crt_script
    assert "30001" in crt_script

    # PuTTY
    putty_script = TerminalLauncherManager.generate_putty_batch_script("Enterprise Lab", nodes)
    assert "putty.exe" in putty_script
    assert "Core-R1" in putty_script

    # iTerm2
    iterm_script = TerminalLauncherManager.generate_iterm2_script("Enterprise Lab", nodes)
    assert "tell application \"iTerm\"" in iterm_script
    assert "Core-R1" in iterm_script


@pytest.mark.asyncio
async def test_fastapi_console_endpoints():
    topo = AzamTopology(name="Console Test Lab")
    n1 = AzamNode(name="ConsoleR1", console_port=32888)
    topo.add_node(n1)
    engine.create_lab(topo)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get URI
        uri_resp = await client.get(f"/api/v1/console/{topo.id}/{n1.id}/uri")
        assert uri_resp.status_code == 200
        assert uri_resp.json()["uri"] == "telnet://127.0.0.1:32888"

        # Download Windows Terminal launcher
        wt_resp = await client.get(f"/api/v1/console/{topo.id}/launcher/wt")
        assert wt_resp.status_code == 200
        assert "wt.exe" in wt_resp.text

        # Download SecureCRT launcher
        crt_resp = await client.get(f"/api/v1/console/{topo.id}/launcher/securecrt")
        assert crt_resp.status_code == 200
        assert "ConnectInTab" in crt_resp.text
