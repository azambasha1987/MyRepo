import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from azamlabs.main import app

client = TestClient(app)


def test_frontend_index_html():
    """Validates that the root endpoint serves AzamLabs Studio SPA shell with all subsystems."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "AzamLabs" in response.text
    assert "topologyCanvas" in response.text
    assert "nodeInspector" in response.text
    assert "terminalDrawer" in response.text
    assert "wiresharkModal" in response.text
    assert "paletteModal" in response.text
    assert "importerModal" in response.text
    assert "labExplorerDrawer" in response.text
    assert "toolToggleExplorer" in response.text
    assert "btnLogout" in response.text
    assert "logo-icon.png" in response.text


def test_frontend_login_html():
    """Validates that the login endpoint serves the Cyber-Tactical OLED Login Page."""
    response = client.get("/login.html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "AZAMLABS" in response.text
    assert "avatar-hero-unit" in response.text
    assert "loginForm" in response.text
    assert "rememberMe" in response.text
    assert "logo.png" in response.text


def test_frontend_css_assets():
    """Validates that all modular CSS stylesheets are served."""
    css_files = ["/css/style.css", "/css/canvas.css", "/css/components.css", "/css/login.css"]
    for path in css_files:
        response = client.get(path)
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")


def test_frontend_js_subsystems():
    """Validates that all modular JavaScript subsystems are served."""
    js_files = [
        "/js/auth.js",
        "/js/explorer.js",
        "/js/canvas.js",
        "/js/terminal.js",
        "/js/sniffer.js",
        "/js/palette.js",
        "/js/importer.js",
        "/js/app.js",
    ]
    for path in js_files:
        response = client.get(path)
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "") or "text/plain" in response.headers.get("content-type", "")


def test_frontend_branding_assets():
    """Validates that official branding logos and icons from Azam-Pnet are served."""
    asset_files = [
        "/assets/logo.png",
        "/assets/logo-icon.png",
        "/assets/favicon.png",
        "/assets/favicon.ico",
    ]
    for path in asset_files:
        response = client.get(path)
        assert response.status_code == 200
        assert len(response.content) > 0


def test_frontend_clean_room_integrity():
    """Verifies that the frontend codebase is 100% clean-room (no legacy code strings)."""
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"

    for file_path in frontend_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".html", ".css", ".js"]:
            content = file_path.read_text(encoding="utf-8").lower()
            # Disallow any legacy runtime variables or function names
            # (Note: descriptive labels like "EVE-NG / PNET" in converter options are allowed user labels,
            # but legacy source strings or stolen identifiers are strictly prohibited).
            assert "unl_" not in content
            assert "unetlab_" not in content
            assert "pnet_" not in content
