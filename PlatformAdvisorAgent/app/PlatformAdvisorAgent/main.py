"""
Platform Advisor — Amazon Bedrock AgentCore Runtime entry point.

Architecture:
  Every user message is a turn in a Strands Agent conversation.
  The Agent calls @tool-wrapped pipeline steps to execute the advisory
  pipeline, handles user changes mid-pipeline, and answers questions —
  all through its natural tool-use + conversation loop.

  Panel events (radar charts, diagrams, etc.) are emitted as side effects
  of tool calls via an asyncio.Queue and merged into the SSE output stream
  concurrently with the agent's text stream.

  PipelineContext is persisted to DynamoDB between invocations so that
  accumulated pipeline state (pattern, components, phases, etc.) survives
  across HTTP calls while AgentCore STM retains the conversation history.

  AgentCore LTM (via session_manager) stores customer context across
  sessions so returning customers get personalised recommendations.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator, Optional

import boto3
import jwt
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from jwt import PyJWKClient
from strands import Agent
from strands.models import BedrockModel

from advisor_core import AssessmentInput, DecisionEngine, build_questionnaire
from advisor_core.models import OverrideRecord
from architecture_v3_runtime import (
    ACTION as ARCHITECTURE_V3_ACTION,
    ArchitectureV3Conflict,
    ArchitectureV3RuntimeAdapter,
    conflict_payload,
)
from pipeline_skills.base import (
    PipelineContext,
    make_error,
    make_complete,
    make_chat_stream,
    make_event,
)
from pipeline_skills.v2_assessment_skill import run_v2_assessment
from memory.context_store import (
    list_customer_contexts,
    load_context,
    save_context,
    session_is_owned,
)
from memory.session import get_memory_session_manager
from pipeline_tools import make_pipeline_tools

app = BedrockAgentCoreApp()
log = app.logger

# ── Config ────────────────────────────────────────────────────────────────────

_TABLE = os.environ.get("DYNAMODB_TABLE", "platform-advisor-main")
_REGION = os.environ.get("AWS_REGION", "us-east-1")
_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
_COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
_COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
_COGNITO_ISSUER = (
    f"https://cognito-idp.{_REGION}.amazonaws.com/{_COGNITO_USER_POOL_ID}"
)
_COGNITO_TOKEN_HEADER = (
    "x-amzn-bedrock-agentcore-runtime-custom-cognito-id-token"
)

_V2_SYSTEM_ADDENDUM = """

PLATFORM ADVISOR V2 RUNTIME RULES:
- Architecture decisions come only from the deterministic v2 AssessmentResult.
- Never infer missing critical evidence or invent sizing values.
- Use get_intake_questionnaire only to explain the applicable questions.
- Use evaluate_platform_assessment only when a complete structured AssessmentInput
  is provided in the conversation.
