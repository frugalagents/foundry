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


def _evidence(
    *,
    control_id: str,
    evidence_id: str,
    verification_id: str,
    status: str,
    observed_at: datetime,
    expires_on: date | None = None,
) -> ControlEvidence:
    return ControlEvidence(
        control_id=control_id,
        evidence_id=evidence_id,
        verification_id=verification_id,
        test_execution_id=(
            f"execution:{evidence_id.split(':', 1)[1]}"
        ),
        verifier="platform-assurance",
        artifact_uri=(
            f"s3://immutable-assurance/{evidence_id.split(':', 1)[1]}.json"
        ),
        artifact_hash=f"sha256:{'a' * 64}",
        status=status,
        observed_at=observed_at,
        expires_on=expires_on,
    )


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
            _evidence(
                control_id="control:identity-binding",
                evidence_id="evidence:identity-pass",
                verification_id="verification:identity-binding",
                status="pass",
                observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
                expires_on=date(2026, 8, 30),
            ),
            _evidence(
                control_id="control:tool-policy-boundary",
                evidence_id="evidence:tool-fail",
                verification_id="verification:tool-policy",
                status="fail",
                observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            ),
            _evidence(
                control_id="control:quota-budget",
                evidence_id="evidence:quota-expired",
                verification_id="verification:quota-enforcement",
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
    assert first.readiness.state == "needs_information"
    assert "economics_not_evidence_backed" in (
        first.readiness.blocking_reason_codes
    )
    assert first.readiness.evidence.status == "incomplete"
    assert first.readiness.freshness.status == "unknown"
    assert first.readiness.stability.status == "unknown"
    assert first.readiness.expert_review.required is False


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


def test_assurance_rejects_forged_revision_and_unknown_inputs():
    catalog, workspace = _workspace()
    revision = workspace.revisions[-1]
    forged_revision = revision.model_copy(
        update={
            "architecture": revision.architecture.model_copy(
                update={"pattern_id": "pattern:developer-local"}
            )
        }
    )
    forged_workspace = workspace.model_copy(
        update={
            "revisions": workspace.revisions[:-1] + (forged_revision,),
        }
    )

    with pytest.raises(ValueError, match="architecture does not match"):
        build_assurance_outputs(
            forged_workspace,
            catalog,
            as_of=AS_OF,
        )

    with pytest.raises(ValueError, match="unknown assurance inputs"):
        build_assurance_outputs(
            workspace,
            catalog,
            {
                "bundle_id": "bundle:unknown-assurance-inputs",
                "control_evidence": [
                    {
                        "control_id": "control:not-in-catalog",
                        "evidence_id": "evidence:unknown-control",
                        "verification_id": "verification:not-in-catalog",
                        "test_execution_id": "execution:unknown-control",
                        "verifier": "platform-assurance",
                        "artifact_uri": (
                            "s3://immutable-assurance/unknown-control.json"
                        ),
                        "artifact_hash": f"sha256:{'b' * 64}",
                        "status": "pass",
                        "observed_at": "2026-07-29T00:00:00Z",
                    }
                ],
                "unit_cost_overrides": [
                    {
                        "cost_id": "unit-cost:not-in-catalog",
                        "value_range": {"low": 1, "high": 2},
                        "effective_on": "2026-07-01",
                        "source": "Unknown rate card",
                        "evidence_status": "approved",
                    }
                ],
            },
            as_of=AS_OF,
        )


def test_latest_control_evidence_determines_verification_status():
    catalog, workspace = _workspace()
    bundle = SelectedBundleContext(
        bundle_id="bundle:evidence-ordering",
        control_evidence=(
            _evidence(
                control_id="control:identity-binding",
                evidence_id="evidence:identity-pass-old",
                verification_id="verification:identity-binding",
                status="pass",
                observed_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
            ),
            _evidence(
                control_id="control:identity-binding",
                evidence_id="evidence:identity-fail-new",
                verification_id="verification:identity-binding",
                status="fail",
                observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            ),
            _evidence(
                control_id="control:identity-binding",
                evidence_id="evidence:identity-pass-future",
                verification_id="verification:identity-binding",
                status="pass",
                observed_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
            ),
        ),
    )

    packet = build_assurance_outputs(
        workspace,
        catalog,
        bundle,
        as_of=AS_OF,
    )
    identity = next(
        item
        for item in packet.security.controls
        if item.control_id == "control:identity-binding"
    )
    assert identity.status == "failed"
    assert identity.evidence_ids == ()
    assert "control:identity-binding" not in {
        control_id
        for threat in packet.security.threats
        for control_id in threat.verified_control_ids
    }


def test_selected_bundle_rejects_duplicate_evidence_and_cost_overrides():
    with pytest.raises(ValidationError, match="control evidence IDs"):
        SelectedBundleContext(
            bundle_id="bundle:duplicate-evidence",
            control_evidence=(
                _evidence(
                    control_id="control:identity-binding",
                    evidence_id="evidence:duplicate",
                    verification_id="verification:identity-binding",
                    status="pass",
                    observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
                ),
                _evidence(
                    control_id="control:tool-policy-boundary",
                    evidence_id="evidence:duplicate",
                    verification_id="verification:tool-policy",
                    status="pass",
                    observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
                ),
            ),
        )

    override = UnitCostOverride(
        cost_id="unit-cost:runtime-hour",
        value_range=NumericRange(low=0.2, high=0.4),
        effective_on=date(2026, 7, 1),
        source="Approved test rate card",
        evidence_status="approved",
    )
    with pytest.raises(ValidationError, match="unit-cost overrides"):
        SelectedBundleContext(
            bundle_id="bundle:duplicate-costs",
            unit_cost_overrides=(override, override),
        )


def test_control_pass_requires_immutable_matching_verification_evidence():
    catalog, workspace = _workspace()
    with pytest.raises(ValidationError, match="test_execution_id"):
        ControlEvidence(
            control_id="control:identity-binding",
            evidence_id="evidence:caller-assertion",
            status="pass",
            observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
        )

    mismatched = SelectedBundleContext(
        bundle_id="bundle:mismatched-verification",
        control_evidence=(
            _evidence(
                control_id="control:identity-binding",
                evidence_id="evidence:mismatched-verification",
                verification_id="verification:tool-policy",
                status="pass",
                observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            ),
        ),
    )
    packet = build_assurance_outputs(
        workspace,
        catalog,
        mismatched,
        as_of=AS_OF,
    )
    control = next(
        item
        for item in packet.security.controls
        if item.control_id == "control:identity-binding"
    )
    threat = next(
        item
        for item in packet.security.threats
        if item.threat_id == "threat:identity-confusion"
    )
    assert control.status == "planned"
    assert control.evidence_ids == ()
    assert threat.residual_score == threat.inherent_score
