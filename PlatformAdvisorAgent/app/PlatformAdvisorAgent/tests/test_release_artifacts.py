from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from advisor_core.knowledge import (
    KnowledgeReleaseArtifacts,
    KnowledgeReleaseManifest,
    ReleaseArtifactConflictError,
    ReleaseArtifactFile,
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


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "knowledge"
    / "migrations"
    / "coding-platform-v3.json"
)
SCENARIO_PATH = (
    REPOSITORY_ROOT / "knowledge" / "scenarios" / "release-safety-v1.yaml"
)
RELEASE_ROOT = (
    REPOSITORY_ROOT
    / "knowledge"
    / "releases"
    / "coding-platform"
    / "1.3.0"
)
AS_OF = date(2026, 8, 11)


def build_current_release() -> KnowledgeReleaseArtifacts:
    migration, _, _ = load_legacy_migration_bundle(MIGRATION_PATH)
    migration_document = json.loads(
        MIGRATION_PATH.read_text(encoding="utf-8")
    )
    logical = compile_knowledge_catalog(
        entities=migration.entities,
        relationships=migration.relationships,
        source_registry=migration.source_registry,
        snapshots=migration.snapshots,
        projection=migration.logical_projection,
        as_of=AS_OF,
    )
    deployable = compile_knowledge_deployable_catalog(
        logical_catalog=logical,
        entities=migration.entities,
        relationships=migration.relationships,
        projection=migration.deployable_projection,
        as_of=AS_OF,
    )
    validation = validate_knowledge_release(
        entities=migration.entities,
        relationships=migration.relationships,
        known_snapshot_ids=tuple(
            snapshot.snapshot_id for snapshot in migration.snapshots
        ),
        as_of=AS_OF,
    )
    runtime_graph = compile_runtime_graph(
        entities=migration.entities,
        relationships=migration.relationships,
        known_snapshot_ids=tuple(
            snapshot.snapshot_id for snapshot in migration.snapshots
        ),
        as_of=AS_OF,
    )
    search_projection = compile_search_projection(
        entities=migration.entities,
        as_of=AS_OF,
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
    suite = load_release_scenario_suite(SCENARIO_PATH)
    return build_knowledge_release_artifacts(
        release_id="release:coding-platform-knowledge",
        release_version="1.3.0",
        built_at=datetime.fromisoformat("2026-08-11T12:00:00+00:00"),
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
        scenario_results=run_release_scenarios(suite, migration),
    )


def test_checked_in_release_matches_manifest_and_file_hashes():
    manifest = KnowledgeReleaseManifest.model_validate_json(
        (RELEASE_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    files = tuple(
        ReleaseArtifactFile(
            path=record.path,
            media_type=record.media_type,
            content=(RELEASE_ROOT / record.path).read_text(encoding="utf-8"),
            content_hash=record.content_hash,
            size_bytes=record.size_bytes,
        )
        for record in manifest.files
    )
    checked_in = KnowledgeReleaseArtifacts(
        manifest=manifest,
        files=files,
    )

    assert checked_in == build_current_release()
    assert manifest.scenario_count == manifest.scenario_pass_count == 6


def test_release_build_and_write_are_deterministic(tmp_path: Path):
    first = build_current_release()
    second = build_current_release()

    assert first == second
    write_knowledge_release_artifacts(tmp_path, first)
    write_knowledge_release_artifacts(tmp_path, second)

    target = tmp_path / first.files[0].path
    target.write_text("conflicting content\n", encoding="utf-8")
    with pytest.raises(
        ReleaseArtifactConflictError,
        match="already exists with different content",
    ):
        write_knowledge_release_artifacts(tmp_path, first)
