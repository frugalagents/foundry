"""Step 8.5 — Cost Estimation: calculate monthly platform costs from graph cost models.

Pure deterministic skill — no LLM call. Reads cost_model and implementation
metadata from each component (now embedded in graph.json), applies tier multipliers
and scale factors from the user's intake answers, and produces a structured
cost breakdown panel that the frontend renders as an interactive cost dashboard.
"""
from __future__ import annotations
from typing import AsyncIterator

from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_panel_complete,
    make_step_transition,
)

# ── Tier multipliers ──────────────────────────────────────────────────────────
# Tier 2 adds more capabilities (approval workflows, distributed traces, etc.)
# Tier 3 adds advanced ML-based features, typically much more compute-intensive.
TIER_MULTIPLIER = {1: 1.0, 2: 1.6, 3: 2.8}

# ── Scale estimation from intake answers ─────────────────────────────────────
# Maps lob_count answer → estimated agent count for cost interpolation.
_LOB_TO_AGENT_COUNT = {
    "1":      50,
    "2":      50,
    "1-2":    50,
    "2-5":   200,
    "3-5":   200,
    "6-10":  500,
    "10+":  1500,
    "11+":  1500,
}

# Maps agent count → at_scale key suffix used in cost_model.at_scale dicts.
def _scale_key(agent_count: int) -> str:
    if agent_count <= 100:
        return "100"
    if agent_count <= 500:
        return "500"
    if agent_count <= 1000:
        return "1000"
    return "5000"


def _find_at_scale_cost(at_scale: dict, key_suffix: str) -> float | None:
    """Look up a cost from at_scale dict whose key contains the suffix."""
    for k, v in at_scale.items():
        if key_suffix in k:
            return float(v)
    return None


def _compute_component_cost(comp: dict, agent_count: int) -> float:
    """Return estimated monthly cost (USD) for a single component."""
    cm = comp.get("cost_model")
    if not cm:
        return 0.0

    tier = comp.get("final_tier", 1)
    multiplier = TIER_MULTIPLIER.get(tier, 1.0)

    # Try at_scale lookup first
    at_scale = cm.get("at_scale", {})
    if at_scale:
        key = _scale_key(agent_count)
        cost = _find_at_scale_cost(at_scale, key)
        if cost is not None:
            return cost * multiplier

    # Fall back to base_monthly_usd
    base = cm.get("base_monthly_usd", 0)
    return base * multiplier


def _format_usd(amount: float) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:.0f}"


