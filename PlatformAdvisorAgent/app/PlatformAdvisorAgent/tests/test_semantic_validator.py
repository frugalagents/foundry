from __future__ import annotations

from datetime import date, datetime, timezone

from advisor_core.knowledge import (
    Capability,
    Claim,
    ClaimScope,
    Component,
    EvidenceReference,
    KnowledgeRelationship,
    ReviewMetadata,
    ScopeDimension,
    validate_knowledge_release,
)


AS_OF = date(2026, 8, 11)
REVIEWED_AT = datetime(2026, 8, 11, 12, tzinfo=timezone.utc)
SNAPSHOT_ID = "snapshot:official-runtime-docs-20260811"


def metadata(entity_id: str, title: str, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": entity_id,
        "title": title,
        "summary": f"Reviewed knowledge for {title}.",
        "lifecycle": "active",
        "owner_id": "team:platform-advisor",
        "effective_from": AS_OF,
        "stale_after": date(2027, 2, 11),
        "review": ReviewMetadata(
            status="approved",
            reviewer_ids=("person:knowledge-reviewer",),
            reviewed_at=REVIEWED_AT,
        ),
    }
    values.update(overrides)
    return values


def scope() -> ClaimScope:
    return ClaimScope(
        provider=ScopeDimension(mode="all"),
        product=ScopeDimension(mode="all"),
        variant=ScopeDimension(mode="all"),
        version=ScopeDimension(mode="all"),
        region=ScopeDimension(mode="all"),
        configuration=ScopeDimension(mode="all"),
    )


def capability(
    entity_id: str,
    *,
    lifecycle: str = "active",
    aliases: tuple[str, ...] = (),
) -> Capability:
    review = ReviewMetadata(
        status="approved",
        reviewer_ids=("person:knowledge-reviewer",),
        reviewed_at=REVIEWED_AT,
    )
    return Capability(
        **metadata(
            entity_id,
            entity_id,
            lifecycle=lifecycle,
            aliases=aliases,
            review=review,
        ),
        category="execution",
    )


def claim(subject_id: str, object_id: str) -> Claim:
    return Claim(
        **metadata("claim:runtime-implements-isolation", "Isolation claim"),
        statement="The runtime implements isolated execution.",
        subject_id=subject_id,
        predicate="implements",
        object_id=object_id,
        scope=scope(),
        claim_class="product_fact",
        evidence=(
            EvidenceReference(
                source_snapshot_id=SNAPSHOT_ID,
                authority_tier="tier_a_decision_authority",
            ),
        ),
    )


def relationship(
    relationship_id: str,
    relationship_type: str,
    source_id: str,
    target_id: str,
) -> KnowledgeRelationship:
    return KnowledgeRelationship(
        **metadata(relationship_id, relationship_id),
        relationship_type=relationship_type,
        source_id=source_id,
        source_kind="Capability",
        target_id=target_id,
        target_kind="Capability",
        cardinality=(
            "many_to_many"
            if relationship_type
            in {"COMPATIBLE_WITH", "INCOMPATIBLE_WITH"}
            else "one_to_many"
        ),
        scope=scope(),
        supporting_claim_ids=("claim:runtime-implements-isolation",),
    )


def issue_codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_valid_release_has_stable_empty_report():
    runtime = capability("capability:managed-runtime")
    isolation = capability("capability:isolated-execution")
    evidence_claim = claim(runtime.id, isolation.id)

    report = validate_knowledge_release(
        entities=(runtime, isolation, evidence_claim),
        known_snapshot_ids=(SNAPSHOT_ID,),
        as_of=AS_OF,
    )
    repeated = validate_knowledge_release(
        entities=(runtime, isolation, evidence_claim),
        known_snapshot_ids=(SNAPSHOT_ID,),
        as_of=AS_OF,
    )

    assert report.is_valid
    assert report.issues == ()
    assert report.report_hash == repeated.report_hash


