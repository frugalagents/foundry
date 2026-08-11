from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from advisor_core.v3 import (
    ArchitectureConflictError,
    DecisionRule,
    RequirementConstraint,
    RequirementOperator,
    RequirementPatch,
    RevisionConflictError,
    RuleAuthority,
    RuleEffect,
    RulePredicate,
    apply_requirement_patch,
    compile_catalog,
    evaluate_deployment_feasibility,
    initialize_workspace,
    rank_next_questions,
)
from advisor_core.v3.demo import build_demo


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "advisor_core"
    / "v3"
    / "catalogs"
    / "coding-platform"
)
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
SCENARIO_PATH = (
    CATALOG_PATH.parents[1]
    / "scenarios"
    / "coding-platform-r0.1.json"
)


def _catalog():
    return compile_catalog(CATALOG_PATH, as_of=date(2026, 7, 30))


def test_catalog_rules_have_explicit_authority():
    catalog = _catalog()
    counts = {
        authority: sum(
            rule.authority is authority for rule in catalog.rules
        )
        for authority in RuleAuthority
    }

    assert counts == {
        RuleAuthority.HARD_CONSTRAINT: 24,
        RuleAuthority.COMPATIBILITY: 15,
        RuleAuthority.PREFERENCE: 1,
        RuleAuthority.EXPLANATION: 0,
    }


def _constraint(requirement_id: str, value, *, minute: int = 0):
    return RequirementConstraint(
        requirement_id=requirement_id,
        value=value,
        source="user",
        recorded_at=NOW.replace(minute=minute),
    )


def _patch(workspace, patch_id: str, *changes: RequirementConstraint):
    return RequirementPatch(
        patch_id=patch_id,
        base_revision_number=workspace.revisions[-1].revision_number,
        changes=changes,
        rationale="Customer requirement update.",
    )


def _component_ids(workspace) -> set[str]:
    return {
        node.component_id
        for node in workspace.revisions[-1].architecture.nodes
    }


def _family_requirement_values(
    pattern_id: str,
    **overrides,
) -> dict[str, object]:
    values: dict[str, object] = {
        "requirement:approved-package-registries": True,
        "requirement:concurrent-agent-tasks": 100,
        "requirement:developer-count": 5000,
        "requirement:enterprise-identity": "entra",
        "requirement:execution-placement": "customer-managed",
        "requirement:restricted-egress": False,
        "requirement:runtime-isolation": "container",
        "requirement:source-control": "gitlab-saas",
    }
    values.update({
        "pattern:developer-local": {
            "requirement:execution-placement": "local",
            "requirement:runtime-isolation": "developer-endpoint",
        },
        "pattern:vendor-ephemeral": {
            "requirement:execution-placement": "vendor-managed",
        },
        "pattern:persistent-remote-workspace": {
            "requirement:long-running-workspaces": True,
        },
    }.get(pattern_id, {}))
    values.update(overrides)
    return values


def _apply_values(workspace, catalog, patch_id: str, values):
    return apply_requirement_patch(
        workspace,
        _patch(
            workspace,
            patch_id,
            *(
                _constraint(requirement_id, value)
                for requirement_id, value in sorted(values.items())
            ),
        ),
        catalog,
        created_at=NOW,
    )


def test_real_seed_catalog_compiles_with_expected_first_slice_inventory():
    catalog = _catalog()

    assert len(catalog.requirements) == 25
    assert len(catalog.components) == 44
    assert len(catalog.patterns) == 7
    assert len(catalog.rules) == 40
    assert len([
        component
        for component in catalog.components
        if component.kind.value == "overlay"
    ]) == 12
    assert catalog.content_hash.startswith("sha256:")


def test_workspace_starts_with_useful_logical_architecture_before_answers():
    workspace = initialize_workspace(
        _catalog(),
        workspace_id="workspace:example",
        created_at=NOW,
    )

    component_ids = _component_ids(workspace)
    assert workspace.revisions[-1].architecture.pattern_id == (
        "pattern:logical-reference"
    )
    assert {
        "component:agent-registry",
        "component:model-gateway",
        "component:tool-gateway",
        "component:execution-broker",
        "component:policy-engine",
        "component:telemetry-pipeline",
        "component:architecture-knowledge",
    } <= component_ids
    architecture = workspace.revisions[-1].architecture
    assert len(architecture.edges) > 15
    assert any(
        edge.source_instance_id == "node:agent-registry"
        and edge.target_instance_id == "node:workload-identity"
        for edge in architecture.edges
    )


