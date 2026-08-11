from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from advisor_core.knowledge import (
    Capability,
    CatalogProjectionSpec,
    Claim,
    ClaimScope,
    Component,
    DeployableProjectionSpec,
    EvidenceReference,
    Interface,
    KnowledgeCatalogCompilationError,
    KnowledgeRelationship,
    Offering,
    ReviewMetadata,
    ScopeDimension,
    SnapshotManifest,
    SourceRegistry,
    Variant,
    compile_knowledge_catalog,
    compile_knowledge_deployable_catalog,
)
from advisor_core.v3 import (
    ArchitecturePattern,
    CatalogManifest,
    DecisionRule,
    RequirementDefinition,
)


AS_OF = date(2026, 8, 11)
REVIEWED_AT = datetime(2026, 8, 11, 12, tzinfo=timezone.utc)
HASH_A = f"sha256:{'a' * 64}"
HASH_B = f"sha256:{'b' * 64}"


def metadata(entity_id: str, title: str) -> dict[str, object]:
    return {
        "id": entity_id,
        "title": title,
        "summary": f"Reviewed semantic definition for {title}.",
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


def scope() -> ClaimScope:
    return ClaimScope(
        provider=ScopeDimension(mode="all"),
        product=ScopeDimension(mode="all"),
        variant=ScopeDimension(mode="all"),
        version=ScopeDimension(mode="all"),
        region=ScopeDimension(mode="all"),
        configuration=ScopeDimension(mode="all"),
    )


def registry() -> SourceRegistry:
    terms = {
        "status": "review_required",
        "allows_automated_collection": False,
        "allows_snapshot_retention": False,
        "allows_derivative_claims": False,
        "review": {"status": "in_review"},
    }
    return SourceRegistry.model_validate(
        {
            "schema_version": "1.0",
            "sources": [
                {
                    "id": "source:provider-docs",
                    "name": "Provider documentation",
                    "publisher": "Example Provider",
                    "source_class": "official_product_documentation",
                    "base_uri": "https://example.test/docs",
                    "owner_id": "team:platform-advisor",
                    "authority_tier": "tier_a_decision_authority",
                    "cadence": "weekly",
                    "collector": "http",
                    "parser": "html",
                    "freshness_days": 14,
                    "terms": terms,
                },
                {
                    "id": "source:provider-api",
                    "name": "Provider API",
                    "publisher": "Example Provider",
                    "source_class": "official_product_api",
                    "base_uri": "https://example.test/api",
                    "owner_id": "team:platform-advisor",
                    "authority_tier": "tier_a_decision_authority",
                    "cadence": "daily",
                    "collector": "api",
                    "parser": "json",
                    "freshness_days": 3,
                    "terms": terms,
                },
            ],
        }
    )


def snapshot(
    snapshot_id: str,
    source_id: str,
    content_hash: str,
) -> SnapshotManifest:
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        source_id=source_id,
        retrieved_at="2026-08-11T10:00:00+00:00",
        final_uri=f"https://example.test/{snapshot_id.split(':', 1)[1]}",
        media_type="text/html",
        headers=(),
        raw_content_hash=content_hash,
        normalized_content_hash=content_hash,
        raw_object_key=f"snapshots/{snapshot_id}/raw",
        normalized_object_key=f"snapshots/{snapshot_id}/normalized.txt",
        manifest_object_key=f"snapshots/{snapshot_id}/manifest.json",
        manifest_hash=content_hash,
    )


def semantic_input():
    component = Component(
        **metadata("component:model-gateway", "Model gateway"),
        plane="model",
        responsibility="Route requests to approved models.",
        boundary="Owns routing and model access policy.",
    )
    capability = Capability(
        **metadata("capability:model-routing", "Model routing"),
        category="model-access",
    )
    knowledge_claim = Claim(
        **metadata("claim:model-gateway-routing", "Gateway routing"),
        statement="The model gateway provides policy-based model routing.",
        subject_id=component.id,
        predicate="implements",
        object_id=capability.id,
        scope=scope(),
        claim_class="product_fact",
        evidence=(
            EvidenceReference(
                source_snapshot_id="snapshot:provider-api-20260811",
                authority_tier="tier_a_decision_authority",
                source_locator="/capabilities/model-routing",
            ),
            EvidenceReference(
                source_snapshot_id="snapshot:provider-docs-20260811",
                authority_tier="tier_a_decision_authority",
                source_locator="Model routing section",
            ),
        ),
    )
    relationship = KnowledgeRelationship(
        **metadata(
            "relationship:model-gateway-supported-by-routing",
            "Gateway routing evidence",
        ),
        relationship_type="SUPPORTED_BY",
        source_id=component.id,
        source_kind="Component",
        target_id=knowledge_claim.id,
        target_kind="Claim",
        cardinality="many_to_many",
        scope=scope(),
        supporting_claim_ids=(knowledge_claim.id,),
    )
    return (component, capability, knowledge_claim), (relationship,)