def test_missing_references_and_evidence_fail_closed():
    report = validate_knowledge_release(
        entities=(
            claim(
                "capability:missing-runtime",
                "capability:missing-isolation",
            ),
        ),
        as_of=AS_OF,
    )

    assert not report.is_valid
    assert issue_codes(report) == {
        "missing_entity_reference",
        "missing_evidence_snapshot",
    }


def test_alias_and_identifier_collisions_are_rejected():
    first = capability(
        "capability:first",
        aliases=("capability:legacy",),
    )
    second = capability(
        "capability:second",
        aliases=("capability:legacy",),
    )
    canonical = capability("capability:legacy")

    report = validate_knowledge_release(
        entities=(first, second, canonical),
        as_of=AS_OF,
    )

    assert not report.is_valid
    assert issue_codes(report) == {
        "alias_conflicts_with_identifier",
        "duplicate_alias",
    }


def test_active_stale_and_retired_references_are_rejected():
    runtime = capability(
        "capability:managed-runtime",
        lifecycle="retired",
    )
    isolation = Capability(
        **metadata(
            "capability:isolated-execution",
            "Isolation",
            effective_from=date(2026, 1, 1),
            stale_after=date(2026, 8, 10),
        ),
        category="execution",
    )
    evidence_claim = claim(runtime.id, isolation.id)

    report = validate_knowledge_release(
        entities=(runtime, isolation, evidence_claim),
        known_snapshot_ids=(SNAPSHOT_ID,),
        as_of=AS_OF,
    )

    assert not report.is_valid
    assert issue_codes(report) == {
        "active_reference_to_retired_entity",
        "stale_active_knowledge",
    }


def test_requires_cycles_are_rejected():
    first = capability("capability:first")
    second = capability("capability:second")
    evidence_claim = claim(first.id, second.id)
    forward = relationship(
        "relationship:first-requires-second",
        "REQUIRES",
        first.id,
        second.id,
    )
    reverse = relationship(
        "relationship:second-requires-first",
        "REQUIRES",
        second.id,
        first.id,
    )

    report = validate_knowledge_release(
        entities=(first, second, evidence_claim),
        relationships=(forward, reverse),
        known_snapshot_ids=(SNAPSHOT_ID,),
        as_of=AS_OF,
    )

    assert not report.is_valid
    assert "requires_cycle" in issue_codes(report)


def test_compatible_and_incompatible_edges_cannot_both_be_active():
    first = capability("capability:first")
    second = capability("capability:second")
    evidence_claim = claim(first.id, second.id)
    compatible = relationship(
        "relationship:first-compatible-second",
        "COMPATIBLE_WITH",
        first.id,
        second.id,
    )
    incompatible = relationship(
        "relationship:first-incompatible-second",
        "INCOMPATIBLE_WITH",
        first.id,
        second.id,
    )

    report = validate_knowledge_release(
        entities=(first, second, evidence_claim),
        relationships=(compatible, incompatible),
        known_snapshot_ids=(SNAPSHOT_ID,),
        as_of=AS_OF,
    )

    assert not report.is_valid
    assert "conflicting_relationships" in issue_codes(report)


def test_relationship_endpoint_kind_is_verified_against_entity():
    component = Component(
        **metadata("component:runtime", "Runtime"),
        plane="execution",
        responsibility="Execute workloads.",
        boundary="Owns execution only.",
    )
    isolation = capability("capability:isolated-execution")
    evidence_claim = claim(component.id, isolation.id)
    invalid = KnowledgeRelationship(
        **metadata("relationship:runtime-requires-isolation", "Requirement"),
        relationship_type="REQUIRES",
        source_id=component.id,
        source_kind="Capability",
        target_id=isolation.id,
        target_kind="Capability",
        cardinality="one_to_many",
        scope=scope(),
        supporting_claim_ids=(evidence_claim.id,),
    )

    report = validate_knowledge_release(
        entities=(component, isolation, evidence_claim),
        relationships=(invalid,),
        known_snapshot_ids=(SNAPSHOT_ID,),
        as_of=AS_OF,
    )

    assert not report.is_valid
    assert "entity_kind_mismatch" in issue_codes(report)
