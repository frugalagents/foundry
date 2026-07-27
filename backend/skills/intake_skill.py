"""Step 1 — Intake: validate and store structured answers from the user."""
from __future__ import annotations
from typing import AsyncIterator

from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_panel_complete,
    make_step_transition,
)

QUESTION_LABELS = {
    "autonomy_model": "Autonomy Model",
    "lob_count": "Lines of Business",
    "governance_model": "Governance Model",
    "cloud_posture": "Cloud Posture",
    "stack_preference": "Stack Preference",
    "auth_identity": "Identity Setup",
    "data_gravity": "Data Location",
    "observability": "Observability",
    "intake_maturity": "AI Maturity",
    "agent_purpose": "Agent Purpose",
    "team_expertise": "Team Expertise",
    "cost_sensitivity": "Cost Sensitivity",
    "compliance_regime": "Compliance Regime",
    "industry": "Industry",
    "pain_points": "Pain Points",
}


async def run_intake(
    ctx: PipelineContext, user_message: str
) -> AsyncIterator[str]:
    """
    Validate the submitted intake form answers and load them into ctx.

    Yields SSE events:
      - panel_update (progress)
      - chat_message (confirmation narrative)
      - panel_complete (structured intake summary)
      - step_transition (1 → 2)
    """
    ctx.current_step = 1

    yield make_panel_update(1, "intake_form", {"status": "validating", "progress": 0})

    # Parse answers from user_message if provided as JSON, else ctx.answers already set
    import json
    if user_message.strip().startswith("{"):
        try:
            data = json.loads(user_message)
            ctx.answers = data.get("answers", ctx.answers)
            ctx.industry = data.get("industry", ctx.answers.get("industry", ctx.industry))
            ctx.pain_points = data.get("pain_points", ctx.answers.get("pain_points", ctx.pain_points))
        except json.JSONDecodeError:
            pass

    if isinstance(ctx.pain_points, str):
        ctx.pain_points = [ctx.pain_points]

    yield make_panel_update(1, "intake_form", {"status": "validating", "progress": 40})

    # Build summary of answered questions
    answered = []
    for key, label in QUESTION_LABELS.items():
        val = ctx.answers.get(key)
        if val:
            answered.append(f"- **{label}**: {val}")

    yield make_panel_update(1, "intake_form", {"status": "complete", "progress": 100})

    summary_text = "\n".join(answered)
    industry_str = ctx.industry or ctx.answers.get("industry", "Enterprise")
    pains_str = ", ".join(ctx.pain_points) if ctx.pain_points else "Not specified"

    narrative = (
        f"I've captured your intake responses. Here's what I recorded:\n\n"
        f"{summary_text}\n\n"
        f"**Industry**: {industry_str}\n"
        f"**Key Pain Points**: {pains_str}\n\n"
        f"Now running the deterministic scoring engine to evaluate your architecture pattern..."
    )

    yield make_chat_message("assistant", narrative)

    yield make_panel_complete(1, "intake_form", {
        "answers": ctx.answers,
        "industry": industry_str,
        "pain_points": ctx.pain_points,
        "answered_count": len([v for v in ctx.answers.values() if v]),
    })

    yield make_step_transition(1, 2, "Running pattern scoring engine...")
