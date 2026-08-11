from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from advisor_core.v3 import (
    DecisionAuthorityError,
    RequirementConstraint,
    RequirementPatch,
    RuleAuthority,
    apply_requirement_patch,
    compile_catalog,
    initialize_workspace,
    validate_decision_authority,
)
from advisor_core.v3.demo import build_demo_workspace
from advisor_core.v3.projection import build_frontend_projection


AS_OF = date(2026, 7, 30)
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "advisor_core"
    / "v3"
    / "catalogs"
    / "coding-platform"
)


def _catalog():
    return compile_catalog(CATALOG_PATH, as_of=AS_OF)


def test_preference_rule_cannot_mutate_authoritative_architecture():
    catalog = _catalog()
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:authority-boundary",
        created_at=NOW,
    )
    workspace = apply_requirement_patch(
        workspace,
        RequirementPatch(
            patch_id="patch:preference-only",
            base_revision_number=1,
            changes=(
                RequirementConstraint(
                    requirement_id="requirement:approved-regions",
                    value="any-approved",
                    source="user",
                    recorded_at=NOW,
                ),
            ),
            rationale="Exercise a matching preference.",
        ),
        catalog,
        created_at=NOW,
    )
    current = workspace.revisions[-1]

    assert "component:multi-region" not in {
        node.component_id for node in current.architecture.nodes
    }
    assert "rule:regional-flexibility" not in {
        evaluation.rule_id for evaluation in current.rule_evaluations
    }


def test_authoritative_rules_cannot_depend_on_advisory_rules():
    catalog = _catalog()
    rules = {rule.id: rule for rule in catalog.rules}
    invalid = rules["rule:multi-provider-routing"].model_copy(update={
        "depends_on_rule_ids": ("rule:regional-flexibility",),
    })
    candidate_rules = tuple(
        invalid if rule.id == invalid.id else rule
        for rule in catalog.rules
    )

    with pytest.raises(
        DecisionAuthorityError,
        match="outside its authority surface",
    ):
        validate_decision_authority(candidate_rules)


def test_feasible_bundle_ranking_is_advisory_and_not_auto_selected():
    catalog, workspace = build_demo_workspace(
        AS_OF,
        {
            "requirement:execution-placement": "customer-managed",
            "requirement:runtime-isolation": "container",
            "requirement:private-connectivity": True,
            "requirement:long-running-workspaces": True,
        },
    )
    projection = build_frontend_projection(workspace, catalog)

    assert projection["decision_authority"] == {
        "schema_version": "1.0",
        "authoritative_operations": [
            "catalog_lifecycle",
            "component_requirements",
            "dependency_closure",
            "deployment_eligibility",
            "required_controls",
        ],
        "advisory_outputs": [
            "candidate_ranking",
            "pareto_analysis",
            "preference_rules",
            "sensitivity_analysis",
        ],
        "automatic_bundle_selection": False,
    }
    recommendation = projection["deployable_solution"]["recommendation"]
    assert recommendation["state"] == "advisory"
    assert recommendation["candidate_id"]
    assert projection["assurance"]["selected_bundle_id"] is None
    assert "bundle_selection_missing" in projection["assurance"][
        "readiness"
    ]["blocking_reason_codes"]


def test_catalog_has_only_expected_rule_authority_surfaces():
    catalog = _catalog()
    counts = {
        authority: sum(
            rule.authority is authority for rule in catalog.rules
        )
        for authority in RuleAuthority
    }

    assert counts[RuleAuthority.HARD_CONSTRAINT] == 24
    assert counts[RuleAuthority.COMPATIBILITY] == 15
    assert counts[RuleAuthority.PREFERENCE] == 1
    assert counts[RuleAuthority.EXPLANATION] == 0
