#!/usr/bin/env python3
"""Build the deterministic coding-platform knowledge release."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
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
    build_knowledge_release_artifacts,
    compile_knowledge_catalog,
    compile_knowledge_deployable_catalog,
    compile_runtime_graph,
    compile_search_projection,
    compile_vector_projection,
    load_legacy_migration_bundle,
    load_release_scenario_suite,
    run_release_scenarios,
    VectorChunkingProfile,
    VectorEmbeddingProfile,
    validate_knowledge_release,
    write_knowledge_release_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "knowledge"
            / "releases"
            / "coding-platform"
            / "1.4.0"
        ),
    )
    args = parser.parse_args()

    migration_path = (
        REPOSITORY_ROOT
        / "knowledge"
        / "migrations"
        / "coding-platform-v3.json"
    )
    migration, _, _ = load_legacy_migration_bundle(migration_path)
    migration_document = json.loads(
        migration_path.read_text(encoding="utf-8")
    )
    as_of = date(2026, 8, 12)
    logical = compile_knowledge_catalog(
        entities=migration.entities,
        relationships=migration.relationships,
        source_registry=migration.source_registry,
        snapshots=migration.snapshots,
        projection=migration.logical_projection,
        as_of=as_of,
    )
    deployable = compile_knowledge_deployable_catalog(
        logical_catalog=logical,
        entities=migration.entities,
        relationships=migration.relationships,
        projection=migration.deployable_projection,
        as_of=as_of,
    )
    validation = validate_knowledge_release(
        entities=migration.entities,
        relationships=migration.relationships,
        known_snapshot_ids=tuple(
            snapshot.snapshot_id for snapshot in migration.snapshots
        ),
        as_of=as_of,
    )
    runtime_graph = compile_runtime_graph(
        entities=migration.entities,
        relationships=migration.relationships,
        known_snapshot_ids=tuple(
            snapshot.snapshot_id for snapshot in migration.snapshots
        ),
        as_of=as_of,
    )
    search_projection = compile_search_projection(
        entities=migration.entities,
        as_of=as_of,
    )
    vector_projection = compile_vector_projection(
        search_projection=search_projection,
        chunking_profile=VectorChunkingProfile(
            id="chunking-profile:architecture-knowledge-v1",
            version="1.0.0",
            max_words=180,
            overlap_words=30,
        ),
        embedding_profile=VectorEmbeddingProfile(
            id="embedding-profile:architecture-knowledge-v1",
            version="1.0.0",
            provider="materialized-at-deployment",
        ),
    )
    suite = load_release_scenario_suite(
        REPOSITORY_ROOT
        / "knowledge"
        / "scenarios"
        / "release-safety-v1.yaml"
    )
    results = run_release_scenarios(suite, migration)
    artifacts = build_knowledge_release_artifacts(
        release_id="release:coding-platform-knowledge",
        release_version="1.4.0",
        built_at=datetime.fromisoformat("2026-08-12T12:00:00+00:00"),
        compiler_version="1.0.0",
        migration_bundle_hash=migration_document["bundle_hash"],
        migration=migration,
        logical_catalog=logical,
        deployable_catalog=deployable,
        validation=validation,
        runtime_graph=runtime_graph,
        search_projection=search_projection,
        vector_projection=vector_projection,
        scenario_suite=suite,
        scenario_results=results,
    )
    write_knowledge_release_artifacts(args.output, artifacts)
    print(f"{args.output}: {artifacts.manifest.manifest_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
