"""Step 8 — Phasing: topological sort of components into P0-P3 roadmap."""
from __future__ import annotations
from typing import AsyncIterator

from agent.graph_loader import get_graph
from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_panel_complete,
    make_step_transition,
)


async def run_phasing(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Compute phased implementation roadmap via topological sort.

    Yields:
      - panel_update
      - panel_complete (timeline data)
      - chat_message
      - step_transition (8 → 9 / blueprint)
    """
    ctx.current_step = 8
    graph = get_graph()

    yield make_panel_update(8, "phase_timeline", {"status": "computing", "progress": 20})

    phases = graph.compute_phases(ctx.components)
    ctx.phases = phases

    yield make_panel_update(8, "phase_timeline", {"status": "computing", "progress": 80})

    # Compute totals
    total_components = sum(len(p["components"]) for p in phases)
    non_empty_phases = [p for p in phases if p["components"]]

    yield make_panel_update(8, "phase_timeline", {"status": "complete", "progress": 100})

    # Derive cross-phase dependencies from component dependency lists
    comp_to_phase: dict[str, str] = {}
    for p in phases:
        for comp in p["components"]:
            comp_to_phase[comp["name"]] = p["id"]

    seen_deps: set[tuple] = set()
    cross_dependencies = []
    for p in phases:
        for comp in p["components"]:
            for dep_name in comp.get("dependencies", []):
                dep_phase = comp_to_phase.get(dep_name)
                if dep_phase and dep_phase != p["id"]:
                    key = (dep_phase, p["id"])
                    if key not in seen_deps:
                        seen_deps.add(key)
                        cross_dependencies.append({
                            "from": dep_phase,
                            "to": p["id"],
                            "reason": f"{comp['name']} depends on {dep_name}",
                        })

    yield make_panel_complete(8, "phase_timeline", {
        "phases": [
            {
                "id": p["id"],
                "name": p["name"],
                "duration": p["duration"],
                "component_count": len(p["components"]),
                "components": p["components"],
            }
            for p in phases
        ],
        "dependencies": cross_dependencies,
        "total_components": total_components,
        "active_phases": len(non_empty_phases),
    })

    phase_summary = "\n".join(
        f"- **{p['name']}** ({p['duration']}): {len(p['components'])} components"
        for p in non_empty_phases
    )

    yield make_chat_message("assistant", (
        f"Implementation roadmap generated across **{len(non_empty_phases)} phases**:\n\n"
        f"{phase_summary}\n\n"
        f"Generating your executive blueprint summary..."
    ))

    yield make_step_transition(8, 9, "Assembling blueprint...")
