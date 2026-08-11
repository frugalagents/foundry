from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from advisor_core.knowledge import (
    KnowledgeSearchProjection,
    compile_search_projection,
    load_legacy_migration_bundle,
    load_okf_corpus,
)


AS_OF = date(2026, 8, 11)
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "knowledge"
    / "migrations"
    / "coding-platform-v3.json"
)
CAPABILITY_PATH = REPOSITORY_ROOT / "knowledge" / "capabilities"


def migration():
    return load_legacy_migration_bundle(MIGRATION_PATH)[0]


def test_search_projection_indexes_only_approved_current_knowledge():
    knowledge = migration()
    projection = compile_search_projection(
        entities=knowledge.entities,
        as_of=AS_OF,
    )

    assert len(projection.documents) == len(knowledge.entities)
    postings = {
        posting.term: set(posting.document_ids)
        for posting in projection.postings
    }
    assert "search-document:component-workforce-identity" in postings[
        "workforce"
    ]

    claim_document = next(
        document
        for document in projection.documents
        if document.entity_id == "claim:architecture-first-authority"
    )
    assert claim_document.evidence_snapshot_ids == (
        "source:platform-advisor-vision",
    )


def test_okf_body_contributes_search_terms():
    corpus = load_okf_corpus(CAPABILITY_PATH)
    projection = compile_search_projection(
        entities=corpus.entities,
        as_of=AS_OF,
        okf_corpus=corpus,
    )
    postings = {
        posting.term: set(posting.document_ids)
        for posting in projection.postings
    }

    assert "search-document:capability-isolated-execution" in postings[
        "untrusted"
    ]


def test_search_projection_excludes_draft_and_stale_entities():
    knowledge = migration()
    first = knowledge.entities[0]
    draft = first.model_copy(
        update={
            "id": "component:draft-search-record",
            "lifecycle": "draft",
        }
    )
    stale = first.model_copy(
        update={
            "id": "component:stale-search-record",
            "stale_after": date(2026, 8, 10),
        }
    )

    projection = compile_search_projection(
        entities=(*knowledge.entities, draft, stale),
        as_of=AS_OF,
    )
    ids = {document.entity_id for document in projection.documents}

    assert draft.id not in ids
    assert stale.id not in ids


def test_search_projection_is_deterministic_and_hash_protected():
    knowledge = migration()
    first = compile_search_projection(
        entities=knowledge.entities,
        as_of=AS_OF,
    )
    second = compile_search_projection(
        entities=tuple(reversed(knowledge.entities)),
        as_of=AS_OF,
    )

    assert first == second
    payload = first.model_dump(mode="json")
    payload["projection_hash"] = f"sha256:{'f' * 64}"
    with pytest.raises(
        ValidationError,
        match="search projection hash does not match",
    ):
        KnowledgeSearchProjection.model_validate(payload)
