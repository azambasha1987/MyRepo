"""
FastAPI Authentication Router for AzamLabs
Endpoints for login, logout, and session verification.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Header, status

from azamlabs.auth.security import session_manager, get_current_user

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = True


class LoginResponse(BaseModel):
    status: str
    token: str
    user: str
    expires_in: int


@auth_router.post("/login", response_model=LoginResponse)
async def login_endpoint(payload: LoginRequest) -> LoginResponse:
    """Authenticates credentials against default store (azam/azam) and issues 7-day bearer token."""
    valid = session_manager.verify_credentials(payload.username, payload.password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password. Default is azam / azam.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = session_manager.create_session(payload.username, payload.remember_me)
    return LoginResponse(
        status="success",
        token=session["token"],
        user=session["username"],
        expires_in=session["expires_in"]
    )


@auth_router.get("/me")
async def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Returns current authenticated user profile and session validity."""
    return {
        "status": "authenticated",
        "user": user["username"],
        "expires_at": user["expires_at"],
    }


@auth_router.post("/logout")
async def logout_endpoint(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Revokes active bearer session token."""
    if authorization:
        session_manager.revoke_token(authorization)
    return {"status": "logged_out"}
