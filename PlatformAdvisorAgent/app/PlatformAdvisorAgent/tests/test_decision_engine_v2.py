"""Golden scenarios and invariants for the Platform Advisor v2 kernel."""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy

import pytest

from advisor_core import AssessmentInput, DecisionEngine, build_questionnaire
from advisor_core.models import Workload
from pipeline_skills.base import PipelineContext
from pipeline_skills.v2_assessment_skill import run_v2_assessment


def volume(low: float, expected: float, high: float, unit: str) -> dict:
    return {"low": low, "expected": expected, "high": high, "unit": unit}


def profile_for(workload: str) -> dict:
    profiles = {
        "coding": {
            "kind": "coding",
            "developers": volume(100, 500, 1000, "developers"),
            "repositories": 1200,
            "concurrent_sessions": volume(20, 100, 250, "sessions"),
            "monthly_model_calls": volume(500_000, 2_000_000, 5_000_000, "calls"),
            "tokens_per_call": volume(1200, 2500, 5000, "tokens"),
            "code_boundary": "vpc_only",
            "execution_sandbox": True,
        },
        "internal_copilot": {
            "kind": "internal_copilot",
            "employees": 20_000,
            "monthly_active_users": volume(2000, 8000, 15000, "users"),
            "data_domains": 14,
            "monthly_queries": volume(200_000, 1_000_000, 2_500_000, "queries"),
            "tokens_per_query": volume(800, 1800, 3500, "tokens"),
            "action_enabled": True,
        },
        "hosting": {
            "kind": "hosting",
            "builder_teams": 24,
            "tenants": volume(10, 30, 60, "tenants"),
            "deployed_agents": volume(100, 600, 1500, "agents"),
            "monthly_model_calls": volume(1_000_000, 6_000_000, 15_000_000, "calls"),
            "tokens_per_call": volume(1000, 2200, 4500, "tokens"),
            "self_service": "approval",
        },
        "customer_facing": {
            "kind": "customer_facing",
            "tenants": volume(50, 250, 600, "tenants"),
            "monthly_active_users": volume(50_000, 250_000, 600_000, "users"),
            "average_rps": volume(10, 80, 250, "requests/second"),
            "peak_rps": 1000,
            "monthly_model_calls": volume(2_000_000, 12_000_000, 30_000_000, "calls"),
            "tokens_per_call": volume(500, 1200, 2500, "tokens"),
        },
        "process_automation": {
            "kind": "process_automation",
            "workflows": 45,
            "monthly_executions": volume(20_000, 100_000, 300_000, "executions"),
            "tokens_per_execution": volume(1000, 3000, 7000, "tokens"),
            "average_duration_minutes": 8,
            "exception_rate_pct": 4.5,
            "approval_required": True,
        },
        "marketplace": {
            "kind": "marketplace",
            "publishers": volume(10, 50, 150, "publishers"),
            "consumers": volume(100, 1000, 5000, "consumers"),
            "listed_agents": volume(50, 500, 2000, "agents"),
            "monthly_transactions": volume(100_000, 1_000_000, 4_000_000, "transactions"),
            "tokens_per_transaction": volume(500, 1500, 4000, "tokens"),
            "external_agents": True,
            "billing_model": "per_call",
        },
    }
    return deepcopy(profiles[workload])


def ownership_for(model: str) -> dict:
    if model == "centralized":
        delivery = runtime = platform = "central"
    elif model == "decentralized":
        delivery = runtime = platform = "domain"
    else:
        delivery = runtime = "domain"
        platform = "central"
    return {
        "platform_owner": platform,
        "funding_owner": "central",
        "policy_owner": "central",
        "identity_owner": "central",
        "agent_delivery_owner": delivery,
        "runtime_operations_owner": runtime,
        "incident_accountability": runtime,
    }


