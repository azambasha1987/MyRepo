"""
Test suite for AzamLabs Authentication & Security Engine
Validates cryptographic verification, bearer token lifecycle, and auth endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from azamlabs.main import app
from azamlabs.auth.security import session_manager

client = TestClient(app)


def test_password_and_credential_verification():
    """Verify credential verification for azam / azam."""
    assert session_manager.verify_credentials("azam", "azam") is True
    assert session_manager.verify_credentials("AZAM", "azam") is True  # user normalized
    assert session_manager.verify_credentials("azam", "wrong_password") is False
    assert session_manager.verify_credentials("other_user", "azam") is False
    assert session_manager.verify_credentials("", "") is False


def test_token_lifecycle():
    """Verify cryptographic bearer token generation, validation, and revocation."""
    session_data = session_manager.create_session("azam", remember_me=True)
    token = session_data["token"]
    assert token is not None
    assert session_data["expires_in"] == 7 * 24 * 3600

    validated = session_manager.validate_token(token)
    assert validated is not None
    assert validated["username"] == "azam"

    # Revoke
    assert session_manager.revoke_token(token) is True
    assert session_manager.validate_token(token) is None


def test_login_endpoint_success():
    """Verify POST /api/v1/auth/login with valid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "azam", "password": "azam", "remember_me": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"] == "azam"
    assert data["status"] == "success"
    assert data["expires_in"] > 0


def test_login_endpoint_invalid_password():
    """Verify POST /api/v1/auth/login with bad password returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "azam", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json().get("detail", "")


def test_login_endpoint_unknown_user():
    """Verify POST /api/v1/auth/login with unknown username returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "unknown_user", "password": "password"}
    )
    assert response.status_code == 401


def test_auth_me_endpoint():
    """Verify GET /api/v1/auth/me with valid and invalid tokens."""
    # 1. Unauthenticated request
    resp_unauth = client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    # 2. Login to get token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "azam", "password": "azam"}
    )
    token = login_resp.json()["token"]

    # 3. Authenticated request
    resp_auth = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_auth.status_code == 200
    data = resp_auth.json()
    assert data["user"] == "azam"
    assert data["status"] == "authenticated"


def test_auth_logout_endpoint():
    """Verify POST /api/v1/auth/logout revokes session."""
    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "azam", "password": "azam"}
    )
    token = login_resp.json()["token"]

    # Logout
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "logged_out"

    # Verify token is now rejected
    resp_after = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_after.status_code == 401
