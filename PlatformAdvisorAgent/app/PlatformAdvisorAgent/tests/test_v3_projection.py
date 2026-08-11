from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from advisor_core.v3.demo import build_demo_workspace
from advisor_core.v3.engine import apply_requirement_patch
from advisor_core.v3.models import (
    AssumptionMetadata,
    RequirementConstraint,
    RequirementPatch,
    content_hash,
)
from advisor_core.v3.projection import (
    build_frontend_projection,
    main,
    write_projection,
)


AS_OF = date(2026, 7, 30)


def _projection():
    catalog, workspace = build_demo_workspace(AS_OF)
    return build_frontend_projection(workspace, catalog)


def test_projection_exposes_named_architecture_and_requirement_state():
    projection = _projection()

    assert projection["schema_version"] == "3.0"
    assert projection["catalog"]["version"] == "3.0.0"
    assert projection["revision"]["revision_number"] == 2
    assert len(projection["requirements"]) == 25
    requirement_by_id = {
        item["requirement_id"]: item
        for item in projection["requirements"]
    }
    assert requirement_by_id["requirement:enterprise-identity"] == {
        "requirement_id": "requirement:enterprise-identity",
        "name": "Enterprise identity",
        "description": (
            "Which workforce identity provider and group source must "
            "authorize developers?"
        ),
        "customer_question": (
            "Which identity system controls who can log in and what "
            "permissions they have on the platform?"
        ),
        "why_it_matters": (
            "The platform connects to your existing identity provider to know "
            "who each developer is, which team they belong to, and what they "
            "are authorized to do — not a separate login system."
        ),
        "value_type": "string",
        "candidate_answers": ["entra", "okta", "cognito", "other-oidc"],
        "required": True,
        "status": "assumed",
        "value": "entra",
        "source": "assumption",
        "assumption": {
            "rationale": (
                "Working demonstration baseline pending customer confirmation."
            ),
            "confidence": 0.6,
            "owner": "Platform Advisor product team",
            "source": "Coding-platform demonstration baseline",
        },
    }
    assert (
        requirement_by_id["requirement:private-connectivity"]["status"]
        == "unanswered"
    )

    architecture = projection["architecture"]
    assert architecture["pattern"]["pattern_id"] == "pattern:logical-reference"
    assert architecture["summary"] == {
        "baseline_component_count": 25,
        "current_component_count": 31,
        "added_component_count": 6,
        "baseline_edge_count": 23,
        "current_edge_count": 31,
        "added_edge_count": 8,
    }
    assert [plane["plane_id"] for plane in architecture["planes"]] == [
        "experience",
        "access",
        "orchestration",
        "model",
        "tool",
        "execution",
        "knowledge",
        "governance",
        "observability",
    ]
    component_by_id = {
        component["component_id"]: component
        for plane in architecture["planes"]
        for component in plane["components"]
    }
    assert component_by_id["component:model-gateway"]["status"] == "baseline"
    assert component_by_id["component:model-gateway"]["name"] == "Model gateway"
    assert component_by_id["component:model-router"]["status"] == "added"
    assert component_by_id["component:model-router"]["name"] == "Model router"

    edge_by_id = {
        edge["edge_id"]: edge for edge in architecture["edges"]
    }
    model_edge = edge_by_id["edge:model-router--depends-on--model-catalog"]
    assert model_edge["source"]["name"] == "Model router"
    assert model_edge["target"]["name"] == "Model catalog"
    assert model_edge["status"] == "added"


def test_projection_explains_families_question_impacts_and_decisions():
    projection = _projection()

    families = {
        family["pattern_id"]: family
        for family in projection["deployment_families"]
    }
    assert families["pattern:developer-local"]["status"] == "rejected"
    assert families["pattern:developer-local"]["name"] == (
        "Developer-hosted local runtime"
    )
    assert families["pattern:developer-local"]["rejection_rule_ids"] == [
        "rule:reject-developer-local-concurrency"
    ]
    assert families["pattern:self-hosted-kubernetes"]["status"] == "rejected"
    assert families["pattern:self-hosted-kubernetes"]["rejection_rule_ids"] == [
        "rule:reject-self-hosted-kubernetes-placement"
    ]
    assert "Constrain self-hosted Kubernetes placement" in {
        evaluation["rule_name"]
        for evaluation
        in families["pattern:self-hosted-kubernetes"]["rule_evaluations"]
    }
    unresolved = families["pattern:persistent-remote-workspace"]
    assert unresolved["status"] == "unknown"
    assert unresolved["blocking_requirements"][0]["name"] == (
        "Long-running workspaces"
    )

    question = projection["next_question"]
    assert question["requirement_name"] == "Long-running workspaces"
    assert len(question["answer_impacts"]) == len(
        question["candidate_answers"]
    )
    persistent_impact = next(
        impact for impact in question["answer_impacts"]
        if impact["answer"] is True
    )
    assert {
        component["component_id"]
        for component in persistent_impact["components"]["added"]
    } == {
        "component:persistent-workspace",
    }
    assert persistent_impact["rules"]["activated_rule_ids"] == [
        "rule:persistent-workspaces"
    ]

    decisions = {
        decision["rule_id"]: decision
        for decision in projection["decision_trace"]
    }
    hybrid = decisions["rule:hybrid-execution"]
    assert hybrid["rule_name"] == "Add hybrid local and remote execution"
    assert hybrid["authority"] == "hard_constraint"
    assert hybrid["requirements"][0]["value"] == "hybrid"
    assert {
        component["name"] for component in hybrid["target_components"]
    } == {"Managed local runtime", "Ephemeral task runtime"}