def projection() -> CatalogProjectionSpec:
    claim_ids = ("claim:model-gateway-routing",)
    return CatalogProjectionSpec(
        manifest=CatalogManifest(
            id="catalog:knowledge-compiled",
            version="3.1.0",
            title="Knowledge compiled coding platform",
            effective_on=AS_OF,
        ),
        requirements=(
            RequirementDefinition(
                id="requirement:multi-provider",
                version="1.0.0",
                name="Multiple providers",
                description="Whether more than one model provider is required.",
                value_type="boolean",
                evidence_claim_ids=claim_ids,
            ),
        ),
        patterns=(
            ArchitecturePattern(
                id="pattern:shared-model-access",
                version="1.0.0",
                name="Shared model access",
                description="Central governed access to approved models.",
                role="deployment_family",
                component_ids=("component:model-gateway",),
                evidence_claim_ids=claim_ids,
            ),
        ),
        rules=(
            DecisionRule(
                id="rule:require-model-gateway",
                version="1.0.0",
                name="Require model gateway",
                description="Multiple providers require governed routing.",
                when=(
                    {
                        "requirement_id": "requirement:multi-provider",
                        "operator": "equals",
                        "value": True,
                    },
                ),
                authority="hard_constraint",
                effect="require",
                target_component_ids=("component:model-gateway",),
                evidence_claim_ids=claim_ids,
            ),
        ),
    )


def snapshots() -> tuple[SnapshotManifest, ...]:
    return (
        snapshot(
            "snapshot:provider-docs-20260811",
            "source:provider-docs",
            HASH_A,
        ),
        snapshot(
            "snapshot:provider-api-20260811",
            "source:provider-api",
            HASH_B,
        ),
    )


def test_compiles_semantic_knowledge_and_expands_corroborating_evidence():
    entities, relationships = semantic_input()

    release = compile_knowledge_catalog(
        entities=entities,
        relationships=relationships,
        source_registry=registry(),
        snapshots=snapshots(),
        projection=projection(),
        as_of=AS_OF,
    )

    generated_claim_ids = tuple(
        claim.id for claim in release.evidence_claims
    )
    assert len(generated_claim_ids) == 2
    assert all(
        claim_id.startswith("claim:model-gateway-routing-evidence-")
        for claim_id in generated_claim_ids
    )
    assert release.components[0].evidence_claim_ids == generated_claim_ids
    assert release.requirements[0].evidence_claim_ids == generated_claim_ids
    assert release.patterns[0].evidence_claim_ids == generated_claim_ids
    assert release.rules[0].evidence_claim_ids == generated_claim_ids


def test_compilation_is_independent_of_input_order():
    entities, relationships = semantic_input()
    first = compile_knowledge_catalog(
        entities=entities,
        relationships=relationships,
        source_registry=registry(),
        snapshots=snapshots(),
        projection=projection(),
        as_of=AS_OF,
    )
    second = compile_knowledge_catalog(
        entities=tuple(reversed(entities)),
        relationships=tuple(reversed(relationships)),
        source_registry=registry(),
        snapshots=tuple(reversed(snapshots())),
        projection=projection(),
        as_of=AS_OF,
    )

    assert first.content_hash == second.content_hash
    assert first.replay_json() == second.replay_json()


def test_source_authority_mismatch_fails_closed():
    entities, relationships = semantic_input()
    invalid_claim = entities[2].model_copy(
        update={
            "evidence": (
                EvidenceReference(
                    source_snapshot_id="snapshot:provider-docs-20260811",
                    authority_tier="tier_b_operational_guidance",
                    source_locator="Model routing section",
                ),
            )
        }
    )

    with pytest.raises(
        KnowledgeCatalogCompilationError,
        match="registered as tier_a_decision_authority",
    ):
        compile_knowledge_catalog(
            entities=(entities[0], entities[1], invalid_claim),
            relationships=relationships,
            source_registry=registry(),
            snapshots=snapshots(),
            projection=projection(),
            as_of=AS_OF,
        )


