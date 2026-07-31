from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from advisor_core.v3.assurance import (
    SelectedBundleContext,
    build_assurance_outputs,
    load_assurance_catalog,
)
from advisor_core.v3.assurance.catalog import AssuranceCatalogError
from advisor_core.v3.assurance.models import (
    BundleImplementation,
    ControlEvidence,
    NumericRange,
    UnitCostOverride,
)
from advisor_core.v3.demo import build_demo_workspace
from advisor_core.v3.models import content_hash


AS_OF = date(2026, 7, 30)


def _workspace():
    return build_demo_workspace(AS_OF)


def _bundle() -> SelectedBundleContext:
    return SelectedBundleContext(
        bundle_id="bundle:test-selection",
        implementations=(
            BundleImplementation(
                component_id="component:model-gateway",
                offering_id="offering:test-model-gateway",
                provider="Test Provider",
                product="Test Gateway",
            ),
        ),
        control_evidence=(
            ControlEvidence(
                control_id="control:identity-binding",
                evidence_id="evidence:identity-pass",
                status="pass",
                observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
                expires_on=date(2026, 8, 30),
            ),
            ControlEvidence(
                control_id="control:tool-policy-boundary",
                evidence_id="evidence:tool-fail",
                status="fail",
                observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            ),
            ControlEvidence(
                control_id="control:quota-budget",
                evidence_id="evidence:quota-expired",
                status="pass",
                observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                expires_on=date(2026, 7, 1),
            ),
        ),
        unit_cost_overrides=(
            UnitCostOverride(
                cost_id="unit-cost:runtime-hour",
                value_range=NumericRange(low=0.2, high=0.4),
                effective_on=date(2026, 7, 1),
                source="Approved test rate card",
                evidence_status="approved",
            ),
        ),
    )


def test_assurance_packet_is_deterministic_and_content_addressed():
    catalog, workspace = _workspace()

    first = build_assurance_outputs(workspace, catalog, as_of=AS_OF)
    second = build_assurance_outputs(workspace, catalog, as_of=AS_OF)

    assert first == second
    assert first.packet_hash == content_hash(
        first.model_dump(mode="json", exclude={"packet_hash"})
    )
    assert first.workspace_revision_id == workspace.current_revision_id
    assert first.architecture_catalog_content_hash == catalog.content_hash
    assert first.assurance_catalog_version == "0.3.0"
    assert len(first.security.threats) == 10
    assert len(first.outcomes.metrics) == 13


def test_only_acceptable_control_evidence_reduces_residual_risk():
    catalog, workspace = _workspace()
    planned = build_assurance_outputs(workspace, catalog, as_of=AS_OF)
    verified = build_assurance_outputs(
        workspace,
        catalog,
        _bundle(),
        as_of=AS_OF,
    )

    planned_threats = {
        item.threat_id: item for item in planned.security.threats
    }
    verified_threats = {
        item.threat_id: item for item in verified.security.threats
    }
    identity = verified_threats["threat:identity-confusion"]
    assert identity.residual_score < identity.inherent_score
    assert identity.verified_control_ids == ("control:identity-binding",)
    assert (
        verified_threats["threat:prompt-tool-injection"].residual_score
        == planned_threats["threat:prompt-tool-injection"].residual_score
    )
    statuses = {
        item.control_id: item.status for item in verified.security.controls
    }
    assert statuses["control:identity-binding"] == "verified"
    assert statuses["control:tool-policy-boundary"] == "failed"
    assert statuses["control:quota-budget"] == "planned"
    assert verified.security.verified_control_count == 1


