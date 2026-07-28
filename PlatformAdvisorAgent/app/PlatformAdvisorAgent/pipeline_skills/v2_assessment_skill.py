"""SSE adapter from the deterministic v2 result to application panels."""
from __future__ import annotations

from typing import AsyncIterator

from advisor_core.models import AssessmentInput, AssessmentResult
from advisor_core.questions import build_questionnaire

from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_complete,
    make_step_transition,
)


def _fmt_usd(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:.0f}"


def _assessment_draft(assessment: AssessmentInput) -> dict:
    raw = assessment.model_dump(mode="json")
    draft = {
        "audience": raw["audience"],
        "primary_workload": raw["primary_workload"],
        "secondary_workloads": raw["secondary_workloads"],
    }
    for group in ("ownership", "risk", "data", "nfr", "current", "economics"):
        for key, value in raw[group].items():
            draft[f"{group}.{key}"] = value
    for key, value in raw["workload_profile"].items():
        if key != "kind":
            draft[f"workload_profile.{key}"] = value
    return draft


def _architecture_payload(result: AssessmentResult) -> dict:
    layers: dict[str, list[dict]] = {}
    for comp in result.components:
        layers.setdefault(comp.layer, []).append({
            "id": comp.id,
            "name": comp.name,
            "base_tier": 1,
            "final_tier": 1,
            "elevation_reason": None,
            "category": comp.layer,
            "aws_service": ", ".join(comp.aws_services),
            "elevated": False,
            "scope": "per_lob" if comp.scope == "per_domain" else "shared_spine",
            "activation_requirements": comp.activation_requirements,
        })
    return {
        "pattern": (result.operating_model or "Undetermined").title(),
        "pattern_id": result.operating_model,
        "pattern_name": result.operating_model,
        "pattern_rationale": (
            "This architecture is derived from the capability ownership matrix, "
            "hard requirements, trust boundaries, and workload-specific scale."
        ),
        "layers": [{"name": name, "components": components} for name, components in layers.items()],
        "topology": result.topology.model_dump(mode="json") if result.topology else None,
    }


def _cost_payload(result: AssessmentResult) -> dict | None:
    if not result.cost:
        return None
    cost = result.cost
    return {
        "currency": cost.currency,
        "price_catalog_date": cost.price_catalog_date,
        "low": cost.low.model_dump(mode="json"),
        "base": cost.base.model_dump(mode="json"),
        "high": cost.high.model_dump(mode="json"),
        "assumptions": cost.assumptions,
        "line_items": cost.line_items,
        # Compatibility fields for exports while the v1 renderer is retired.
        "total_monthly_usd": cost.base.monthly_usd,
        "total_annual_usd": cost.base.annual_usd,
        "total_monthly_fmt": _fmt_usd(cost.base.monthly_usd),
        "total_annual_fmt": _fmt_usd(cost.base.annual_usd),
    }


def _blueprint_markdown(assessment: AssessmentInput, result: AssessmentResult) -> str:
    ownership = "\n".join(
        f"- **{row.capability.replace('_', ' ').title()}**: {row.owner.value}"
        for row in result.ownership_matrix
    )
    requirements = "\n".join(f"- {item.statement}" for item in result.requirements)
    components = "\n".join(
        f"- **{item.name}** ({item.scope}): {', '.join(item.aws_services)}"
        for item in result.components
    )
    risks = "\n".join(
        f"- **{item.scenario}** Residual risk: {item.residual.value}. Treatment: {item.treatment}."
        for item in result.risks
    ) or "- No material scenarios were activated by the supplied evidence."
    roadmap = "\n".join(
        f"- **{phase.id} — {phase.name}** ({phase.duration_weeks[0]}–{phase.duration_weeks[1]} weeks)"
        for phase in result.roadmap
    )
    cost = (
        f"Low {_fmt_usd(result.cost.low.monthly_usd)}, "
        f"base {_fmt_usd(result.cost.base.monthly_usd)}, "
        f"high {_fmt_usd(result.cost.high.monthly_usd)} per month."
        if result.cost else "Blocked until critical sizing evidence is complete."
    )
    return f"""# Platform Architecture Blueprint

## Decision

Primary workload: **{assessment.primary_workload.value}**

Operating model: **{result.operating_model}**

Evidence coverage: **{result.evidence_coverage:.0%}**

## Capability Ownership

{ownership}

## Architecture Requirements

{requirements}

## Components and AWS Mapping

{components}

## Residual Risks

{risks}

## Roadmap

{roadmap}

## Planning Cost

{cost}
"""