def complete_input(
    workload: str,
    model: str,
    *,
    regulated: bool = False,
    multi_region: bool = False,
) -> AssessmentInput:
    external = workload in {"customer_facing", "marketplace"}
    audience = {
        "coding": "employees",
        "internal_copilot": "employees",
        "hosting": "internal_builders",
        "customer_facing": "external_customers",
        "process_automation": "employees",
        "marketplace": "third_parties",
    }[workload]
    return AssessmentInput.model_validate({
        "audience": audience,
        "primary_workload": workload,
        "secondary_workloads": ["internal_copilot"] if workload == "hosting" else [],
        "ownership": ownership_for(model),
        "risk": {
            "autonomy": "autonomous",
            "failure_impact": "high",
            "reversible_actions": True,
            "human_approval_required": workload == "process_automation",
            "regulator_facing_audit": regulated,
        },
        "data": {
            "classifications": ["phi"] if regulated else ["internal"],
            "residency": "multi_region" if multi_region else "single_region",
            "regulations": ["HIPAA", "SOC2"] if regulated else ["SOC2"],
            "data_locations": ["AWS"],
            "crosses_trust_boundaries": external,
        },
        "nfr": {
            "tenant_isolation": "account" if external else "namespace",
            "availability_pct": 99.99 if external else 99.9,
            "p95_latency_ms": 500 if external else 1500,
            "rto_hours": 1,
            "rpo_hours": 0.25,
            "regions": 2 if multi_region else 1,
        },
        "current": {
            "maturity": "pilot",
            "identity": "oidc",
            "observability": "enterprise",
            "cicd": "standardized",
            "reusable_gateway": True,
            "reusable_data_platform": True,
        },
        "economics": {
            "monthly_budget_usd": 250_000,
            "target_months": 6,
            "priority": "predictability",
        },
        "workload_profile": profile_for(workload),
    })


GOLDEN_SCENARIOS = [
    pytest.param(workload, model, regulated, multi_region, id=f"{workload}-{label}")
    for workload in [item.value for item in Workload]
    for model, regulated, multi_region, label in [
        ("centralized", False, False, "central"),
        ("federated", False, False, "federated"),
        ("decentralized", False, False, "domain"),
        ("federated", True, False, "regulated"),
        ("federated", False, True, "multiregion"),
    ]
]


@pytest.fixture(scope="module")
def engine() -> DecisionEngine:
    return DecisionEngine()


@pytest.mark.parametrize("workload,model,regulated,multi_region", GOLDEN_SCENARIOS)
def test_thirty_golden_scenarios_complete(
    engine: DecisionEngine,
    workload: str,
    model: str,
    regulated: bool,
    multi_region: bool,
):
    result = engine.assess(complete_input(
        workload, model, regulated=regulated, multi_region=multi_region
    ))
    assert result.status == "complete"
    assert result.evidence_coverage == 1.0
    assert result.operating_model == model
    assert result.topology is not None
    assert result.components
    assert result.controls
    assert result.roadmap
    assert result.cost is not None
    assert result.cost.low.monthly_usd <= result.cost.base.monthly_usd <= result.cost.high.monthly_usd
    if multi_region:
        assert result.topology.regional_model == "multi_region"
        assert any(c.id == "resilience" for c in result.components)
    if regulated:
        assert any(c.source == "HIPAA" for c in result.controls)


@pytest.mark.parametrize(
    "workload,required_component",
    [
        ("coding", "sandbox"),
        ("internal_copilot", "data_access"),
        ("hosting", "registry"),
        ("customer_facing", "tenant_control"),
        ("process_automation", "policy"),
        ("marketplace", "metering"),
    ],
)
def test_workload_branches_materially_change_components(
    engine: DecisionEngine, workload: str, required_component: str
):
    result = engine.assess(complete_input(workload, "federated"))
    assert required_component in {c.id for c in result.components}


def test_missing_critical_evidence_blocks_roadmap_and_cost(engine: DecisionEngine):
    raw = complete_input("coding", "centralized").model_dump(mode="json")
    raw["workload_profile"]["monthly_model_calls"] = None
    result = engine.assess(AssessmentInput.model_validate(raw))
    assert result.status == "needs_information"
    assert result.cost is None
    assert result.roadmap == []
    assert "workload_profile.monthly_model_calls" in {g.field for g in result.missing_evidence}


def test_every_critical_field_has_a_question(engine: DecisionEngine):
    for workload in Workload:
        assessment = complete_input(workload.value, "federated")
        paths = {q["path"] for q in build_questionnaire(workload)["questions"]}
        assert set(engine._critical_fields(assessment)) <= paths


def test_every_question_declares_a_consumer():
    for workload in Workload:
        for question in build_questionnaire(workload)["questions"]:
            assert question["consumers"], question["id"]


def test_multiselect_compliance_applies_all_regimes(engine: DecisionEngine):
    raw = complete_input("customer_facing", "federated").model_dump(mode="json")
    raw["data"]["regulations"] = ["hipaa", "pci_dss", "eu_ai_act"]
    result = engine.assess(AssessmentInput.model_validate(raw))
    sources = {c.source for c in result.controls}
    assert {"HIPAA", "PCI-DSS", "EU-AI-ACT"} <= sources


