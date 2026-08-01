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
    FeasibilityStatus,
    RequirementConstraint,
    RequirementPatch,
    content_hash,
)
from advisor_core.v3.engine import evaluate_revision_deployment_families


AS_OF = date(2026, 7, 30)


def _workspace():
    return build_demo_workspace(AS_OF)


def _feasible_workspace():
    return build_demo_workspace(
        AS_OF,
        {
            "requirement:execution-placement": "customer-managed",
            "requirement:runtime-isolation": "container",
            "requirement:private-connectivity": True,
            "requirement:long-running-workspaces": True,
        },
    )


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
    components = {
        component.id: component for component in logical_catalog.components
    }
    bindings = {
        binding.component_id: binding
        for binding in deployable.component_bindings
    }
    assert all(
        variant.dependency_component_ids
        == components[variant.component_id].dependency_ids
        and variant.provides_interface_ids
        == bindings[variant.component_id].provides_interface_ids
        and variant.requires_interface_ids
        == bindings[variant.component_id].requires_interface_ids
        for variant in deployable.service_variants
    )
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
    assert (
        first.recommendation.state
        is RecommendationState.NO_VIABLE_CANDIDATE
    )
    assert first.recommendation.candidate_id is None
    assert [candidate.rank for candidate in first.candidates] == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert first.pareto_candidate_ids == ()
    assert first.sensitivity == ()

    baseline_components = {
        node.component_id for node in revision.architecture.nodes
    }
    family_components = {
        evaluation.pattern_id: baseline_components | {
            node.component_id for node in evaluation.architecture.nodes
        }
        for evaluation in evaluate_revision_deployment_families(
            revision,
            logical_catalog,
        )
    }
    for candidate in first.candidates:
        assert {
            selection.component_id
            for selection in candidate.selections
        } == family_components[candidate.deployment_family_id]
        assert len(candidate.dimension_scores) == 5
        assert candidate.tradeoffs


def test_completed_scenario_recommends_interface_closed_baseline_overlay():
    logical_catalog, workspace = _feasible_workspace()
    revision = workspace.revisions[-1]
    matrix = build_deployable_solution(revision, logical_catalog)

    assert matrix.recommendation.state in {
        RecommendationState.RECOMMENDED,
        RecommendationState.CONDITIONAL,
    }
    assert matrix.recommendation.candidate_id is not None
    recommended = _candidate(
        matrix,
        matrix.recommendation.candidate_id,
    )
    baseline_components = {
        node.component_id for node in revision.architecture.nodes
    }
    selected_components = {
        selection.component_id for selection in recommended.selections
    }

    assert baseline_components <= selected_components
    assert "component:connector-registry" in selected_components
    assert recommended.family_feasibility_status is FeasibilityStatus.FEASIBLE
    assert "missing_interface_provider" not in {
        finding.code for finding in recommended.findings
    }
    assert "missing_variant_dependency" not in {
        finding.code for finding in recommended.findings
    }


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
    } >= {
        "deployment_family_unresolved",
        "required_capability_unsupported",
    }
    assert "missing_interface_provider" not in {
        finding.code for finding in saas.findings
    }
    assert {
        finding.requirement_id for finding in saas.findings
    } >= {"requirement:restricted-egress"}

    byop = _candidate(matrix, "bundle:byop-portable-r2")
    assert byop.compatibility_status is CompatibilityStatus.CONDITIONAL
    assert (
        byop.family_feasibility_status is FeasibilityStatus.UNKNOWN
    )
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
    } >= {
        "deployment_family_mismatch",
        "deployment_family_rejected",
    }
    assert "missing_interface_provider" not in {
        finding.code for finding in oss.findings
    }


def test_sensitivity_excludes_unknown_and_rejected_families():
    logical_catalog, workspace = _workspace()
    matrix = build_deployable_solution(
        workspace.revisions[-1],
        logical_catalog,
    )
    assert matrix.sensitivity == ()
    assert matrix.pareto_candidate_ids == ()
    assert matrix.recommendation.candidate_id is None


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
    oss = _candidate(
        after,
        "bundle:oss-sovereign-r3",
    )
    assert oss.family_feasibility_status is FeasibilityStatus.UNKNOWN
    assert oss.compatibility_status is CompatibilityStatus.CONDITIONAL
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


def test_builder_rejects_revision_not_derived_from_pinned_inputs():
    logical_catalog, workspace = _workspace()
    revision = workspace.revisions[-1]
    forged_architecture = revision.architecture.model_copy(
        update={"pattern_id": "pattern:developer-local"}
    )
    forged_revision = revision.model_copy(
        update={"architecture": forged_architecture}
    )

    with pytest.raises(ValueError, match="architecture does not match"):
        build_deployable_solution(forged_revision, logical_catalog)


