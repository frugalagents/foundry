from __future__ import annotations

from datetime import date

from advisor_core.v3.assurance import (
    SelectedBundleContext,
    build_assurance_outputs,
)
from advisor_core.v3.demo import build_demo_workspace
from advisor_core.v3.deployable import (
    RecommendationState,
    build_deployable_solution,
)
from advisor_core.v3.models import FeasibilityStatus


AS_OF = date(2026, 7, 30)


def test_release_safety_blocks_rejected_and_unknown_families():
    catalog, workspace = build_demo_workspace(AS_OF)
    matrix = build_deployable_solution(
        workspace.revisions[-1],
        catalog,
    )

    assert (
        matrix.recommendation.state
        is RecommendationState.NO_VIABLE_CANDIDATE
    )
    assert matrix.recommendation.candidate_id is None
    assert matrix.pareto_candidate_ids == ()
    assert matrix.sensitivity == ()
    assert all(
        candidate.family_feasibility_status
        is not FeasibilityStatus.FEASIBLE
        for candidate in matrix.candidates
    )


def test_rejected_family_and_placeholder_economics_block_readiness():
    catalog, workspace = build_demo_workspace(AS_OF)
    rejected = SelectedBundleContext(
        bundle_id="bundle:aws-governed-r2",
    )
    packet = build_assurance_outputs(
        workspace,
        catalog,
        rejected,
        as_of=AS_OF,
    )

    assert packet.readiness.state == "expert_review"
    assert packet.readiness.expert_review.required is True
    assert "deployment_family_rejected" in (
        packet.readiness.expert_review.reason_codes
    )
    assert "economics_not_evidence_backed" in (
        packet.readiness.blocking_reason_codes
    )
    assert packet.readiness.evidence.status != "complete"
    assert packet.readiness.freshness.status == "current"
    assert packet.readiness.stability.status == "unknown"


def test_readiness_serialization_is_deterministic():
    catalog, workspace = build_demo_workspace(AS_OF)
    first = build_assurance_outputs(
        workspace,
        catalog,
        as_of=AS_OF,
    )
    second = build_assurance_outputs(
        workspace,
        catalog,
        as_of=AS_OF,
    )

    assert first.readiness == second.readiness
    assert first.packet_hash == second.packet_hash
