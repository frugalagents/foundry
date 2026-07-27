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
from pathlib import Path
from typing import AsyncIterator, Optional

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

from pipeline_skills.base import (
    PipelineContext,
    make_error,
    make_complete,
    make_chat_stream,
)
from memory.session import get_memory_session_manager
from pipeline_tools import make_pipeline_tools

app = BedrockAgentCoreApp()
log = app.logger

# ── Config ────────────────────────────────────────────────────────────────────

_TABLE = os.environ.get("DYNAMODB_TABLE", "platform-advisor-main")
_REGION = os.environ.get("AWS_REGION", "us-east-1")
_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

_ddb = None
_cached_system_prompt: str | None = None


# ── DynamoDB helpers ──────────────────────────────────────────────────────────

def _get_ddb():
    global _ddb
    if _ddb is None:
        _ddb = boto3.resource("dynamodb", region_name=_REGION)
    return _ddb


def _save_ctx(ctx: PipelineContext) -> None:
    """Persist PipelineContext to DynamoDB for next-turn retrieval."""
    table = _get_ddb().Table(_TABLE)
    table.put_item(Item={
        "PK": f"CUST#{ctx.customer_id}",
        "SK": f"SESSION#{ctx.session_id}#PIPELINE_CTX",
        "entity_type": "PipelineContext",
        "ctx_json": json.dumps({
            "session_id":       ctx.session_id,
            "customer_id":      ctx.customer_id,
            "answers":          ctx.answers,
            "industry":         ctx.industry,
            "pain_points":      ctx.pain_points,
            "pattern_id":       ctx.pattern_id,
            "confidence":       ctx.confidence,
            "axis_scores":      ctx.axis_scores,
            "components":       ctx.components,
            "innovations":      ctx.innovations,
            "compliance_notes": ctx.compliance_notes,
            "service_map":      ctx.service_map,
            "antipatterns":     ctx.antipatterns,
            "phases":           ctx.phases,
            "blueprint_md":     ctx.blueprint_md,
            "customer_history": ctx.customer_history,
            "current_step":     ctx.current_step,
            "cost_estimate":    ctx.cost_estimate,
        }),
    })


def _load_customer_history(customer_id: str, current_session_id: str) -> str:
    """Query prior completed advisory sessions for this customer and return a summary."""
    try:
        from boto3.dynamodb.conditions import Key, Attr
        table = _get_ddb().Table(_TABLE)
        resp = table.query(
            KeyConditionExpression=(
                Key("PK").eq(f"CUST#{customer_id}") &
                Key("SK").begins_with("SESSION#")
            ),
            FilterExpression=Attr("entity_type").eq("PipelineContext"),
        )
        items = resp.get("Items", [])
        history_parts = []
        for item in items:
            sk = item.get("SK", "")
            # SK: SESSION#{session_id}#PIPELINE_CTX
            sk_parts = sk.split("#")
            if len(sk_parts) < 3:
                continue
            sess_id = sk_parts[1]
            if sess_id == current_session_id:
                continue
            try:
                d = json.loads(item.get("ctx_json", "{}"))
            except Exception:
                continue
            if not d.get("blueprint_md"):
                continue  # only completed sessions
            pattern = d.get("pattern_id", "").split(":")[-1].title()
            answers = d.get("answers", {})
            lobs = answers.get("lob_count", "?")
            industry = d.get("industry", "")
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