def test_progressive_requirements_add_overlays_and_dependency_closure():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )

    workspace = apply_requirement_patch(
        workspace,
        _patch(
            workspace,
            "patch:platform-shape",
            _constraint("requirement:multi-model-provider", True),
            _constraint("requirement:multi-agent", True),
            _constraint("requirement:restricted-egress", True),
        ),
        catalog,
        created_at=NOW,
    )

    component_ids = _component_ids(workspace)
    delta = workspace.revisions[-1].delta
    assert {
        "component:model-router",
        "component:multi-agent-supervisor",
        "component:restricted-egress",
    } <= component_ids
    assert "component:model-catalog" in component_ids
    assert "component:orchestration-runtime" in component_ids
    assert "component:execution-broker" in component_ids
    assert set(delta.activated_rule_ids) == {
        "rule:multi-agent-supervision",
        "rule:multi-provider-routing",
        "rule:restricted-egress",
    }
    assert {
        "edge:model-router--depends-on--model-catalog",
        "edge:multi-agent-supervisor--depends-on--orchestration-runtime",
        "edge:restricted-egress--depends-on--execution-broker",
        "edge:restricted-egress--depends-on--policy-engine",
    } <= set(delta.added_edge_ids)
    evaluations = {
        evaluation.rule_id: evaluation
        for evaluation in workspace.revisions[-1].rule_evaluations
    }
    assert evaluations["rule:multi-provider-routing"].requirement_ids == (
        "requirement:multi-model-provider",
    )
    assert "model catalog" in (
        evaluations["rule:multi-provider-routing"].rationale
    )


def test_one_variable_flip_produces_declared_architecture_delta():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    enabled = apply_requirement_patch(
        workspace,
        _patch(
            workspace,
            "patch:enable-multi-agent",
            _constraint("requirement:multi-agent", True),
        ),
        catalog,
        created_at=NOW,
    )
    disabled = apply_requirement_patch(
        enabled,
        _patch(
            enabled,
            "patch:disable-multi-agent",
            _constraint("requirement:multi-agent", False, minute=1),
        ),
        catalog,
        created_at=NOW.replace(minute=1),
    )

    delta = disabled.revisions[-1].delta
    assert delta.removed_component_ids == ("component:multi-agent-supervisor",)
    assert delta.deactivated_rule_ids == ("rule:multi-agent-supervision",)
    assert "component:multi-agent-supervisor" not in _component_ids(disabled)


def test_stale_patch_and_invalid_requirement_values_fail_closed():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    stale = RequirementPatch(
        patch_id="patch:stale",
        base_revision_number=0,
        changes=(_constraint("requirement:multi-agent", True),),
        rationale="Stale browser state.",
    )

    with pytest.raises(RevisionConflictError):
        apply_requirement_patch(workspace, stale, catalog, created_at=NOW)

    unknown = _patch(
        workspace,
        "patch:unknown",
        _constraint("requirement:not-in-catalog", True),
    )
    with pytest.raises(ValueError, match="unknown requirement"):
        apply_requirement_patch(workspace, unknown, catalog, created_at=NOW)

    wrong_type = _patch(
        workspace,
        "patch:wrong-type",
        _constraint("requirement:developer-count", "five thousand"),
    )
    with pytest.raises(ValueError, match="expects integer"):
        apply_requirement_patch(workspace, wrong_type, catalog, created_at=NOW)

    unsupported_value = _patch(
        workspace,
        "patch:unsupported-value",
        _constraint("requirement:orchestration-mode", "committee"),
    )
    with pytest.raises(ValueError, match="must be one of"):
        apply_requirement_patch(
            workspace,
            unsupported_value,
            catalog,
            created_at=NOW,
        )

    with pytest.raises(ValidationError):
        RequirementPatch(
            patch_id="patch:empty",
            base_revision_number=1,
            changes=(),
            rationale="No changes.",
        )


def test_unknown_value_preserves_architecture_without_firing_rule():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    updated = apply_requirement_patch(
        workspace,
        _patch(
            workspace,
            "patch:unknown-concurrency",
            _constraint("requirement:concurrent-agent-tasks", None),
        ),
        catalog,
        created_at=NOW,
    )

    assert "component:ephemeral-runtime" not in _component_ids(updated)
    assert updated.revisions[-1].delta.activated_rule_ids == ()


