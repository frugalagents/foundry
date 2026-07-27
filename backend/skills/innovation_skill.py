"""Step 4 — Innovation Overlay: match pain points to emerging capabilities."""
from __future__ import annotations
from typing import AsyncIterator

from agent.graph_loader import get_graph
from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_card_add,
    make_panel_complete,
    make_step_transition,
)

STATUS_BADGE = {
    "ga":       "GA",
    "preview":  "Preview",
    "emerging": "Emerging",
}


async def run_innovation(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Identify applicable innovations from the knowledge graph.
    In production this also calls Bedrock Knowledge Base MCP for verification.

    Yields:
      - panel_update
      - card_add (per innovation)
      - panel_complete
      - chat_message
      - step_transition (4 → 5)
    """
    ctx.current_step = 4
    graph = get_graph()

    yield make_panel_update(4, "innovation_overlay", {"status": "scanning", "progress": 10})

    innovations = graph.get_innovations_for_pain_points(ctx.pain_points, ctx.pattern_id)
    ctx.innovations = innovations

    total = max(len(innovations), 1)
    for i, inn in enumerate(innovations):
        progress = int(15 + (i / total) * 65)
        yield make_panel_update(4, "innovation_overlay", {
            "status": "scanning",
            "progress": progress,
            "current": inn["name"],
        })

        yield make_card_add(
            card_id=inn["id"],
            card_type="innovation",
            payload={
                "name": inn["name"],
                "date_emerged": inn["date_emerged"],
                "constraint_solved": inn["constraint_solved"],
                "replaces": inn.get("replaces"),
                "enables": inn.get("enables"),
                "aws_implementation": inn["aws_implementation"],
                "status": STATUS_BADGE.get(inn["status"], inn["status"].upper()),
                "verified_via_mcp": inn.get("verified_via_mcp", False),
                "enabled": inn.get("enabled", True),
            },
        )

    yield make_panel_update(4, "innovation_overlay", {"status": "complete", "progress": 100})

    ga_count = sum(1 for i in innovations if i["status"] == "ga")
    preview_count = sum(1 for i in innovations if i["status"] == "preview")
    emerging_count = sum(1 for i in innovations if i["status"] == "emerging")

    yield make_panel_complete(4, "innovation_overlay", {
        "innovations": innovations,
        "counts": {
            "total": len(innovations),
            "ga": ga_count,
            "preview": preview_count,
            "emerging": emerging_count,
        },
        "before_architecture": _build_arch_diagram(ctx.components, ctx.pattern_id),
        "after_architecture": _build_after_arch(ctx, innovations),
    })

    yield make_chat_message("assistant", (
        f"Found **{len(innovations)} innovation opportunities** relevant to your pain points:\n\n"
        + "\n".join(
            f"- **{i['name']}** ({STATUS_BADGE.get(i['status'], i['status'].upper())}): "
            f"{i['constraint_solved']}"
            for i in innovations[:4]
        )
        + f"\n\n{'...' if len(innovations) > 4 else ''}"
        f"\n\nProceed to compliance check →"
    ))

    yield make_step_transition(4, 5, "Running compliance analysis...")


def _build_arch_diagram(components: list[dict], pattern_id: str) -> dict:
    """Convert component list to ArchitectureDiagramData shape."""
    layers: dict[str, list] = {}
    for comp in components:
        layers.setdefault(comp.get("layer", "Foundation"), []).append({
            "name": comp["name"],
            "base_tier": comp.get("base_tier", comp.get("final_tier", 1)),
            "final_tier": comp.get("final_tier", 1),
            "elevation_reason": comp.get("elevation_reason"),
            "category": comp.get("category", ""),
        })
    return {
        "layers": [{"name": layer, "components": comps} for layer, comps in layers.items()],
        "pattern": pattern_id,
        "streaming": False,
    }


def _build_after_arch(ctx: PipelineContext, innovations: list[dict]) -> dict:
    """After-innovation architecture — same base with any enabled components added."""
    base = _build_arch_diagram(ctx.components, ctx.pattern_id)
    enabled_comps = [
        {
            "name": inn["enables"],
            "base_tier": 3,
            "final_tier": 3,
            "elevation_reason": f"Enabled by {inn['name']}",
            "category": "Innovation",
        }
        for inn in innovations
        if inn.get("enables")
    ]
    if enabled_comps:
        return {**base, "layers": base["layers"] + [{"name": "Innovations", "components": enabled_comps}]}
    return base
