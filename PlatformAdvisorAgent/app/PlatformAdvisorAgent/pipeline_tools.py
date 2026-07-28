"""
Pipeline tools — @tool-decorated wrappers around each pipeline skill.

Each tool:
  - Is callable by the Strands Agent via its tool-use loop
  - Closes over a shared PipelineContext (mutable, carries all step outputs)
  - Drains the skill's async generator into panel_queue so panel events
    reach the frontend concurrently while the agent is running
  - Returns structured JSON so the agent can reason about results and
    decide what to call next (or answer questions from context)

Usage:
    tools = make_pipeline_tools(ctx, panel_queue, session_manager)
    agent = Agent(model=model, tools=tools, ...)
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Optional

from strands import tool

from pipeline_skills.base import PipelineContext
from pipeline_skills import (
    run_intake,
    run_scoring,
    run_component_selection,
    run_innovation,
    run_compliance,
    run_service_mapping,
    run_antipattern_check,
    run_phasing,
    run_cost_estimation,
    run_blueprint,
)

log = logging.getLogger(__name__)

# Scored spine + archetype filter (discovery-methodology §3). These must be present
# before scoring. "not_sure" is an accepted value that contributes zero pressure.
# Secondary/current-state fields (governance_model, intake_maturity, observability,
# auth_identity, stack_preference) are optional and drive non-scoring outputs.
_INTAKE_REQUIRED = [
    "archetype", "autonomy_model", "lob_count", "team_expertise",
    "cloud_posture", "data_gravity", "cost_sensitivity", "compliance_regime",
]

_VALID_PATTERNS = {
    "pattern:federated", "pattern:centralized",
    "pattern:mesh", "pattern:economy",
}


def _missing_intake(answers: dict) -> list[str]:
    """Required fields that are absent or empty. An empty string / empty list
    (e.g. a field the user un-skipped without re-answering) counts as missing."""
    def _empty(v) -> bool:
        return v is None or v == "" or (isinstance(v, (list, dict)) and len(v) == 0)
    return [k for k in _INTAKE_REQUIRED if k not in answers or _empty(answers[k])]


async def _drain(gen, queue: asyncio.Queue) -> None:
    """Drain an async generator into the panel queue."""
    async for event in gen:
        await queue.put(event)


def make_pipeline_tools(
    ctx: PipelineContext,
    panel_queue: asyncio.Queue,
    session_manager=None,
) -> list:
    """
    Factory — returns @tool-decorated functions closing over ctx, panel_queue,
    and session_manager for this invocation.
    """

    @tool
    async def collect_intake_answers(
        answers_json: str,
        industry: str = "",
        pain_points_json: str = "[]",
    ) -> str:
        """
        Process the user's intake answers for the 12 structured questions.
        Call this when the user provides their organizational constraints,
        or call again with updated values whenever any answer changes.

        answers_json: JSON object mapping question IDs to answer values
        industry: the user's industry (e.g. "Financial Services", "Healthcare")
        pain_points_json: JSON array of pain-point strings
        """
        try:
            answers = json.loads(answers_json)
        except json.JSONDecodeError:
            answers = {}
        try:
            pain_points = json.loads(pain_points_json)
        except json.JSONDecodeError:
            pain_points = []

        ctx.answers.update(answers)
        if industry:
            ctx.industry = industry
        if pain_points:
            ctx.pain_points = pain_points

        user_message = json.dumps({
            "answers": ctx.answers,
            "industry": ctx.industry,
            "pain_points": ctx.pain_points,
        })

        await _drain(run_intake(ctx, user_message), panel_queue)

        missing = _missing_intake(ctx.answers)
        return json.dumps({
            "ok": True,
            "answers_collected": len(ctx.answers),
            "industry": ctx.industry,
            "pain_points": ctx.pain_points,
            "missing_fields": missing,
            "ready_to_score": len(missing) == 0,
        })

    @tool
    async def score_architecture_patterns() -> str:
        """
        Deterministically score the 4 architecture patterns (Centralized,
        Federated, Mesh, Economy) against the collected intake answers using
        weighted graph traversal. Emits a radar chart panel to the UI.

        Call after collect_intake_answers is complete, or whenever any
        intake answer changes — all downstream steps must re-run after this.
        Requires all 12 intake fields to be present.
        """
        missing = _missing_intake(ctx.answers)
        if missing:
            return json.dumps({
                "error": f"Intake incomplete. Missing: {missing}. "
                         "Call collect_intake_answers first."
            })

        await _drain(run_scoring(ctx), panel_queue)

        pattern_name = {
            "pattern:federated": "Federated Platform",
            "pattern:centralized": "Centralized Platform",
            "pattern:mesh": "Data Mesh",
            "pattern:economy": "Platform Economy",
        }.get(ctx.pattern_id, ctx.pattern_id)
        conf_pct = int(ctx.confidence * 100)
        return json.dumps({
            "recommended_pattern": ctx.pattern_id,
            "confidence": round(ctx.confidence, 3),
            "next_action": (
                f"The radar chart panel has been sent. "
                f"Reply with EXACTLY ONE sentence asking the user to confirm: "
                f"'Proceed with {pattern_name} ({conf_pct}% confidence)?' "
                f"Do NOT output a table or scoring breakdown — the panel shows everything."
            ),
        })

    @tool
    async def select_platform_components(pattern_override: str = "") -> str:
        """
        Determine fabric components and their tiers for the selected pattern.
        Applies constraint-based tier elevations and industry compliance forcing.
        Emits an architecture diagram panel to the UI.

        Call after the user confirms the scored pattern.

        pattern_override: optional — one of "pattern:federated",
            "pattern:centralized", "pattern:mesh", "pattern:economy".
            Supply this when the user explicitly requests a different pattern.
        """
        if pattern_override and pattern_override in _VALID_PATTERNS:
            ctx.pattern_id = pattern_override
            ctx.confidence = 0.8
            log.info("Pattern overridden to %s", pattern_override)

        if not ctx.pattern_id:
            return json.dumps({
                "error": "No pattern selected. Call score_architecture_patterns first."
            })

        await _drain(run_component_selection(ctx), panel_queue)

        return json.dumps({
            "pattern_used": ctx.pattern_id,
            "components_selected": len(ctx.components),
            "next_action": (
                f"Architecture diagram sent to panel ({len(ctx.components)} components). "
                f"Reply with ONE sentence confirming and then immediately call apply_innovation_overlay. "
                f"Do NOT list components in chat."
            ),
        })

    @tool
    async def apply_innovation_overlay() -> str:
        """
        Match user pain points to emerging capabilities and recent innovations.
        Validates GA/Preview/Emerging status via AWS documentation.
        Emits an innovation overlay panel showing before/after architecture.

        Call after select_platform_components. Re-call if pain points change.
        """
        if not ctx.components:
            return json.dumps({
                "error": "No components. Call select_platform_components first."
            })

        await _drain(run_innovation(ctx), panel_queue)

        return json.dumps({
            "innovations_applied": len(ctx.innovations),
            "next_action": (
                f"Innovation overlay panel sent ({len(ctx.innovations)} innovations). "
                f"Reply with ONE sentence and call apply_compliance_overlay. "
                f"Do NOT list innovations in chat."
            ),
        })

    @tool
    async def apply_compliance_overlay() -> str:
        """
        Apply industry compliance controls based on the compliance frameworks
        selected in intake (HIPAA, SOC2, GDPR, PCI-DSS, FedRAMP).
        Forces minimum component tiers where regulation requires.

        Call after apply_innovation_overlay. Re-call if industry or
        compliance answers change.
        """
        await _drain(run_compliance(ctx), panel_queue)

        return json.dumps({
            "regime": ctx.answers.get("compliance_regime", "General Best Practices"),
            "law_notes_count": len(ctx.compliance_notes),
            "next_action": (
                "Compliance overlay panel sent. "
                "Reply with ONE sentence and call map_aws_services. "
                "Do NOT list compliance controls in chat."
            ),
        })

    @tool
    async def map_aws_services() -> str:
        """
        Map each platform component at its determined tier to specific AWS
        services. Fetches relevant workshops and documentation links.
        Emits a service map panel to the UI.

        Call after apply_compliance_overlay.
        """
        if not ctx.components:
            return json.dumps({
                "error": "No components. Call select_platform_components first."
            })

        await _drain(run_service_mapping(ctx), panel_queue)

        return json.dumps({
            "services_mapped": len(ctx.service_map),
            "next_action": (
                f"Service map panel sent ({len(ctx.service_map)} services). "
                f"Reply with ONE sentence and call check_antipatterns. "
                f"Do NOT output a service table in chat."
            ),
        })

    @tool
    async def check_antipatterns() -> str:
        """
        Detect architecture anti-patterns triggered by the current pattern
        and constraints. Determines which are already prevented by selected
        components and which require the user's attention.
        Emits a risk cards panel to the UI.

        Call after map_aws_services.
        """
        await _drain(run_antipattern_check(ctx), panel_queue)

        warnings = [a for a in ctx.antipatterns if a.get("status") == "warning"]
        blocked = [a for a in ctx.antipatterns if a.get("status") == "blocked"]
        prevented = [a for a in ctx.antipatterns if a.get("status") == "prevented"]

        return json.dumps({
            "total_detected": len(ctx.antipatterns),
            "already_prevented": len(prevented),
            "critical_blockers_count": len(blocked),
            "next_action": (
                f"Risk cards panel sent ({len(ctx.antipatterns)} detected, {len(prevented)} prevented). "
                f"Reply with ONE sentence and call build_phase_roadmap. "
                f"Do NOT list anti-patterns in chat."
            ),
        })

    @tool
    async def build_phase_roadmap() -> str:
        """
        Compute the P0-P3 implementation roadmap using topological sort of
        component dependencies. Assigns components to phases with effort
        estimates and dependency arrows.
        Emits a phase timeline panel to the UI.

        Call after check_antipatterns.
        """
        if not ctx.components:
            return json.dumps({
                "error": "No components. Call select_platform_components first."
            })

        await _drain(run_phasing(ctx), panel_queue)

        return json.dumps({
            "phases_count": len([p for p in ctx.phases if p.get("components")]),
            "next_action": (
                "Phase timeline panel sent. "
                "Reply with ONE sentence and call estimate_costs. "
                "Do NOT output a roadmap table in chat."
            ),
        })

    @tool
    async def estimate_costs() -> str:
        """
        Calculate the quantified cost estimate for the full platform blueprint.
        Uses real AWS pricing data from the knowledge graph to produce per-component
        monthly costs, compliance uplifts, LLM spend projections with and without
        intelligent routing, and total annual platform cost.
        Emits a cost estimate panel to the UI.

        Call after build_phase_roadmap. Required before generate_blueprint.
        """
        if not ctx.components:
            return json.dumps({
                "error": "No components. Call select_platform_components first."
            })
        if not ctx.phases:
            return json.dumps({
                "error": "No phases. Call build_phase_roadmap first."
            })

        await _drain(run_cost_estimation(ctx), panel_queue)

        ce = ctx.cost_estimate
        return json.dumps({
            "cost_estimate_generated": True,
            "total_monthly_usd": ce.get("total_monthly_usd", 0),
            "total_annual_usd": ce.get("total_annual_usd", 0),
            "total_monthly_fmt": ce.get("total_monthly_fmt", ""),
            "total_annual_fmt": ce.get("total_annual_fmt", ""),
            "llm_savings_annual": ce.get("llm_savings_annual", 0),
            "next_action": (
                "Cost estimate panel sent. "
                "Reply with ONE sentence acknowledging the cost summary and call generate_blueprint. "
                "Do NOT output a cost table in chat — the panel shows everything."
            ),
        })

    @tool
    async def generate_blueprint() -> str:
        """
        Assemble all pipeline outputs into a final executive blueprint.
        Uses an LLM to generate a McKinsey-style executive summary covering
        pattern rationale, key components, phasing, risks, and next steps.
        Emits the final blueprint panel to the UI.

        Only call this after all prior steps have completed successfully:
        collect_intake_answers → score_architecture_patterns →
        select_platform_components → apply_innovation_overlay →
        apply_compliance_overlay → map_aws_services →
        check_antipatterns → build_phase_roadmap → estimate_costs → generate_blueprint.
        """
        missing = []
        if not ctx.pattern_id:
            missing.append("pattern (score_architecture_patterns)")
        if not ctx.components:
            missing.append("components (select_platform_components)")
        if not ctx.phases:
            missing.append("phasing (build_phase_roadmap)")
        if not ctx.cost_estimate:
            missing.append("cost estimate (estimate_costs)")
        if missing:
            return json.dumps({
                "error": f"Cannot generate blueprint. Incomplete steps: {', '.join(missing)}"
            })

        await _drain(run_blueprint(ctx, session_manager=session_manager), panel_queue)

        return json.dumps({
            "blueprint_generated": True,
            "next_action": (
                "Blueprint panel populated. "
                "Reply with EXACTLY: 'Blueprint complete — see the right panel for the full document. "
                "Use the Export buttons to download PDF or PPTX.' "
                "Do NOT reproduce any part of the blueprint in chat."
            ),
        })

    return [
        collect_intake_answers,
        score_architecture_patterns,
        select_platform_components,
        apply_innovation_overlay,
        apply_compliance_overlay,
        map_aws_services,
        check_antipatterns,
        build_phase_roadmap,
        estimate_costs,
        generate_blueprint,
    ]
