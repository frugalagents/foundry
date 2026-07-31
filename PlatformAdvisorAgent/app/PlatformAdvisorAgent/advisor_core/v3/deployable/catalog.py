"""Compiler for the structured R0.2 deployable-offering catalog."""
from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from ..models import CatalogRelease, PatternRole, content_hash
from .models import (
    ComponentInterfaceBinding,
    ComponentOffering,
    DeployableCatalogDocument,
    DeployableCatalogManifest,
    DeployableCatalogRelease,
    DeliveryModel,
    ProviderClass,
    ProviderProfile,
    ServiceVariant,
)


DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalogs"
    / "coding-platform-r0.2"
)


class DeployableCatalogCompilationError(ValueError):
    """Raised when R0.2 catalog data cannot produce a safe release."""


def _collect(
    documents: Iterable[DeployableCatalogDocument],
    field: str,
) -> tuple[object, ...]:
    return tuple(
        item
        for document in documents
        for item in getattr(document, field)
    )


def _sorted(records: Iterable[object]) -> tuple[object, ...]:
    return tuple(
        sorted(
            records,
            key=lambda record: (
                str(getattr(record, "id", "")),
                str(getattr(record, "component_id", "")),
            ),
        )
    )


def load_deployable_documents(
    path: str | Path = DEFAULT_CATALOG_PATH,
) -> tuple[DeployableCatalogDocument, ...]:
    root = Path(path)
    if not root.exists():
        raise DeployableCatalogCompilationError(
            f"deployable catalog path does not exist: {root}"
        )
    paths = sorted(root.rglob("*.json")) if root.is_dir() else [root]
    if not paths:
        raise DeployableCatalogCompilationError(
            f"deployable catalog path contains no JSON: {root}"
        )

    documents: list[DeployableCatalogDocument] = []
    for source_path in paths:
        try:
            raw = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DeployableCatalogCompilationError(
                f"invalid JSON in {source_path}: {exc.msg}"
            ) from exc
        try:
            documents.append(DeployableCatalogDocument.model_validate(raw))
        except ValidationError as exc:
            raise DeployableCatalogCompilationError(
                f"invalid deployable catalog contract in {source_path}: {exc}"
            ) from exc
    return tuple(documents)


def _one_manifest(
    documents: tuple[DeployableCatalogDocument, ...],
) -> DeployableCatalogManifest:
    manifests = [
        document.manifest for document in documents if document.manifest
    ]
    if len(manifests) != 1:
        raise DeployableCatalogCompilationError(
            "deployable catalog requires exactly one manifest; "
            f"found {len(manifests)}"
        )
    return manifests[0]


def _unique_ids(kind: str, records: Iterable[object]) -> None:
    ids = [str(getattr(record, "id")) for record in records]
    duplicates = sorted(
        record_id for record_id in set(ids) if ids.count(record_id) > 1
    )
    if duplicates:
        raise DeployableCatalogCompilationError(
            f"duplicate {kind} IDs: {duplicates}"
        )


def _expand_offerings(
    offerings: tuple[ComponentOffering, ...],
    providers: tuple[ProviderProfile, ...],
) -> tuple[ServiceVariant, ...]:
    provider_by_class = {
        provider.provider_class: provider for provider in providers
    }
    variants: list[ServiceVariant] = []
    for offering in offerings:
        component_slug = offering.component_id.split(":", 1)[1]
        for provider_class in ProviderClass:
            provider = provider_by_class[provider_class]
            variants.append(ServiceVariant(
                id=f"service:{component_slug}-{provider_class.value}",
                version="1.0.0",
                name=str(getattr(offering, provider_class.value)),
                component_id=offering.component_id,
                provider_id=provider.id,
                provider_class=provider_class,
                delivery_model=provider.delivery_model,
            ))
    return tuple(variants)