- Do not refer to graph scores, radar confidence, Mesh, or Economy as operating models.
- Explain trace evidence and recorded overrides; do not replace deterministic outputs.
"""

_ddb = None
_cached_system_prompt: str | None = None


# ── DynamoDB helpers ──────────────────────────────────────────────────────────

def _get_ddb():
    global _ddb
    if _ddb is None:
        _ddb = boto3.resource("dynamodb", region_name=_REGION)
    return _ddb


def _save_ctx(ctx: PipelineContext, actor_id: str) -> None:
    """Persist PipelineContext into the API-owned session aggregate."""
    table = _get_ddb().Table(_TABLE)
    save_context(table, ctx, owner_id=actor_id)


def _load_customer_history(
    customer_id: str,
    current_session_id: str,
    actor_id: str,
) -> str:
    """Query prior completed advisory sessions for this customer and return a summary."""
    try:
        table = _get_ddb().Table(_TABLE)
        history_parts = []
        for data in list_customer_contexts(
            table,
            customer_id,
            owner_id=actor_id,
        ):
            sess_id = data.get("session_id")
            if sess_id == current_session_id:
                continue
            if not data.get("blueprint_md"):
                continue  # only completed sessions
            pattern = data.get("pattern_id", "").split(":")[-1].title()
            answers = data.get("answers", {})
            lobs = answers.get("lob_count", "?")
            industry = data.get("industry", "")
            regime = answers.get("compliance_regime", "none")
            history_parts.append(
                f"{pattern} pattern, {lobs} LOBs"
                + (f", {industry}" if industry else "")
                + (f", {regime}" if regime and regime != "none" else "")
            )
        if history_parts:
            return f"Prior advisory sessions: {'; '.join(history_parts[:3])}"
        return ""
    except Exception as exc:
        log.warning("Could not load customer history: %s", exc)
        return ""


def _load_ctx(
    customer_id: str,
    session_id: str,
    actor_id: str,
) -> PipelineContext | None:
    """Load a previously saved PipelineContext from DynamoDB."""
    table = _get_ddb().Table(_TABLE)
    return load_context(
        table,
        customer_id,
        session_id,
        owner_id=actor_id,
    )


def _session_is_owned(customer_id: str, session_id: str, actor_id: str) -> bool:
    table = _get_ddb().Table(_TABLE)
    return session_is_owned(table, customer_id, session_id, actor_id)


def _request_header(context, name: str) -> str | None:
    headers = getattr(context, "request_headers", None)
    if not isinstance(headers, dict):
        return None
    target = name.lower()
    for header_name, value in headers.items():
        if header_name.lower() == target and isinstance(value, str):
            return value.strip() or None
    return None


@lru_cache(maxsize=1)
def _cognito_jwk_client() -> PyJWKClient:
    return PyJWKClient(f"{_COGNITO_ISSUER}/.well-known/jwks.json")


def _runtime_actor_id(context) -> str | None:
    """Verify the forwarded Cognito ID token and return its immutable subject."""
    claims = _runtime_identity_claims(context)
    if claims is None:
        return None
    actor_id = claims.get("sub")
    return (
        actor_id.strip()
        if isinstance(actor_id, str) and actor_id.strip()
        else None
    )


def _runtime_identity_claims(context) -> dict | None:
    """Verify the forwarded Cognito ID token and return trusted claims."""
    token = _request_header(context, _COGNITO_TOKEN_HEADER)
    if not token or not _COGNITO_USER_POOL_ID or not _COGNITO_CLIENT_ID:
        return None
    try:
        signing_key = _cognito_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=_COGNITO_CLIENT_ID,
            issuer=_COGNITO_ISSUER,
            options={"require": ["exp", "iat", "sub", "token_use"]},
        )
    except jwt.PyJWTError as exc:
        log.warning("Rejected Cognito identity token: %s", type(exc).__name__)
        return None
    if claims.get("token_use") != "id":
        return None
    return claims


def _runtime_tenant_id(claims: dict, actor_id: str) -> str:
    for claim in (
        "custom:tenant_id",
        "tenant_id",
        "custom:organization_id",
        "organization_id",
    ):
        value = claims.get(claim)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return actor_id


# ── System prompt ─────────────────────────────────────────────────────────────

def _load_system_prompt() -> str:
    global _cached_system_prompt
    if _cached_system_prompt:
        return _cached_system_prompt

    # 1. Try active prompt from DynamoDB (admin-editable)
    try:
        table = _get_ddb().Table(_TABLE)
        resp = table.get_item(Key={"PK": "CONFIG#SYSTEM", "SK": "PROMPT#active"})
        item = resp.get("Item")
        if item and item.get("content"):
            _cached_system_prompt = item["content"] + _V2_SYSTEM_ADDENDUM
            return _cached_system_prompt
    except Exception as exc:
        log.warning("Could not load system prompt from DynamoDB: %s", exc)

    # 2. Fall back to file
    prompt_path = (
        Path(__file__).parent.parent.parent.parent
        / "knowledge-base" / "system-prompt.md"
    )
    if prompt_path.exists():
        _cached_system_prompt = prompt_path.read_text() + _V2_SYSTEM_ADDENDUM
    else:
        _cached_system_prompt = (
            "You are the Agentic Platform Advisor. "
            "Guide enterprise leaders through AI agent platform strategy."
            + _V2_SYSTEM_ADDENDUM
        )
    return _cached_system_prompt


# ── Stream merge ──────────────────────────────────────────────────────────────

def _agent_event_to_sse(ev) -> str | None:
    """Convert a Strands streaming event to a chat_stream SSE string, or None.

    Strands stream_async yields dicts: {"data": "<text>", "complete": bool, ...}
    """
    # Strands primary format: dict with "data" key
    if isinstance(ev, dict):
        text = ev.get("data", "")
        if text and isinstance(text, str):
            return make_chat_stream(text)
        return None
    # Plain string fallback
    if isinstance(ev, str) and ev:
        return make_chat_stream(ev)
    # Object with .delta.text (legacy / alternative Bedrock event shape)
    if hasattr(ev, "delta") and hasattr(ev.delta, "text") and ev.delta.text:
        return make_chat_stream(ev.delta.text)
    return None


async def _merge_streams(
    agent_gen: AsyncIterator,
    panel_queue: asyncio.Queue,
) -> AsyncIterator[str]:
    """
    Merge the Strands agent text stream with panel events from tool calls.

    Two background tasks pump into a shared output queue so panel events
    emitted during tool execution reach the client immediately, without
    waiting for the next agent text event.
    """
    out: asyncio.Queue[str | None] = asyncio.Queue()
    agent_done = asyncio.Event()

    async def _agent_pump():
        try:
            async for ev in agent_gen:
                sse = _agent_event_to_sse(ev)
                if sse:
                    await out.put(sse)
        except Exception as exc:
            log.exception("Agent stream error")
            await out.put(make_error(0, str(exc)))
        finally:
            agent_done.set()

    async def _panel_pump():
        while not agent_done.is_set() or not panel_queue.empty():
            try:
                item = panel_queue.get_nowait()
                await out.put(item)
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.005)  # 5 ms poll

    agent_task = asyncio.create_task(_agent_pump())
    panel_task = asyncio.create_task(_panel_pump())

    try:
        while True:
            if agent_done.is_set() and panel_queue.empty() and out.empty():
                break
            try:
                item = await asyncio.wait_for(out.get(), timeout=0.1)
                yield item
            except asyncio.TimeoutError:
                if agent_done.is_set() and panel_queue.empty():
                    break
    finally:
        panel_task.cancel()
        try:
            await panel_task
        except asyncio.CancelledError:
            pass
        await agent_task


# ── AgentCore entrypoint ──────────────────────────────────────────────────────

@app.entrypoint
async def invoke(payload: dict, context):
    """
    Single entrypoint for all user interactions.

    Every message — whether starting the pipeline, confirming a pattern,
    changing an intake answer, or asking a question — is a user_message.
    The Strands Agent decides which tools to call and in what order.

    payload keys:
      user_message : str        required — the user's message
      session_id   : str        required
      customer_id  : str        required
      answers      : dict       optional — intake answers to prime/update in ctx
      industry     : str        optional
      pain_points  : list[str]  optional
    """
    # agentcore CLI wraps --json input as {"prompt": "<json-string>"}.
    # Direct InvokeAgentRuntime calls (frontend) send the fields at top level.
    if "prompt" in payload and isinstance(payload.get("prompt"), str):
        try:
            payload = json.loads(payload["prompt"])
        except (json.JSONDecodeError, TypeError):
            pass

    session_id   = payload.get("session_id", "")
    customer_id  = payload.get("customer_id", "")
    user_message = payload.get("user_message") or "Start the advisory session."

    agentcore_session_id = getattr(context, "session_id", None) or session_id
    identity_claims = _runtime_identity_claims(context)
    actor_id = None
    if identity_claims is not None:
        subject = identity_claims.get("sub")
        if isinstance(subject, str) and subject.strip():
            actor_id = subject.strip()

    log.info(
        "invoke: session=%s customer=%s action=%s msg=%.120s",
        session_id, customer_id, payload.get("action", "chat"), user_message,
    )

    # ── Action short-circuits (drilldown, whatif) ─────────────────────────
    # These bypass the Strands agent entirely — pure computation, immediate response.
    action = payload.get("action")

    if action == "questionnaire":
        workload = payload.get("primary_workload") or None
        try:
            questionnaire = build_questionnaire(workload)
            event = json.dumps({
                "type": "panel_complete",
                "data": {"step": 1, "panel_type": "intake", "data": {
                    "schema_version": "2.0",
                    "questionnaire": questionnaire,
                    "assessment": {},
                    "missing": [],
                    "complete": False,
                    "status": "collecting",
                }},
            })
            yield f"event: panel_complete\ndata: {event}\n\n"
        except ValueError as exc:
            yield make_error(1, str(exc))
        yield make_complete(session_id)
        return

    if not actor_id:
        yield make_error(
            0,
            "Authenticated runtime user identity is required.",
            recoverable=False,
        )
        return
    if not _session_is_owned(customer_id, session_id, actor_id):
        yield make_error(0, "Session not found.", recoverable=False)
        return

    if action == ARCHITECTURE_V3_ACTION:
        try:
            request = payload.get("architecture_v3")
            if not isinstance(request, dict):
                raise ValueError("architecture_v3 object is required")
            tenant_id = _runtime_tenant_id(identity_claims, actor_id)
            adapter = ArchitectureV3RuntimeAdapter(
                _get_ddb().Table(_TABLE),
                tenant_id=tenant_id,
                owner_id=actor_id,
                customer_id=customer_id,
                session_id=session_id,
            )
            result = adapter.execute(request)
            yield make_event("architecture_v3_complete", result)
        except ArchitectureV3Conflict as exc:
            yield make_event("architecture_v3_error", conflict_payload(exc))
        except ValueError as exc:
            log.warning(
                "Architecture v3 request rejected: %s",
                exc,
            )
            yield make_event("architecture_v3_error", {
                "contract_version": "3.0",
                "action": ARCHITECTURE_V3_ACTION,
                "code": "invalid_request",
                "message": str(exc),
            })
        except Exception:
            log.exception("Architecture v3 workspace operation failed")
            yield make_event("architecture_v3_error", {
                "contract_version": "3.0",
                "action": ARCHITECTURE_V3_ACTION,
                "code": "service_error",
                "message": "Architecture v3 workspace operation failed.",
            })
        yield make_complete(session_id)
        return

    if action == "whatif":
        ctx = _load_ctx(customer_id, session_id, actor_id) or PipelineContext(
            session_id=session_id,
            customer_id=customer_id,
        )
        yield make_error(
            2,
            "Legacy score-only what-if is removed. Re-evaluate a cloned v2 AssessmentInput.",
            recoverable=False,
        )
        return

    if payload.get("action") == "drilldown":
        component_id   = payload.get("component_id", "")
        component_name = payload.get("component_name", "")
        ctx = _load_ctx(customer_id, session_id, actor_id) or PipelineContext(
            session_id=session_id,
            customer_id=customer_id,
        )
        component = next(
            (
                item for item in ctx.assessment_result.get("components", [])
                if item.get("id") == component_id
            ),
            None,
        )
        if component:
            traces = [
                item for item in ctx.assessment_result.get("trace", [])
                if item.get("decision") == f"components.{component_id}"
            ]
            sse_data = json.dumps({
                "type": "drilldown_complete",
                "data": {
                    "component_id": component_id,
                    "component_name": component.get("name", component_name),
                    "decision": component,
                    "trace": traces,
                    "read_only": True,
                },
            })
            yield f"event: drilldown_complete\ndata: {sse_data}\n\n"
        else:
            yield make_error(3, f"V2 component not found: {component_id}")
        return

    # ── Restore or create pipeline context ────────────────────────────────
    ctx = _load_ctx(customer_id, session_id, actor_id) or PipelineContext(
        session_id=session_id,
        customer_id=customer_id,
    )

    # Structured v2 assessments bypass the LLM tool loop. The LLM explains
    # decisions; it does not sequence or make deterministic architecture choices.
    if payload.get("assessment_input"):
        try:
            assessment = AssessmentInput.model_validate(payload["assessment_input"])
            overrides = [
                OverrideRecord.model_validate(item).model_copy(update={
                    "author": actor_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                for item in (payload.get("overrides") or [])
            ]
            result = DecisionEngine().assess(assessment, overrides)
            async for event in run_v2_assessment(ctx, assessment, result):
                yield event
            _save_ctx(ctx, actor_id)
        except Exception as exc:
            log.exception("V2 assessment failed")
            yield make_error(1, f"Assessment validation failed: {exc}")
        yield make_complete(session_id)
        return

    # Records created before v2 are intentionally read-only. Their missing
    # evidence cannot be safely inferred into the new decision contract.
    if ctx.schema_version == "1.0":
        if ctx.blueprint_md:
            event = json.dumps({
                "type": "panel_complete",
                "data": {"step": 10, "panel_type": "blueprint", "data": {
                    "schema_version": "1.0",
                    "pattern_id": ctx.pattern_id,
                    "pattern_name": ctx.pattern_id.split(":")[-1].title(),
                    "confidence": ctx.confidence,
                    "markdown": ctx.blueprint_md,
                    "components_count": len(ctx.components),
                    "phases_count": len(ctx.phases),
                    "services_count": len(ctx.service_map),
                    "antipatterns_count": len(ctx.antipatterns),
                    "innovations_count": len(ctx.innovations),
                    "industry": ctx.industry,
                    "compliance_regime": str(ctx.answers.get("compliance_regime", "")),
                    "export_ready": True,
                    "cost_estimate": ctx.cost_estimate or None,
                    "read_only": True,
                }},
            })
            yield f"event: panel_complete\ndata: {event}\n\n"
            yield make_complete(session_id)
            return
        yield make_error(
            1,
            "This incomplete v1 assessment cannot be migrated safely. Start a new v2 session.",
            recoverable=False,
        )
        yield make_complete(session_id)
        return

    # ── P5: Load customer history for new sessions ─────────────────────────
    # On the first interaction (no pattern yet), check for prior completed
    # sessions so the agent can reference them in conversation.
    if not ctx.customer_history and not ctx.pattern_id:
        history = _load_customer_history(customer_id, session_id, actor_id)
        if history:
            ctx.customer_history = history
            log.info("Loaded customer history for %s: %s", customer_id, history[:80])

    if payload.get("answers"):
        yield make_error(
            1,
            "Legacy flat intake payloads are not accepted. Submit schema_version 2.0 assessment_input.",
            recoverable=False,
        )
        yield make_complete(session_id)
        return

    # If history exists, surface it so the agent can reference it naturally
    if ctx.customer_history and not ctx.pattern_id:
        user_message = (
            f"[Customer context: {ctx.customer_history}]\n\n"
            + user_message
        )

    # ── Panel events side channel ──────────────────────────────────────────
    # Tools write SSE strings here; _merge_streams yields them to the client
    # concurrently with agent text events.
    panel_queue: asyncio.Queue[str] = asyncio.Queue()

    # ── AgentCore Memory session manager ──────────────────────────────────
    # Provides STM (conversation history across invocations under the same
    # session ID) and LTM (customer context across sessions).
    session_manager = get_memory_session_manager(agentcore_session_id, actor_id)

    # ── Build tools and agent ─────────────────────────────────────────────
    tools = make_pipeline_tools(ctx, panel_queue, session_manager=session_manager)

    model = BedrockModel(model_id=_MODEL_ID, streaming=True)
    agent = Agent(
        model=model,
        tools=tools,
        system_prompt=_load_system_prompt(),
        session_manager=session_manager,
    )

    # ── Stream merged output ───────────────────────────────────────────────
    try:
        async for sse_event in _merge_streams(agent.stream_async(user_message), panel_queue):
            yield sse_event
    finally:
        # Persist updated context so the next turn picks up where we left off
        try:
            _save_ctx(ctx, actor_id)
        except Exception as exc:
            log.warning("Failed to persist pipeline context: %s", exc)

    yield make_complete(session_id)


if __name__ == "__main__":
    app.run()
