"""OIDC token exchange — exchanges an authorization code for a Midway id_token."""
from __future__ import annotations
import os
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

MIDWAY_ISSUER  = os.environ.get("MIDWAY_ISSUER", "").rstrip("/")
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")


class TokenRequest(BaseModel):
    code: str
    redirect_uri: str


@router.post("/auth/token")
async def exchange_token(body: TokenRequest):
    """Exchange an OIDC authorization code for a Midway id_token."""
    if not MIDWAY_ISSUER or not OIDC_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Midway OIDC is not configured on this server")

    token_url = f"{MIDWAY_ISSUER}/token"
    data = {
        "grant_type":   "authorization_code",
        "code":         body.code,
        "redirect_uri": body.redirect_uri,
        "client_id":    OIDC_CLIENT_ID,
    }
    auth = (OIDC_CLIENT_ID, OIDC_CLIENT_SECRET) if OIDC_CLIENT_SECRET else None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(token_url, data=data, auth=auth)
        resp.raise_for_status()
        tokens = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Midway token exchange failed: %s %s", exc.response.status_code, exc.response.text)
        raise HTTPException(status_code=401, detail="Midway token exchange failed") from exc
    except Exception as exc:
        logger.error("Midway token exchange error: %s", exc)
        raise HTTPException(status_code=502, detail="Midway unreachable") from exc

    id_token = tokens.get("id_token") or tokens.get("access_token")
    if not id_token:
        raise HTTPException(status_code=401, detail="No id_token in Midway response")

    return {"access_token": id_token}
