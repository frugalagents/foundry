from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from advisor_core.knowledge import (
    Capability,
    Claim,
    ClaimScope,
    Component,
    DecisionPattern,
    EvidenceReference,
    Interface,
    IdentifierTransition,
    KnowledgeEntity,
    KnowledgeRelationship,
    Offering,
    OutcomeObservation,
    ReviewMetadata,
    ScopeDimension,
    Variant,
)


EFFECTIVE_FROM = date(2026, 8, 11)
STALE_AFTER = date(2026, 11, 11)
REVIEWED_AT = datetime(2026, 8, 11, 12, tzinfo=timezone.utc)


def approved_metadata(entity_id: str, title: str) -> dict[str, object]:
    return {
        "id": entity_id,
        "title": title,
        "summary": f"Reviewed definition for {title}.",
        "lifecycle": "active",
        "owner_id": "team:platform-advisor",
        "effective_from": EFFECTIVE_FROM,
        "stale_after": STALE_AFTER,
        "review": ReviewMetadata(
            status="approved",
            reviewer_ids=("person:knowledge-reviewer",),
            reviewed_at=REVIEWED_AT,
        ),
    }


def example_scope() -> ClaimScope:
    return ClaimScope(
        provider=ScopeDimension(
            mode="specified",
            values=("Example Provider",),
        ),
        product=ScopeDimension(
            mode="specified",
            values=("Example Runtime",),
        ),
        variant=ScopeDimension(
            mode="specified",
            values=("variant:example-runtime-managed",),
        ),
        version=ScopeDimension(
            mode="specified",
            values=("2026-08",),
        ),
        region=ScopeDimension(
            mode="specified",
            values=("eu-central-1",),
        ),
        configuration=ScopeDimension(mode="all"),
    )


@pytest.mark.parametrize(
    "entity",
    [
        Capability(
            **approved_metadata("capability:model-routing", "Model routing"),
            category="model-access",
            desired_outcomes=("provider portability",),
        ),
        Component(
            **approved_metadata("component:model-gateway", "Model gateway"),
            plane="model",
            responsibility="Route governed requests to approved models.",
            boundary="Owns model selection, policy enforcement, and failover.",
        ),
        Offering(
            **approved_metadata("offering:example-runtime", "Example runtime"),
            provider="Example Provider",
            product="Example Runtime",
            offering_type="managed_service",
        ),
        Variant(
            **approved_metadata(
                "variant:example-runtime-managed",
                "Example managed runtime",
            ),
            provider="Example Provider",
            product="Example Runtime",
            release="2026-08",
            deployment_model="managed",
            regions=("eu-central-1", "us-east-1"),
        ),
        Interface(
            **approved_metadata("interface:mcp-stdio", "MCP over stdio"),
            protocol="MCP",
            protocol_version="2026-06-18",
            transports=("stdio",),
        ),
        Claim(
            **approved_metadata(
                "claim:runtime-supports-mcp",
                "Runtime supports MCP",
            ),
            statement="The managed runtime supports MCP over stdio.",
            subject_id="variant:example-runtime-managed",
            predicate="supports_interface",
            object_id="interface:mcp-stdio",
            scope=example_scope(),
            claim_class="product_fact",
            evidence=(
                EvidenceReference(
                    source_snapshot_id=(
                        "snapshot:example-runtime-docs-20260811"
                    ),
                    authority_tier="tier_a_decision_authority",
                ),
            ),
        ),
        DecisionPattern(
            **approved_metadata(
                "decision-pattern:prefer-isolated-runtime",
                "Prefer isolated runtime",
            ),
            decision="Use an isolated runtime for untrusted code execution.",
            recommended_when=("agent-generated code is executed",),
            avoid_when=("the platform never executes code",),
            tradeoffs=("stronger isolation increases startup overhead",),
            supporting_claim_ids=("claim:runtime-supports-isolation",),
        ),
        OutcomeObservation(
            **approved_metadata(
                "outcome:runtime-latency-pilot",
                "Runtime latency pilot",
            ),
            workspace_id="workspace:pilot-one",
            architecture_revision_id="revision:pilot-one-r3",
            decision_pattern_ids=(
                "decision-pattern:prefer-isolated-runtime",
            ),
            metric_name="p95_startup_latency",
            metric_value=1.8,
            unit="seconds",
            observed_from=REVIEWED_AT,
            observed_until=datetime(
                2026,
                8,
                18,
                12,
                tzinfo=timezone.utc,
            ),
        ),
    ],
)
def test_all_entity_kinds_round_trip_through_discriminated_union(entity):
    adapter = TypeAdapter(KnowledgeEntity)

    parsed = adapter.validate_python(entity.model_dump(mode="json"))

    assert parsed == entity


def test_active_entity_requires_approved_review():
    with pytest.raises(ValidationError, match="active knowledge must be approved"):
        Capability(
            id="capability:model-routing",
            title="Model routing",
            summary="Route requests to an appropriate model.",
            lifecycle="active",
            owner_id="team:platform-advisor",
            effective_from=EFFECTIVE_FROM,
            stale_after=STALE_AFTER,
            category="model-access",
        )