def test_required_unknown_does_not_activate_rule_and_is_reasked():
    catalog = _catalog()
    negative_rule = DecisionRule(
        id="rule:non-local-model-router",
        version="1.0.0",
        name="Route non-local models",
        description="Non-local execution requires model routing.",
        when=(
            RulePredicate(
                requirement_id="requirement:execution-placement",
                operator=RequirementOperator.NOT_EQUALS,
                value="local",
            ),
        ),
        authority=RuleAuthority.HARD_CONSTRAINT,
        effect=RuleEffect.REQUIRE,
        target_component_ids=("component:model-router",),
    )
    catalog = catalog.model_copy(update={
        "content_hash": f"sha256:{'c' * 64}",
        "rules": catalog.rules + (negative_rule,),
    })
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    updated = apply_requirement_patch(
        workspace,
        _patch(
            workspace,
            "patch:unknown-placement",
            _constraint("requirement:execution-placement", None),
        ),
        catalog,
        created_at=NOW,
    )

    assert "component:model-router" not in _component_ids(updated)
    assert negative_rule.id not in {
        evaluation.rule_id
        for evaluation in updated.revisions[-1].rule_evaluations
    }
    questions = {
        question.requirement_id: question
        for question in rank_next_questions(updated, catalog)
    }
    assert "requirement:execution-placement" in questions
    assert None not in questions[
        "requirement:execution-placement"
    ].candidate_answers


def test_child_answer_is_dormant_when_prerequisite_becomes_false():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    enabled = apply_requirement_patch(
        workspace,
        _patch(
            workspace,
            "patch:enable-fallback",
            _constraint("requirement:multi-model-provider", True),
            _constraint("requirement:model-fallback", True),
        ),
        catalog,
        created_at=NOW,
    )
    dormant = apply_requirement_patch(
        enabled,
        _patch(
            enabled,
            "patch:disable-multi-provider",
            _constraint("requirement:multi-model-provider", False, minute=1),
        ),
        catalog,
        created_at=NOW.replace(minute=1),
    )
    restored = apply_requirement_patch(
        dormant,
        _patch(
            dormant,
            "patch:restore-multi-provider",
            _constraint("requirement:multi-model-provider", True, minute=2),
        ),
        catalog,
        created_at=NOW.replace(minute=2),
    )

    assert "component:model-fallback" in _component_ids(enabled)
    assert "component:model-fallback" not in _component_ids(dormant)
    assert "component:model-fallback" in _component_ids(restored)
    assert any(
        requirement.requirement_id == "requirement:model-fallback"
        and requirement.value is True
        for requirement in dormant.revisions[-1].requirements
    )


def test_catalog_content_pin_and_component_conflicts_fail_closed():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    forged_catalog = catalog.model_copy(update={
        "content_hash": f"sha256:{'d' * 64}",
    })
    patch = _patch(
        workspace,
        "patch:catalog-pin",
        _constraint("requirement:multi-agent", True),
    )
    with pytest.raises(ValueError, match="catalog pin"):
        apply_requirement_patch(
            workspace,
            patch,
            forged_catalog,
            created_at=NOW,
        )

    exclude_dependency = DecisionRule(
        id="rule:exclude-execution-broker",
        version="1.0.0",
        name="Exclude execution broker",
        description="Test-only hard conflict.",
        when=(
            RulePredicate(
                requirement_id="requirement:asynchronous-tasks",
                operator=RequirementOperator.EQUALS,
                value=True,
            ),
        ),
        authority=RuleAuthority.HARD_CONSTRAINT,
        effect=RuleEffect.EXCLUDE,
        target_component_ids=("component:execution-broker",),
    )
    conflict_catalog = catalog.model_copy(update={
        "content_hash": f"sha256:{'e' * 64}",
        "rules": catalog.rules + (exclude_dependency,),
    })
    conflict_workspace = initialize_workspace(
        conflict_catalog,
        workspace_id="workspace:conflict",
        created_at=NOW,
    )
    with pytest.raises(
        ArchitectureConflictError,
        match="exclude required dependencies.*execution-broker",
    ):
        apply_requirement_patch(
            conflict_workspace,
            _patch(
                conflict_workspace,
                "patch:hard-conflict",
                _constraint("requirement:asynchronous-tasks", True),
            ),
            conflict_catalog,
            created_at=NOW,
        )


