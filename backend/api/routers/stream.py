"""Session interaction endpoints — local-dev SSE streaming.

SSE streaming in production is handled directly by the frontend via AgentCore Runtime.
The /run endpoint here is for local development only (no AgentCore / no Strands Agent).
It implements a deterministic state machine that mirrors the agent's pipeline logic.
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from api.middleware.auth import get_current_user
from api.db import dynamodb as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["stream"])

CurrentUser = Annotated[dict, Depends(get_current_user)]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _ctx_to_dict(ctx) -> dict:
    return {
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
        "current_step":     ctx.current_step,
        "cost_estimate":    ctx.cost_estimate,
        "schema_version":   ctx.schema_version,
        "assessment_input": ctx.assessment_input,
        "assessment_result": ctx.assessment_result,
        "overrides":        ctx.overrides,
    }


def _ctx_from_dict(data: dict, session_id: str, customer_id: str):
    from pipeline_skills.base import PipelineContext
    ctx = PipelineContext(session_id=session_id, customer_id=customer_id)
    ctx.answers          = data.get("answers", {})
    ctx.industry         = data.get("industry", "")
    ctx.pain_points      = data.get("pain_points", [])
    ctx.pattern_id       = data.get("pattern_id", "")
    ctx.confidence       = data.get("confidence", 0.0)
    ctx.axis_scores      = data.get("axis_scores", [])
    ctx.components       = data.get("components", [])
    ctx.innovations      = data.get("innovations", [])
    ctx.compliance_notes = data.get("compliance_notes", [])
    ctx.service_map      = data.get("service_map", [])
    ctx.antipatterns     = data.get("antipatterns", [])
    ctx.phases           = data.get("phases", [])
    ctx.blueprint_md     = data.get("blueprint_md", "")
    ctx.current_step     = data.get("current_step", 0)
    ctx.cost_estimate    = data.get("cost_estimate", {})
    ctx.schema_version   = data.get("schema_version", "1.0")
    ctx.assessment_input = data.get("assessment_input", {})
    ctx.assessment_result = data.get("assessment_result", {})
    ctx.overrides        = data.get("overrides", [])
    return ctx


_CONFIRM_WORDS = {"yes", "confirm", "continue", "proceed", "correct", "right",
                  "looks good", "go ahead", "agree", "approved", "accept"}

_PATTERN_MAP = {
    "federated":   "pattern:federated",
    "centralized": "pattern:centralized",
    "mesh":        "pattern:mesh",
    "economy":     "pattern:economy",
}


def _detect_pattern_override(msg: str) -> str | None:
    msg_lower = msg.lower()
    trigger_words = ("use ", "switch to ", "choose ", "override ", "select ")
    if any(t in msg_lower for t in trigger_words):
        for name, pid in _PATTERN_MAP.items():
            if name in msg_lower:
                return pid
    return None


def _is_confirmation(msg: str) -> bool:
    msg_lower = msg.lower()
    return any(w in msg_lower for w in _CONFIRM_WORDS)


# ── Local-dev SSE stream ──────────────────────────────────────────────────────

@router.get("/{customer_id}/{session_id}/run")
async def run_session(
    customer_id: str,
    session_id: str,
    user_message: str = Query(default=""),
    answers: str = Query(default="{}"),
    industry: str = Query(default=""),
    pain_points: str = Query(default="[]"),
    assessment_input: str = Query(default=""),
    overrides: str = Query(default="[]"),
    token: str = Query(default=""),
):
    """
    Local-dev unified SSE stream. Single endpoint handles all interaction types:
    - Intake submission  (user_message + answers/industry/pain_points params)
    - Pattern confirm    (user_message = "Yes, continue" / "Use Centralized instead")
    - Free-text question (user_message = any text — returns placeholder, no LLM in local dev)

    In production the frontend calls AgentCore Runtime directly and this endpoint
    is never reached.

    State machine:
      answers provided OR ctx has no pattern → intake + scoring
      pattern scored, not confirmed           → check for confirmation / override
      pattern confirmed, pipeline incomplete  → run remaining steps from current state
      blueprint complete                      → return placeholder chat reply
    """
    from advisor_core import AssessmentInput, DecisionEngine
    from advisor_core.models import OverrideRecord
    from pipeline_skills.base import PipelineContext, make_chat_message, make_complete, make_error
    from pipeline_skills.v2_assessment_skill import run_v2_assessment

    # Load or create pipeline context
    session_data = db.get_session(customer_id, session_id)
    ctx_data = (session_data or {}).get("pipeline_ctx")
    if ctx_data:
        ctx = _ctx_from_dict(ctx_data, session_id, customer_id)
    else:
        ctx = PipelineContext(session_id=session_id, customer_id=customer_id)

    async def stream() -> AsyncIterator[bytes]:
        try:
            if assessment_input:
                assessment = AssessmentInput.model_validate_json(assessment_input)
                override_values = [
                    OverrideRecord.model_validate(item).model_copy(update={
                        "author": "local-user",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    for item in json.loads(overrides or "[]")
                ]
                result = DecisionEngine().assess(assessment, override_values)
                async for ev in run_v2_assessment(ctx, assessment, result):
                    yield ev.encode()
                    await asyncio.sleep(0)
            elif ctx.schema_version == "1.0":
                yield make_error(
                    1,
                    "This v1 session is read-only. Start a new v2 assessment.",
                    recoverable=False,
                ).encode()
            else:
                reply = (
                    f'[Local dev] Received: "{user_message}". Submit the structured '
                    "v2 assessment form to evaluate architecture decisions."
                )
                yield make_chat_message("assistant", reply).encode()
                await asyncio.sleep(0)

            yield make_complete(session_id).encode()

        except Exception as exc:
            logger.exception("Pipeline error in local-dev /run")
            yield make_error(ctx.current_step, str(exc)).encode()

        finally:
            try:
                result = ctx.assessment_result or {}
                evidence_state = {
                    "needs_information": "provisional",
                    "complete": "decision_ready",
                    "overridden": "overridden",
                }.get(result.get("status"), "not_started")
                db.update_session(customer_id, session_id, {
                    "pipeline_ctx": _ctx_to_dict(ctx),
                    "current_step": ctx.current_step,
                    "status": "complete" if ctx.current_step >= 10 else "active",
                    "recommendation": result.get("operating_model") or ctx.pattern_id or "",
                    "evidence_state": evidence_state,
                    "primary_workload": ctx.assessment_input.get("primary_workload", ""),
                })
            except Exception as persist_exc:
                logger.warning("Failed to persist pipeline ctx: %s", persist_exc)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{customer_id}/{session_id}/whatif")
async def whatif_scenario(
    customer_id: str,
    session_id: str,
    body: dict,
    token: str = Query(default=""),
):
    """
    P4 What-If: re-score with hypothetical intake answer overrides.
    Returns the full radar diff payload as JSON.
    Local dev only — production uses AgentCore directly (action:"whatif").
    """
    raise HTTPException(
        status_code=410,
        detail="Legacy score-only what-if is removed. Re-evaluate a cloned v2 AssessmentInput.",
    )


@router.get("/{customer_id}/{session_id}/drilldown")
async def drilldown_component(
    customer_id: str,
    session_id: str,
    component_id: str = Query(...),
    component_name: str = Query(default=""),
    token: str = Query(default=""),
):
    """
    On-demand component deep-dive for the Depth on Demand (P1) feature.

    Returns a single JSON payload with: why_needed, tier_options, your_cost,
    CDK snippet, implementation details, workshop hint, engagement pattern.

    In production, the frontend calls AgentCore directly (action:"drilldown")
    and receives an SSE drilldown_complete event. This REST endpoint is for
    local development only.
    """
    session_data = db.get_session(customer_id, session_id)
    ctx_data = (session_data or {}).get("pipeline_ctx")
    result = (ctx_data or {}).get("assessment_result", {})
    component = next(
        (item for item in result.get("components", []) if item.get("id") == component_id),
        None,
    )
    if not component:
        raise HTTPException(status_code=404, detail="V2 component not found")
    traces = [
        item for item in result.get("trace", [])
        if item.get("decision") == f"components.{component_id}"
    ]
    return JSONResponse(content={
        "component_id": component_id,
        "component_name": component.get("name", component_name),
        "decision": component,
        "trace": traces,
        "read_only": True,
    })
