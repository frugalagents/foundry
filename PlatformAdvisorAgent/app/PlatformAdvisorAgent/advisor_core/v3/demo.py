"""Headless proof for progressive coding-platform architecture revisions."""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timezone
from pathlib import Path

from .catalog import compile_catalog
from .engine import (
    apply_requirement_patch,
    evaluate_deployment_feasibility,
    initialize_workspace,
    rank_next_questions,
)
from .models import AssumptionMetadata, RequirementConstraint, RequirementPatch


CATALOG_PATH = Path(__file__).parent / "catalogs" / "coding-platform"
DEMO_ASSUMPTIONS = {
    "requirement:action-approval": True,
    "requirement:approved-package-registries": True,
    "requirement:approved-regions": "any-approved",
    "requirement:asynchronous-tasks": True,
    "requirement:concurrent-agent-tasks": 1000,
    "requirement:developer-count": 5000,
    "requirement:enterprise-identity": "entra",
    "requirement:execution-placement": "hybrid",
    "requirement:multi-agent": False,
    "requirement:multi-model-provider": True,
    "requirement:outcome-observability": True,
    "requirement:restricted-egress": True,
    "requirement:source-control": "gitlab-saas",
    "requirement:team-boundaries": True,
    "requirement:warm-runtime-capacity": True,
}


def build_demo_workspace(
    as_of: date,
    requirement_values: dict[str, object] | None = None,
):
    """Build the deterministic workspace shared by headless demo projections."""

    recorded_at = datetime.combine(as_of, time(12, 0), tzinfo=timezone.utc)
    catalog = compile_catalog(CATALOG_PATH, as_of=as_of)
    workspace = initialize_workspace(
        catalog,
        workspace_id="workspace:coding-platform-demo",
        created_at=recorded_at,
    )
    initial = workspace.revisions[-1]
    user_values = requirement_values or {}
    values = {**DEMO_ASSUMPTIONS, **user_values}
    patch = RequirementPatch(
        patch_id="patch:enterprise-coding-platform",
        base_revision_number=initial.revision_number,
        changes=tuple(
            RequirementConstraint(
                requirement_id=requirement_id,
                value=value,
                source=(
                    "user"
                    if requirement_id in user_values
                    else "assumption"
                ),
                assumption=(
                    None
                    if requirement_id in user_values
                    else AssumptionMetadata(
                        rationale=(
                            "Working demonstration baseline pending customer "
                            "confirmation."
                        ),
                        confidence=0.6,
                        owner="Platform Advisor product team",
                        source="Coding-platform demonstration baseline",
                    )
                ),
                recorded_at=recorded_at,
            )
            for requirement_id, value in sorted(values.items())
        ),
        rationale=(
            "Apply demonstration assumptions and any explicit user requirements."
        ),
    )
    workspace = apply_requirement_patch(
        workspace,
        patch,
        catalog,
        created_at=recorded_at,
    )
    return catalog, workspace


def build_demo(as_of: date) -> dict[str, object]:
    catalog, workspace = build_demo_workspace(as_of)
    initial = workspace.revisions[0]
    current = workspace.revisions[-1]
    feasibility = evaluate_deployment_feasibility(workspace, catalog)
    questions = rank_next_questions(workspace, catalog)
    return {
        "catalog": {
            "id": catalog.id,
            "version": catalog.version,
            "content_hash": catalog.content_hash,
            "inventory": {
                "requirements": len(catalog.requirements),
                "components": len(catalog.components),
                "patterns": len(catalog.patterns),
                "rules": len(catalog.rules),
            },
        },
        "initial_architecture": {
            "pattern_id": initial.architecture.pattern_id,
            "component_count": len(initial.architecture.nodes),
            "edge_count": len(initial.architecture.edges),
            "state_hash": initial.state_hash,
        },
        "revision": {
            "revision_id": current.revision_id,
            "revision_number": current.revision_number,
            "state_hash": current.state_hash,
            "delta": current.delta.model_dump(mode="json"),
            "component_count": len(current.architecture.nodes),
            "edge_count": len(current.architecture.edges),
            "decision_trace": [
                evaluation.model_dump(mode="json")
                for evaluation in current.rule_evaluations
            ],
        },
        "deployment_feasibility": {
            "result_hash": feasibility.result_hash,
            "families": [
                {
                    "pattern_id": evaluation.pattern_id,
                    "status": evaluation.status.value,
                    "rejection_rule_ids": evaluation.rejection_rule_ids,
                    "blocking_requirement_ids": (
                        evaluation.blocking_requirement_ids
                    ),
                }
                for evaluation in feasibility.family_evaluations
            ],
        },
        "next_question": (
            questions[0].model_dump(mode="json") if questions else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the architecture-first v3 coding-platform proof."
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="Evidence validation date in YYYY-MM-DD format.",
    )
    args = parser.parse_args()
    print(json.dumps(build_demo(args.as_of), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
