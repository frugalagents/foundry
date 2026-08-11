from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from advisor_core.knowledge import (
    KnowledgeVectorProjection,
    VectorChunkingProfile,
    VectorEmbeddingProfile,
    compile_search_projection,
    compile_vector_projection,
    load_legacy_migration_bundle,
)


AS_OF = date(2026, 8, 11)
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "knowledge"
    / "migrations"
    / "coding-platform-v3.json"
)


def projection_inputs():
    migration = load_legacy_migration_bundle(MIGRATION_PATH)[0]
    search = compile_search_projection(
        entities=migration.entities,
        as_of=AS_OF,
    )
    chunking = VectorChunkingProfile(
        id="chunking-profile:architecture-knowledge-v1",
        version="1.0.0",
        max_words=180,
        overlap_words=30,
    )
    embedding = VectorEmbeddingProfile(
        id="embedding-profile:architecture-knowledge-v1",
        version="1.0.0",
        provider="materialized-at-deployment",
    )
    return search, chunking, embedding


def test_vector_projection_contains_rebuildable_inputs_not_vectors():
    search, chunking, embedding = projection_inputs()

    projection = compile_vector_projection(
        search_projection=search,
        chunking_profile=chunking,
        embedding_profile=embedding,
    )

    assert projection.materialization_state == "inputs_only"
    assert projection.embedding_profile.model_id is None
    assert len(projection.chunks) >= len(search.documents)
    assert all(chunk.word_count <= chunking.max_words for chunk in projection.chunks)
    assert all(chunk.input_hash.startswith("sha256:") for chunk in projection.chunks)


def test_chunk_overlap_and_identity_are_deterministic():
    search, chunking, embedding = projection_inputs()
    first = compile_vector_projection(
        search_projection=search,
        chunking_profile=chunking,
        embedding_profile=embedding,
    )
    second = compile_vector_projection(
        search_projection=search,
        chunking_profile=chunking,
        embedding_profile=embedding,
    )

    assert first == second
    assert len({chunk.id for chunk in first.chunks}) == len(first.chunks)


def test_embedding_model_and_dimensions_must_be_pinned_together():
    with pytest.raises(
        ValidationError,
        match="must be pinned together",
    ):
        VectorEmbeddingProfile(
            id="embedding-profile:invalid",
            version="1.0.0",
            provider="bedrock",
            model_id="example-model",
        )


def test_vector_projection_rejects_forged_hash():
    search, chunking, embedding = projection_inputs()
    projection = compile_vector_projection(
        search_projection=search,
        chunking_profile=chunking,
        embedding_profile=embedding,
    )
    payload = projection.model_dump(mode="json")
    payload["projection_hash"] = f"sha256:{'f' * 64}"

    with pytest.raises(
        ValidationError,
        match="vector projection hash does not match",
    ):
        KnowledgeVectorProjection.model_validate(payload)