def test_roadmap_is_dependency_ordered_and_uses_selected_offering():
    catalog, workspace = _workspace()
    packet = build_assurance_outputs(
        workspace,
        catalog,
        _bundle(),
        as_of=AS_OF,
    )

    packages = [
        item
        for phase in packet.roadmap.phases
        for item in phase.work_packages
    ]
    phase_by_package = {
        item.package_id: phase.sequence
        for phase in packet.roadmap.phases
        for item in phase.work_packages
    }
    assert packages
    assert all(
        phase_by_package[dependency_id] < phase_by_package[item.package_id]
        for item in packages
        for dependency_id in item.dependency_package_ids
    )
    gateway = next(
        item
        for item in packages
        if item.component_id == "component:model-gateway"
    )
    assert gateway.offering_id == "offering:test-model-gateway"
    assert "Test Provider Test Gateway" in gateway.title
    assert packet.roadmap.total_effort_person_days.high > (
        packet.roadmap.total_effort_person_days.low
    )
    assert packet.roadmap.critical_path_package_ids


def test_economics_exposes_formulas_placeholders_and_approved_override():
    catalog, workspace = _workspace()
    packet = build_assurance_outputs(
        workspace,
        catalog,
        _bundle(),
        as_of=AS_OF,
    )
    economics = packet.economics
    costs = {item.cost_id: item for item in economics.unit_costs}

    assert costs["unit-cost:runtime-hour"].status == "evidence_backed"
    assert costs["unit-cost:runtime-hour"].effective_on == date(2026, 7, 1)
    assert any(item.status == "placeholder" for item in economics.unit_costs)
    assert "not provider quotes" in economics.pricing_warning
    assert "successful_task_rate" in economics.formulas[
        "cost_per_successful_task"
    ]
    assert (
        economics.totals.cost_per_successful_task.low
        > economics.totals.cost_per_requested_task.low
    )
    assert (
        economics.totals.cost_per_accepted_pull_request.high
        > economics.totals.cost_per_successful_task.high
    )
    developer_count = next(
        item
        for item in economics.assumptions
        if item.assumption_id == "economic-assumption:developer-count"
    )
    assert developer_count.source == "workspace_requirement"
    assert developer_count.value_range.low == 5000


def test_outcome_contract_joins_advisor_tasks_gitlab_ci_and_production():
    catalog, workspace = _workspace()
    outcomes = build_assurance_outputs(
        workspace, catalog, as_of=AS_OF
    ).outcomes

    assert outcomes.join_path[0] == "advisor decision"
    assert outcomes.join_path[-1] == "deployment and production outcome"
    event_types = {item.event_type for item in outcomes.event_contract}
    assert {
        "agent.task.completed",
        "gitlab.merge_request.updated",
        "gitlab.ci_pipeline.completed",
        "production.outcome.observed",
    } <= event_types
    assert tuple(item.horizon for item in outcomes.measurement_horizons) == (
        "baseline",
        "day_30",
        "day_90",
        "day_180",
    )
    assert outcomes.gitlab_ci_mapping["commit_sha"] == "CI_COMMIT_SHA"
    cost_metric = next(
        item
        for item in outcomes.metrics
        if item.metric_id == "metric:cost-per-accepted-pr"
    )
    assert {"GitLab", "economics ledger"} <= set(cost_metric.source_systems)
    assert cost_metric.denominator == "merged agent-linked merge requests"


def test_assurance_catalog_and_bundle_fail_closed():
    catalog, workspace = _workspace()
    with pytest.raises(AssuranceCatalogError, match="not effective"):
        load_assurance_catalog(catalog, as_of=date(2026, 7, 29))

    with pytest.raises(ValidationError, match="one implementation"):
        SelectedBundleContext(
            bundle_id="bundle:duplicate",
            implementations=(
                BundleImplementation(
                    component_id="component:model-gateway",
                    offering_id="offering:first",
                    provider="Provider",
                    product="First",
                ),
                BundleImplementation(
                    component_id="component:model-gateway",
                    offering_id="offering:second",
                    provider="Provider",
                    product="Second",
                ),
            ),
        )

    with pytest.raises(ValueError, match="inactive components"):
        build_assurance_outputs(
            workspace,
            catalog,
            {
                "bundle_id": "bundle:invalid",
                "implementations": [
                    {
                        "component_id": "component:kubernetes-runtime",
                        "offering_id": "offering:test-kubernetes",
                        "provider": "Test",
                        "product": "Kubernetes",
                    }
                ],
            },
            as_of=AS_OF,
        )