def test_semantic_state_hash_ignores_capture_time_and_replay_is_deterministic():
    catalog = _catalog()

    def replay(recorded_minute: int):
        workspace = initialize_workspace(
            catalog,
            workspace_id="workspace:example",
            created_at=NOW,
        )
        return apply_requirement_patch(
            workspace,
            _patch(
                workspace,
                "patch:multi-provider",
                _constraint(
                    "requirement:multi-model-provider",
                    True,
                    minute=recorded_minute,
                ),
            ),
            catalog,
            created_at=NOW,
        )

    first = replay(0)
    second = replay(5)

    assert first.revisions[-1].state_hash == second.revisions[-1].state_hash
    assert first.revisions[-1].revision_id == second.revisions[-1].revision_id
    assert (
        first.revisions[-1].architecture
        == second.revisions[-1].architecture
    )


def test_question_ranking_surfaces_hard_architecture_effects():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )

    questions = rank_next_questions(workspace, catalog)
    by_requirement = {
        question.requirement_id: question for question in questions
    }
    assert "requirement:model-fallback" not in by_requirement
    assert "requirement:model-routing-mode" not in by_requirement
    assert "requirement:orchestration-mode" not in by_requirement
    assert "requirement:private-connectivity" not in by_requirement
    assert "requirement:warm-runtime-capacity" not in by_requirement
    assert "requirement:source-control" in by_requirement
    assert "requirement:enterprise-identity" in by_requirement
    candidate = by_requirement["requirement:restricted-egress"]
    placement = by_requirement["requirement:execution-placement"]

    assert candidate.hard_constraint_risk is True
    assert "component:restricted-egress" in candidate.affected_component_ids
    assert True in candidate.candidate_answers
    assert False in candidate.candidate_answers
    assert None not in candidate.candidate_answers
    assert candidate.candidate_elimination_count == 0
    assert candidate.information_gain > 100
    impacts = {impact.answer: impact for impact in candidate.answer_impacts}
    assert impacts[True].added_component_ids == (
        "component:restricted-egress",
    )
    assert {
        "edge:restricted-egress--depends-on--execution-broker",
        "edge:restricted-egress--depends-on--policy-engine",
    } == set(impacts[True].added_edge_ids)
    assert impacts[False].added_component_ids == ()
    placement_impacts = {
        impact.answer: impact for impact in placement.answer_impacts
    }
    assert placement_impacts["local"].added_component_ids == (
        "component:local-runtime",
    )
    assert placement_impacts["customer-managed"].added_component_ids == (
        "component:container-runtime",
    )
    assert placement_impacts["vendor-managed"].added_component_ids == (
        "component:ephemeral-runtime",
    )
    assert set(placement_impacts["hybrid"].added_component_ids) == {
        "component:ephemeral-runtime",
        "component:local-runtime",
    }
    assert placement.candidate_elimination_count == 5
    assert placement_impacts["local"].feasible_pattern_ids == ()
    assert {
        "pattern:developer-local",
    } <= set(placement_impacts["local"].unknown_pattern_ids)
    assert {
        "pattern:managed-customer-execution",
        "pattern:self-hosted-container",
        "pattern:self-hosted-kubernetes",
        "pattern:vendor-ephemeral",
    } <= set(placement_impacts["local"].rejected_pattern_ids)
    assert questions[0].hard_constraint_risk is True


def test_deployment_feasibility_is_separate_from_single_logical_baseline():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    initial = evaluate_deployment_feasibility(workspace, catalog)

    assert workspace.revisions[-1].architecture.pattern_id == (
        "pattern:logical-reference"
    )
    assert len(initial.family_evaluations) == 6
    assert {
        evaluation.status.value
        for evaluation in initial.family_evaluations
    } == {"unknown"}
    assert initial == evaluate_deployment_feasibility(workspace, catalog)
    assert initial.result_hash.startswith("sha256:")

    local_values = _family_requirement_values("pattern:developer-local")
    local_values["requirement:long-running-workspaces"] = False
    local = _apply_values(
        workspace,
        catalog,
        "patch:local-feasibility",
        local_values,
    )
    assessment = evaluate_deployment_feasibility(local, catalog)
    by_pattern = {
        evaluation.pattern_id: evaluation
        for evaluation in assessment.family_evaluations
    }

    assert local.revisions[-1].architecture.pattern_id == (
        "pattern:logical-reference"
    )
    assert by_pattern["pattern:developer-local"].status.value == "feasible"
    assert by_pattern["pattern:persistent-remote-workspace"].status.value == (
        "rejected"
    )
    assert by_pattern["pattern:vendor-ephemeral"].status.value == "rejected"
    assert by_pattern["pattern:developer-local"].rejection_rule_ids == ()
    assert by_pattern[
        "pattern:vendor-ephemeral"
    ].rejection_rule_ids == (
        "rule:reject-vendor-ephemeral-isolation",
        "rule:reject-vendor-ephemeral-placement",
    )


