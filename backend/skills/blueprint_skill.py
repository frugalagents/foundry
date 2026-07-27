"""Step 9 — Blueprint Assembly: LLM-generated executive summary via Strands Agent."""
from __future__ import annotations
from typing import AsyncIterator

from strands import Agent
from strands.models import BedrockModel

from .base import (
    PipelineContext,
    make_chat_stream,
    make_panel_update,
    make_panel_complete,
    make_complete,
)

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
        f"**Risk Flags**: {risks_str}\n\n"
        f"Write the executive blueprint summary."
    )


async def run_blueprint(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Generate executive blueprint using Strands Agent with Bedrock (Claude Sonnet).

    Yields:
      - panel_update
      - chat_stream (delta streaming)
      - panel_complete (full blueprint payload)
      - complete
    """
    ctx.current_step = 10

    yield make_panel_update(10, "blueprint", {"status": "generating", "progress": 10})

    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        streaming=True,
        max_tokens=1024,
    )
    agent = Agent(
        model=model,
        system_prompt=BLUEPRINT_SYSTEM_PROMPT,
    )

    prompt = _build_blueprint_prompt(ctx)
    full_text = ""

    yield make_panel_update(10, "blueprint", {"status": "generating", "progress": 30})

    async for event in agent.stream_async(prompt):
        if hasattr(event, "data") and isinstance(event.data, str):
            delta = event.data
            full_text += delta
            yield make_chat_stream(delta, done=False)
        elif isinstance(event, str):
            full_text += event
            yield make_chat_stream(event, done=False)

    yield make_chat_stream("", done=True)
    ctx.blueprint_md = full_text

    yield make_panel_update(10, "blueprint", {"status": "complete", "progress": 100})

    pattern_name = PATTERN_DISPLAY.get(ctx.pattern_id, ctx.pattern_id)

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
        "export_ready": True,
        "cost_estimate": ctx.cost_estimate if ctx.cost_estimate else None,
    })

    yield make_complete(ctx.session_id)
