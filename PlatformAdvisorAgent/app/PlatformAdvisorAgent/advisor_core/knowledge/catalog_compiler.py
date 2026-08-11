"""Compile approved semantic knowledge into the v3 runtime catalog contract."""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path

import yaml
from pydantic import Field, field_validator

from advisor_core.v3.catalog import compile_catalog_documents
from advisor_core.v3.deployable.catalog import compile_deployable_documents
from advisor_core.v3.deployable.models import (
    BundleTemplate,
    ComponentInterfaceBinding,
    DeployableCatalogDocument,
    DeployableCatalogManifest,
    DeployableCatalogRelease,
    DeliveryModel,
    DimensionValue,
    InterfaceContract,
    ProviderClass,
    ProviderProfile,
    RequirementCapabilityRule,
    ScoreDimension,
    ScoreProfile,
    ServiceVariant,
)
from advisor_core.v3.models import (
    ArchitecturePattern,
    CatalogDocument,
    CatalogManifest,
    CatalogRelease,
    ComponentDefinition,
    DecisionRule,
    EvidenceClaim,
    EvidenceReviewStatus,
    EvidenceSource,
    RequirementDefinition,
)

from .models import (
    Claim,
    Component,
    FrozenModel,
    Interface,
    KnowledgeEntity,
    KnowledgeLifecycle,
    KnowledgeRelationship,
    Offering,
    RelationshipType,
    ReviewStatus,
    StableId,
    Variant,
)
from .okf import load_okf_corpus
from .snapshot_store import SnapshotManifest
from .source_registry import SourceRegistry
from .validation import validate_knowledge_release


class KnowledgeCatalogCompilationError(ValueError):
    pass