def test_recorded_override_recomputes_downstream_topology(engine: DecisionEngine):
    assessment = complete_input("hosting", "centralized")
    original = engine.assess(assessment)
    override = engine.create_override(
        decision_path="operating_model",
        engine_value=original.operating_model or "",
        override_value="decentralized",
        rationale="Domain teams have accepted independent runtime accountability.",
        author="architecture-reviewer",
    )
    result = engine.assess(assessment, [override])
    assert result.status == "overridden"
    assert result.operating_model == "decentralized"
    assert result.topology.runtime_placement == "domain_runtimes"
    assert result.overrides == [override]


def test_result_is_deterministic(engine: DecisionEngine):
    assessment = complete_input("marketplace", "federated", regulated=True)
    first = engine.assess(assessment).model_dump(mode="json")
    second = engine.assess(assessment).model_dump(mode="json")
    assert first == second


@pytest.mark.parametrize(
    "workload,path",
    [
        ("coding", "concurrent_sessions"),
        ("internal_copilot", "monthly_active_users"),
        ("hosting", "deployed_agents"),
        ("customer_facing", "tenants"),
        ("process_automation", "workflows"),
        ("marketplace", "listed_agents"),
    ],
)
def test_branch_scale_evidence_changes_cost(
    engine: DecisionEngine, workload: str, path: str
):
    baseline = complete_input(workload, "centralized")
    expanded_raw = baseline.model_dump(mode="json")
    current = expanded_raw["workload_profile"][path]
    if isinstance(current, dict):
        current.update({"low": current["low"] * 10, "expected": current["expected"] * 10, "high": current["high"] * 10})
    else:
        expanded_raw["workload_profile"][path] = current * 10
    expanded = engine.assess(AssessmentInput.model_validate(expanded_raw))
    original = engine.assess(baseline)
    assert expanded.cost.base.monthly_usd > original.cost.base.monthly_usd


def test_external_high_impact_shared_rbac_is_blocked(engine: DecisionEngine):
    raw = complete_input("customer_facing", "centralized").model_dump(mode="json")
    raw["nfr"]["tenant_isolation"] = "shared_rbac"
    result = engine.assess(AssessmentInput.model_validate(raw))
    assert result.status == "needs_information"
    assert result.cost is None
    assert any("insufficient" in gap.reason.lower() for gap in result.missing_evidence)


def test_coding_sandbox_is_conditional(engine: DecisionEngine):
    raw = complete_input("coding", "centralized").model_dump(mode="json")
    raw["workload_profile"]["execution_sandbox"] = False
    result = engine.assess(AssessmentInput.model_validate(raw))
    assert "sandbox" not in {item.id for item in result.components}


def test_sse_adapter_emits_complete_v2_contract(engine: DecisionEngine):
    assessment = complete_input("customer_facing", "federated", regulated=True)
    result = engine.assess(assessment)
    ctx = PipelineContext(session_id="session-test", customer_id="customer-test")

    async def collect() -> list[str]:
        return [event async for event in run_v2_assessment(ctx, assessment, result)]

    events = asyncio.run(collect())
    decoded = [
        json.loads(next(line[6:] for line in event.splitlines() if line.startswith("data: ")))
        for event in events if "data: " in event
    ]
    completed_steps = {
        item["data"]["step"]
        for item in decoded if item["type"] == "panel_complete"
    }
    assert completed_steps == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
    assert ctx.schema_version == "2.0"
    assert ctx.assessment_result["status"] == "complete"
    assert ctx.blueprint_md.startswith("# Platform Architecture Blueprint")
    intake = next(
        item for item in decoded
        if item["type"] == "panel_complete" and item["data"]["step"] == 1
    )
    assert intake["data"]["data"]["answers"]["primary_workload"] == "customer_facing"


def test_none_regulation_does_not_activate_audit(engine: DecisionEngine):
    raw = complete_input("process_automation", "centralized").model_dump(mode="json")
    raw["data"]["regulations"] = ["NONE"]
    result = engine.assess(AssessmentInput.model_validate(raw))
    assert "audit" not in {item.id for item in result.components}


def test_unsupported_override_is_rejected(engine: DecisionEngine):
    assessment = complete_input("hosting", "centralized")
    override = engine.create_override(
        decision_path="cost.base.monthly_usd",
        engine_value="1000",
        override_value="1",
        rationale="Attempt to bypass deterministic cost calculations.",
        author="test-user",
    )
    with pytest.raises(ValueError, match="Unsupported override path"):
        engine.assess(assessment, [override])
