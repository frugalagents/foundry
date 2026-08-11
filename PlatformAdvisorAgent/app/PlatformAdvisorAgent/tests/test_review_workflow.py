from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from advisor_core.knowledge import (
    ClaimCandidate,
    ClaimScope,
    ExtractorMetadata,
    ReviewTransitionError,
    ScopeDimension,
    SourceLocator,
    apply_review_action,
    initialize_review,
)


CREATED_AT = datetime(2026, 8, 11, 21, tzinfo=timezone.utc)


def scope() -> ClaimScope:
    return ClaimScope(
        provider=ScopeDimension(mode="specified", values=("Example",)),
        product=ScopeDimension(mode="specified", values=("Runtime",)),
        variant=ScopeDimension(mode="not_applicable"),
        version=ScopeDimension(mode="all"),
        region=ScopeDimension(mode="all"),
        configuration=ScopeDimension(mode="all"),
    )


def candidate(claim_class: str = "product_fact") -> ClaimCandidate:
    text = "The runtime supports MCP."
    return ClaimCandidate(
        id=f"candidate:runtime-{claim_class}",
        generated_at=CREATED_AT,
        extractor=ExtractorMetadata(
            extractor_id="extractor:bedrock-claim-extractor",
            extractor_version="1.0.0",
            model_id="us.example.model",
            prompt_version="v1",
        ),
        locator=SourceLocator(
            source_snapshot_id="snapshot:runtime-docs-abc123",
            source_uri="https://docs.example.com/runtime",
            source_content_hash=f"sha256:{'a' * 64}",
            exact_text=text,
            section_path=("MCP",),
        ),
        extracted_text=text,
        normalized_statement="Example Runtime supports MCP.",
        subject_id="offering:example-runtime",
        subject_kind="Offering",
        predicate="supports_interface",
        object_id="interface:mcp",
        proposed_scope=scope(),
        claim_class=claim_class,
        confidence=0.9,
    )


def apply(record, extracted, action, reviewer, minutes, **kwargs):
    return apply_review_action(
        record,
        extracted,
        action=action,
        reviewer_id=reviewer,
        decided_at=CREATED_AT + timedelta(minutes=minutes),
        rationale=f"{action} after source and scope review.",
        base_record_hash=record.record_hash,
        **kwargs,
    )


def test_standard_claim_approval_is_append_only():
    extracted = candidate()
    proposed = initialize_review(extracted, created_at=CREATED_AT)
    approved = apply(
        proposed,
        extracted,
        "approve",
        "person:reviewer-one",
        1,
    )

    assert proposed.state.value == "proposed"
    assert approved.state.value == "approved"
    assert len(approved.decisions) == 1
    assert approved.record_hash != proposed.record_hash


def test_compatibility_claim_requires_two_distinct_reviewers():
    extracted = candidate("compatibility")
    proposed = initialize_review(extracted, created_at=CREATED_AT)
    first = apply(
        proposed,
        extracted,
        "approve",
        "person:reviewer-one",
        1,
    )
    second = apply(
        first,
        extracted,
        "approve",
        "person:reviewer-two",
        2,
    )

    assert first.state.value == "proposed"
    assert second.state.value == "approved"

    with pytest.raises(
        ReviewTransitionError,
        match="already approved",
    ):
        apply(
            first,
            extracted,
            "approve",
            "person:reviewer-one",
            2,
        )


def test_review_supports_disputed_stale_and_superseded_states():
    extracted = candidate()
    record = initialize_review(extracted, created_at=CREATED_AT)
    disputed = apply(
        record,
        extracted,
        "dispute",
        "person:reviewer-one",
        1,
    )
    stale = apply(
        disputed,
        extracted,
        "mark_stale",
        "person:reviewer-two",
        2,
    )
    superseded = apply(
        stale,
        extracted,
        "supersede",
        "person:reviewer-one",
        3,
        replacement_candidate_id="candidate:runtime-replacement",
    )

    assert disputed.state.value == "disputed"
    assert stale.state.value == "stale"
    assert superseded.state.value == "superseded"
    assert superseded.replacement_candidate_id == (
        "candidate:runtime-replacement"
    )


def test_rejected_state_is_terminal():
    extracted = candidate()
    record = initialize_review(extracted, created_at=CREATED_AT)
    rejected = apply(
        record,
        extracted,
        "reject",
        "person:reviewer-one",
        1,
    )

    with pytest.raises(
        ReviewTransitionError,
        match="cannot transition terminal state rejected",
    ):
        apply(
            rejected,
            extracted,
            "approve",
            "person:reviewer-two",
            2,
        )


def test_stale_record_hash_rejects_concurrent_decision():
    extracted = candidate()
    record = initialize_review(extracted, created_at=CREATED_AT)

    with pytest.raises(
        ReviewTransitionError,
        match="stale review record hash",
    ):
        apply_review_action(
            record,
            extracted,
            action="approve",
            reviewer_id="person:reviewer-one",
            decided_at=CREATED_AT + timedelta(minutes=1),
            rationale="Reviewed.",
            base_record_hash=f"sha256:{'f' * 64}",
        )