def test_projection_includes_deployable_matrix_and_assurance_packet():
    projection = _projection()

    deployable = projection["deployable_solution"]
    assert deployable["recommendation"]["state"] == "no_viable_candidate"
    assert deployable["recommendation"]["candidate_id"] is None
    assert len(deployable["candidates"]) == 5
    assert deployable["pareto_candidate_ids"] == []
    conditional = next(
        candidate
        for candidate in deployable["candidates"]
        if candidate["bundle_id"] == "bundle:byop-portable-r2"
    )
    assert len(conditional["selections"]) >= (
        projection["architecture"]["summary"]["current_component_count"]
    )

    assurance = projection["assurance"]
    assert assurance["selected_bundle_id"] is None
    assert assurance["workspace_revision_id"] == projection["revision"][
        "revision_id"
    ]
    assert len(assurance["security"]["threats"]) == 10
    assert len(assurance["roadmap"]["phases"]) == 6
    assert [
        phase["sequence"] for phase in assurance["roadmap"]["phases"]
    ] == list(range(1, 7))
    assert assurance["roadmap"]["phases"][-1]["name"] == (
        "Control verification"
    )
    assert len(assurance["outcomes"]["metrics"]) == 13
    assert assurance["packet_hash"].startswith("sha256:")


def test_projection_is_deterministic_and_cli_writes_exact_json(tmp_path):
    first = _projection()
    second = _projection()

    assert first == second
    projection_hash = first.pop("projection_hash")
    assert projection_hash == content_hash(first)
    first["projection_hash"] = projection_hash
    assert write_projection(first) == write_projection(second)

    output = tmp_path / "frontend-projection.json"
    main(["--as-of", AS_OF.isoformat(), "--output", str(output)])

    assert json.loads(output.read_text(encoding="utf-8")) == second


def test_assumptions_are_validated_and_user_answers_replace_them():
    with pytest.raises(ValidationError, match="assumption metadata"):
        RequirementConstraint(
            requirement_id="requirement:multi-agent",
            value=True,
            source="assumption",
            recorded_at="2026-07-30T12:00:00Z",
        )
    with pytest.raises(ValidationError, match="only valid"):
        RequirementConstraint(
            requirement_id="requirement:multi-agent",
            value=True,
            source="user",
            assumption=AssumptionMetadata(
                rationale="Test-only assumption.",
                confidence=0.5,
                owner="Test owner",
                source="Test source",
            ),
            recorded_at="2026-07-30T12:00:00Z",
        )

    catalog, workspace = build_demo_workspace(
        AS_OF,
        {"requirement:enterprise-identity": "entra"},
    )
    projection = build_frontend_projection(workspace, catalog)
    identity = next(
        item
        for item in projection["requirements"]
        if item["requirement_id"] == "requirement:enterprise-identity"
    )

    assert identity["status"] == "answered"
    assert identity["source"] == "user"
    assert identity["assumption"] is None
    assert "requirement:enterprise-identity" not in {
        item["requirement_id"] for item in projection["assumptions"]
    }
    assert len(projection["assumptions"]) == 14


def test_decision_history_links_revisions_and_explains_patch_deltas():
    catalog, workspace = build_demo_workspace(AS_OF)
    prior = workspace.revisions[-1]
    recorded_at = datetime(2026, 7, 30, 12, 1, tzinfo=timezone.utc)
    workspace = apply_requirement_patch(
        workspace,
        RequirementPatch(
            patch_id="patch:disable-restricted-egress",
            base_revision_number=prior.revision_number,
            changes=(
                RequirementConstraint(
                    requirement_id="requirement:restricted-egress",
                    value=False,
                    source="user",
                    recorded_at=recorded_at,
                ),
            ),
            rationale="Customer confirms unrestricted outbound access.",
        ),
        catalog,
        created_at=recorded_at,
    )

    projection = build_frontend_projection(workspace, catalog)
    history = projection["decision_history"]
    assert history["initial_revision"]["revision_number"] == 1
    assert history["current_revision"]["revision_number"] == 3
    assert len(history["transitions"]) == 2
    latest = history["transitions"][-1]
    assert latest["prior_revision"]["revision_id"] == prior.revision_id
    assert latest["current_revision"]["parent_revision_id"] == prior.revision_id

    change = latest["requirement_changes"][0]
    assert change["requirement_id"] == "requirement:restricted-egress"
    assert change["previous"]["source"] == "assumption"
    assert change["previous"]["assumption"]["confidence"] == 0.6
    assert change["current"]["source"] == "user"
    assert change["current"]["assumption"] is None

    assert {
        rule["rule_id"] for rule in latest["rules"]["deactivated"]
    } >= {"rule:restricted-egress"}
    assert {
        component["component_id"]
        for component in latest["architecture_delta"]["components"]["removed"]
    } >= {"component:restricted-egress"}
    assert latest["architecture_delta"]["edges"]["removed"]
    assert latest["transition_hash"].startswith("sha256:")

    history_without_hash = {
        key: value for key, value in history.items() if key != "history_hash"
    }
    assert history["history_hash"] == content_hash(history_without_hash)
