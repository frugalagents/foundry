"""Step 9 — Blueprint Assembly: executive summary generated via Bedrock converse_stream.

No inner Agent is created here — this is a pure pipeline skill (async generator)
that calls Bedrock directly, exactly like all other pipeline steps.  Creating a
second Strands Agent with the same session_manager as the outer pipeline agent
causes an agent_id uniqueness violation at the AgentCore Memory level.
"""
from __future__ import annotations
import json
import os
from typing import AsyncIterator

import boto3

from . import kb_utils
from .base import (
    PipelineContext,
    make_chat_stream,
    make_panel_update,
    make_panel_complete,
    make_complete,
)

_REGION   = os.environ.get("AWS_REGION", "us-east-1")
_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

PATTERN_DISPLAY = {
    "pattern:centralized":  "Centralized AI Platform",
    "pattern:federated":    "Federated AI Platform",
    "pattern:mesh":         "Decentralized Data Mesh",
    "pattern:economy":      "Platform Economy Model",
}

BLUEPRINT_SYSTEM_PROMPT = """You are an enterprise AI architecture advisor.
Your task is to write a concise, executive-level blueprint summary (400-500 words).

Structure:
1. **Executive Summary** — 2-3 sentences on the strategic recommendation
2. **Architecture Pattern** — Why this pattern was chosen
3. **Key Components** — 3-5 highest-value components
4. **Implementation Timeline** — Phase overview
5. **Risk Considerations** — Top 2-3 risks/mitigations
6. **Next Steps** — Concrete actions for the next 30 days

Tone: authoritative, concise, McKinsey-style. No filler phrases.
Use markdown with bold headers."""


def _build_blueprint_prompt(ctx: PipelineContext) -> str:
    pattern_name = PATTERN_DISPLAY.get(ctx.pattern_id, ctx.pattern_id)
    confidence_pct = int(ctx.confidence * 100)

    top_components = [c["name"] for c in ctx.components[:5]]
    comp_str = ", ".join(top_components) if top_components else "core platform components"

    phase_strs = [
        f"{p['id']} ({p['duration']}): {len(p['components'])} components"
        for p in ctx.phases if p["components"]
    ]
    phases_str = "\n".join(phase_strs) if phase_strs else "Standard 4-phase rollout"

    blocked_ap = [a["name"] for a in ctx.antipatterns if a["status"] == "blocked"]
    risks_str = ", ".join(blocked_ap[:3]) if blocked_ap else "No critical blockers identified"

    # Cost section — include quantified numbers if available
    cost_section = ""
    ce = ctx.cost_estimate
    if ce:
        monthly_fmt = ce.get("total_monthly_fmt", "")
        annual_fmt = ce.get("total_annual_fmt", "")
        savings = ce.get("llm_savings_annual", 0)
        agents = ce.get("agent_count_assumed", 0)
        compliance_note = ce.get("compliance_note", "")
        cost_section = (
            f"\n\n**Quantified Cost Model**:\n"
            f"- Platform monthly cost: {monthly_fmt} (~{agents} agents)\n"
            f"- Annual platform cost: {annual_fmt}\n"
        )
        if savings > 0:
            from .cost_estimation_skill import _format_usd
            cost_section += f"- LLM routing savings (annual): {_format_usd(savings)}\n"
        if compliance_note:
            cost_section += f"- Compliance cost note: {compliance_note}\n"

        # Top 3 most expensive components
        line_items = sorted(ce.get("line_items", []), key=lambda x: x.get("monthly_usd", 0), reverse=True)
        if line_items:
            cost_section += "\nTop cost drivers:\n"
            for li in line_items[:3]:
                cost_section += f"  - {li['name']} (T{li['tier']}): {li['monthly_fmt']}/month — {li['cost_drivers'][:80]}\n"

    kb_section = ""
    if kb_utils.is_configured():
        kb_query = (
            f"enterprise AI platform blueprint {ctx.industry} "
            f"{ctx.answers.get('autonomy_model', '')} "
            f"{ctx.answers.get('governance_model', '')} {ctx.pattern_id}"
        )
        kb_text = kb_utils.retrieve_text(kb_query, top_k=3)
        if kb_text:
            kb_section = f"\n\n**Reference Knowledge**:\n{kb_text}"

    history_section = (
        f"\n\n**Previous Engagement Context**:\n{ctx.customer_history}"
        if ctx.customer_history
        else ""
    )

    return (
        f"Generate a blueprint for this enterprise AI platform engagement:\n\n"
        f"**Organization**: {ctx.industry or 'Enterprise'} industry\n"
        f"**Recommended Pattern**: {pattern_name} ({confidence_pct}% confidence)\n"
        f"**Pain Points**: {', '.join(ctx.pain_points) if ctx.pain_points else 'General platform improvement'}\n"
        f"**Key Components**: {comp_str}\n"
        f"**Total Components**: {len(ctx.components)}\n"
        f"**Compliance**: {ctx.answers.get('compliance_regime', 'Standard')}\n"
        f"**Autonomy Model**: {ctx.answers.get('autonomy_model', 'Hybrid')}\n\n"
        f"**Implementation Phases**:\n{phases_str}\n\n"
        f"**Risk Flags**: {risks_str}"
        f"{cost_section}"
        f"{history_section}"
        f"{kb_section}\n\n"
        f"Write the executive blueprint summary. Where cost figures are provided above, "
        f"cite them directly (e.g. '$X/month', '$Y/year') — do not generalize or omit them."
    )


