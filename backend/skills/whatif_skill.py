"""P4 What-If Scenarios — re-score with hypothetical intake overrides (local dev)."""
from __future__ import annotations

from .base import PipelineContext
from agent.graph_loader import get_graph
from agent.graph_engine import PATTERN_AXIS, SIMPLICITY_AXIS

PATTERN_DISPLAY = {
    "pattern:centralized": "Centralized Platform",
    "pattern:federated":   "Federated Platform",
    "pattern:mesh":        "Data Mesh / Decentralized",
    "pattern:economy":     "Platform Economy",
}
PATTERN_COLORS = {
    "pattern:centralized": "#3B82F6",
    "pattern:federated":   "#10B981",
    "pattern:mesh":        "#F59E0B",
    "pattern:economy":     "#8B5CF6",
}
AXIS_LABELS = ["Centralization", "Federation", "Mesh", "Economy", "Simplicity"]


async def run_whatif(ctx: PipelineContext, overrides: dict) -> dict:
    whatif_answers = {**ctx.answers, **overrides}
    graph = get_graph()
    raw_scores = graph.compute_pattern_scores(whatif_answers)
    scores = graph.apply_laws(raw_scores, whatif_answers)
    whatif_pattern_id, whatif_confidence = graph.select_pattern(scores)
    signals = graph.compute_scoring_signals(whatif_answers, whatif_pattern_id)

    valid_scores = {pid: sd for pid, sd in scores.items() if sd["total"] > -100}
    max_total = max((sd["total"] for sd in valid_scores.values()), default=1.0) or 1.0

    radar_datasets = []
    for pid, score_data in valid_scores.items():
        own_axis = PATTERN_AXIS.get(pid)
        normalized_axes = []
        for j in range(5):
            if j == own_axis:
                normalized_axes.append(round((score_data["total"] / max_total) * 10, 2))
            elif j == SIMPLICITY_AXIS and own_axis != SIMPLICITY_AXIS:
                raw = score_data["axes"][j]
                normalized_axes.append(round((raw / max_total) * 10, 2) if raw else 2.0)
            else:
                cross = score_data["axes"][j]
                if cross > 0:
                    normalized_axes.append(round((cross / max_total) * 5, 2))
                else:
                    own_frac = score_data["total"] / max_total
                    normalized_axes.append(round(max(2.0 - own_frac * 1.5, 0.5), 2))
        radar_datasets.append({
            "pattern_id": pid,
            "name": PATTERN_DISPLAY.get(pid, pid),
            "scores": normalized_axes,
            "total": round(score_data["total"], 4),
            "selected": pid == whatif_pattern_id,
            "color": PATTERN_COLORS.get(pid, "#6B7280"),
        })

    valid_sorted = sorted(valid_scores.items(), key=lambda x: x[1]["total"], reverse=True)
    runner_up = None
    if len(valid_sorted) > 1:
        ru_id, ru_data = valid_sorted[1]
        runner_up = {"pattern_id": ru_id, "pattern_name": PATTERN_DISPLAY.get(ru_id, ru_id), "total": round(ru_data["total"], 4)}

    original_pattern_id = ctx.pattern_id or whatif_pattern_id
    return {
        "original_pattern_id":   original_pattern_id,
        "original_pattern_name": PATTERN_DISPLAY.get(original_pattern_id, original_pattern_id),
        "original_confidence":   round(ctx.confidence, 3),
        "whatif_pattern_id":     whatif_pattern_id,
        "whatif_pattern_name":   PATTERN_DISPLAY.get(whatif_pattern_id, whatif_pattern_id),
        "whatif_confidence":     round(whatif_confidence, 3),
        "pattern_changed":       whatif_pattern_id != original_pattern_id,
        "confidence_delta":      round(whatif_confidence - ctx.confidence, 3),
        "overrides":             overrides,
        "patterns":              radar_datasets,
        "axes":                  AXIS_LABELS,
        "signals":               signals,
        "runner_up":             runner_up,
    }
