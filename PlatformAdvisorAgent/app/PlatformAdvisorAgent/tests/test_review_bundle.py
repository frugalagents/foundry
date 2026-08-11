from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from advisor_core.knowledge import (
    ClaimCandidate,
    ClaimScope,
    ContradictionReport,
    ExtractorMetadata,
    ProposedRelationship,
    ReviewBundleConflictError,
    ReviewMetadata,
    ScopeDimension,
    SourceLocator,
    SourceRegistryEntry,
    SourceTerms,
    StructuralChange,
    StructuralDiff,
    build_knowledge_pull_request,
    write_review_bundle,
)


GENERATED_AT = datetime(2026, 8, 11, 21, tzinfo=timezone.utc)
CURRENT_SNAPSHOT = "snapshot:example-docs-current"
HASH_A = f"sha256:{'a' * 64}"
HASH_B = f"sha256:{'b' * 64}"


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
        version=ScopeDimension(mode="all"),
        region=ScopeDimension(mode="all"),
        configuration=ScopeDimension(mode="all"),
    )


def candidate() -> ClaimCandidate:
    text = "The runtime supports MCP over HTTP."
    return ClaimCandidate(
        id="candidate:runtime-supports-mcp",
        generated_at=GENERATED_AT,
        extractor=ExtractorMetadata(
            extractor_id="extractor:bedrock-claim-extractor",
            extractor_version="1.0.0",
            model_id="us.example.model-v1",
            prompt_version="claim-extraction-v1",
        ),
        locator=SourceLocator(
            source_snapshot_id=CURRENT_SNAPSHOT,
            source_uri="https://docs.example.com/runtime/mcp",
            source_content_hash=HASH_B,
            exact_text=text,
            section_path=("Tool integration", "MCP"),
        ),
        extracted_text=text,
        normalized_statement="Example Runtime supports MCP over HTTP.",
        subject_id="offering:example-runtime",
        subject_kind="Offering",
        predicate="supports_interface",
        object_id="interface:mcp-http",
        proposed_scope=scope(),
        claim_class="product_fact",
        confidence=0.91,
        proposed_relationships=(
            ProposedRelationship(
                relationship_type="IMPLEMENTS",
                target_id="capability:governed-tool-access",
                target_kind="Capability",
                cardinality="many_to_many",
                confidence=0.82,
                rationale="MCP support enables governed tool access.",
            ),
        ),
    )


def source() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        id="source:example-docs",
        name="Example runtime documentation",
        publisher="Example Provider",
        source_class="official_product_documentation",
        base_uri="https://docs.example.com/runtime",
        owner_id="team:platform-advisor",
        authority_tier="tier_a_decision_authority",
        cadence="weekly",
        collector="http",
        parser="html",
        freshness_days=14,
        enabled=False,
        terms=SourceTerms(
            status="review_required",
            allows_automated_collection=False,
            allows_snapshot_retention=False,
            allows_derivative_claims=False,
            review=ReviewMetadata(status="in_review"),
        ),
    )


def diff() -> StructuralDiff:
    return StructuralDiff(
        source_id="source:example-docs",
        prior_snapshot_id="snapshot:example-docs-prior",
        current_snapshot_id=CURRENT_SNAPSHOT,
        prior_content_hash=HASH_A,
        current_content_hash=HASH_B,
        prior_block_count=4,
        current_block_count=5,
        ignored_noise_blocks=3,
        changes=(
            StructuralChange(
                operation="added",
                block_type="table",
                after="MCP HTTP supported",
                significance="decision_relevant",
                reason="table structure changed",
            ),
        ),
        diff_hash=HASH_B,
    )


def contradiction_report() -> ContradictionReport:
    return ContradictionReport(
        as_of=date(2026, 8, 11),
        evaluated_claim_ids=(),
        contradictions=(),
        report_hash=HASH_A,
    )


def test_review_bundle_contains_required_pr_artifacts():
    bundle = build_knowledge_pull_request(
        source(),
        diff(),
        (candidate(),),
        generated_at=GENERATED_AT,
        contradictions=contradiction_report(),
    )

    paths = [file.path for file in bundle.files]
    assert any(path.endswith("/source-diff.json") for path in paths)
    assert any(path.endswith("/affected-entities.json") for path in paths)
    assert any(path.endswith("/contradiction-report.json") for path in paths)
    assert any(path.endswith("/reviewer-guide.md") for path in paths)
    assert any("/candidates/" in path for path in paths)
    assert bundle.branch_name.startswith("knowledge/example-docs/")
    assert "## Reviewer Guide" in bundle.body_markdown
    assert "Confirm each exact excerpt" in bundle.body_markdown
    assert {entity.entity_id for entity in bundle.affected_entities} == {
        "capability:governed-tool-access",
        "interface:mcp-http",
        "offering:example-runtime",
    }


def test_review_bundle_is_deterministic():
    first = build_knowledge_pull_request(
        source(),
        diff(),
        (candidate(),),
        generated_at=GENERATED_AT,
    )
    second = build_knowledge_pull_request(
        source(),
        diff(),
        (candidate(),),
        generated_at=GENERATED_AT,
    )

    assert first == second


def test_review_bundle_requires_current_snapshot_candidates():
    stale = candidate().model_copy(
        update={
            "locator": candidate().locator.model_copy(
                update={"source_snapshot_id": "snapshot:example-docs-stale"}
            )
        }
    )

    with pytest.raises(
        ValueError,
        match="must reference the current source snapshot",
    ):
        build_knowledge_pull_request(
            source(),
            diff(),
            (stale,),
            generated_at=GENERATED_AT,
        )


def test_review_bundle_writer_is_immutable(tmp_path):
    bundle = build_knowledge_pull_request(
        source(),
        diff(),
        (candidate(),),
        generated_at=GENERATED_AT,
    )
    write_review_bundle(tmp_path, bundle)
    write_review_bundle(tmp_path, bundle)

    first_file = tmp_path / bundle.files[0].path
    first_file.write_text("tampered", encoding="utf-8")
    with pytest.raises(
        ReviewBundleConflictError,
        match="different content",
    ):
        write_review_bundle(tmp_path, bundle)