def test_catalog_compiler_requires_template_for_each_provider_class(
    tmp_path: Path,
):
    catalog_path = tmp_path / "catalog"
    shutil.copytree(DEFAULT_CATALOG_PATH, catalog_path)
    templates_path = catalog_path / "30-bundle-templates.json"
    payload = json.loads(templates_path.read_text(encoding="utf-8"))
    for template in payload["bundle_templates"]:
        template["default_provider_class"] = "aws"
    templates_path.write_text(json.dumps(payload), encoding="utf-8")
    logical_catalog, _ = _workspace()

    with pytest.raises(
        DeployableCatalogCompilationError,
        match="one bundle template per provider class",
    ):
        compile_deployable_catalog(
            logical_catalog,
            catalog_path,
            as_of=AS_OF,
        )


def test_catalog_compiler_rejects_invalid_capability_rule_semantics(
    tmp_path: Path,
):
    catalog_path = tmp_path / "catalog"
    shutil.copytree(DEFAULT_CATALOG_PATH, catalog_path)
    rules_path = catalog_path / "40-capability-rules.json"
    payload = json.loads(rules_path.read_text(encoding="utf-8"))
    rule = next(
        item
        for item in payload["capability_rules"]
        if item["id"] == "capability-rule:enterprise-scale"
    )
    rule["value"] = "many"
    rules_path.write_text(json.dumps(payload), encoding="utf-8")
    logical_catalog, _ = _workspace()

    with pytest.raises(
        DeployableCatalogCompilationError,
        match="invalid operator or value",
    ):
        compile_deployable_catalog(
            logical_catalog,
            catalog_path,
            as_of=AS_OF,
        )


def test_recommendation_uses_feasible_family_over_logical_baseline():
    logical_catalog, workspace = _feasible_workspace()
    revision = workspace.revisions[-1]
    deployable = compile_deployable_catalog(
        logical_catalog,
        as_of=AS_OF,
    )
    interface_complete = deployable.model_copy(update={
        "component_bindings": tuple(
            binding.model_copy(update={"requires_interface_ids": ()})
            for binding in deployable.component_bindings
        ),
        "service_variants": tuple(
            variant.model_copy(update={"requires_interface_ids": ()})
            for variant in deployable.service_variants
        ),
    })

    matrix = build_deployable_solution(
        revision,
        logical_catalog,
        interface_complete,
    )
    recommended = _candidate(
        matrix,
        matrix.recommendation.candidate_id,
    )
    evaluations = {
        item.pattern_id: item
        for item in evaluate_revision_deployment_families(
            revision,
            logical_catalog,
        )
    }

    assert matrix.recommendation.state is RecommendationState.RECOMMENDED
    assert (
        recommended.family_feasibility_status
        is FeasibilityStatus.FEASIBLE
    )
    baseline_components = {
        node.component_id for node in revision.architecture.nodes
    }
    assert {
        selection.component_id for selection in recommended.selections
    } == baseline_components | {
        node.component_id
        for node in evaluations[
            recommended.deployment_family_id
        ].architecture.nodes
    }


def test_missing_variant_and_interface_contracts_fail_closed():
    logical_catalog, workspace = _feasible_workspace()
    revision = workspace.revisions[-1]
    deployable = compile_deployable_catalog(
        logical_catalog,
        as_of=AS_OF,
    )
    missing_variant = deployable.model_copy(update={
        "service_variants": tuple(
            variant
            for variant in deployable.service_variants
            if variant.id != "service:developer-clients-aws"
        ),
    })
    variant_matrix = build_deployable_solution(
        revision,
        logical_catalog,
        missing_variant,
    )
    aws = _candidate(variant_matrix, "bundle:aws-governed-r2")
    assert aws.compatibility_status is CompatibilityStatus.INCOMPATIBLE
    assert "missing_service_variant" in {
        finding.code for finding in aws.findings
    }

    missing_binding = deployable.model_copy(update={
        "component_bindings": tuple(
            binding
            for binding in deployable.component_bindings
            if binding.component_id != "component:developer-clients"
        ),
    })
    interface_matrix = build_deployable_solution(
        revision,
        logical_catalog,
        missing_binding,
    )
    aws = _candidate(interface_matrix, "bundle:aws-governed-r2")
    assert aws.compatibility_status is CompatibilityStatus.INCOMPATIBLE
    assert "missing_interface_binding" in {
        finding.code for finding in aws.findings
    }

    incompatible_variant = deployable.model_copy(update={
        "service_variants": tuple(
            (
                variant.model_copy(update={
                    "dependency_component_ids": (),
                    "requires_interface_ids": (),
                })
                if variant.id == "service:model-gateway-aws"
                else variant
            )
            for variant in deployable.service_variants
        ),
    })
    variant_matrix = build_deployable_solution(
        revision,
        logical_catalog,
        incompatible_variant,
    )
    aws = _candidate(variant_matrix, "bundle:aws-governed-r2")
    assert {
        "incompatible_variant_dependencies",
        "incompatible_variant_interfaces",
    } <= {finding.code for finding in aws.findings}
