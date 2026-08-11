from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from advisor_core.knowledge import (
    ClaimCandidate,
    ClaimScope,
    ExtractorMetadata,
    ProposedRelationship,
    ScopeDimension,
    SourceLocator,
)


GENERATED_AT = datetime(2026, 8, 11, 19, tzinfo=timezone.utc)
SOURCE_HASH = f"sha256:{'a' * 64}"


def scope() -> ClaimScope:
    return ClaimScope(
        provider=ScopeDimension(
            mode="specified",
            values=("Example Provider",),
        ),
        product=ScopeDimension(
            mode="specified",
            values=("Example Runtime",),
        ),
        variant=ScopeDimension(mode="not_applicable"),
        version=ScopeDimension(
            mode="specified",
            values=("2026-08",),
        ),
        region=ScopeDimension(mode="all"),
        configuration=ScopeDimension(mode="all"),
    )


def locator(
    exact_text: str = "The runtime supports MCP over HTTP.",
) -> SourceLocator:
    return SourceLocator(
        source_snapshot_id="snapshot:example-docs-abc123",
        source_uri="https://docs.example.com/runtime/mcp",
        source_content_hash=SOURCE_HASH,
        exact_text=exact_text,
        section_path=("Tool integration", "MCP"),
    )


def candidate(**overrides) -> ClaimCandidate:
    exact_text = "The runtime supports MCP over HTTP."
    values = {
        "id": "candidate:runtime-supports-mcp",
        "generated_at": GENERATED_AT,
        "extractor": ExtractorMetadata(
            extractor_id="extractor:bedrock-claim-extractor",
            extractor_version="1.0.0",
            model_id="example.model-v1",
            prompt_version="claim-extraction-v1",
        ),
        "locator": locator(exact_text),
        "extracted_text": exact_text,
        "normalized_statement": (
            "Example Runtime 2026-08 supports MCP over HTTP."
        ),
        "subject_id": "offering:example-runtime",
        "subject_kind": "Offering",
        "predicate": "supports_interface",
        "object_id": "interface:mcp-http",
        "proposed_scope": scope(),
        "claim_class": "product_fact",
        "confidence": 0.93,
        "proposed_relationships": (
            ProposedRelationship(
                relationship_type="IMPLEMENTS",
                target_id="capability:governed-tool-access",
                target_kind="Capability",
                cardinality="many_to_many",
                confidence=0.82,
                rationale="MCP support implements governed tool integration.",
            ),
        ),
    }
    values.update(overrides)
    return ClaimCandidate(**values)


def test_candidate_keeps_source_text_and_normalized_claim_separate():
    extracted = candidate()

    assert extracted.extracted_text == extracted.locator.exact_text
    assert extracted.normalized_statement != extracted.extracted_text
    assert extracted.confidence == 0.93
    assert extracted.proposed_relationships[0].target_id == (
        "capability:governed-tool-access"
    )


def test_candidate_rejects_text_not_present_at_locator():
    with pytest.raises(
        ValidationError,
        match="extracted_text must exactly match locator exact_text",
    ):
        candidate(extracted_text="The runtime supports every protocol.")


def test_low_confidence_candidate_requires_explicit_warning():
    with pytest.raises(
        ValidationError,
        match="requires low_confidence warning",
    ):
        candidate(confidence=0.55)

    extracted = candidate(
        confidence=0.55,
        warnings=("low_confidence", "scope_incomplete"),
    )
    assert [warning.value for warning in extracted.warnings] == [
        "low_confidence",
        "scope_incomplete",
    ]


def test_source_locator_requires_structural_position():
    with pytest.raises(
        ValidationError,
        match="requires a structural position",
    ):
        SourceLocator(
            source_snapshot_id="snapshot:example-docs-abc123",
            source_uri="https://docs.example.com/runtime/mcp",
            source_content_hash=SOURCE_HASH,
            exact_text="The runtime supports MCP.",
        )
