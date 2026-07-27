"""Step 3 — Component Selection: graph-driven component mapping with tier elevation."""
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

TIER_LABELS = {1: "Tier 1 (Essential)", 2: "Tier 2 (Enhanced)", 3: "Tier 3 (Advanced)"}

PATTERN_RATIONALE = {
    "pattern:federated": (
        "A Federated Platform connects independent LOB agent stacks through a shared "
        "governance and observability spine. Each LOB retains autonomy over its own agents "
        "while the common Registry, Gateway, Policy Engine, and Observability components "
        "enforce enterprise standards and prevent fragmentation."
    ),
    "pattern:centralized": (
        "A Centralized Platform provisions a single shared control plane consumed by all "
        "teams. Components are deployed once, maximizing governance, cost efficiency, and "
        "standardization. Best for organizations with strong central IT and few LOBs."
    ),
    "pattern:mesh": (
        "A Decentralized Data Mesh gives each domain full ownership of its agent stack "
        "with peer-to-peer discovery. No shared control plane — each domain is a "
        "first-class citizen. Requires high technical maturity across every domain."
    ),
    "pattern:economy": (
        "A Platform Economy treats agent capabilities as tradeable services with commercial "
        "APIs. Components expose monetizable endpoints enabling internal chargebacks or "
        "external customer-facing offerings. Requires mature governance before activation."
    ),
}

LAYER_COLORS = {
    "Foundation":      "#3B82F6",
    "Data":            "#10B981",
    "Governance":      "#F59E0B",
    "Shared Services": "#8B5CF6",
    "Experience":      "#EC4899",
    "AgentOps":        "#06B6D4",
}


async def run_component_selection(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Resolve required components from the graph for the selected pattern.

    Yields:
      - panel_update (progress)
      - card_add (per component as they resolve)
      - panel_complete (architecture diagram data)
      - chat_message (summary)
      - step_transition (3 → 4)
    """
    ctx.current_step = 3
    graph = get_graph()

    yield make_panel_update(3, "architecture_diagram", {"status": "resolving", "progress": 5})

    components = graph.get_components_for_pattern(
        ctx.pattern_id, ctx.answers, ctx.industry
    )
    ctx.components = components

    total = max(len(components), 1)
    for i, comp in enumerate(components):
        progress = int(10 + (i / total) * 70)
        yield make_panel_update(3, "architecture_diagram", {
            "status": "resolving",
            "progress": progress,
            "resolving": comp["name"],
        })

        yield make_card_add(
            card_id=comp["id"],
            card_type="component",
            payload={
                "name": comp["name"],
                "category": comp["category"],
                "layer": comp["layer"],
                "tier": comp["final_tier"],
                "tier_label": TIER_LABELS.get(comp["final_tier"], "Tier 1"),
                "elevated": comp["final_tier"] > comp["base_tier"],
                "elevation_reason": comp["elevation_reason"],
                "aws_service": comp["aws_service"],
                "color": LAYER_COLORS.get(comp["layer"], "#6B7280"),
            },
        )

    yield make_panel_update(3, "architecture_diagram", {"status": "complete", "progress": 100})

    # Group by layer for the diagram
    layers: dict[str, list] = {}
    for comp in components:
        layers.setdefault(comp["layer"], []).append({
            "id": comp["id"],
            "name": comp["name"],
            "base_tier": comp["base_tier"],
            "final_tier": comp["final_tier"],
            "category": comp.get("category", ""),
            "aws_service": comp["aws_service"],
            "elevated": comp["final_tier"] > comp["base_tier"],
            "elevation_reason": comp["elevation_reason"],
            "scope": comp.get("scope", "shared_spine"),
        })

    pattern_name = ctx.pattern_id.split(":")[-1].title()
    pattern_rationale = PATTERN_RATIONALE.get(ctx.pattern_id, "")

    yield make_panel_complete(3, "architecture_diagram", {
        "pattern_id": ctx.pattern_id,
        "pattern_name": pattern_name,
        "pattern": pattern_name,
        "pattern_rationale": pattern_rationale,
        "confidence": ctx.confidence,
        "layers": [
            {
                "name": layer,
                "color": LAYER_COLORS.get(layer, "#6B7280"),
                "components": comps,
            }
            for layer, comps in layers.items()
        ],
        "total_components": len(components),
        "tier_counts": {
            "tier1": sum(1 for c in components if c["final_tier"] == 1),
            "tier2": sum(1 for c in components if c["final_tier"] == 2),
            "tier3": sum(1 for c in components if c["final_tier"] == 3),
        },
    })

    elevated_count = sum(1 for c in components if c["final_tier"] > c["base_tier"])
    yield make_chat_message("assistant", (
        f"Selected **{len(components)} components** for the "
        f"**{pattern_name}** architecture across "
        f"**{len(layers)} layers**.\n\n"
        f"{elevated_count} component(s) had their tier elevated based on your "
        f"compliance, industry, or scale requirements.\n\n"
        f"Now scanning for innovation opportunities..."
    ))

    yield make_step_transition(3, 4, "Scanning innovation catalog...")