async def run_blueprint(ctx: PipelineContext, session_manager=None) -> AsyncIterator[str]:
    """
    Generate executive blueprint by calling Bedrock converse_stream directly.

    No inner Agent is created — this is a plain async generator skill,
    consistent with all other pipeline steps.

    Yields:
      - panel_update
      - chat_stream (delta streaming)
      - panel_complete (full blueprint payload)
      - complete
    """
    ctx.current_step = 10

    yield make_panel_update(10, "blueprint", {"status": "generating", "progress": 10})

    prompt = _build_blueprint_prompt(ctx)

    yield make_panel_update(10, "blueprint", {"status": "generating", "progress": 30})

    # Call Bedrock converse_stream directly — no Agent, no session conflict.
    client = boto3.client("bedrock-runtime", region_name=_REGION)
    full_text = ""

    try:
        response = client.converse_stream(
            modelId=_MODEL_ID,
            system=[{"text": BLUEPRINT_SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1024, "temperature": 0.3},
        )

        stream = response.get("stream")
        if stream:
            for event in stream:
                delta = (
                    event.get("contentBlockDelta", {})
                    .get("delta", {})
                    .get("text", "")
                )
                if delta:
                    full_text += delta
                    yield make_chat_stream(delta, done=False)

    except Exception as exc:
        # Fallback: emit a structured blueprint from context without LLM
        import logging
        logging.getLogger(__name__).warning("Bedrock converse_stream failed: %s", exc)
        full_text = _fallback_blueprint(ctx)
        yield make_chat_stream(full_text, done=False)

    yield make_chat_stream("", done=True)
    ctx.blueprint_md = full_text

    yield make_panel_update(10, "blueprint", {"status": "complete", "progress": 100})

    pattern_name = PATTERN_DISPLAY.get(ctx.pattern_id, ctx.pattern_id)

    ce = ctx.cost_estimate
    yield make_panel_complete(10, "blueprint", {
        "pattern_id": ctx.pattern_id,
        "pattern_name": pattern_name,
        "confidence": ctx.confidence,
        "markdown": full_text,
        "components_count": len(ctx.components),
        "phases_count": len([p for p in ctx.phases if p["components"]]),
        "services_count": len(ctx.service_map),
        "antipatterns_count": len(ctx.antipatterns),
        "industry": ctx.industry,
        "compliance_regime": ctx.answers.get("compliance_regime", ""),
        "innovations_count": len(ctx.innovations),
        "export_ready": bool(full_text),
        # Quantified cost data for the frontend dashboard
        "cost_estimate": ce if ce else None,
    })

    yield make_complete(ctx.session_id)


def _fallback_blueprint(ctx: PipelineContext) -> str:
    """Structured blueprint assembled from context — used when Bedrock call fails."""
    pattern_name = PATTERN_DISPLAY.get(ctx.pattern_id, ctx.pattern_id)
    conf = int(ctx.confidence * 100)
    top_comps = ", ".join(c["name"] for c in ctx.components[:5]) or "—"
    phases = [p for p in ctx.phases if p["components"]]

    lines = [
        f"## Executive Summary",
        f"Recommendation: adopt the **{pattern_name}** for {ctx.industry or 'this enterprise'}.",
        f"Pattern confidence: {conf}%. All {len(ctx.components)} required components have been mapped.",
        "",
        f"## Architecture Pattern",
        f"**{pattern_name}** was selected based on your intake profile across autonomy model, governance structure, and scale requirements.",
        "",
        f"## Key Components",
    ]
    for c in ctx.components[:5]:
        lines.append(f"- **{c['name']}** (T{c['final_tier']}) — {c.get('aws_service', '')}")
    lines += [
        "",
        "## Implementation Timeline",
    ]
    for p in phases:
        lines.append(f"- **{p['id']}** ({p.get('duration', 'TBD')}): {len(p['components'])} components")
    lines += [
        "",
        "## Risk Considerations",
        f"- {len(ctx.antipatterns)} anti-pattern(s) evaluated; {sum(1 for a in ctx.antipatterns if a['status'] == 'prevented')} prevented by selected components.",
        "",
        "## Next Steps",
        "1. Confirm architecture pattern and component tier selections.",
        "2. Stand up Phase 0 infrastructure (IAM, VPC, AgentCore runtime).",
        "3. Onboard first LOB pilot within 30 days.",
    ]
    return "\n".join(lines)