def test_approved_review_requires_reviewer_and_timestamp():
    with pytest.raises(
        ValidationError,
        match="approved knowledge requires reviewer_ids and reviewed_at",
    ):
        ReviewMetadata(status="approved")


def test_claim_requires_exactly_one_object_form():
    values = {
        **approved_metadata("claim:invalid-object", "Invalid object"),
        "statement": "This claim has two object representations.",
        "subject_id": "offering:example-runtime",
        "predicate": "supports",
        "object_id": "interface:mcp-stdio",
        "object_value": True,
        "scope": example_scope(),
        "claim_class": "product_fact",
        "evidence": (
            EvidenceReference(
                source_snapshot_id="snapshot:example-docs-20260811",
                authority_tier="tier_a_decision_authority",
            ),
        ),
    }

    with pytest.raises(
        ValidationError,
        match="claim requires exactly one of object_id or object_value",
    ):
        Claim(**values)


def test_outcome_observation_rejects_reversed_window():
    values = {
        **approved_metadata("outcome:invalid-window", "Invalid window"),
        "workspace_id": "workspace:pilot-one",
        "architecture_revision_id": "revision:pilot-one-r3",
        "metric_name": "availability",
        "metric_value": 99.9,
        "unit": "percent",
        "observed_from": datetime(2026, 8, 12, tzinfo=timezone.utc),
        "observed_until": datetime(2026, 8, 11, tzinfo=timezone.utc),
    }

    with pytest.raises(
        ValidationError,
        match="observed_until must not precede observed_from",
    ):
        OutcomeObservation(**values)


def test_relationship_encodes_direction_cardinality_scope_and_provenance():
    relationship = KnowledgeRelationship(
        **approved_metadata(
            "relationship:managed-runtime-implements-isolation",
            "Managed runtime implements isolation",
        ),
        relationship_type="IMPLEMENTS",
        source_id="offering:managed-runtime",
        source_kind="Offering",
        target_id="capability:isolated-execution",
        target_kind="Capability",
        cardinality="many_to_many",
        scope=example_scope(),
        supporting_claim_ids=("claim:managed-runtime-isolation",),
    )

    assert relationship.relationship_type.value == "IMPLEMENTS"
    assert relationship.scope.region.values == ("eu-central-1",)
    assert relationship.supporting_claim_ids == (
        "claim:managed-runtime-isolation",
    )


def test_relationship_rejects_invalid_entity_kinds():
    values = {
        **approved_metadata(
            "relationship:claim-implements-capability",
            "Invalid implementation relationship",
        ),
        "relationship_type": "IMPLEMENTS",
        "source_id": "claim:managed-runtime-isolation",
        "source_kind": "Claim",
        "target_id": "capability:isolated-execution",
        "target_kind": "Capability",
        "cardinality": "many_to_many",
        "scope": example_scope(),
        "supporting_claim_ids": ("claim:managed-runtime-isolation",),
    }

    with pytest.raises(
        ValidationError,
        match="IMPLEMENTS does not allow source kind Claim",
    ):
        KnowledgeRelationship(**values)


def test_symmetric_relationships_have_canonical_direction():
    values = {
        **approved_metadata(
            "relationship:runtime-alternative",
            "Runtime alternatives",
        ),
        "relationship_type": "ALTERNATIVE_TO",
        "source_id": "offering:z-runtime",
        "source_kind": "Offering",
        "target_id": "offering:a-runtime",
        "target_kind": "Offering",
        "cardinality": "many_to_many",
        "scope": example_scope(),
        "supporting_claim_ids": ("claim:runtime-alternatives",),
    }

    with pytest.raises(
        ValidationError,
        match="symmetric relationships must store identifiers in lexical order",
    ):
        KnowledgeRelationship(**values)


def test_supported_by_relationship_names_its_target_claim_as_provenance():
    values = {
        **approved_metadata(
            "relationship:runtime-supported-by",
            "Runtime evidence",
        ),
        "relationship_type": "SUPPORTED_BY",
        "source_id": "offering:managed-runtime",
        "source_kind": "Offering",
        "target_id": "claim:managed-runtime-isolation",
        "target_kind": "Claim",
        "cardinality": "many_to_many",
        "scope": example_scope(),
        "supporting_claim_ids": ("claim:different-evidence",),
    }

    with pytest.raises(
        ValidationError,
        match="SUPPORTED_BY target must be included",
    ):
        KnowledgeRelationship(**values)


