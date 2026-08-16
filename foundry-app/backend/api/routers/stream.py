"""SSE streaming endpoint — proxies user messages to the AgentCore Runtime.

In production each platform module has a dedicated AgentCore Runtime endpoint.
The endpoint ARN is resolved from the environment:
  AGENTCORE_ENDPOINT_{MODULE_ID_UPPER}   e.g. AGENTCORE_ENDPOINT_CODING_AGENT
  AGENTCORE_ENDPOINT_DEFAULT             fallback for any unrecognised module

For local development, set AGENTCORE_LOCAL_URL to a running CodingAgentRuntime
server (e.g. http://localhost:8080) and the backend will HTTP-proxy to it instead.
"""
from __future__ import annotations
import json
import logging
import os
from typing import Annotated, AsyncIterator

import boto3
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.middleware.auth import (
    authorize_owned_resource,
    get_current_user,
    get_user_id,
)
from api.db import dynamodb as db
from api.db.models import StreamRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stream"])

CurrentUser = Annotated[dict, Depends(get_current_user)]

_REGION = os.environ.get("AWS_REGION", "us-east-1")
_LOCAL_URL = os.environ.get("AGENTCORE_LOCAL_URL", "").rstrip("/")


# ── Endpoint resolution ───────────────────────────────────────────────────────

def _endpoint_arn(module_id: str) -> str | None:
    key = f"AGENTCORE_ENDPOINT_{module_id.upper().replace('-', '_')}"
    return os.environ.get(key) or os.environ.get("AGENTCORE_ENDPOINT_DEFAULT")


# ── AgentCore Runtime invocation ─────────────────────────────────────────────

async def _invoke_agentcore(
    endpoint_arn: str,
    agentcore_session_id: str,
    payload: dict,
    actor_id: str,
) -> AsyncIterator[bytes]:
    """Invoke the AgentCore Runtime and forward its SSE response."""
    client = boto3.client("bedrock-agentcore", region_name=_REGION)
    try:
        resp = client.invoke_agent_runtime(
            agentRuntimeArn=endpoint_arn,
            runtimeSessionId=agentcore_session_id,
            payload=json.dumps(payload).encode(),
            qualifier="DEFAULT",
            runtimeUserId=actor_id,
        )
        for chunk in resp["response"].iter_chunks():
            if chunk:
                yield chunk
    except client.exceptions.ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        logger.error("AgentCore invocation failed: %s", exc)
        err = json.dumps({"type": "error", "data": {"message": f"AgentCore error: {code}"}})
        yield f"data: {err}\n\n".encode()


async def _invoke_local(
    local_url: str,
    agentcore_session_id: str,
    payload: dict,
    actor_token: str,
) -> AsyncIterator[bytes]:
    """HTTP-proxy to a locally running CodingAgentRuntime (dev mode)."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {actor_token}",
        "X-Session-Id": agentcore_session_id,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{local_url}/invoke",
            json=payload,
            headers=headers,
        ) as resp:
            async for chunk in resp.aiter_bytes():
                if chunk:
                    yield chunk


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/customers/{customer_id}/sessions/{session_id}/stream")
async def stream_session(
    customer_id: str,
    session_id: str,
    body: StreamRequest,
    user: CurrentUser,
):
    # Auth
    authorize_owned_resource(
        user, db.get_customer(customer_id), resource_name="Customer"
    )
    session = authorize_owned_resource(
        user, db.get_session(customer_id, session_id), resource_name="Session"
    )

    actor_id    = get_user_id(user)
    module_id   = session.get("module_id") or "coding-agent"
    raw_token   = _extract_raw_token(user)

    # Build AgentCore payload
    payload = {
        "user_message": body.message,
        "session_id":   session_id,
        "customer_id":  customer_id,
        "module_id":    module_id,
    }

    # Tag session with module if first message detects one
    if not session.get("module_id"):
        db.update_session(customer_id, session_id, {"module_id": module_id},
                          owner_id=actor_id)

    # AgentCore requires runtimeSessionId >= 33 chars; pad legacy short IDs
    agentcore_session_id = session_id if len(session_id) >= 33 else f"foundry-session-{session_id}"

    async def generate() -> AsyncIterator[bytes]:
        if _LOCAL_URL:
            async for chunk in _invoke_local(_LOCAL_URL, agentcore_session_id, payload, raw_token):
                yield chunk
        else:
            arn = _endpoint_arn(module_id)
            if not arn:
                err = json.dumps({
                    "type": "chat_stream",
                    "data": {"text": (
                        "⚠️  No AgentCore endpoint configured. "
                        f"Set `AGENTCORE_ENDPOINT_{module_id.upper().replace('-','_')}` "
                        "or `AGENTCORE_LOCAL_URL` for local development."
                    )},
                })
                yield f"data: {err}\n\ndata: [DONE]\n\n".encode()
                return
            async for chunk in _invoke_agentcore(arn, agentcore_session_id, payload, actor_id):
                yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _extract_raw_token(user: dict) -> str:
    """Get the raw JWT string stored on the user dict during auth."""
    # We piggy-back the raw token via a hidden key set in get_current_user.
    return user.get("_raw_token", "")
