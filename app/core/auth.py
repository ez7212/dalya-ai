"""
Authentication dependencies for FastAPI.

Uses Supabase-issued JWTs verified with ES256 (ECC P-256) via the JWKS endpoint.
Public keys are fetched once and cached — no network call on every request.
"""

import os
import time
from typing import Annotated, Optional

from dotenv import load_dotenv
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

load_dotenv()

_bearer_scheme = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "")

# JWKS client — fetches and caches public keys from Supabase
_jwks_client: Optional[PyJWKClient] = None
_jwks_client_created_at: float = 0
_JWKS_CACHE_SECONDS = 3600  # refresh keys every hour


def _get_jwks_client() -> PyJWKClient:
    """Get or create a cached JWKS client for Supabase."""
    global _jwks_client, _jwks_client_created_at
    now = time.time()
    if _jwks_client is None or (now - _jwks_client_created_at) > _JWKS_CACHE_SECONDS:
        if not SUPABASE_URL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SUPABASE_URL not configured",
            )
        jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
        _jwks_client_created_at = now
    return _jwks_client


class CurrentUser(BaseModel):
    id: str
    email: str


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> CurrentUser:
    """Decode and validate a Supabase JWT using the JWKS public key."""
    token = credentials.credentials
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            options={"require": ["sub", "exp"]},
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {e}",
        )

    user_id = payload.get("sub")
    email = payload.get("email", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    return CurrentUser(id=user_id, email=email)


async def require_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Restrict access to the configured admin user."""
    if not ADMIN_USER_ID or user.id != ADMIN_USER_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
