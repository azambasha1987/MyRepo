"""
AzamLabs Security & Cryptographic Session Authentication Manager
Handles password verification, bearer token lifecycle, and route protection.
"""

import time
import secrets
import hashlib
import hmac
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status, Header

DEFAULT_USERNAME = "azam"
DEFAULT_PASSWORD_HASH = hashlib.sha256(b"azam").hexdigest()
SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 Days


class SessionManager:
    """Manages active bearer tokens, creation, expiry, and revocation."""

    def __init__(self):
        # In-memory session store: token -> { username, created_at, expires_at }
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def verify_credentials(self, username: str, password: str) -> bool:
        """Constant-time verification of username and password."""
        if not username or not password:
            return False

        user_match = hmac.compare_digest(username.strip().lower(), DEFAULT_USERNAME)
        pwd_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        pwd_match = hmac.compare_digest(pwd_hash, DEFAULT_PASSWORD_HASH)

        return user_match and pwd_match

    def create_session(self, username: str, remember_me: bool = True) -> Dict[str, Any]:
        """Issues a new secure bearer token with 7-day TTL."""
        token = secrets.token_urlsafe(36)
        now = time.time()
        ttl = SESSION_TTL_SECONDS if remember_me else 86400  # 1 day if not remember_me
        expires_at = now + ttl

        session_data = {
            "token": token,
            "username": username.lower(),
            "created_at": now,
            "expires_at": expires_at,
            "expires_in": int(ttl),
        }
        self._sessions[token] = session_data
        return session_data

    def validate_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Validates bearer token, checking presence and expiration."""
        if not token:
            return None

        clean_token = token.replace("Bearer ", "").strip()
        session = self._sessions.get(clean_token)
        if not session:
            return None

        if time.time() > session["expires_at"]:
            self.revoke_token(clean_token)
            return None

        return session

    def revoke_token(self, token: str) -> bool:
        """Revokes an active session token."""
        clean_token = token.replace("Bearer ", "").strip()
        if clean_token in self._sessions:
            del self._sessions[clean_token]
            return True
        return False


# Global Session Manager Instance
session_manager = SessionManager()


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    FastAPI security dependency for route protection.
    Requires 'Authorization: Bearer <token>' header.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = session_manager.validate_token(authorization)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session
