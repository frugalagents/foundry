"""Versioned, decision-grade demo assessments for Northwind Finance."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from advisor_core import AssessmentInput


DEMO_VERSION = "1.0"
DEMO_CUSTOMER_ID = "cust_demo_northwind"
DEMO_CUSTOMER_NAME = "Northwind Finance (Demo)"
DEMO_CREATED_BY = "demo-seed"


@dataclass(frozen=True)
class DemoBlueprint:
    session_id: str
    title: str
    description: str
    created_at: str
    assessment_data: dict[str, Any]

    def assessment(self) -> AssessmentInput:
        return AssessmentInput.model_validate(deepcopy(self.assessment_data))


def _volume(low: float, expected: float, high: float, unit: str) -> dict[str, Any]:
    return {"low": low, "expected": expected, "high": high, "unit": unit}


def _base_assessment(
    *,
    audience: str,
    workload: str,
    ownership: dict[str, str],
    risk: dict[str, Any],
    data: dict[str, Any],
    nfr: dict[str, Any],
    workload_profile: dict[str, Any],
    secondary_workloads: list[str] | None = None,
    current: dict[str, Any] | None = None,
    economics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "audience": audience,
        "primary_workload": workload,
        "secondary_workloads": secondary_workloads or [],
        "ownership": ownership,
        "risk": risk,
        "data": data,
        "nfr": nfr,
        "current": current or {
            "maturity": "production",
            "identity": "multiple_idps",
            "observability": "enterprise",
            "cicd": "standardized",
            "reusable_gateway": True,
            "reusable_data_platform": True,
        },
        "economics": economics or {
            "monthly_budget_usd": 300_000,
            "target_months": 9,
            "priority": "predictability",
        },
        "workload_profile": workload_profile,
    }


DEMO_BLUEPRINTS: tuple[DemoBlueprint, ...] = (
    DemoBlueprint(
        session_id="sess_demo_centralized",
        title="Enterprise Employee Copilot",
        description=(
            "A centrally owned employee assistant for policy, operations, and "
            "financial knowledge with governed enterprise actions."
        ),
        created_at="2026-07-28T14:15:00+00:00",
        assessment_data=_base_assessment(
            audience="employees",
            workload="internal_copilot",
            ownership={
                "platform_owner": "central",
                "funding_owner": "central",
                "policy_owner": "central",
                "identity_owner": "central",
                "agent_delivery_owner": "central",
                "runtime_operations_owner": "central",
                "incident_accountability": "central",
            },
            risk={
                "autonomy": "approval",
                "failure_impact": "high",
                "reversible_actions": True,
                "human_approval_required": True,
                "regulator_facing_audit": True,
            },
            data={
                "classifications": ["internal", "confidential"],
                "residency": "single_region",
                "regulations": ["SOX", "SOC2"],
                "data_locations": [
                    "Amazon S3 data lake",
                    "enterprise knowledge repositories",
                    "finance systems",
                ],
                "crosses_trust_boundaries": False,
            },
            nfr={
                "tenant_isolation": "namespace",
                "availability_pct": 99.9,
                "p95_latency_ms": 1800,
                "rto_hours": 2,
                "rpo_hours": 1,
                "regions": 1,
            },
            workload_profile={
                "kind": "internal_copilot",
                "employees": 42_000,
                "monthly_active_users": _volume(6_000, 15_000, 28_000, "users"),
                "data_domains": 18,
                "monthly_queries": _volume(
                    750_000, 2_500_000, 6_000_000, "queries"
                ),
                "tokens_per_query": _volume(900, 2_200, 4_500, "tokens"),
                "action_enabled": True,
            },
            secondary_workloads=["process_automation"],
            economics={
                "monthly_budget_usd": 180_000,
                "target_months": 6,
                "priority": "predictability",
            },
        ),
    ),
    DemoBlueprint(
        session_id="sess_demo_federated",
        title="Multi-division Agent Hosting Platform",
        description=(
            "A shared enterprise control plane with division-owned delivery and "
            "runtime operations across banking, insurance, and wealth teams."
        ),
        created_at="2026-07-28T15:00:00+00:00",
        assessment_data=_base_assessment(
            audience="internal_builders",
            workload="hosting",
            ownership={
                "platform_owner": "central",
                "funding_owner": "shared",
                "policy_owner": "central",
                "identity_owner": "central",
                "agent_delivery_owner": "domain",
                "runtime_operations_owner": "domain",
                "incident_accountability": "domain",
            },
            risk={
                "autonomy": "autonomous",
                "failure_impact": "high",
                "reversible_actions": True,
                "human_approval_required": False,
                "regulator_facing_audit": True,
            },
            data={
                "classifications": ["internal", "confidential", "restricted"],
                "residency": "multi_region",
                "regulations": ["SOX", "SOC2", "GDPR"],
                "data_locations": [
                    "US banking accounts",
                    "EU wealth accounts",
                    "division data products",
                ],
                "crosses_trust_boundaries": True,
            },
            nfr={
                "tenant_isolation": "account",
                "availability_pct": 99.95,
                "p95_latency_ms": 1200,
                "rto_hours": 1,
                "rpo_hours": 0.25,
                "regions": 3,
            },
            workload_profile={
                "kind": "hosting",
                "builder_teams": 32,
                "tenants": _volume(8, 24, 45, "divisions"),
                "deployed_agents": _volume(150, 700, 1_800, "agents"),
                "monthly_model_calls": _volume(
                    4_000_000, 18_000_000, 45_000_000, "calls"
                ),
                "tokens_per_call": _volume(800, 2_000, 4_200, "tokens"),
                "self_service": "approval",
            },
            secondary_workloads=["coding", "process_automation"],
            economics={
                "monthly_budget_usd": 450_000,
                "target_months": 12,
                "priority": "outcomes",
            },
        ),
    ),
    DemoBlueprint(
        session_id="sess_demo_decentralized",
        title="External Agent Marketplace",
        description=(
            "A third-party marketplace for independently published financial "
            "agents with provenance, entitlement, metering, and isolated execution."
        ),
        created_at="2026-07-28T15:45:00+00:00",
        assessment_data=_base_assessment(
            audience="third_parties",
            workload="marketplace",
            ownership={
                "platform_owner": "domain",
                "funding_owner": "domain",
                "policy_owner": "shared",
                "identity_owner": "shared",
                "agent_delivery_owner": "domain",
                "runtime_operations_owner": "domain",
                "incident_accountability": "domain",
            },
            risk={
                "autonomy": "autonomous",
                "failure_impact": "severe",
                "reversible_actions": False,
                "human_approval_required": True,
                "regulator_facing_audit": True,
            },
            data={
                "classifications": ["confidential", "restricted", "pci"],
                "residency": "country_bound",
                "regulations": ["PCI-DSS", "SOC2", "GDPR", "EU-AI-ACT"],
                "data_locations": [
                    "publisher-owned systems",
                    "regional transaction stores",
                    "customer financial accounts",
                ],
                "crosses_trust_boundaries": True,
            },
            nfr={
                "tenant_isolation": "dedicated_stack",
                "availability_pct": 99.99,
                "p95_latency_ms": 700,
                "rto_hours": 0.5,
                "rpo_hours": 0.1,
                "regions": 4,
            },
            workload_profile={
                "kind": "marketplace",
                "publishers": _volume(40, 180, 500, "publishers"),
                "consumers": _volume(2_000, 15_000, 60_000, "consumers"),
                "listed_agents": _volume(200, 1_500, 6_000, "agents"),
                "monthly_transactions": _volume(
                    500_000, 6_000_000, 25_000_000, "transactions"
                ),
                "tokens_per_transaction": _volume(500, 1_600, 4_000, "tokens"),
                "external_agents": True,
                "billing_model": "per_outcome",
            },
            secondary_workloads=["customer_facing"],
            current={
                "maturity": "pilot",
                "identity": "multiple_idps",
                "observability": "fragmented",
                "cicd": "team_specific",
                "reusable_gateway": True,
                "reusable_data_platform": False,
            },
            economics={
                "monthly_budget_usd": 650_000,
                "target_months": 15,
                "priority": "outcomes",
            },
        ),
    ),
)
