#!/usr/bin/env python3
"""Export the pinned v3 catalogs as a content-addressed knowledge bundle."""
from __future__ import annotations

import argparse
from dataclasses import replace
import sys
from datetime import date
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = (
    REPOSITORY_ROOT
    / "PlatformAdvisorAgent"
    / "app"
    / "PlatformAdvisorAgent"
)
sys.path.insert(0, str(PACKAGE_ROOT))

from advisor_core.knowledge import (  # noqa: E402
    load_okf_corpus,
    migrate_legacy_catalogs,
    write_legacy_migration_bundle,
)
from advisor_core.v3 import compile_catalog  # noqa: E402
from advisor_core.v3.deployable import compile_deployable_catalog  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date(2026, 8, 12),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "knowledge"
            / "migrations"
            / "coding-platform-v3.json"
        ),
    )
    args = parser.parse_args()

    catalog_root = PACKAGE_ROOT / "advisor_core" / "v3" / "catalogs"
    logical = compile_catalog(
        catalog_root / "coding-platform",
        as_of=args.as_of,
    )
    deployable = compile_deployable_catalog(
        logical,
        catalog_root / "coding-platform-r0.2",
        as_of=args.as_of,
    )
    migration = migrate_legacy_catalogs(logical, deployable)
    decision_patterns = load_okf_corpus(
        REPOSITORY_ROOT / "knowledge" / "decision-patterns"
    )
    migration = replace(
        migration,
        entities=tuple(
            sorted(
                (*migration.entities, *decision_patterns.entities),
                key=lambda entity: entity.id,
            )
        ),
        relationships=tuple(
            sorted(
                (*migration.relationships, *decision_patterns.relationships),
                key=lambda relationship: relationship.id,
            )
        ),
    )
    bundle_hash = write_legacy_migration_bundle(
        args.output,
        migration,
        logical_source_hash=logical.content_hash,
        deployable_source_hash=deployable.content_hash,
    )
    print(f"{args.output}: {bundle_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
