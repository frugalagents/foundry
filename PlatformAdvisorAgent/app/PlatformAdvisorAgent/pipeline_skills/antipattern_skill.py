"""Step 7 — Anti-pattern Detection: identify triggered risks and mitigations."""
from __future__ import annotations
from typing import AsyncIterator

from agent_core_engine.graph_loader import get_graph
from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_card_add,
    make_panel_complete,
    make_step_transition,
)

SEVERITY_ORDER = {"blocked": 0, "high": 1, "medium": 2, "low": 3, "warning": 4}


async def run_antipattern_check(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Detect anti-patterns triggered by intake answers and check prevention
    by selected components.

    Yields:
      - panel_update
      - card_add (per anti-pattern)
      - panel_complete
      - chat_message
      - step_transition (7 → 8)
    """
    ctx.current_step = 7
    graph = get_graph()

    yield make_panel_update(7, "risk_cards", {"status": "scanning", "progress": 10})

    antipatterns = graph.get_antipatterns(
        ctx.pattern_id, ctx.answers, ctx.components
    )
    ctx.antipatterns = antipatterns

    # Sort by severity
    antipatterns.sort(key=lambda a: SEVERITY_ORDER.get(a.get("severity", "medium"), 4))

    total = max(len(antipatterns), 1)
    for i, ap in enumerate(antipatterns):
        progress = int(20 + (i / total) * 60)
        yield make_panel_update(7, "risk_cards", {
            "status": "scanning",
            "progress": progress,
            "current": ap["name"],
        })

        card_id = f"ap:{ap['name'].lower().replace(' ', '_')}"
        yield make_card_add(
            card_id=card_id,
            card_type="antipattern",
            payload={
                "name": ap["name"],
                "severity": ap["severity"],
                "status": ap["status"],
                "trigger_condition": ap["trigger_condition"],
                "prevented_by": ap.get("prevented_by"),
                "recommended_fix": ap.get("recommended_fix"),
            },
        )

    yield make_panel_update(7, "risk_cards", {"status": "complete", "progress": 100})

    blocked = [a for a in antipatterns if a["status"] == "blocked"]
    warnings = [a for a in antipatterns if a["status"] == "warning"]
    prevented = [a for a in antipatterns if a["status"] == "prevented"]

    yield make_panel_complete(7, "risk_cards", {
        "risks": antipatterns,
        "summary": {
            "total_detected": len(antipatterns),
            "addressed": len(prevented),
            "requires_attention": len(blocked) + len(warnings),
        },
    })

    if not antipatterns:
        status_msg = "No risks detected."
    elif blocked:
        status_msg = f"{len(blocked)} blocked, {len(warnings)} warnings, {len(prevented)} mitigated."
    else:
        status_msg = f"{len(warnings)} warnings, {len(prevented)} mitigated."

    yield make_chat_message("assistant",
        f"Risk scan complete — {status_msg} See Risk Assessment →"
    )

    yield make_step_transition(7, 8, "Generating implementation phases...")
