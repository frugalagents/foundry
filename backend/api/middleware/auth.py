"""JWT authentication middleware — supports Cognito JWKS and dev-mode bypass."""
from __future__ import annotations
import os
import json
import logging
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

DEV_MODE = os.environ.get("DEV_MODE", "false").lower() == "true"
COGNITO_REGION = os.environ.get("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")

_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    if not COGNITO_USER_POOL_ID:
        return {}
    url = (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )
    try:
        resp = httpx.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch JWKS: %s", exc)
        return {}


def _decode_dev_token(token: str) -> dict:
    """Decode unsigned dev token (header.payload.sig) — no verification."""
    import base64
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("Invalid token format")
    padding = "=" * (4 - len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
    return payload


def _decode_cognito_token(token: str) -> dict:
    jwks = _get_jwks()
    if not jwks:
        raise JWTError("No JWKS available")
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k["kid"] == kid), None)
    if not key:
        raise JWTError("Key not found in JWKS")
    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=COGNITO_CLIENT_ID or None,
    )


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    token = creds.credentials

    try:
        if DEV_MODE:
            payload = _decode_dev_token(token)
        else:
            payload = _decode_cognito_token(token)
    except (JWTError, ValueError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )

    return payload


async def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    groups = user.get("cognito:groups", user.get("groups", []))
    if isinstance(groups, str):
        groups = [groups]
    if user.get("custom:role") != "admin" and "admin" not in groups:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def get_user_id(user: dict) -> str:
    return user.get("sub", user.get("user_id", "unknown"))