def _load_ctx(customer_id: str, session_id: str) -> PipelineContext | None:
    """Load a previously saved PipelineContext from DynamoDB."""
    table = _get_ddb().Table(_TABLE)
    resp = table.get_item(Key={
        "PK": f"CUST#{customer_id}",
        "SK": f"SESSION#{session_id}#PIPELINE_CTX",
    })
    item = resp.get("Item")
    if not item:
        return None
    d = json.loads(item["ctx_json"])
    ctx = PipelineContext(session_id=d["session_id"], customer_id=d["customer_id"])
    ctx.answers          = d.get("answers", {})
    ctx.industry         = d.get("industry", "")
    ctx.pain_points      = d.get("pain_points", [])
    ctx.pattern_id       = d.get("pattern_id", "")
    ctx.confidence       = d.get("confidence", 0.0)
    ctx.axis_scores      = d.get("axis_scores", [])
    ctx.components       = d.get("components", [])
    ctx.innovations      = d.get("innovations", [])
    ctx.compliance_notes = d.get("compliance_notes", [])
    ctx.service_map      = d.get("service_map", [])
    ctx.antipatterns     = d.get("antipatterns", [])
    ctx.phases           = d.get("phases", [])
    ctx.blueprint_md     = d.get("blueprint_md", "")
    ctx.customer_history = d.get("customer_history", "")
    ctx.current_step     = d.get("current_step", 0)
    ctx.cost_estimate    = d.get("cost_estimate", {})
    return ctx


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
            _cached_system_prompt = item["content"]
            return _cached_system_prompt
    except Exception as exc:
        log.warning("Could not load system prompt from DynamoDB: %s", exc)

    # 2. Fall back to file
    prompt_path = (
        Path(__file__).parent.parent.parent.parent
        / "knowledge-base" / "system-prompt.md"
    )
    if prompt_path.exists():
        _cached_system_prompt = prompt_path.read_text()
    else:
        _cached_system_prompt = (
            "You are the Agentic Platform Advisor. "
            "Guide enterprise leaders through AI agent platform strategy."
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
    actor_id             = getattr(context, "user_id", None) or customer_id or "anonymous"

    log.info(
        "invoke: session=%s customer=%s action=%s msg=%.120s",
        session_id, customer_id, payload.get("action", "chat"), user_message,
    )

    # ── Action short-circuits (drilldown, whatif) ─────────────────────────
    # These bypass the Strands agent entirely — pure computation, immediate response.
    action = payload.get("action")

    if action == "whatif":
        from pipeline_skills.whatif_skill import run_whatif
        overrides = payload.get("overrides") or {}
        ctx = _load_ctx(customer_id, session_id) or PipelineContext(
            session_id=session_id,
            customer_id=customer_id,
        )
        try:
            whatif_payload = await run_whatif(ctx, overrides)
            sse_data = json.dumps({"type": "whatif_complete", "data": whatif_payload})
            yield f"event: whatif_complete\ndata: {sse_data}\n\n"
        except Exception as exc:
            log.exception("What-if error")
            yield make_error(0, str(exc))
        return

    if payload.get("action") == "drilldown":
        from pipeline_skills.drilldown_skill import run_drilldown
        component_id   = payload.get("component_id", "")
        component_name = payload.get("component_name", "")
        ctx = _load_ctx(customer_id, session_id) or PipelineContext(
            session_id=session_id,
            customer_id=customer_id,
        )
        try:
            drilldown_payload = await run_drilldown(ctx, component_id, component_name)
            sse_data = json.dumps({
                "type": "drilldown_complete",
                "data": drilldown_payload,
            })
            yield f"event: drilldown_complete\ndata: {sse_data}\n\n"
        except Exception as exc:
            log.exception("Drilldown error for component=%s", component_id)
            yield make_error(0, str(exc))
        return

    # ── Restore or create pipeline context ────────────────────────────────
    ctx = _load_ctx(customer_id, session_id) or PipelineContext(
        session_id=session_id,
        customer_id=customer_id,
    )

    # ── P5: Load customer history for new sessions ─────────────────────────
    # On the first interaction (no pattern yet), check for prior completed
    # sessions so the agent can reference them in conversation.
    if not ctx.customer_history and not ctx.pattern_id:
        history = _load_customer_history(customer_id, session_id)
        if history:
            ctx.customer_history = history
            log.info("Loaded customer history for %s: %s", customer_id, history[:80])

    # Prime context with any data sent directly in the payload.
    # Also surface the answers in the user_message so the agent can pass them
    # verbatim to collect_intake_answers — without this the agent cannot call
    # the tool correctly because the answers are only in ctx, not in the
    # conversation history the model sees.
    intake_provided = False
    if payload.get("answers"):
        ctx.answers.update(payload["answers"])
        intake_provided = True
    if payload.get("industry"):
        ctx.industry = payload["industry"]
    if payload.get("pain_points"):
        ctx.pain_points = payload["pain_points"]

    # If history exists, surface it so the agent can reference it naturally
    if ctx.customer_history and not ctx.pattern_id and not intake_provided:
        user_message = (
            f"[Customer context: {ctx.customer_history}]\n\n"
            + user_message
        )

    if intake_provided and ctx.answers:
        user_message = (
            "Intake form submitted. Call collect_intake_answers with exactly these values:\n"
            f"answers_json={json.dumps(ctx.answers)}\n"
            f"industry={ctx.industry}\n"
            f"pain_points_json={json.dumps(ctx.pain_points)}\n\n"
            "After collect_intake_answers completes, immediately call score_architecture_patterns."
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
            _save_ctx(ctx)
        except Exception as exc:
            log.warning("Failed to persist pipeline context: %s", exc)

    yield make_complete(session_id)


if __name__ == "__main__":
    app.run()
