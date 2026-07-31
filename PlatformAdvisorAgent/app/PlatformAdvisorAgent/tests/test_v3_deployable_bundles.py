from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from advisor_core.v3.demo import build_demo_workspace
from advisor_core.v3.deployable import (
    DEFAULT_CATALOG_PATH,
    CompatibilityStatus,
    DeployableCatalogCompilationError,
    ProviderClass,
    RecommendationState,
    build_deployable_solution,
    compile_deployable_catalog,
)
from advisor_core.v3.engine import apply_requirement_patch
from advisor_core.v3.models import (
    RequirementConstraint,
    RequirementPatch,
    content_hash,
)


AS_OF = date(2026, 7, 30)


def _workspace():
    return build_demo_workspace(AS_OF)


def _candidate(matrix, bundle_id: str):
    return next(
        candidate
        for candidate in matrix.candidates
        if candidate.bundle_id == bundle_id
    )


def test_deployable_catalog_covers_every_component_and_provider_class():
    logical_catalog, _ = _workspace()
    deployable = compile_deployable_catalog(
        logical_catalog,
        as_of=AS_OF,
    )

    expected = {
        (component.id, provider_class)
        for component in logical_catalog.components
        for provider_class in ProviderClass
    }
    actual = {
        (variant.component_id, variant.provider_class)
        for variant in deployable.service_variants
    }

    assert deployable.id == "deployable-catalog:coding-platform"
    assert deployable.version == "0.2.0"
    assert actual == expected
    assert len(deployable.service_variants) == 44 * 4
    assert len(deployable.interfaces) == 22
    assert {
        provider.provider_class for provider in deployable.providers
    } == set(ProviderClass)
    assert deployable.content_hash == compile_deployable_catalog(
        logical_catalog,
        as_of=AS_OF,
    ).content_hash


def test_builder_is_deterministic_and_returns_ranked_decision_matrix():
    logical_catalog, workspace = _workspace()
    revision = workspace.revisions[-1]

    first = build_deployable_solution(revision, logical_catalog)
    second = build_deployable_solution(revision, logical_catalog)

    assert first == second
    assert first.schema_version == "3.0-r0.2"
    assert first.result_hash == content_hash(
        first.model_dump(mode="json", exclude={"result_hash"})
    )
    assert first.recommendation.state is RecommendationState.RECOMMENDED
    assert first.recommendation.candidate_id == "bundle:aws-governed-r2"
    assert [candidate.rank for candidate in first.candidates] == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert first.pareto_candidate_ids == (
        "bundle:aws-governed-r2",
        "bundle:hybrid-governed-r2",
    )

    active_components = {
        node.component_id for node in revision.architecture.nodes
    }
    for candidate in first.candidates:
        assert {
            selection.component_id
            for selection in candidate.selections
        } == active_components
        assert len(candidate.dimension_scores) == 5
        assert candidate.tradeoffs


def test_compatibility_fails_closed_and_byop_remains_conditional():
    logical_catalog, workspace = _workspace()
    matrix = build_deployable_solution(
        workspace.revisions[-1],
        logical_catalog,
    )

    saas = _candidate(matrix, "bundle:saas-composable-r2")
    assert saas.compatibility_status is CompatibilityStatus.INCOMPATIBLE
    assert {
        finding.code for finding in saas.findings
    } == {"required_capability_unsupported"}
    assert {
        finding.requirement_id for finding in saas.findings
    } >= {"requirement:restricted-egress"}

    byop = _candidate(matrix, "bundle:byop-portable-r2")
    assert byop.compatibility_status is CompatibilityStatus.CONDITIONAL
    assert "required_capability_unverified" in {
        finding.code for finding in byop.findings
    }
    assert "requirement_unresolved" in {
        finding.code for finding in byop.findings
    }

    oss = _candidate(matrix, "bundle:oss-sovereign-r2")
    assert oss.compatibility_status is CompatibilityStatus.INCOMPATIBLE
    assert {
        finding.code for finding in oss.findings
    } == {"deployment_family_mismatch"}


def test_sensitivity_reports_first_weight_where_recommendation_changes():
    logical_catalog, workspace = _workspace()
    matrix = build_deployable_solution(
        workspace.revisions[-1],
        logical_catalog,
    )
    by_dimension = {
        item.dimension_id: item for item in matrix.sensitivity
    }

    speed = by_dimension["dimension:delivery-speed"]
    assert speed.baseline_candidate_id == "bundle:aws-governed-r2"
    assert speed.winner_changes is True
    assert speed.switch_weight == 0.65
    assert speed.challenger_candidate_id == (
        "bundle:hybrid-governed-r2"
    )
    assert speed.score_margin_at_baseline > 0
    assert by_dimension["dimension:security"].winner_changes is False


def test_requirement_change_rebuilds_candidates_from_new_revision():
    logical_catalog, workspace = _workspace()
    current = workspace.revisions[-1]
    created_at = datetime(
        2026,
        7,
        30,
        15,
        0,
        tzinfo=timezone.utc,
    )
    updated = apply_requirement_patch(
        workspace,
        RequirementPatch(
            patch_id="patch:customer-managed-execution",
            base_revision_number=current.revision_number,
            changes=(
                RequirementConstraint(
                    requirement_id="requirement:execution-placement",
                    value="customer-managed",
                    source="user",
                    recorded_at=created_at,
                ),
            ),
            rationale="Test deterministic candidate regeneration.",
        ),
        logical_catalog,
        created_at=created_at,
    )

    before = build_deployable_solution(current, logical_catalog)
    after = build_deployable_solution(
        updated.revisions[-1],
        logical_catalog,
    )

    assert before.result_hash != after.result_hash
    assert after.workspace_revision_number == 3
    assert _candidate(
        after,
        "bundle:oss-sovereign-r3",
    ).compatibility_status is CompatibilityStatus.COMPATIBLE
    assert _candidate(
        after,
        "bundle:saas-composable-r3",
    ).compatibility_status is CompatibilityStatus.INCOMPATIBLE


def test_catalog_compiler_rejects_incomplete_service_coverage(
    tmp_path: Path,
):
    catalog_path = tmp_path / "catalog"
    shutil.copytree(DEFAULT_CATALOG_PATH, catalog_path)
    offerings_path = catalog_path / "50-service-offerings.json"
    payload = json.loads(offerings_path.read_text(encoding="utf-8"))
    payload["component_offerings"].pop()
    offerings_path.write_text(json.dumps(payload), encoding="utf-8")
    logical_catalog, _ = _workspace()

    with pytest.raises(
        DeployableCatalogCompilationError,
        match="offering coverage",
    ):
        compile_deployable_catalog(
            logical_catalog,
            catalog_path,
            as_of=AS_OF,
        )


def test_builder_rejects_revision_from_different_catalog_release():
    logical_catalog, workspace = _workspace()
    revision = workspace.revisions[-1]
    mismatched_catalog = logical_catalog.model_copy(
        update={"version": "3.0.1"}
    )

    with pytest.raises(ValueError, match="catalog pin"):
        build_deployable_solution(revision, mismatched_catalog)