class CatalogProjectionSpec(FrozenModel):
    """Runtime-only records that cannot be inferred from semantic facts."""

    manifest: CatalogManifest
    requirements: tuple[RequirementDefinition, ...] = ()
    patterns: tuple[ArchitecturePattern, ...] = ()
    rules: tuple[DecisionRule, ...] = ()

    @field_validator("requirements", "patterns", "rules")
    @classmethod
    def records_are_unique(cls, records: tuple[object, ...]) -> tuple[object, ...]:
        identifiers = [record.id for record in records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("projection record IDs must be unique")
        return tuple(sorted(records, key=lambda record: record.id))


class VariantRuntimeBinding(FrozenModel):
    variant_id: StableId
    component_id: StableId
    provider_id: StableId
    provider_class: ProviderClass
    delivery_model: DeliveryModel
    supported_capabilities: tuple[str, ...] = ()
    unsupported_capabilities: tuple[str, ...] = ()
    score_adjustments: tuple[DimensionValue, ...] = ()


class DeployableProjectionSpec(FrozenModel):
    """Deployable policy that cannot be inferred from product facts alone."""

    manifest: DeployableCatalogManifest
    component_bindings: tuple[ComponentInterfaceBinding, ...]
    providers: tuple[ProviderProfile, ...]
    variant_bindings: tuple[VariantRuntimeBinding, ...]
    bundle_templates: tuple[BundleTemplate, ...]
    score_dimensions: tuple[ScoreDimension, ...]
    score_profiles: tuple[ScoreProfile, ...]
    capability_rules: tuple[RequirementCapabilityRule, ...] = ()

    @field_validator(
        "component_bindings",
        "providers",
        "variant_bindings",
        "bundle_templates",
        "score_dimensions",
        "score_profiles",
        "capability_rules",
    )
    @classmethod
    def deployable_records_are_unique(
        cls,
        records: tuple[object, ...],
    ) -> tuple[object, ...]:
        def identity(record: object) -> str:
            return str(
                getattr(
                    record,
                    "id",
                    getattr(
                        record,
                        "variant_id",
                        getattr(record, "component_id", ""),
                    ),
                )
            )
        identities = [
            identity(record)
            for record in records
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("deployable projection records must be unique")
        return tuple(sorted(records, key=identity))


def load_catalog_projection(path: Path) -> CatalogProjectionSpec:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise KnowledgeCatalogCompilationError(
            "catalog projection document must be an object"
        )
    try:
        return CatalogProjectionSpec.model_validate(document)
    except ValueError as error:
        raise KnowledgeCatalogCompilationError(
            f"invalid catalog projection in {path}: {error}"
        ) from error


def load_deployable_projection(path: Path) -> DeployableProjectionSpec:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise KnowledgeCatalogCompilationError(
            "deployable projection document must be an object"
        )
    try:
        return DeployableProjectionSpec.model_validate(document)
    except ValueError as error:
        raise KnowledgeCatalogCompilationError(
            f"invalid deployable projection in {path}: {error}"
        ) from error


def _runtime_version(schema_version: str) -> str:
    major, minor = schema_version.split(".", maxsplit=1)
    return f"{major}.{minor}.0"


def _derived_claim_id(claim_id: str, snapshot_id: str) -> str:
    digest = hashlib.sha256(snapshot_id.encode("utf-8")).hexdigest()[:12]
    return f"{claim_id}-evidence-{digest}"


def _expand_claim_ids(
    claim_ids: tuple[str, ...],
    generated_ids: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    expanded: list[str] = []
    for claim_id in claim_ids:
        if claim_id not in generated_ids:
            raise KnowledgeCatalogCompilationError(
                f"runtime projection references unknown semantic claim {claim_id}"
            )
        expanded.extend(generated_ids[claim_id])
    return tuple(sorted(set(expanded)))


def compile_knowledge_catalog(
    *,
    entities: tuple[KnowledgeEntity, ...],
    relationships: tuple[KnowledgeRelationship, ...],
    source_registry: SourceRegistry,
    snapshots: tuple[SnapshotManifest, ...],
    projection: CatalogProjectionSpec,
    as_of: date,
) -> CatalogRelease:
    """Generate a deterministic runtime catalog from approved active knowledge."""

    active_entities = tuple(
        entity
        for entity in entities
        if entity.lifecycle is KnowledgeLifecycle.ACTIVE
    )
    active_ids = {entity.id for entity in active_entities}
    active_relationships = tuple(
        relationship
        for relationship in relationships
        if (
            relationship.lifecycle is KnowledgeLifecycle.ACTIVE
            and relationship.source_id in active_ids
            and relationship.target_id in active_ids
        )
    )
    snapshot_ids = tuple(
        sorted(snapshot.snapshot_id for snapshot in snapshots)
    )
    validation = validate_knowledge_release(
        entities=active_entities,
        relationships=active_relationships,
        known_snapshot_ids=snapshot_ids,
        as_of=as_of,
    )
    if not validation.is_valid:
        errors = "; ".join(
            f"{issue.code} at {issue.location}: {issue.message}"
            for issue in validation.issues
            if issue.severity.value == "error"
        )
        raise KnowledgeCatalogCompilationError(
            f"semantic knowledge is not publishable: {errors}"
        )

    registry_by_id = {source.id: source for source in source_registry.sources}
    snapshots_by_id = {snapshot.snapshot_id: snapshot for snapshot in snapshots}
    if len(snapshots_by_id) != len(snapshots):
        raise KnowledgeCatalogCompilationError(
            "snapshot inventory contains duplicate identifiers"
        )

    evidence_sources: list[EvidenceSource] = []
    for snapshot in sorted(snapshots, key=lambda item: item.snapshot_id):
        source = registry_by_id.get(snapshot.source_id)
        if source is None:
            raise KnowledgeCatalogCompilationError(
                f"snapshot {snapshot.snapshot_id} references unregistered "
                f"source {snapshot.source_id}"
            )
        try:
            retrieved_at = datetime.fromisoformat(snapshot.retrieved_at)
        except ValueError as error:
            raise KnowledgeCatalogCompilationError(
                f"snapshot {snapshot.snapshot_id} has invalid retrieved_at"
            ) from error
        evidence_sources.append(
            EvidenceSource(
                id=snapshot.snapshot_id,
                version="1.0.0",
                title=f"{source.name} snapshot",
                uri=snapshot.final_uri,
                publisher=source.publisher,
                retrieved_at=retrieved_at,
                snapshot_hash=snapshot.raw_content_hash,
            )
        )

    claims = tuple(
        entity for entity in active_entities if isinstance(entity, Claim)
    )
    generated_claim_ids: dict[str, tuple[str, ...]] = {}
    evidence_claims: list[EvidenceClaim] = []
    for claim in sorted(claims, key=lambda item: item.id):
        generated: list[str] = []
        for evidence in claim.evidence:
            snapshot = snapshots_by_id[evidence.source_snapshot_id]
            source = registry_by_id.get(snapshot.source_id)
            if source is None:
                raise KnowledgeCatalogCompilationError(
                    f"claim {claim.id} uses snapshot from unregistered source "
                    f"{snapshot.source_id}"
                )
            if evidence.authority_tier is not source.authority_tier:
                raise KnowledgeCatalogCompilationError(
                    f"claim {claim.id} declares {evidence.authority_tier.value} "
                    f"for {snapshot.source_id}, registered as "
                    f"{source.authority_tier.value}"
                )
            runtime_claim_id = (
                claim.id
                if len(claim.evidence) == 1
                else _derived_claim_id(claim.id, evidence.source_snapshot_id)
            )
            generated.append(runtime_claim_id)
            evidence_claims.append(
                EvidenceClaim(
                    id=runtime_claim_id,
                    version=_runtime_version(claim.schema_version),
                    source_id=evidence.source_snapshot_id,
                    statement=claim.statement,
                    critical=claim.criticality.value == "critical",
                    review_status=EvidenceReviewStatus(
                        claim.review.status.value
                    ),
                    effective_on=claim.effective_from,
                    expires_on=claim.effective_until,
                    source_locator=evidence.source_locator,
                    reviewer=", ".join(claim.review.reviewer_ids),
                )
            )
        generated_claim_ids[claim.id] = tuple(sorted(generated))

    dependencies: dict[str, set[str]] = {}
    component_claims: dict[str, set[str]] = {}
    for relationship in active_relationships:
        if relationship.relationship_type is RelationshipType.REQUIRES:
            dependencies.setdefault(relationship.source_id, set()).add(
                relationship.target_id
            )
        if (
            relationship.relationship_type is RelationshipType.SUPPORTED_BY
            and relationship.source_id in active_ids
        ):
            component_claims.setdefault(relationship.source_id, set()).add(
                relationship.target_id
            )

    components: list[ComponentDefinition] = []
    for component in sorted(
        (
            entity
            for entity in active_entities
            if isinstance(entity, Component)
        ),
        key=lambda item: item.id,
    ):
        components.append(
            ComponentDefinition(
                id=component.id,
                version=_runtime_version(component.schema_version),
                name=component.title,
                description=component.summary,
                plane=component.plane.value,
                kind=component.component_kind,
                dependency_ids=tuple(
                    sorted(dependencies.get(component.id, set()))
                ),
                evidence_claim_ids=_expand_claim_ids(
                    tuple(sorted(component_claims.get(component.id, set()))),
                    generated_claim_ids,
                ),
            )
        )

    requirements = tuple(
        requirement.model_copy(
            update={
                "evidence_claim_ids": _expand_claim_ids(
                    requirement.evidence_claim_ids,
                    generated_claim_ids,
                )
            }
        )
        for requirement in projection.requirements
    )
    patterns = tuple(
        pattern.model_copy(
            update={
                "evidence_claim_ids": _expand_claim_ids(
                    pattern.evidence_claim_ids,
                    generated_claim_ids,
                )
            }
        )
        for pattern in projection.patterns
    )
    rules = tuple(
        rule.model_copy(
            update={
                "evidence_claim_ids": _expand_claim_ids(
                    rule.evidence_claim_ids,
                    generated_claim_ids,
                )
            }
        )
        for rule in projection.rules
    )

    document = CatalogDocument(
        manifest=projection.manifest,
        evidence_sources=tuple(evidence_sources),
        evidence_claims=tuple(evidence_claims),
        requirements=requirements,
        components=tuple(components),
        patterns=patterns,
        rules=rules,
    )
    return compile_catalog_documents((document,), as_of=as_of)


def compile_okf_catalog(
    *,
    knowledge_root: Path,
    source_registry: SourceRegistry,
    snapshots: tuple[SnapshotManifest, ...],
    projection_path: Path,
    as_of: date,
) -> CatalogRelease:
    """Load repository-authored OKF documents and compile a runtime release."""

    corpus = load_okf_corpus(knowledge_root)
    return compile_knowledge_catalog(
        entities=corpus.entities,
        relationships=corpus.relationships,
        source_registry=source_registry,
        snapshots=snapshots,
        projection=load_catalog_projection(projection_path),
        as_of=as_of,
    )


def compile_knowledge_deployable_catalog(
    *,
    logical_catalog: CatalogRelease,
    entities: tuple[KnowledgeEntity, ...],
    relationships: tuple[KnowledgeRelationship, ...],
    projection: DeployableProjectionSpec,
    as_of: date,
) -> DeployableCatalogRelease:
    """Generate interfaces and service variants from approved knowledge."""

    active_entities = tuple(
        entity
        for entity in entities
        if entity.lifecycle is KnowledgeLifecycle.ACTIVE
    )
    interfaces = tuple(
        InterfaceContract(
            id=interface.id,
            version=_runtime_version(interface.schema_version),
            name=interface.title,
            protocol=interface.protocol,
            contract_version=(
                interface.protocol_version or interface.schema_version
            ),
            description=interface.summary,
        )
        for interface in sorted(
            (
                entity
                for entity in active_entities
                if isinstance(entity, Interface)
            ),
            key=lambda item: item.id,
        )
    )

    offerings = {
        (offering.provider, offering.product): offering
        for offering in active_entities
        if isinstance(offering, Offering)
    }
    variants = {
        variant.id: variant
        for variant in active_entities
        if isinstance(variant, Variant)
    }
    binding_by_variant = {
        binding.variant_id: binding
        for binding in projection.variant_bindings
    }
    if set(binding_by_variant) != set(variants):
        missing = sorted(set(variants) - set(binding_by_variant))
        extra = sorted(set(binding_by_variant) - set(variants))
        raise KnowledgeCatalogCompilationError(
            "variant binding coverage mismatch: "
            f"missing={missing}, extra={extra}"
        )

    logical_components = {
        component.id: component for component in logical_catalog.components
    }
    component_bindings = {
        binding.component_id: binding
        for binding in projection.component_bindings
    }
    implemented_capabilities: dict[str, set[str]] = {}
    for relationship in relationships:
        if (
            relationship.lifecycle is KnowledgeLifecycle.ACTIVE
            and relationship.relationship_type is RelationshipType.IMPLEMENTS
            and relationship.source_id in variants
        ):
            implemented_capabilities.setdefault(
                relationship.source_id,
                set(),
            ).add(relationship.target_id)

    service_variants: list[ServiceVariant] = []
    used_offerings: set[tuple[str, str]] = set()
    for variant_id, variant in sorted(variants.items()):
        offering_key = (variant.provider, variant.product)
        if offering_key not in offerings:
            raise KnowledgeCatalogCompilationError(
                f"variant {variant.id} has no active offering for "
                f"{variant.provider}/{variant.product}"
            )
        used_offerings.add(offering_key)
        binding = binding_by_variant[variant_id]
        component = logical_components.get(binding.component_id)
        if component is None:
            raise KnowledgeCatalogCompilationError(
                f"variant {variant.id} binds unknown component "
                f"{binding.component_id}"
            )
        interface_binding = component_bindings.get(binding.component_id)
        if interface_binding is None:
            raise KnowledgeCatalogCompilationError(
                f"variant {variant.id} has no component interface binding"
            )
        service_variants.append(
            ServiceVariant(
                id=variant.id,
                version=_runtime_version(variant.schema_version),
                name=variant.title,
                component_id=binding.component_id,
                provider_id=binding.provider_id,
                provider_class=binding.provider_class,
                delivery_model=binding.delivery_model,
                supported_capabilities=tuple(
                    sorted(
                        set(binding.supported_capabilities)
                        | implemented_capabilities.get(variant.id, set())
                    )
                ),
                unsupported_capabilities=binding.unsupported_capabilities,
                score_adjustments=binding.score_adjustments,
                dependency_component_ids=component.dependency_ids,
                provides_interface_ids=(
                    interface_binding.provides_interface_ids
                ),
                requires_interface_ids=(
                    interface_binding.requires_interface_ids
                ),
            )
        )

    unused_offerings = sorted(set(offerings) - used_offerings)
    if unused_offerings:
        formatted = [f"{provider}/{product}" for provider, product in unused_offerings]
        raise KnowledgeCatalogCompilationError(
            f"active offerings have no deployable variants: {formatted}"
        )

    document = DeployableCatalogDocument(
        manifest=projection.manifest,
        interfaces=interfaces,
        component_bindings=projection.component_bindings,
        providers=projection.providers,
        service_variants=tuple(service_variants),
        bundle_templates=projection.bundle_templates,
        score_dimensions=projection.score_dimensions,
        score_profiles=projection.score_profiles,
        capability_rules=projection.capability_rules,
    )
    return compile_deployable_documents(
        logical_catalog,
        (document,),
        as_of=as_of,
    )


def compile_okf_deployable_catalog(
    *,
    knowledge_root: Path,
    logical_catalog: CatalogRelease,
    projection_path: Path,
    as_of: date,
) -> DeployableCatalogRelease:
    corpus = load_okf_corpus(knowledge_root)
    return compile_knowledge_deployable_catalog(
        logical_catalog=logical_catalog,
        entities=corpus.entities,
        relationships=corpus.relationships,
        projection=load_deployable_projection(projection_path),
        as_of=as_of,
    )
