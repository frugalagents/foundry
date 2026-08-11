from __future__ import annotations

from datetime import date, datetime, timezone

from advisor_core.knowledge import (
    Claim,
    ClaimScope,
    EvidenceReference,
    ReviewMetadata,
    ScopeDimension,
    detect_contradictions,
)


AS_OF = date(2026, 8, 11)
REVIEWED_AT = datetime(2026, 8, 11, 12, tzinfo=timezone.utc)


def dimension(mode: str, *values: str) -> ScopeDimension:
    return ScopeDimension(mode=mode, values=values)


def scope(*, regions: tuple[str, ...] = ("us-east-1",)) -> ClaimScope:
    return ClaimScope(
        provider=dimension("specified", "Example Provider"),
        product=dimension("specified", "Managed Runtime"),
        variant=dimension("not_applicable"),
        version=dimension("specified", "2026-08"),
        region=dimension("specified", *regions),
        configuration=dimension("all"),
    )


def claim(
    claim_id: str,
    *,
    predicate: str,
    object_value=None,
    object_id=None,
    claim_scope: ClaimScope | None = None,
    effective_from: date = date(2026, 8, 1),
    effective_until: date | None = None,
    claim_class: str = "product_fact",
) -> Claim:
    reviewers = (
        "person:reviewer-one",
        "person:reviewer-two",
    ) if claim_class == "compatibility" else ("person:reviewer-one",)
    return Claim(
        id=claim_id,
        title=claim_id,
        summary=f"Reviewed claim {claim_id}.",
        lifecycle="active",
        owner_id="team:platform-advisor",
        effective_from=effective_from,
        effective_until=effective_until,
        stale_after=date(2026, 12, 1),
        review=ReviewMetadata(
            status="approved",
            reviewer_ids=reviewers,
            reviewed_at=REVIEWED_AT,
        ),
        statement=f"Statement for {claim_id}.",
        subject_id="offering:managed-runtime",
        predicate=predicate,
        object_value=object_value,
        object_id=object_id,
        scope=claim_scope or scope(),
        claim_class=claim_class,
        evidence=(
            EvidenceReference(
                source_snapshot_id=f"snapshot:{claim_id.split(':')[1]}",
                authority_tier="tier_a_decision_authority",
            ),
        ),
    )


def test_overlapping_scalar_facts_are_contradictory():
    report = detect_contradictions(
        (
            claim(
                "claim:context-window-old",
                predicate="max_context_tokens",
                object_value=100000,
            ),
            claim(
                "claim:context-window-new",
                predicate="max_context_tokens",
                object_value=200000,
            ),
        ),
        as_of=AS_OF,
    )

    assert len(report.contradictions) == 1
    contradiction = report.contradictions[0]
    assert contradiction.contradiction_type.value == "direct_value_conflict"
    assert contradiction.severity.value == "warning"


def test_disjoint_regions_do_not_conflict():
    report = detect_contradictions(
        (
            claim(
                "claim:availability-us",
                predicate="availability_status",
                object_value="available",
                claim_scope=scope(regions=("us-east-1",)),
            ),
            claim(
                "claim:availability-eu",
                predicate="availability_status",
                object_value="unavailable",
                claim_scope=scope(regions=("eu-central-1",)),
            ),
        ),
        as_of=AS_OF,
    )

    assert report.contradictions == ()


def test_non_overlapping_effective_periods_do_not_conflict():
    report = detect_contradictions(
        (
            claim(
                "claim:price-old",
                predicate="price_per_unit",
                object_value=0.01,
                effective_from=date(2026, 1, 1),
                effective_until=date(2026, 7, 31),
            ),
            claim(
                "claim:price-new",
                predicate="price_per_unit",
                object_value=0.02,
                effective_from=date(2026, 8, 1),
            ),
        ),
        as_of=AS_OF,
    )

    assert len(report.evaluated_claim_ids) == 1
    assert report.contradictions == ()


def test_multi_valued_relationships_are_not_false_conflicts():
    report = detect_contradictions(
        (
            claim(
                "claim:supports-mcp",
                predicate="supports_interface",
                object_id="interface:mcp-http",
            ),
            claim(
                "claim:supports-openapi",
                predicate="supports_interface",
                object_id="interface:openapi",
            ),
        ),
        as_of=AS_OF,
    )

    assert report.contradictions == ()


def test_positive_and_negative_relationships_conflict():
    report = detect_contradictions(
        (
            claim(
                "claim:compatible",
                predicate="compatible_with",
                object_id="offering:tool-gateway",
                claim_class="compatibility",
            ),
            claim(
                "claim:incompatible",
                predicate="incompatible_with",
                object_id="offering:tool-gateway",
                claim_class="compatibility",
            ),
        ),
        as_of=AS_OF,
    )

    assert len(report.contradictions) == 1
    contradiction = report.contradictions[0]
    assert contradiction.contradiction_type.value == "negated_relationship"
    assert contradiction.severity.value == "blocking"
