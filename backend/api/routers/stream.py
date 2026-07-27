"""Session interaction endpoints — local-dev SSE streaming.

SSE streaming in production is handled directly by the frontend via AgentCore Runtime.
The /run endpoint here is for local development only (no AgentCore / no Strands Agent).
It implements a deterministic state machine that mirrors the agent's pipeline logic.
"""
from __future__ import annotations
import asyncio
import json
import logging
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
    }


def _ctx_from_dict(data: dict, session_id: str, customer_id: str):
    from skills.base import PipelineContext
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
    from skills.base import PipelineContext, make_chat_message, make_complete, make_error
    from skills import (
        run_intake, run_scoring, run_component_selection,
        run_innovation, run_compliance, run_service_mapping,
        run_antipattern_check, run_phasing, run_cost_estimation, run_blueprint,
    )

    # Parse structured params
    try:
        parsed_answers = json.loads(answers) if answers.strip() not in ("{}", "") else {}
    except json.JSONDecodeError:
        parsed_answers = {}

    try:
        pain_list: list = json.loads(pain_points) if pain_points.strip() not in ("[]", "") else []
    except json.JSONDecodeError:
        pain_list = [p.strip() for p in pain_points.split(",") if p.strip()]

    # Load or create pipeline context
    session_data = db.get_session(customer_id, session_id)
    ctx_data = (session_data or {}).get("pipeline_ctx")
    if ctx_data:
        ctx = _ctx_from_dict(ctx_data, session_id, customer_id)
    else:
        ctx = PipelineContext(session_id=session_id, customer_id=customer_id)

    # Merge incoming data into context
    if parsed_answers:
        ctx.answers.update(parsed_answers)
    if industry:
        ctx.industry = industry
    if pain_list:
        ctx.pain_points = pain_list

    # Determine which pipeline steps to run
    pattern_override = _detect_pattern_override(user_message)

    if parsed_answers or not ctx.pattern_id:
        mode = "intake_and_score"
    elif ctx.pattern_id and not ctx.components:
        if pattern_override or _is_confirmation(user_message):
            mode = "full_pipeline"
        else:
            mode = "question"
    elif ctx.blueprint_md:
        mode = "question"
    else:
        # Mid-pipeline (e.g. user changed an answer) — re-run from current incomplete step
        mode = "resume_pipeline"

    async def stream() -> AsyncIterator[bytes]:
        try:
            if mode == "intake_and_score":
                user_msg_json = json.dumps({
                    "answers": ctx.answers,
                    "industry": ctx.industry,
                    "pain_points": ctx.pain_points,
                })
                async for ev in run_intake(ctx, user_msg_json):
                    yield ev.encode(); await asyncio.sleep(0)
                async for ev in run_scoring(ctx):
                    yield ev.encode(); await asyncio.sleep(0)

            elif mode in ("full_pipeline", "resume_pipeline"):
                if pattern_override:
                    ctx.pattern_id = pattern_override
                    ctx.confidence = 0.8

                # Only run steps that haven't completed yet
                remaining = []
                if not ctx.components:        remaining.append(run_component_selection)
                if not ctx.innovations:       remaining.append(run_innovation)
                if not ctx.compliance_notes:  remaining.append(run_compliance)
                if not ctx.service_map:       remaining.append(run_service_mapping)
                if not ctx.antipatterns:      remaining.append(run_antipattern_check)
                if not ctx.phases:            remaining.append(run_phasing)
                if not ctx.cost_estimate:     remaining.append(run_cost_estimation)
                if not ctx.blueprint_md:      remaining.append(run_blueprint)

                for step_fn in remaining:
                    async for ev in step_fn(ctx):
                        yield ev.encode(); await asyncio.sleep(0)

            else:  # question
                reply = (
                    f'[Local dev] Received: "{user_message}". '
                    "In production the Strands Agent answers from conversation context."
                )
                yield make_chat_message("assistant", reply).encode()
                await asyncio.sleep(0)

            yield make_complete(session_id).encode()

        except Exception as exc:
            logger.exception("Pipeline error in local-dev /run")
            yield make_error(ctx.current_step, str(exc)).encode()

        finally:
            try:
                db.update_session(customer_id, session_id, {"pipeline_ctx": _ctx_to_dict(ctx)})
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
    from skills.base import PipelineContext
    from skills.whatif_skill import run_whatif

    overrides = body.get("overrides", {})
    session_data = db.get_session(customer_id, session_id)
    ctx_data = (session_data or {}).get("pipeline_ctx")
    if ctx_data:
        ctx = _ctx_from_dict(ctx_data, session_id, customer_id)
    else:
        ctx = PipelineContext(session_id=session_id, customer_id=customer_id)

    try:
        payload = await run_whatif(ctx, overrides)
        return JSONResponse(content=payload)
    except Exception as exc:
        logger.exception("What-if error for session=%s", session_id)
        raise HTTPException(status_code=500, detail=str(exc))


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
    from skills.base import PipelineContext
    from skills.drilldown_skill import run_drilldown

    session_data = db.get_session(customer_id, session_id)
    ctx_data = (session_data or {}).get("pipeline_ctx")
    if ctx_data:
        ctx = _ctx_from_dict(ctx_data, session_id, customer_id)
    else:
        ctx = PipelineContext(session_id=session_id, customer_id=customer_id)

    try:
        payload = await run_drilldown(ctx, component_id, component_name)
        return JSONResponse(content=payload)
    except Exception as exc:
        logger.exception("Drilldown error for component=%s", component_id)
        raise HTTPException(status_code=500, detail=str(exc))
