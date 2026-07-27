"""Step 2 — Scoring: deterministic graph-based pattern evaluation."""
from __future__ import annotations
from typing import AsyncIterator

from agent_core_engine.graph_loader import get_graph
from agent_core_engine.graph_engine import PATTERN_AXIS, SIMPLICITY_AXIS
from .base import (
    PipelineContext,
    make_panel_update,
    make_panel_complete,
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
    # Normalize to 0-10 scale so RadarSVG polygons are visible (SVG divides by 10)
    valid_scores = {pid: sd for pid, sd in scores.items() if sd["total"] > -100}
    max_total = max((sd["total"] for sd in valid_scores.values()), default=1.0) or 1.0

    radar_datasets = []
    for pid, score_data in valid_scores.items():
        # Derive full 5-axis profile: own axis gets total * 10, others scaled inversely
        own_axis = PATTERN_AXIS.get(pid)
        normalized_axes = []
        for j in range(5):
            if j == own_axis:
                # Own axis: scale to 0-10 based on relative total score
                normalized_axes.append(round((score_data["total"] / max_total) * 10, 2))
            elif j == SIMPLICITY_AXIS and own_axis != SIMPLICITY_AXIS:
                # Simplicity axis: shared signal, scale proportionally
                raw = score_data["axes"][j]
                normalized_axes.append(round((raw / max_total) * 10, 2) if raw else 2.0)
            else:
                # Cross-axes: small base so polygon doesn't collapse to a point
                cross = score_data["axes"][j]
                if cross > 0:
                    normalized_axes.append(round((cross / max_total) * 5, 2))
                else:
                    # Inverse: winning pattern on own axis penalizes cross-pattern axes
                    own_frac = (score_data["total"] / max_total)
                    normalized_axes.append(round(max(2.0 - own_frac * 1.5, 0.5), 2))

        radar_datasets.append({
            "pattern_id": pid,
            "name": PATTERN_DISPLAY.get(pid, pid),
            "scores": normalized_axes,
            "total": round(score_data["total"], 4),
            "selected": pid == pattern_id,
            "color": PATTERN_COLORS.get(pid, "#6B7280"),
        })

    yield make_panel_update(2, "radar_chart", {"status": "complete", "progress": 100})

    pattern_name = PATTERN_DISPLAY.get(pattern_id, pattern_id)
    confidence_pct = int(confidence * 100)

    ctx.axis_scores = scores.get(pattern_id, {}).get("axes", [0.0] * 5)

    signals = graph.compute_scoring_signals(ctx.answers, pattern_id)

    # Build runner-up info
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

    # Confirmation is handled by the outer agent after it receives the tool result.


def _generate_followup_questions(ctx: PipelineContext, pattern_id: str) -> list[dict]:
    """
    Generate 2 probing questions to validate edge cases for the recommended pattern.
    Pure data-driven — no LLM call. Questions are specific to the pattern + key answers.
    """
    questions: list[dict] = []
    a = ctx.answers
    lob_count  = a.get("lob_count", "")
    autonomy   = a.get("autonomy_model", "")
    governance = a.get("governance_model", "")
    compliance = a.get("compliance_regime", "none")
    cost       = a.get("cost_sensitivity", "")
    expertise  = a.get("team_expertise", "")

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
        if expertise == "low":
            questions.append({
                "id": "economy_expertise",
                "question": "Platform Economy requires marketplace governance and multi-tenant agent hosting expertise — do you have that capability?",
                "options": ["Will hire/train for it", "Will partner with a consultancy", "Have the capability already"],
            })

    return questions[:2]