def test_customer_managed_answers_preserve_multiple_feasible_implementation_paths():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    workspace = _apply_values(
        workspace,
        catalog,
        "patch:customer-managed-feasibility",
        _family_requirement_values("pattern:persistent-remote-workspace"),
    )

    assessment = evaluate_deployment_feasibility(workspace, catalog)
    feasible = {
        evaluation.pattern_id
        for evaluation in assessment.family_evaluations
        if evaluation.status.value == "feasible"
    }
    rejected = {
        evaluation.pattern_id
        for evaluation in assessment.family_evaluations
        if evaluation.status.value == "rejected"
    }

    assert feasible == {
        "pattern:managed-customer-execution",
        "pattern:persistent-remote-workspace",
        "pattern:self-hosted-container",
        "pattern:self-hosted-kubernetes",
    }
    assert rejected == {
        "pattern:developer-local",
        "pattern:vendor-ephemeral",
    }


def test_missing_family_rule_coverage_fails_closed():
    catalog = _catalog()
    reduced_rules = tuple(
        rule
        for rule in catalog.rules
        if rule.id != "rule:reject-self-hosted-kubernetes-isolation"
    )
    catalog = catalog.model_copy(update={
        "content_hash": f"sha256:{'f' * 64}",
        "rules": reduced_rules,
    })
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:missing-coverage",
        created_at=NOW,
    )

    with pytest.raises(
            ValueError,
            match=(
                "self-hosted-kubernetes.*missing eligibility-rule coverage.*"
                "runtime-isolation"
            ),
    ):
        evaluate_deployment_feasibility(workspace, catalog)


@pytest.mark.parametrize(
    "missing_requirement_id",
    [
        "requirement:approved-package-registries",
        "requirement:concurrent-agent-tasks",
        "requirement:developer-count",
        "requirement:enterprise-identity",
        "requirement:execution-placement",
        "requirement:private-connectivity",
        "requirement:restricted-egress",
        "requirement:runtime-isolation",
        "requirement:source-control",
    ],
)
def test_family_stays_unknown_until_each_material_dimension_is_known(
    missing_requirement_id: str,
):
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:material-gates",
        created_at=NOW,
    )
    values = _family_requirement_values(
        "pattern:managed-customer-execution"
    )
    values.update({
        "requirement:private-connectivity": False,
        "requirement:restricted-egress": True,
    })
    del values[missing_requirement_id]
    workspace = _apply_values(
        workspace,
        catalog,
        f"patch:missing-{missing_requirement_id.split(':', 1)[1]}",
        values,
    )

    evaluation = next(
        item
        for item in evaluate_deployment_feasibility(
            workspace,
            catalog,
        ).family_evaluations
        if item.pattern_id == "pattern:managed-customer-execution"
    )

    assert evaluation.status.value == "unknown"
    assert missing_requirement_id in evaluation.blocking_requirement_ids


def test_rejections_are_traceable_for_scale_isolation_and_connectivity():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:traceable-rejections",
        created_at=NOW,
    )
    values = _family_requirement_values("pattern:developer-local")
    values["requirement:concurrent-agent-tasks"] = 500
    workspace = _apply_values(
        workspace,
        catalog,
        "patch:local-scale-rejection",
        values,
    )
    by_pattern = {
        item.pattern_id: item
        for item in evaluate_deployment_feasibility(
            workspace,
            catalog,
        ).family_evaluations
    }
    assert by_pattern["pattern:developer-local"].rejection_rule_ids == (
        "rule:reject-developer-local-concurrency",
    )

    vendor_values = _family_requirement_values("pattern:vendor-ephemeral")
    vendor_values.update({
        "requirement:private-connectivity": True,
        "requirement:restricted-egress": True,
    })
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:vendor-connectivity-rejection",
        created_at=NOW,
    )
    workspace = _apply_values(
        workspace,
        catalog,
        "patch:vendor-connectivity-rejection",
        vendor_values,
    )
    vendor = next(
        item
        for item in evaluate_deployment_feasibility(
            workspace,
            catalog,
        ).family_evaluations
        if item.pattern_id == "pattern:vendor-ephemeral"
    )
    assert vendor.status.value == "rejected"
    assert vendor.rejection_rule_ids == (
        "rule:reject-vendor-ephemeral-private-connectivity",
    )


