"""Step 2 — Scoring: deterministic graph-based pattern evaluation."""
from __future__ import annotations
from typing import AsyncIterator

from agent.graph_loader import get_graph
from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_panel_complete,
    make_step_transition,
    make_confirmation_request,
)

PATTERN_DISPLAY = {
    "pattern:centralized":  "Centralized Platform",
    "pattern:federated":    "Federated Platform",
    "pattern:mesh":         "Data Mesh / Decentralized",
    "pattern:economy":      "Platform Economy",
}

AXIS_LABELS = ["Centralization", "Federation", "Mesh", "Economy", "Simplicity"]

PATTERN_COLORS = {
    "pattern:centralized": "#3B82F6",
    "pattern:federated":   "#10B981",
    "pattern:mesh":        "#F59E0B",
    "pattern:economy":     "#8B5CF6",
}


async def run_scoring(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Run deterministic pattern scoring and surface the radar chart.

    Yields:
      - panel_update (progress ticks)
      - panel_complete (radar chart data)
      - chat_message (interpretation)
      - confirmation_request (user confirms/adjusts)
      - step_transition (2 → 3)
    """
    ctx.current_step = 2
    graph = get_graph()

    yield make_panel_update(2, "radar_chart", {"status": "computing", "progress": 10})

    # Compute pattern scores
    raw_scores = graph.compute_pattern_scores(ctx.answers)
    yield make_panel_update(2, "radar_chart", {"status": "computing", "progress": 50})

    # Apply regulatory laws
    scores = graph.apply_laws(raw_scores, ctx.answers)
    yield make_panel_update(2, "radar_chart", {"status": "computing", "progress": 80})

    # Select winning pattern
    pattern_id, confidence = graph.select_pattern(scores)

    ctx.pattern_id = pattern_id
    ctx.confidence = confidence

    # Build radar data (5 axes per pattern)
    radar_datasets = []
    for pid, score_data in scores.items():
        if score_data["total"] <= -100:
            continue
        axes = score_data["axes"]
        if not any(v != 0.0 for v in axes):
            # Fallback: distribute total equally across axes
            axes = [round(score_data["total"] / 5, 3)] * 5
        radar_datasets.append({
            "pattern_id": pid,
            "name": PATTERN_DISPLAY.get(pid, pid),
            "scores": [round(v, 4) for v in axes],
            "total": round(score_data["total"], 4),
            "selected": pid == pattern_id,
            "color": PATTERN_COLORS.get(pid, "#6B7280"),
        })

    yield make_panel_update(2, "radar_chart", {"status": "complete", "progress": 100})

    pattern_name = PATTERN_DISPLAY.get(pattern_id, pattern_id)
    confidence_pct = int(confidence * 100)

    ctx.axis_scores = scores.get(pattern_id, {}).get("axes", [0.0] * 5)

    signals = graph.compute_scoring_signals(ctx.answers, pattern_id)

    valid_sorted = sorted(
        [(pid, sd) for pid, sd in scores.items() if sd["total"] > -100],
        key=lambda x: x[1]["total"], reverse=True
    )
    runner_up = None
    if len(valid_sorted) > 1:
        ru_id, ru_data = valid_sorted[1]
        runner_up = {
            "pattern_id": ru_id,
            "pattern_name": PATTERN_DISPLAY.get(ru_id, ru_id),
            "total": round(ru_data["total"], 4),
        }

    follow_up_questions = _generate_followup_questions(ctx, pattern_id)

    yield make_panel_complete(2, "radar_chart", {
        "recommended_pattern": pattern_id,
        "pattern_name": pattern_name,
        "confidence": confidence,
        "patterns": radar_datasets,
        "axes": AXIS_LABELS,
        "signals": signals,
        "runner_up": runner_up,
        "follow_up_questions": follow_up_questions,
    })

    yield make_chat_message("assistant",
        f"**{pattern_name}** recommended ({confidence_pct}% confidence) — "
        f"see the Pattern Analysis panel for the scoring breakdown. "
        f"Confirm to proceed or choose a different pattern."
    )

    yield make_confirmation_request(
        step=2,
        question=f"Proceed with **{pattern_name}** ({confidence_pct}% confidence)?",
        options=["Confirm", "Choose Federated", "Choose Centralized", "Choose Mesh", "Choose Economy"],
    )


def _generate_followup_questions(ctx: PipelineContext, pattern_id: str) -> list[dict]:
    questions: list[dict] = []
    a = ctx.answers
    lob_count = a.get("lob_count", "")
    autonomy  = a.get("autonomy_model", "")
    compliance = a.get("compliance_regime", "none")
    cost      = a.get("cost_sensitivity", "")
    expertise = a.get("team_expertise", "")

    if pattern_id == "pattern:federated":
        if lob_count in ("10+", "6-10"):
            questions.append({
                "id": "fed_deploy_autonomy",
                "question": f"With {lob_count} LOBs, do they deploy agents via independent pipelines or through a central release gate?",
                "options": ["Independent per-LOB pipelines", "Central release gate", "Mixed — varies by LOB"],
            })
        if compliance not in ("none", ""):
            questions.append({
                "id": "fed_compliance_spine",
                "question": "Will compliance controls be maintained per LOB, or via a shared governance spine?",
                "options": ["Shared compliance spine", "Each LOB owns compliance", "Not yet decided"],
            })
        if not questions and autonomy == "hitl":
            questions.append({
                "id": "fed_hitl_scope",
                "question": "For HITL agents in a federated model, does each LOB define its own human review thresholds?",
                "options": ["Yes, per-LOB thresholds", "One enterprise standard", "Not decided"],
            })

    elif pattern_id == "pattern:centralized":
        if lob_count in ("10+", "6-10"):
            questions.append({
                "id": "central_lob_buy_in",
                "question": f"With {lob_count} LOBs, have they agreed to a central platform team owning deployment gates?",
                "options": ["Yes, all aligned", "Some LOBs will resist", "Change management needed"],
            })
        if autonomy == "full":
            questions.append({
                "id": "central_guardrails",
                "question": "Full-autonomy agents on a centralized platform require strong guardrails — do you have a compliance team to maintain them?",
                "options": ["Yes, team in place", "Will build one in parallel", "Risk accepted for now"],
            })

    elif pattern_id == "pattern:mesh":
        if expertise in ("low", "medium"):
            questions.append({
                "id": "mesh_domain_readiness",
                "question": "Data Mesh requires each domain team to operate as a platform owner — are your domain teams ready?",
                "options": ["Yes, domains are ready", "Needs an enablement program first", "Some domains are, others aren't"],
            })
        if cost == "primary":
            questions.append({
                "id": "mesh_cost_overhead",
                "question": "Mesh architectures carry higher per-domain operational overhead. Have you budgeted for per-team platform engineering?",
                "options": ["Yes, budget allocated", "Will reassess budget", "Cost is a hard constraint"],
            })

    elif pattern_id == "pattern:economy":
        if lob_count in ("1", "2-5"):
            questions.append({
                "id": "economy_scale",
                "question": "Platform Economy delivers most value at scale. With fewer LOBs, would starting with Federated then evolving work?",
                "options": ["Economy is the target state", "Open to Federated as starting point", "Need Economy for external marketplace"],
            })

    return questions[:2]