def _validate_bindings(
    bindings: tuple[ComponentInterfaceBinding, ...],
    *,
    component_ids: set[str],
    interface_ids: set[str],
) -> None:
    bound_ids = [binding.component_id for binding in bindings]
    if len(bound_ids) != len(set(bound_ids)):
        raise DeployableCatalogCompilationError(
            "component interface bindings must be unique"
        )
    missing = sorted(component_ids - set(bound_ids))
    extra = sorted(set(bound_ids) - component_ids)
    if missing or extra:
        raise DeployableCatalogCompilationError(
            "component interface coverage mismatch: "
            f"missing={missing}, extra={extra}"
        )
    for binding in bindings:
        references = set(binding.provides_interface_ids) | set(
            binding.requires_interface_ids
        )
        unknown = sorted(references - interface_ids)
        if unknown:
            raise DeployableCatalogCompilationError(
                f"binding {binding.component_id!r} references unknown "
                f"interfaces {unknown}"
            )

    providers = {
        interface_id
        for binding in bindings
        for interface_id in binding.provides_interface_ids
    }
    required = {
        interface_id
        for binding in bindings
        for interface_id in binding.requires_interface_ids
    }
    if required - providers:
        raise DeployableCatalogCompilationError(
            "required interfaces have no logical provider: "
            f"{sorted(required - providers)}"
        )


def _validate_service_coverage(
    variants: tuple[ServiceVariant, ...],
    *,
    component_ids: set[str],
    providers: tuple[ProviderProfile, ...],
) -> None:
    provider_by_id = {provider.id: provider for provider in providers}
    pairs = [
        (variant.component_id, variant.provider_class)
        for variant in variants
    ]
    if len(pairs) != len(set(pairs)):
        raise DeployableCatalogCompilationError(
            "service variants must be unique per component and provider class"
        )
    expected = {
        (component_id, provider_class)
        for component_id in component_ids
        for provider_class in ProviderClass
    }
    actual = set(pairs)
    if actual != expected:
        missing = sorted(
            f"{component_id}/{provider_class.value}"
            for component_id, provider_class in expected - actual
        )
        extra = sorted(
            f"{component_id}/{provider_class.value}"
            for component_id, provider_class in actual - expected
        )
        raise DeployableCatalogCompilationError(
            f"service variant coverage mismatch: missing={missing}, extra={extra}"
        )
    for variant in variants:
        provider = provider_by_id.get(variant.provider_id)
        if provider is None:
            raise DeployableCatalogCompilationError(
                f"service {variant.id!r} references unknown provider "
                f"{variant.provider_id!r}"
            )
        if (
            variant.provider_class != provider.provider_class
            or variant.delivery_model != provider.delivery_model
        ):
            raise DeployableCatalogCompilationError(
                f"service {variant.id!r} conflicts with provider profile"
            )


