"""Executable migration from the authored v3 JSON catalogs to knowledge inputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import json
from pathlib import Path

from pydantic import TypeAdapter

from advisor_core.v3.models import CatalogManifest, CatalogRelease
from advisor_core.v3.deployable.models import (
    DeployableCatalogManifest,
    DeployableCatalogRelease,
    ProviderClass,
)

from .catalog_compiler import (
    CatalogProjectionSpec,
    DeployableProjectionSpec,
    VariantRuntimeBinding,
)
from .models import (
    Capability,
    Claim,
    ClaimScope,
    Component,
    EvidenceReference,
    Interface,
    KnowledgeEntity,
    KnowledgeRelationship,
    Offering,
    ReviewMetadata,
    ScopeDimension,
    Variant,
    content_hash,
)
from .snapshot_store import SnapshotManifest
from .source_registry import SourceRegistry


@dataclass(frozen=True)
class LegacyKnowledgeMigration:
    entities: tuple[KnowledgeEntity, ...]
    relationships: tuple[KnowledgeRelationship, ...]
    source_registry: SourceRegistry
    snapshots: tuple[SnapshotManifest, ...]
    logical_projection: CatalogProjectionSpec
    deployable_projection: DeployableProjectionSpec


class LegacyMigrationIntegrityError(ValueError):
    pass


def _approved_review() -> ReviewMetadata:
    return ReviewMetadata(
        status="approved",
        reviewer_ids=("person:legacy-catalog-reviewer",),
        reviewed_at="2026-08-11T12:00:00Z",
        rationale="Approved migration of the pinned v3 catalog baseline.",
    )


def _metadata(
    *,
    entity_id: str,
    title: str,
    summary: str,
    effective_from: date,
    stale_after: date,
) -> dict[str, object]:
    return {
        "id": entity_id,
        "title": title,
        "summary": summary,
        "lifecycle": "active",
        "owner_id": "team:platform-advisor",
        "effective_from": effective_from,
        "stale_after": stale_after,
        "review": _approved_review(),
    }


def _global_scope() -> ClaimScope:
    return ClaimScope(
        provider=ScopeDimension(mode="all"),
        product=ScopeDimension(mode="all"),
        variant=ScopeDimension(mode="all"),
        version=ScopeDimension(mode="all"),
        region=ScopeDimension(mode="all"),
        configuration=ScopeDimension(mode="all"),
    )


def _offering_type(provider_class: ProviderClass) -> str:
    return {
        ProviderClass.AWS: "managed_service",
        ProviderClass.OSS: "open_source",
        ProviderClass.SAAS: "saas",
        ProviderClass.BYOP: "commercial_software",
    }[provider_class]


def migrate_legacy_catalogs(
    logical: CatalogRelease,
    deployable: DeployableCatalogRelease,
) -> LegacyKnowledgeMigration:
    """Translate a pinned legacy release without renaming runtime identities."""

    if deployable.logical_catalog_id != logical.id:
        raise ValueError("deployable release does not target the logical release")

    effective_from = logical.effective_on
    default_stale_after = effective_from + timedelta(days=3650)
    scope = _global_scope()

    source_registry = SourceRegistry.model_validate(
        {
            "sources": [
                {
                    "id": source.id,
                    "name": source.title,
                    "publisher": source.publisher,
                    "source_class": "legacy_v3_evidence",
                    "base_uri": source.uri,
                    "owner_id": "team:platform-advisor",
                    "authority_tier": "tier_a_decision_authority",
                    "cadence": "manual",
                    "collector": "manual_upload",
                    "parser": "text",
                    "freshness_days": 365,
                    "enabled": False,
                    "terms": {
                        "status": "approved",
                        "allows_automated_collection": False,
                        "allows_snapshot_retention": True,
                        "allows_derivative_claims": True,
                        "review": _approved_review().model_dump(mode="json"),
                    },
                    "tags": ["legacy-v3", "migration"],
                }
                for source in logical.evidence_sources
            ]
        }
    )
    snapshots = tuple(
        SnapshotManifest(
            snapshot_id=source.id,
            source_id=source.id,
            retrieved_at=source.retrieved_at.isoformat(),
            final_uri=source.uri,
            media_type="text/plain",
            headers=(),
            raw_content_hash=source.snapshot_hash,
            normalized_content_hash=source.snapshot_hash,
            raw_object_key=f"knowledge/legacy/{source.id}/raw",
            normalized_object_key=f"knowledge/legacy/{source.id}/normalized.txt",
            manifest_object_key=f"knowledge/legacy/{source.id}/manifest.json",
            manifest_hash=source.snapshot_hash,
        )
        for source in logical.evidence_sources
    )

    component_claims = {
        claim_id: component.id
        for component in logical.components
        for claim_id in component.evidence_claim_ids
    }
    fallback_subject = (
        "component:architecture-knowledge"
        if any(
            component.id == "component:architecture-knowledge"
            for component in logical.components
        )
        else logical.components[0].id
    )

    components: tuple[KnowledgeEntity, ...] = tuple(
        Component(
            **_metadata(
                entity_id=component.id,
                title=component.name,
                summary=component.description,
                effective_from=effective_from,
                stale_after=default_stale_after,
            ),
            plane=component.plane.value,
            component_kind=component.kind.value,
            responsibility=component.description,
            boundary=(
                "Preserves the logical responsibility boundary from the "
                "pinned v3 migration baseline."
            ),
        )
        for component in logical.components
    )
    claims: tuple[KnowledgeEntity, ...] = tuple(
        Claim(
            **_metadata(
                entity_id=claim.id,
                title=claim.id.split(":", 1)[1].replace("-", " ").title(),
                summary=claim.statement,
                effective_from=claim.effective_on,
                stale_after=claim.expires_on or default_stale_after,
            ),
            effective_until=claim.expires_on,
            statement=claim.statement,
            subject_id=component_claims.get(claim.id, fallback_subject),
            predicate="supports_decision",
            object_value=True,
            scope=scope,
            claim_class="decision_guidance",
            evidence=(
                EvidenceReference(
                    source_snapshot_id=claim.source_id,
                    authority_tier="tier_a_decision_authority",
                    source_locator=claim.source_locator,
                ),
            ),
            criticality="critical" if claim.critical else "standard",
        )
        for claim in logical.evidence_claims
    )

    interfaces: tuple[KnowledgeEntity, ...] = tuple(
        Interface(
            **_metadata(
                entity_id=interface.id,
                title=interface.name,
                summary=interface.description,
                effective_from=deployable.effective_on,
                stale_after=default_stale_after,
            ),
            protocol=interface.protocol,
            protocol_version=interface.contract_version,
        )
        for interface in deployable.interfaces
    )
    provider_by_id = {
        provider.id: provider for provider in deployable.providers
    }
    offerings: list[KnowledgeEntity] = []
    variants: list[KnowledgeEntity] = []
    for service in deployable.service_variants:
        provider = provider_by_id[service.provider_id]
        offering_id = f"offering:{service.id.split(':', 1)[1]}"
        offerings.append(
            Offering(
                **_metadata(
                    entity_id=offering_id,
                    title=service.name,
                    summary=(
                        f"Legacy {provider.provider_class.value} offering for "
                        f"{service.component_id}."
                    ),
                    effective_from=deployable.effective_on,
                    stale_after=default_stale_after,
                ),
                provider=provider.name,
                product=service.name,
                offering_type=_offering_type(provider.provider_class),
            )
        )
        variants.append(
            Variant(
                **_metadata(
                    entity_id=service.id,
                    title=service.name,
                    summary=(
                        f"Deployable variant for {service.component_id} "
                        f"migrated from the v3 catalog."
                    ),
                    effective_from=deployable.effective_on,
                    stale_after=default_stale_after,
                ),
                provider=provider.name,
                product=service.name,
                deployment_model=service.delivery_model.value,
            )
        )

    architecture_claim_id = (
        "claim:architecture-first-authority"
        if any(
            claim.id == "claim:architecture-first-authority"
            for claim in logical.evidence_claims
        )
        else logical.evidence_claims[0].id
    )
    relationships: list[KnowledgeRelationship] = []
    for component in logical.components:
        dependency_evidence = (
            component.evidence_claim_ids or (architecture_claim_id,)
        )
        for dependency_id in component.dependency_ids:
            relationships.append(
                KnowledgeRelationship(
                    **_metadata(
                        entity_id=(
                            "relationship:"
                            f"{component.id.split(':', 1)[1]}-requires-"
                            f"{dependency_id.split(':', 1)[1]}"
                        ),
                        title=f"{component.name} dependency",
                        summary=(
                            f"{component.id} requires {dependency_id} in the "
                            "pinned v3 logical architecture."
                        ),
                        effective_from=effective_from,
                        stale_after=default_stale_after,
                    ),
                    relationship_type="REQUIRES",
                    source_id=component.id,
                    source_kind="Component",
                    target_id=dependency_id,
                    target_kind="Component",
                    cardinality="one_to_many",
                    scope=scope,
                    supporting_claim_ids=dependency_evidence,
                )
            )
        for claim_id in component.evidence_claim_ids:
            relationships.append(
                KnowledgeRelationship(
                    **_metadata(
                        entity_id=(
                            "relationship:"
                            f"{component.id.split(':', 1)[1]}-supported-by-"
                            f"{claim_id.split(':', 1)[1]}"
                        ),
                        title=f"{component.name} evidence",
                        summary=f"{component.id} is supported by {claim_id}.",
                        effective_from=effective_from,
                        stale_after=default_stale_after,
                    ),
                    relationship_type="SUPPORTED_BY",
                    source_id=component.id,
                    source_kind="Component",
                    target_id=claim_id,
                    target_kind="Claim",
                    cardinality="many_to_many",
                    scope=scope,
                    supporting_claim_ids=(claim_id,),
                )
            )

    logical_projection = CatalogProjectionSpec(
        manifest=CatalogManifest(
            id=logical.id,
            version=logical.version,
            schema_version=logical.schema_version,
            title=logical.title,
            effective_on=logical.effective_on,
        ),
        requirements=logical.requirements,
        patterns=logical.patterns,
        rules=logical.rules,
    )
    deployable_projection = DeployableProjectionSpec(
        manifest=DeployableCatalogManifest(
            id=deployable.id,
            version=deployable.version,
            schema_version=deployable.schema_version,
            title=deployable.title,
            effective_on=deployable.effective_on,
            logical_catalog_id=deployable.logical_catalog_id,
        ),
        component_bindings=deployable.component_bindings,
        providers=deployable.providers,
        variant_bindings=tuple(
            VariantRuntimeBinding(
                variant_id=service.id,
                component_id=service.component_id,
                provider_id=service.provider_id,
                provider_class=service.provider_class,
                delivery_model=service.delivery_model,
                supported_capabilities=service.supported_capabilities,
                unsupported_capabilities=service.unsupported_capabilities,
                score_adjustments=service.score_adjustments,
            )
            for service in deployable.service_variants
        ),
        bundle_templates=deployable.bundle_templates,
        score_dimensions=deployable.score_dimensions,
        score_profiles=deployable.score_profiles,
        capability_rules=deployable.capability_rules,
    )
    return LegacyKnowledgeMigration(
        entities=(
            *components,
            *claims,
            *interfaces,
            *offerings,
            *variants,
        ),
        relationships=tuple(relationships),
        source_registry=source_registry,
        snapshots=snapshots,
        logical_projection=logical_projection,
        deployable_projection=deployable_projection,
    )


def legacy_migration_payload(
    migration: LegacyKnowledgeMigration,
    *,
    logical_source_hash: str,
    deployable_source_hash: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "logical_source_hash": logical_source_hash,
        "deployable_source_hash": deployable_source_hash,
        "entities": [
            entity.model_dump(mode="json", exclude_none=True)
            for entity in sorted(migration.entities, key=lambda item: item.id)
        ],
        "relationships": [
            relationship.model_dump(mode="json", exclude_none=True)
            for relationship in sorted(
                migration.relationships,
                key=lambda item: item.id,
            )
        ],
        "source_registry": migration.source_registry.model_dump(
            mode="json",
            exclude_none=True,
        ),
        "snapshots": [
            snapshot.model_dump(mode="json", exclude_none=True)
            for snapshot in sorted(
                migration.snapshots,
                key=lambda item: item.snapshot_id,
            )
        ],
        "logical_projection": migration.logical_projection.model_dump(
            mode="json",
            exclude_none=True,
        ),
        "deployable_projection": migration.deployable_projection.model_dump(
            mode="json",
            exclude_none=True,
        ),
    }
    return {**payload, "bundle_hash": content_hash(payload)}


def write_legacy_migration_bundle(
    path: Path,
    migration: LegacyKnowledgeMigration,
    *,
    logical_source_hash: str,
    deployable_source_hash: str,
) -> str:
    payload = legacy_migration_payload(
        migration,
        logical_source_hash=logical_source_hash,
        deployable_source_hash=deployable_source_hash,
    )
    serialized = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")
    return str(payload["bundle_hash"])


def load_legacy_migration_bundle(
    path: Path,
) -> tuple[LegacyKnowledgeMigration, str, str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise LegacyMigrationIntegrityError(
            "legacy migration bundle must be an object"
        )
    expected_hash = document.pop("bundle_hash", None)
    if expected_hash != content_hash(document):
        raise LegacyMigrationIntegrityError(
            "legacy migration bundle hash does not match its content"
        )
    if document.get("schema_version") != "1.0":
        raise LegacyMigrationIntegrityError(
            "unsupported legacy migration bundle schema"
        )

    entity_adapter = TypeAdapter(KnowledgeEntity)
    migration = LegacyKnowledgeMigration(
        entities=tuple(
            entity_adapter.validate_python(entity)
            for entity in document["entities"]
        ),
        relationships=tuple(
            KnowledgeRelationship.model_validate(relationship)
            for relationship in document["relationships"]
        ),
        source_registry=SourceRegistry.model_validate(
            document["source_registry"]
        ),
        snapshots=tuple(
            SnapshotManifest.model_validate(snapshot)
            for snapshot in document["snapshots"]
        ),
        logical_projection=CatalogProjectionSpec.model_validate(
            document["logical_projection"]
        ),
        deployable_projection=DeployableProjectionSpec.model_validate(
            document["deployable_projection"]
        ),
    )
    return (
        migration,
        str(document["logical_source_hash"]),
        str(document["deployable_source_hash"]),
    )
