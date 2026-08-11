"""Checked-in behavioral baseline for knowledge-system migrations."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Sequence

from .demo import DEMO_ASSUMPTIONS, build_demo_workspace
from .models import content_hash
from .projection import build_frontend_projection


BASELINE_SCHEMA_VERSION = "1.0"
BASELINE_ID = "baseline:coding-platform-v3"


def build_migration_baseline(as_of: date) -> dict[str, object]:
    """Build the compact contract used to detect migration behavior drift."""

    catalog, workspace = build_demo_workspace(as_of)
    current = workspace.revisions[-1]
    projection = build_frontend_projection(workspace, catalog)
    architecture = projection["architecture"]
    deployable = projection["deployable_solution"]
    assurance = projection["assurance"]

    authority_counts = Counter(rule.authority.value for rule in catalog.rules)
    baseline: dict[str, object] = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "baseline_id": BASELINE_ID,
        "as_of": as_of.isoformat(),
        "catalog": {
            "catalog_release_id": catalog.id,
            "version": catalog.version,
            "content_hash": catalog.content_hash,
            "inventory": {
                "requirements": len(catalog.requirements),
                "components": len(catalog.components),
                "patterns": len(catalog.patterns),
                "rules": len(catalog.rules),
                "evidence_sources": len(catalog.evidence_sources),
                "evidence_claims": len(catalog.evidence_claims),
            },
            "rule_authority_counts": {
                authority: authority_counts[authority]
                for authority in sorted(authority_counts)
            },
        },
        "representative_case": {
            "case_id": "case:enterprise-coding-platform-demo",
            "requirements": {
                requirement_id: DEMO_ASSUMPTIONS[requirement_id]
                for requirement_id in sorted(DEMO_ASSUMPTIONS)
            },
            "logical_architecture": {
                "pattern_id": current.architecture.pattern_id,
                "state_hash": current.state_hash,
                "component_ids": sorted(
                    node.component_id for node in current.architecture.nodes
                ),
                "edge_ids": sorted(
                    edge.edge_id for edge in current.architecture.edges
                ),
                "summary": architecture["summary"],
                "active_rule_ids": sorted(
                    evaluation.rule_id for evaluation in current.rule_evaluations
                ),
            },
            "deployment_families": [
                {
                    "pattern_id": family["pattern_id"],
                    "status": family["status"],
                    "rejection_rule_ids": family["rejection_rule_ids"],
                    "blocking_requirement_ids": [
                        requirement["requirement_id"]
                        for requirement in family["blocking_requirements"]
                    ],
                }
                for family in projection["deployment_families"]
            ],
            "deployable_solution": {
                "result_hash": deployable["result_hash"],
                "recommendation": deployable["recommendation"],
                "bundle_ids": sorted(
                    candidate["bundle_id"]
                    for candidate in deployable["candidates"]
                ),
                "pareto_candidate_ids": deployable["pareto_candidate_ids"],
            },
            "assurance": {
                "packet_hash": assurance["packet_hash"],
                "readiness_state": assurance["readiness"]["state"],
                "blocking_reason_codes": assurance["readiness"][
                    "blocking_reason_codes"
                ],
            },
            "projection_hash": projection["projection_hash"],
        },
    }
    baseline["baseline_hash"] = content_hash(baseline)
    return baseline


def write_migration_baseline(
    baseline: dict[str, object],
    output: Path | None = None,
) -> str:
    """Serialize the baseline deterministically."""

    serialized = json.dumps(
        baseline,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    return serialized


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build the v3 coding-platform migration baseline."
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="Evidence validation date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the deterministic JSON baseline to this path.",
    )
    args = parser.parse_args(argv)
    serialized = write_migration_baseline(
        build_migration_baseline(args.as_of),
        args.output,
    )
    if args.output is None:
        print(serialized, end="")


if __name__ == "__main__":
    main()