def test_versioned_r0_1_scenario_suite_covers_every_family_and_outcome():
    suite = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    catalog = _catalog()
    scenarios = suite["scenarios"]

    assert suite["catalog_id"] == catalog.id
    assert suite["catalog_version"] == catalog.version
    assert suite["version"] == "1.1.0"
    assert len(scenarios) == 24
    assert len({scenario["id"] for scenario in scenarios}) == 24
    assert {
        kind: sum(scenario["kind"] == kind for scenario in scenarios)
        for kind in {
            "positive",
            "rejection",
            "unknown",
            "one_variable_flip",
        }
    } == {
        "positive": 6,
        "rejection": 6,
        "unknown": 6,
        "one_variable_flip": 6,
    }

    covered_patterns: set[str] = set()
    for index, scenario in enumerate(scenarios):
        workspace = initialize_workspace(
            catalog,
            workspace_id=f"workspace:scenario-{index}",
            created_at=NOW,
        )
        requirements = {
            **suite["baseline_requirements"],
            **scenario["requirements"],
        }
        for requirement_id in scenario.get("unset_requirements", []):
            requirements.pop(requirement_id)
        if requirements:
            workspace = apply_requirement_patch(
                workspace,
                _patch(
                    workspace,
                    f"patch:scenario-{index}",
                    *(
                        _constraint(requirement_id, value)
                        for requirement_id, value in sorted(
                            requirements.items()
                        )
                    ),
                ),
                catalog,
                created_at=NOW,
            )
        target_pattern_id = scenario["target_pattern_id"]
        covered_patterns.add(target_pattern_id)
        before = {
            evaluation.pattern_id: evaluation
            for evaluation in evaluate_deployment_feasibility(
                workspace,
                catalog,
            ).family_evaluations
        }

        if scenario["kind"] != "one_variable_flip":
            evaluation = before[target_pattern_id]
            assert evaluation.status.value == scenario["expected_status"]
            assert list(evaluation.rejection_rule_ids) == scenario.get(
                "expected_rejection_rule_ids",
                [],
            )
            assert list(evaluation.blocking_requirement_ids) == scenario.get(
                "expected_blocking_requirement_ids",
                [],
            )
            continue

        flip = scenario["flip"]
        assert requirements[flip["requirement_id"]] == flip["from"]
        assert (
            before[target_pattern_id].status.value
            == flip["expected_before_status"]
        )
        workspace = apply_requirement_patch(
            workspace,
            _patch(
                workspace,
                f"patch:scenario-{index}-flip",
                _constraint(
                    flip["requirement_id"],
                    flip["to"],
                    minute=1,
                ),
            ),
            catalog,
            created_at=NOW.replace(minute=1),
        )
        after = {
            evaluation.pattern_id: evaluation
            for evaluation in evaluate_deployment_feasibility(
                workspace,
                catalog,
            ).family_evaluations
        }
        assert (
            after[target_pattern_id].status.value
            == flip["expected_after_status"]
        )
        assert list(after[target_pattern_id].rejection_rule_ids) == flip.get(
            "expected_rejection_rule_ids",
            [],
        )

    assert covered_patterns == {
        pattern.id
        for pattern in catalog.patterns
        if pattern.role.value == "deployment_family"
    }


def test_question_applicability_unlocks_only_after_prerequisite_decisions():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:example",
        created_at=NOW,
    )
    workspace = apply_requirement_patch(
        workspace,
        _patch(
            workspace,
            "patch:question-prerequisites",
            _constraint("requirement:multi-model-provider", True),
            _constraint("requirement:multi-agent", True),
            _constraint("requirement:restricted-egress", True),
            _constraint("requirement:asynchronous-tasks", True),
        ),
        catalog,
        created_at=NOW,
    )

    requirement_ids = {
        question.requirement_id
        for question in rank_next_questions(workspace, catalog)
    }
    assert {
        "requirement:model-fallback",
        "requirement:model-routing-mode",
        "requirement:orchestration-mode",
        "requirement:private-connectivity",
        "requirement:warm-runtime-capacity",
    } <= requirement_ids


