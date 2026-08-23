"""JWT authentication middleware — Cognito JWKS verification with dev-mode bypass."""
from __future__ import annotations
import os
import json
import logging
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

DEV_MODE             = os.environ.get("DEV_MODE", "false").lower() == "true"
COGNITO_REGION       = os.environ.get("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID    = os.environ.get("COGNITO_CLIENT_ID", "")
GUEST_GROUP_NAME     = os.environ.get("GUEST_GROUP_NAME", "foundry-guests")
GUEST_ACCESS_EXPIRES_AT = os.environ.get("GUEST_ACCESS_EXPIRES_AT", "").strip()

_bearer = HTTPBearer(auto_error=False)


def _guest_access_cutoff() -> float | None:
    if not GUEST_ACCESS_EXPIRES_AT:
        return None
    try:
        normalized = GUEST_ACCESS_EXPIRES_AT.replace("Z", "+00:00")
        from datetime import datetime
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        logger.warning("Invalid GUEST_ACCESS_EXPIRES_AT value: %s", GUEST_ACCESS_EXPIRES_AT)
        return None


def guest_access_window_closed() -> bool:
    cutoff = _guest_access_cutoff()
    if cutoff is None:
        return False
    from time import time
    return time() >= cutoff


def _is_guest_user(user: dict) -> bool:
    groups = user.get("cognito:groups", user.get("groups", []))
    if isinstance(groups, str):
        groups = [groups]
    return GUEST_GROUP_NAME in groups


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
        logger.warning("Failed to fetch Cognito JWKS: %s", exc)
        return {}


def _decode_dev_token(token: str) -> dict:
    """Decode unsigned dev token (header.payload.sig) — no verification."""
    import base64
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("Invalid token format")
    padding = "=" * (4 - len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(parts[1] + padding))


def _decode_cognito_token(token: str) -> dict:
    if not COGNITO_USER_POOL_ID or not COGNITO_CLIENT_ID:
        raise JWTError("Cognito is not configured (COGNITO_USER_POOL_ID or COGNITO_CLIENT_ID not set)")

    jwks = _get_jwks()
    if not jwks:
        raise JWTError("No JWKS available from Cognito")
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise JWTError("Invalid JWKS format")

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    key = next(
        (k for k in keys if isinstance(k, dict) and k.get("kid") == kid),
        None,
    )
    if not key:
        raise JWTError("Key not found in Cognito JWKS")

    issuer = (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_USER_POOL_ID}"
    )
    payload = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        issuer=issuer,
        options={
            # Cognito access tokens use client_id (not aud) — disable aud check
            "verify_aud": False,
            "require_exp": True,
            "require_iss": True,
            "require_sub": True,
        },
    )
    if payload.get("token_use") == "access" and payload.get("client_id") != COGNITO_CLIENT_ID:
        raise JWTError("Token client_id does not match configured Cognito client")
    return payload


async def get_current_user(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    token = creds.credentials if creds else None
    if not token and DEV_MODE:
        # EventSource / SSE cannot send Authorization headers — allow query param in dev
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    try:
        payload = _decode_dev_token(token) if DEV_MODE else _decode_cognito_token(token)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc

    get_user_id(payload)  # validates sub is present
    if not DEV_MODE and _is_guest_user(payload) and guest_access_window_closed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest access for this event has ended",
        )
    # Attach raw token so stream router can forward it to the AgentCore runtime
    payload["_raw_token"] = token
    return payload


def get_user_id(user: dict) -> str:
    actor_id = user.get("sub") or user.get("user_id")
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a user identifier (sub)",
        )
    return actor_id


def is_admin(user: dict) -> bool:
    groups = user.get("cognito:groups", user.get("groups", []))
    if isinstance(groups, str):
        groups = [groups]
    return (
        user.get("custom:role") == "admin"
        or "admin" in groups
        or "foundry-admins" in groups
    )


def authorize_owned_resource(
    user: dict,
    item: dict | None,
    *,
    resource_name: str,
    write: bool = False,
) -> dict:
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"{resource_name} not found")
    actor_id = get_user_id(user)
    if item.get("created_by") == actor_id:
        return item
    if item.get("demo_data") is True and not write:
        return item
    if is_admin(user) and not write:
        return item
    if is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"{resource_name} is read-only for admins")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{resource_name} not found")