@pytest.mark.parametrize(
    ("transition_type", "prior_ids", "successor_ids"),
    [
        (
            "rename",
            ("capability:old-routing",),
            ("capability:model-routing",),
        ),
        (
            "merge",
            ("capability:model-proxy", "capability:model-router"),
            ("capability:model-gateway",),
        ),
        (
            "split",
            ("capability:execution",),
            (
                "capability:code-execution",
                "capability:workflow-execution",
            ),
        ),
        ("retire", ("capability:legacy-runtime",), ()),
    ],
)
def test_identifier_transition_shapes(
    transition_type,
    prior_ids,
    successor_ids,
):
    transition = IdentifierTransition(
        id=f"transition:{transition_type}-example",
        transition_type=transition_type,
        prior_ids=prior_ids,
        successor_ids=successor_ids,
        effective_on=EFFECTIVE_FROM,
        rationale="Preserve historical identity while evolving the model.",
        review=ReviewMetadata(
            status="approved",
            reviewer_ids=("person:knowledge-reviewer",),
            reviewed_at=REVIEWED_AT,
        ),
    )

    assert transition.transition_type.value == transition_type


def test_identifier_transition_must_be_approved():
    with pytest.raises(
        ValidationError,
        match="identifier transitions must be approved",
    ):
        IdentifierTransition(
            id="transition:unapproved-rename",
            transition_type="rename",
            prior_ids=("capability:old-routing",),
            successor_ids=("capability:model-routing",),
            effective_on=EFFECTIVE_FROM,
            rationale="Proposed rename.",
            review=ReviewMetadata(status="in_review"),
        )


def test_identifier_transition_rejects_ambiguous_rename():
    with pytest.raises(
        ValidationError,
        match="invalid identifier shape for rename",
    ):
        IdentifierTransition(
            id="transition:ambiguous-rename",
            transition_type="rename",
            prior_ids=("capability:old-routing",),
            successor_ids=(
                "capability:model-routing",
                "capability:model-selection",
            ),
            effective_on=EFFECTIVE_FROM,
            rationale="This should be modeled as a split.",
            review=ReviewMetadata(
                status="approved",
                reviewer_ids=("person:knowledge-reviewer",),
                reviewed_at=REVIEWED_AT,
            ),
        )


def test_claim_scope_requires_every_applicability_dimension():
    with pytest.raises(ValidationError, match="Field required"):
        ClaimScope(
            provider=ScopeDimension(mode="all"),
            product=ScopeDimension(mode="all"),
            variant=ScopeDimension(mode="not_applicable"),
            version=ScopeDimension(mode="all"),
            region=ScopeDimension(mode="all"),
        )


def test_specified_scope_requires_values():
    with pytest.raises(
        ValidationError,
        match="specified scope requires at least one value",
    ):
        ScopeDimension(mode="specified")


def test_compatibility_claim_requires_two_reviewers():
    values = {
        **approved_metadata(
            "claim:runtime-compatible-with-gateway",
            "Runtime compatibility",
        ),
        "statement": "The runtime is compatible with the gateway.",
        "subject_id": "offering:managed-runtime",
        "predicate": "compatible_with",
        "object_id": "offering:managed-gateway",
        "scope": example_scope(),
        "claim_class": "compatibility",
        "evidence": (
            EvidenceReference(
                source_snapshot_id="snapshot:compatibility-docs-20260811",
                authority_tier="tier_a_decision_authority",
            ),
        ),
    }

    with pytest.raises(
        ValidationError,
        match="compatibility requires at least 2 reviewers",
    ):
        Claim(**values)


def test_product_fact_rejects_comparative_source_authority():
    values = {
        **approved_metadata(
            "claim:runtime-product-fact",
            "Runtime product fact",
        ),
        "statement": "The runtime supports a product capability.",
        "subject_id": "offering:managed-runtime",
        "predicate": "supports",
        "object_value": True,
        "scope": example_scope(),
        "claim_class": "product_fact",
        "evidence": (
            EvidenceReference(
                source_snapshot_id="snapshot:independent-benchmark-20260811",
                authority_tier="tier_c_comparative_evidence",
            ),
        ),
    }

    with pytest.raises(
        ValidationError,
        match="product_fact does not allow source tiers",
    ):
        Claim(**values)


def test_comparative_claim_requires_independent_corroboration():
    metadata = approved_metadata(
        "claim:runtime-comparative-latency",
        "Runtime comparative latency",
    )
    metadata["review"] = ReviewMetadata(
        status="approved",
        reviewer_ids=("person:knowledge-reviewer",),
        reviewed_at=REVIEWED_AT,
    )
    values = {
        **metadata,
        "statement": "The runtime has lower startup latency.",
        "subject_id": "offering:managed-runtime",
        "predicate": "lower_latency_than",
        "object_id": "offering:alternative-runtime",
        "scope": example_scope(),
        "claim_class": "comparative_evidence",
        "evidence": (
            EvidenceReference(
                source_snapshot_id="snapshot:benchmark-one-20260811",
                authority_tier="tier_c_comparative_evidence",
            ),
        ),
    }

    with pytest.raises(
        ValidationError,
        match="comparative_evidence requires independent corroboration",
    ):
        Claim(**values)