async def run_v2_assessment(
    ctx: PipelineContext,
    assessment: AssessmentInput,
    result: AssessmentResult,
) -> AsyncIterator[str]:
    ctx.schema_version = "2.0"
    ctx.assessment_input = assessment.model_dump(mode="json")
    ctx.assessment_result = result.model_dump(mode="json")
    ctx.overrides = [item.model_dump(mode="json") for item in result.overrides]
    ctx.answers = ctx.assessment_input
    ctx.pattern_id = result.operating_model or ""
    ctx.confidence = result.evidence_coverage
    ctx.topology = result.topology.model_dump(mode="json") if result.topology else {}
    ctx.components = [item.model_dump(mode="json") for item in result.components]
    ctx.compliance_notes = [item.model_dump_json() for item in result.controls]
    ctx.antipatterns = [item.model_dump(mode="json") for item in result.risks]
    ctx.phases = [item.model_dump(mode="json") for item in result.roadmap]
    ctx.cost_estimate = _cost_payload(result) or {}

    yield make_panel_complete(1, "intake", {
        "schema_version": "2.0",
        "questionnaire": build_questionnaire(assessment.primary_workload),
        "answers": _assessment_draft(assessment),
        "assessment": ctx.assessment_input,
        "missing": [gap.field for gap in result.missing_evidence],
        "complete": not result.missing_evidence,
        "status": result.status,
    })

    yield make_panel_complete(2, "decision_summary", {
        "status": result.status,
        "evidence_coverage": result.evidence_coverage,
        "missing_evidence": [item.model_dump(mode="json") for item in result.missing_evidence],
        "operating_model": result.operating_model,
        "ownership_matrix": [item.model_dump(mode="json") for item in result.ownership_matrix],
        "topology": result.topology.model_dump(mode="json") if result.topology else None,
        "trace": [item.model_dump(mode="json") for item in result.trace if item.decision in ("operating_model", "topology")],
        "overrides": [item.model_dump(mode="json") for item in result.overrides],
    })

    if result.missing_evidence:
        ctx.current_step = 2
        yield make_chat_message(
            "assistant",
            f"Assessment is provisional. {len(result.missing_evidence)} critical evidence "
            "items must be resolved before a blueprint or cost estimate can be produced.",
        )
        yield make_step_transition(1, 2, "Critical evidence required")
        return

    architecture = _architecture_payload(result)
    yield make_panel_complete(3, "architecture_diagram", architecture)
    yield make_panel_complete(4, "requirements", {
        "requirements": [item.model_dump(mode="json") for item in result.requirements],
        "assumptions": result.assumptions,
    })
    yield make_panel_complete(5, "compliance", {
        "regime": ", ".join(assessment.data.regulations) or "Baseline",
        "controls": [
            {
                "name": item.name,
                "status": "required",
                "description": item.implementation,
                "source": item.source,
            }
            for item in result.controls
        ],
        "counts": {
            "required": len(result.controls),
            "advisory": 0,
            "best_practice": 0,
        },
        "law_notes": [],
    })
    yield make_panel_complete(6, "service_map", {
        "components": [
            {
                "name": item.name,
                "tier": 1,
                "aws_services": [
                    {"name": service, "icon_url": "", "notes": "Deterministic v2 mapping"}
                    for service in item.aws_services
                ],
                "workshops": [],
                "alternatives": [],
            }
            for item in result.components
        ],
    })
    yield make_panel_complete(7, "risk_cards", {
        "risks": [
            {
                "name": item.scenario,
                "severity": "medium" if item.residual.value == "moderate" else item.residual.value if item.residual.value in ("high", "low") else "high",
                "trigger_condition": item.exposure,
                "status": "prevented" if item.residual.value in ("low", "moderate") else "warning",
                "prevented_by": ", ".join(item.controls) or None,
                "recommended_fix": item.treatment,
            }
            for item in result.risks
        ],
        "summary": {
            "total_detected": len(result.risks),
            "addressed": sum(1 for item in result.risks if item.residual.value in ("low", "moderate")),
            "requires_attention": sum(1 for item in result.risks if item.residual.value in ("high", "severe")),
        },
    })
    component_by_id = {item.id: item for item in result.components}
    yield make_panel_complete(8, "phase_timeline", {
        "phases": [
            {
                "id": phase.id,
                "name": phase.name,
                "duration": f"{phase.duration_weeks[0]}–{phase.duration_weeks[1]} weeks",
                "components": [
                    {
                        "name": component_by_id[comp_id].name,
                        "tier": 1,
                        "aws_service": ", ".join(component_by_id[comp_id].aws_services),
                        "effort": "medium",
                        "dependencies": component_by_id[comp_id].dependencies,
                    }
                    for comp_id in phase.component_ids if comp_id in component_by_id
                ],
                "exit_criteria": phase.exit_criteria,
            }
            for phase in result.roadmap
        ],
        "dependencies": [
            {"from": dependency, "to": phase.id, "reason": "Phase prerequisite"}
            for phase in result.roadmap for dependency in phase.dependencies
        ],
    })
    yield make_panel_complete(9, "cost_estimate", _cost_payload(result))

    markdown = _blueprint_markdown(assessment, result)
    ctx.blueprint_md = markdown
    ctx.current_step = 10
    yield make_panel_complete(10, "blueprint", {
        "schema_version": "2.0",
        "pattern_id": result.operating_model,
        "pattern_name": (result.operating_model or "").title(),
        "evidence_coverage": result.evidence_coverage,
        "markdown": markdown,
        "components_count": len(result.components),
        "phases_count": len(result.roadmap),
        "services_count": sum(len(item.aws_services) for item in result.components),
        "risks_count": len(result.risks),
        "compliance_regime": ", ".join(assessment.data.regulations),
        "export_ready": True,
        "cost_estimate": _cost_payload(result),
    })
    yield make_chat_message(
        "assistant",
        "Blueprint complete. Every architecture, control, risk, roadmap, and cost "
        "decision is linked to structured intake evidence.",
    )
    yield make_step_transition(9, 10, "Blueprint complete")
