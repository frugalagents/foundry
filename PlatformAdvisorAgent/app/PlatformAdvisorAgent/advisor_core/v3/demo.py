"""Headless proof for progressive coding-platform architecture revisions."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .catalog import compile_catalog
from .engine import (
    evaluate_deployment_feasibility,
    rank_next_questions,
)
from .runtime import (
    CODING_PLATFORM_WORKING_ASSUMPTIONS,
    build_workspace_from_catalog,
)


CATALOG_PATH = Path(__file__).parent / "catalogs" / "coding-platform"
DEMO_ASSUMPTIONS = CODING_PLATFORM_WORKING_ASSUMPTIONS


def build_demo_workspace(
    as_of: date,
    requirement_values: dict[str, object] | None = None,
):
    """Build the deterministic workspace shared by headless demo projections."""

    catalog = compile_catalog(CATALOG_PATH, as_of=as_of)
    workspace = build_workspace_from_catalog(
        catalog,
        as_of=as_of,
        workspace_id="workspace:coding-platform-demo",
        requirement_values=requirement_values,
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