def compile_deployable_catalog(
    logical_catalog: CatalogRelease,
    path: str | Path = DEFAULT_CATALOG_PATH,
    *,
    as_of: date | None = None,
) -> DeployableCatalogRelease:
    """Compile R0.2 artifacts against an exact logical catalog release."""

    documents = load_deployable_documents(path)
    manifest = _one_manifest(documents)
    validated_as_of = as_of or logical_catalog.validated_as_of
    if validated_as_of < manifest.effective_on:
        raise DeployableCatalogCompilationError(
            f"deployable catalog is not effective until {manifest.effective_on}"
        )
    if manifest.logical_catalog_id != logical_catalog.id:
        raise DeployableCatalogCompilationError(
            "deployable manifest does not target the supplied logical catalog"
        )

    interfaces = _sorted(_collect(documents, "interfaces"))
    bindings = _sorted(_collect(documents, "component_bindings"))
    providers = _sorted(_collect(documents, "providers"))
    offerings = _sorted(_collect(documents, "component_offerings"))
    explicit_variants = _collect(documents, "service_variants")
    templates = _sorted(_collect(documents, "bundle_templates"))
    dimensions = _sorted(_collect(documents, "score_dimensions"))
    score_profiles = _sorted(_collect(documents, "score_profiles"))
    capability_rules = _sorted(_collect(documents, "capability_rules"))

    for kind, records in (
        ("interface", interfaces),
        ("provider", providers),
        ("service", explicit_variants),
        ("bundle template", templates),
        ("score dimension", dimensions),
        ("score profile", score_profiles),
        ("capability rule", capability_rules),
    ):
        _unique_ids(kind, records)

    provider_classes = [provider.provider_class for provider in providers]
    if set(provider_classes) != set(ProviderClass) or len(
        provider_classes
    ) != len(ProviderClass):
        raise DeployableCatalogCompilationError(
            "catalog requires exactly one provider profile for AWS, OSS, "
            "SaaS, and BYOP"
        )

    component_ids = {component.id for component in logical_catalog.components}
    requirement_ids = {
        requirement.id for requirement in logical_catalog.requirements
    }
    pattern_ids = {
        pattern.id
        for pattern in logical_catalog.patterns
        if pattern.role is PatternRole.DEPLOYMENT_FAMILY
    }
    interface_ids = {interface.id for interface in interfaces}
    dimension_ids = {dimension.id for dimension in dimensions}

    _validate_bindings(
        bindings,
        component_ids=component_ids,
        interface_ids=interface_ids,
    )

    offering_ids = [offering.component_id for offering in offerings]
    if len(offering_ids) != len(set(offering_ids)):
        raise DeployableCatalogCompilationError(
            "component offering records must be unique"
        )
    if set(offering_ids) != component_ids:
        raise DeployableCatalogCompilationError(
            "component offering coverage must exactly match logical components"
        )

    variants = _sorted(
        (*_expand_offerings(offerings, providers), *explicit_variants)
    )
    _unique_ids("service", variants)
    _validate_service_coverage(
        variants,
        component_ids=component_ids,
        providers=providers,
    )

    for provider in providers:
        if {
            item.dimension_id for item in provider.dimension_scores
        } != dimension_ids:
            raise DeployableCatalogCompilationError(
                f"provider {provider.id!r} must score every dimension"
            )
    for profile in score_profiles:
        if {item.dimension_id for item in profile.weights} != dimension_ids:
            raise DeployableCatalogCompilationError(
                f"score profile {profile.id!r} must weight every dimension"
            )
    if len(score_profiles) != 1:
        raise DeployableCatalogCompilationError(
            "catalog requires exactly one active score profile"
        )

    for template in templates:
        if template.deployment_family_id not in pattern_ids:
            raise DeployableCatalogCompilationError(
                f"template {template.id!r} references unknown deployment family"
            )
        unknown_components = {
            item.component_id for item in template.component_selections
        } - component_ids
        unknown_requirements = {
            item.requirement_id for item in template.requirement_acceptance
        } - requirement_ids
        unknown_dimensions = {
            item.dimension_id for item in template.score_adjustments
        } - dimension_ids
        if unknown_components or unknown_requirements or unknown_dimensions:
            raise DeployableCatalogCompilationError(
                f"template {template.id!r} has dangling references"
            )
    if len(templates) < len(ProviderClass):
        raise DeployableCatalogCompilationError(
            "catalog requires at least one bundle template per provider class"
        )

    known_capabilities = {
        capability
        for provider in providers
        for capability in (
            *provider.supported_capabilities,
            *provider.unsupported_capabilities,
        )
    } | {
        capability
        for variant in variants
        for capability in (
            *variant.supported_capabilities,
            *variant.unsupported_capabilities,
        )
    }
    for rule in capability_rules:
        if (
            rule.requirement_id not in requirement_ids
            or not set(rule.target_component_ids) <= component_ids
            or rule.required_capability not in known_capabilities
        ):
            raise DeployableCatalogCompilationError(
                f"capability rule {rule.id!r} has dangling references"
            )

    groups = {
        "interfaces": interfaces,
        "component_bindings": bindings,
        "providers": providers,
        "service_variants": variants,
        "bundle_templates": templates,
        "score_dimensions": dimensions,
        "score_profiles": score_profiles,
        "capability_rules": capability_rules,
    }
    hash_payload = {
        "manifest": manifest.model_dump(mode="json"),
        **{
            field: [
                record.model_dump(mode="json", exclude_none=True)
                for record in records
            ]
            for field, records in groups.items()
        },
    }
    return DeployableCatalogRelease(
        **manifest.model_dump(),
        content_hash=content_hash(hash_payload),
        validated_as_of=validated_as_of,
        **groups,
    )