def deployable_entities():
    entities, relationships = semantic_input()
    interface = Interface(
        **metadata("interface:model-api", "Model API"),
        protocol="HTTPS",
        protocol_version="1.0",
        transports=("https",),
        authentication_methods=("oauth2",),
    )
    provider_records = (
        ("aws", "AWS", "Managed Gateway"),
        ("oss", "Open Source", "Open Gateway"),
        ("saas", "SaaS Vendor", "SaaS Gateway"),
        ("byop", "Customer Platform", "Customer Gateway"),
    )
    offerings = tuple(
        Offering(
            **metadata(f"offering:{slug}-gateway", product),
            provider=provider,
            product=product,
            offering_type=(
                "open_source"
                if slug == "oss"
                else "managed_service"
            ),
        )
        for slug, provider, product in provider_records
    )
    variants = tuple(
        Variant(
            **metadata(f"variant:{slug}-gateway", f"{product} variant"),
            provider=provider,
            product=product,
            deployment_model=(
                "self_managed"
                if slug == "oss"
                else "customer_selected"
                if slug == "byop"
                else "managed"
            ),
        )
        for slug, provider, product in provider_records
    )
    return (*entities, interface, *offerings, *variants), relationships


def deployable_projection(logical_catalog_id: str) -> DeployableProjectionSpec:
    dimension_id = "dimension:fitness"
    provider_data = (
        ("aws", "provider:aws", "managed"),
        ("oss", "provider:oss", "self_managed"),
        ("saas", "provider:saas", "managed"),
        ("byop", "provider:byop", "customer_selected"),
    )
    return DeployableProjectionSpec.model_validate(
        {
            "manifest": {
                "id": "catalog:knowledge-deployable",
                "version": "3.1.0",
                "title": "Knowledge compiled deployable catalog",
                "effective_on": AS_OF,
                "logical_catalog_id": logical_catalog_id,
            },
            "component_bindings": [
                {
                    "component_id": "component:model-gateway",
                    "provides_interface_ids": ["interface:model-api"],
                }
            ],
            "providers": [
                {
                    "id": provider_id,
                    "version": "1.0.0",
                    "name": f"{slug.upper()} provider",
                    "provider_class": slug,
                    "delivery_model": delivery_model,
                    "dimension_scores": [
                        {"dimension_id": dimension_id, "value": 75}
                    ],
                }
                for slug, provider_id, delivery_model in provider_data
            ],
            "variant_bindings": [
                {
                    "variant_id": f"variant:{slug}-gateway",
                    "component_id": "component:model-gateway",
                    "provider_id": provider_id,
                    "provider_class": slug,
                    "delivery_model": delivery_model,
                }
                for slug, provider_id, delivery_model in provider_data
            ],
            "bundle_templates": [
                {
                    "id": f"bundle-template:{slug}",
                    "version": "1.0.0",
                    "name": f"{slug.upper()} bundle",
                    "description": f"{slug.upper()} deployable bundle.",
                    "deployment_family_id": "pattern:shared-model-access",
                    "default_provider_class": slug,
                    "integration_penalty": 0,
                }
                for slug, _, _ in provider_data
            ],
            "score_dimensions": [
                {
                    "id": dimension_id,
                    "version": "1.0.0",
                    "name": "Fitness",
                    "description": "Overall contextual fitness.",
                }
            ],
            "score_profiles": [
                {
                    "id": "score-profile:balanced",
                    "version": "1.0.0",
                    "name": "Balanced",
                    "weights": [
                        {"dimension_id": dimension_id, "weight": 1.0}
                    ],
                    "conditional_penalty": 5,
                }
            ],
        }
    )


def test_compiles_semantic_offerings_variants_and_interfaces():
    entities, relationships = deployable_entities()
    logical = compile_knowledge_catalog(
        entities=entities,
        relationships=relationships,
        source_registry=registry(),
        snapshots=snapshots(),
        projection=projection(),
        as_of=AS_OF,
    )

    deployable = compile_knowledge_deployable_catalog(
        logical_catalog=logical,
        entities=entities,
        relationships=relationships,
        projection=deployable_projection(logical.id),
        as_of=AS_OF,
    )

    assert [interface.id for interface in deployable.interfaces] == [
        "interface:model-api"
    ]
    assert [variant.id for variant in deployable.service_variants] == [
        "variant:aws-gateway",
        "variant:byop-gateway",
        "variant:oss-gateway",
        "variant:saas-gateway",
    ]