async def run_cost_estimation(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Calculate monthly and annual cost estimates for the full platform blueprint.

    Reads cost_model + implementation from ctx.components (populated by graph engine),
    applies tier multipliers and scale factors from ctx.answers, and emits a structured
    cost breakdown panel with per-component, per-phase, and total rollup.

    Step number: 8.5 (runs between build_phase_roadmap and generate_blueprint).
    """
    ctx.current_step = 9  # Re-uses step 9 slot before blueprint (9 → blueprint)

    yield make_panel_update(9, "cost_estimate", {"status": "calculating", "progress": 10})

    # Determine agent count from intake
    lob_raw = ctx.answers.get("lob_count", ctx.answers.get("team_count", "2-5"))
    agent_count = _LOB_TO_AGENT_COUNT.get(str(lob_raw).strip(), 200)

    # Per-component cost breakdown
    line_items: list[dict] = []
    total_monthly = 0.0

    for comp in ctx.components:
        cm = comp.get("cost_model") or {}
        impl = comp.get("implementation") or {}

        monthly = _compute_component_cost(comp, agent_count)
        total_monthly += monthly

        line_items.append({
            "id": comp["id"],
            "name": comp["name"],
            "layer": comp.get("layer", ""),
            "tier": comp.get("final_tier", 1),
            "monthly_usd": round(monthly, 0),
            "monthly_fmt": _format_usd(monthly),
            "aws_service": comp.get("aws_service", ""),
            "cost_drivers": cm.get("cost_drivers", ""),
            "unit": cm.get("unit", ""),
            "weeks_min": impl.get("weeks_min", 1),
            "weeks_max": impl.get("weeks_max", 4),
            "team_size": impl.get("team_size", 2),
            "role_mix": impl.get("role_mix", ""),
            "complexity": impl.get("complexity", "medium"),
            "cdk_construct": impl.get("cdk_construct", ""),
            "workshop_hint": impl.get("workshop_hint", ""),
            "engagement_pattern": impl.get("engagement_pattern", ""),
        })

    yield make_panel_update(9, "cost_estimate", {"status": "calculating", "progress": 60})

    # Compliance cost uplift
    compliance = ctx.answers.get("compliance_regime", "")
    compliance_uplift_pct = 0
    compliance_note = ""
    if "HIPAA" in compliance:
        compliance_uplift_pct += 15
        compliance_note += "HIPAA adds ~15% uplift (content filtering, audit logging). "
    if "SOX" in compliance or "PCI" in compliance:
        compliance_uplift_pct += 10
        compliance_note += "SOX/PCI adds ~10% uplift (formal verification, immutable audit trail). "
    if "FedRAMP" in compliance:
        compliance_uplift_pct += 20
        compliance_note += "FedRAMP adds ~20% uplift (GovCloud deployment, continuous monitoring). "

    compliance_uplift_usd = total_monthly * (compliance_uplift_pct / 100)
    total_monthly_with_compliance = total_monthly + compliance_uplift_usd
    annual_usd = total_monthly_with_compliance * 12

    # Implementation timeline rollup
    total_weeks_min = max(item["weeks_min"] for item in line_items) if line_items else 0
    total_weeks_max = max(item["weeks_max"] for item in line_items) if line_items else 0
    # Full build includes all phases serially — P0 completes before P1, etc.
    phase_weeks = _rollup_phase_weeks(ctx.phases, line_items)

    # Savings model — cost without intelligent routing/caching
    cost_engine_comp = next(
        (c for c in ctx.components if "cost" in c["id"].lower()), None
    )
    has_cost_engine = cost_engine_comp is not None
    unoptimized_llm_usd = _estimate_unoptimized_llm(agent_count)
    optimized_llm_usd = unoptimized_llm_usd * 0.35  # 65% savings from routing + cache
    llm_savings_usd = unoptimized_llm_usd - optimized_llm_usd if has_cost_engine else 0

    ctx.cost_estimate = {
        "agent_count_assumed": agent_count,
        "line_items": line_items,
        "subtotal_platform_monthly": round(total_monthly, 0),
        "compliance_uplift_usd": round(compliance_uplift_usd, 0),
        "compliance_uplift_pct": compliance_uplift_pct,
        "compliance_note": compliance_note.strip(),
        "total_monthly_usd": round(total_monthly_with_compliance, 0),
        "total_annual_usd": round(annual_usd, 0),
        "total_monthly_fmt": _format_usd(total_monthly_with_compliance),
        "total_annual_fmt": _format_usd(annual_usd),
        "llm_cost_unoptimized_monthly": round(unoptimized_llm_usd, 0),
        "llm_cost_optimized_monthly": round(optimized_llm_usd, 0),
        "llm_savings_monthly": round(llm_savings_usd, 0),
        "llm_savings_annual": round(llm_savings_usd * 12, 0),
        "has_cost_engine": has_cost_engine,
        "phase_timeline_weeks": phase_weeks,
        "total_team_weeks": _estimate_total_team_weeks(line_items),
    }

    yield make_panel_update(9, "cost_estimate", {"status": "complete", "progress": 100})

    yield make_panel_complete(9, "cost_estimate", ctx.cost_estimate)

    # Chat summary with key numbers
    monthly_fmt = _format_usd(total_monthly_with_compliance)
    annual_fmt = _format_usd(annual_usd)
    savings_line = ""
    if has_cost_engine and llm_savings_usd > 0:
        savings_line = (
            f" The Cost Engine alone saves "
            f"**{_format_usd(llm_savings_usd * 12)}/year** through intelligent model routing."
        )

    yield make_chat_message("assistant", (
        f"**Cost estimate complete.** "
        f"Your {len(ctx.components)}-component platform runs at "
        f"**{monthly_fmt}/month** ({annual_fmt}/year) at ~{agent_count} agents "
        f"across {lob_raw} LOB(s).{savings_line}\n\n"
        f"Full breakdown is in the cost panel. Generating blueprint now..."
    ))

    yield make_step_transition(9, 10, "Assembling executive blueprint...")


def _rollup_phase_weeks(phases: list[dict], line_items: list[dict]) -> list[dict]:
    """Map components to their phase and compute per-phase timeline."""
    comp_by_name = {item["name"]: item for item in line_items}
    result = []
    for phase in phases:
        if not phase.get("components"):
            continue
        comp_names = [c.get("name", c) if isinstance(c, dict) else c
                      for c in phase["components"]]
        weeks_max = max(
            (comp_by_name.get(n, {}).get("weeks_max", 2) for n in comp_names),
            default=2
        )
        result.append({
            "phase_id": phase["id"],
            "duration_label": phase.get("duration", f"{weeks_max} weeks"),
            "weeks": weeks_max,
            "components": comp_names,
        })
    return result


def _estimate_total_team_weeks(line_items: list[dict]) -> int:
    """Rough FTE-week estimate: sum team_size * avg_weeks across all components."""
    total = 0
    for item in line_items:
        avg_weeks = (item["weeks_min"] + item["weeks_max"]) / 2
        total += int(item["team_size"] * avg_weeks)
    return total


def _estimate_unoptimized_llm(agent_count: int) -> float:
    """
    Estimate monthly Bedrock cost WITHOUT intelligent routing (naive all-Sonnet).
    Assumes 50 invocations/agent/day, 1500 avg tokens/call (input+output).
    Claude Sonnet 4.5: ~$3/M input, $15/M output. Blended: ~$6/M tokens.
    """
    invocations_per_month = agent_count * 50 * 30
    tokens_per_call = 1500
    total_tokens = invocations_per_month * tokens_per_call
    return (total_tokens / 1_000_000) * 6.0