def test_headless_demo_proves_progressive_architecture_without_ui():
    result = build_demo(date(2026, 7, 30))

    assert result["catalog"]["inventory"] == {
        "requirements": 25,
        "components": 44,
        "patterns": 7,
        "rules": 40,
    }
    assert result["initial_architecture"]["component_count"] > 20
    assert result["initial_architecture"]["edge_count"] > 15
    assert result["revision"]["revision_number"] == 2
    assert {
        "component:model-router",
        "component:restricted-egress",
        "component:warm-runtime-pool",
        "component:local-runtime",
    } <= set(result["revision"]["delta"]["added_component_ids"])
    assert {
        "component:multi-agent-supervisor",
        "component:parallel-reviewer",
    }.isdisjoint(result["revision"]["delta"]["added_component_ids"])
    assert result["next_question"]["hard_constraint_risk"] is True
    assert (
        result["next_question"]["requirement_id"]
        != "requirement:execution-placement"
    )
    rule_ids = {
        evaluation["rule_id"]
        for evaluation in result["revision"]["decision_trace"]
    }
    assert {
        "rule:hybrid-execution",
        "rule:multi-provider-routing",
        "rule:restricted-egress",
    } <= rule_ids
    assert "rule:parallel-independent-review" not in rule_ids
    family_statuses = {
        family["pattern_id"]: family["status"]
        for family in result["deployment_feasibility"]["families"]
    }
    assert family_statuses["pattern:developer-local"] == "rejected"
    assert family_statuses["pattern:vendor-ephemeral"] == "unknown"
    assert family_statuses["pattern:self-hosted-kubernetes"] == "rejected"


@pytest.mark.parametrize(
    "answer,expected_component,expected_rule,expected_claim",
    [
        (
            "managed",
            "component:managed-model-provider",
            "rule:provider-managed",
            "claim:bedrock-managed-inference",
        ),
        (
            "self-hosted",
            "component:self-hosted-inference",
            "rule:provider-self-hosted",
            "claim:self-hosted-residency",
        ),
        (
            "multi-provider",
            "component:model-router",
            "rule:provider-multi",
            "claim:multi-provider-resilience",
        ),
    ],
)
def test_provider_hosting_decision_drives_component_and_cited_evidence(
    answer: str,
    expected_component: str,
    expected_rule: str,
    expected_claim: str,
):
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:provider-slice",
        created_at=NOW,
    )
    workspace = apply_requirement_patch(
        workspace,
        _patch(
            workspace,
            "patch:provider-hosting",
            _constraint("requirement:provider-hosting", answer),
        ),
        catalog,
        created_at=NOW,
    )

    assert expected_component in _component_ids(workspace)
    evaluations = {
        evaluation.rule_id: evaluation
        for evaluation in workspace.revisions[-1].rule_evaluations
    }
    assert expected_rule in evaluations
    assert expected_claim in evaluations[expected_rule].evidence_claim_ids


def test_provider_hosting_evidence_is_resolved_and_cited_in_projection():
    from advisor_core.v3.demo import build_demo_workspace
    from advisor_core.v3.projection import build_frontend_projection

    catalog, workspace = build_demo_workspace(
        date(2026, 7, 30),
        {"requirement:provider-hosting": "managed"},
    )
    projection = build_frontend_projection(workspace, catalog)

    evidence_by_id = {
        item["claim_id"]: item for item in projection["evidence"]
    }
    assert "claim:bedrock-managed-inference" in evidence_by_id
    citation = evidence_by_id["claim:bedrock-managed-inference"]
    assert citation["source_title"] == "Amazon Bedrock Documentation"
    assert citation["source_uri"].startswith("https://docs.aws.amazon.com/bedrock")
    assert citation["review_status"] == "approved"

    managed_decision = next(
        decision
        for decision in projection["decision_trace"]
        if decision["rule_id"] == "rule:provider-managed"
    )
    assert "claim:bedrock-managed-inference" in (
        managed_decision["evidence_claim_ids"]
    )
