"""
Authentication for rag_app: token validation and current user.
Cart and Favorites APIs require a valid Bearer token (from /api/login).
"""
import hashlib
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=True)

# Demo users: same as rag_app.main login. Used to validate token and get user.
DEMO_USERS = {
    "admin@finfit.com": {
        "password": "admin123",
        "name": "Admin User",
        "role": "super_admin",
        "email": "admin@finfit.com",
    },
    "user@finfit.com": {
        "password": "user123",
        "name": "Regular User",
        "role": "user",
        "email": "user@finfit.com",
    },
    "test@example.com": {
        "password": "test123",
        "name": "Test User",
        "role": "user",
        "email": "test@example.com",
    },
}


def make_token(email: str, role: str) -> str:
    """Same as rag_app.main login: deterministic token from email+role."""
    return hashlib.sha256(f"{email}{role}".encode()).hexdigest()[:32]


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Validate Bearer token and return current user dict { email, name, role }.
    Used by cart and favorites APIs. Raises 401 if missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Connexion requise. Connectez-vous pour accéder au panier et aux favoris.",
        )
    token = credentials.credentials.strip()
    for user in DEMO_USERS.values():
        if make_token(user["email"], user["role"]) == token:
            return {
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
            }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré. Reconnectez-vous.",
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[dict]:
    """Same as get_current_user but returns None if no/invalid token (for optional auth)."""
    if not credentials or not credentials.credentials:
        return None
    token = credentials.credentials.strip()
    for user in DEMO_USERS.values():
        if make_token(user["email"], user["role"]) == token:
            return {"email": user["email"], "name": user["name"], "role": user["role"]}
    return None
