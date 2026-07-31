"""Immutable R0.2 contracts for deployable solution bundles."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from ..models import (
    ArchitecturePlane,
    FrozenModel,
    RequirementValue,
    SemanticVersion,
    StableId,
    VersionedRecord,
    content_hash,
)


class StrEnum(str, Enum):
    pass


class ProviderClass(StrEnum):
    AWS = "aws"
    OSS = "oss"
    SAAS = "saas"
    BYOP = "byop"


class DeliveryModel(StrEnum):
    MANAGED = "managed"
    SELF_MANAGED = "self_managed"
    CUSTOMER_SELECTED = "customer_selected"


class CompatibilityStatus(StrEnum):
    COMPATIBLE = "compatible"
    CONDITIONAL = "conditional"
    INCOMPATIBLE = "incompatible"


class FindingSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RecommendationState(StrEnum):
    RECOMMENDED = "recommended"
    CONDITIONAL = "conditional"
    NO_VIABLE_CANDIDATE = "no_viable_candidate"


class TradeOffKind(StrEnum):
    ADVANTAGE = "advantage"
    COMPROMISE = "compromise"
    INTEGRATION = "integration"
    CONSTRAINT = "constraint"


def _sorted_unique(values: tuple[StableId, ...]) -> tuple[StableId, ...]:
    if len(values) != len(set(values)):
        raise ValueError("references must be unique")
    return tuple(sorted(values))


class DeployableCatalogManifest(VersionedRecord):
    schema_version: Literal["3.0-r0.2"] = "3.0-r0.2"
    title: str = Field(min_length=1)
    effective_on: date
    logical_catalog_id: StableId


class InterfaceContract(VersionedRecord):
    name: str = Field(min_length=1)
    protocol: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    description: str = Field(min_length=1)


class ComponentInterfaceBinding(FrozenModel):
    component_id: StableId
    provides_interface_ids: tuple[StableId, ...] = ()
    requires_interface_ids: tuple[StableId, ...] = ()

    _sort_provides = field_validator("provides_interface_ids")(_sorted_unique)
    _sort_requires = field_validator("requires_interface_ids")(_sorted_unique)


class DimensionValue(FrozenModel):
    dimension_id: StableId
    value: float = Field(ge=-100, le=100)


class ProviderProfile(VersionedRecord):
    name: str = Field(min_length=1)
    provider_class: ProviderClass
    delivery_model: DeliveryModel
    dimension_scores: tuple[DimensionValue, ...]
    supported_capabilities: tuple[str, ...] = ()
    unsupported_capabilities: tuple[str, ...] = ()

    @field_validator("supported_capabilities", "unsupported_capabilities")
    @classmethod
    def unique_capabilities(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("capabilities must be unique")
        return tuple(sorted(values))

    @model_validator(mode="after")
    def capabilities_do_not_conflict(self) -> "ProviderProfile":
        overlap = set(self.supported_capabilities) & set(
            self.unsupported_capabilities
        )
        if overlap:
            raise ValueError(
                f"provider capabilities conflict: {sorted(overlap)}"
            )
        dimensions = [item.dimension_id for item in self.dimension_scores]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("provider dimension scores must be unique")
        return self


class ServiceVariant(VersionedRecord):
    name: str = Field(min_length=1)
    component_id: StableId
    provider_id: StableId
    provider_class: ProviderClass
    delivery_model: DeliveryModel
    supported_capabilities: tuple[str, ...] = ()
    unsupported_capabilities: tuple[str, ...] = ()
    score_adjustments: tuple[DimensionValue, ...] = ()

    @field_validator("supported_capabilities", "unsupported_capabilities")
    @classmethod
    def unique_capabilities(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("capabilities must be unique")
        return tuple(sorted(values))

    @model_validator(mode="after")
    def values_do_not_conflict(self) -> "ServiceVariant":
        if set(self.supported_capabilities) & set(
            self.unsupported_capabilities
        ):
            raise ValueError("service capabilities cannot conflict")
        dimensions = [item.dimension_id for item in self.score_adjustments]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("service score adjustments must be unique")
        return self


class PlaneProviderSelection(FrozenModel):
    plane: ArchitecturePlane
    provider_class: ProviderClass


class ComponentProviderSelection(FrozenModel):
    component_id: StableId
    provider_class: ProviderClass


class RequirementAcceptance(FrozenModel):
    requirement_id: StableId
    accepted_values: tuple[RequirementValue, ...] = Field(min_length=1)


class BundleTemplate(VersionedRecord):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    deployment_family_id: StableId
    default_provider_class: ProviderClass
    plane_selections: tuple[PlaneProviderSelection, ...] = ()
    component_selections: tuple[ComponentProviderSelection, ...] = ()
    requirement_acceptance: tuple[RequirementAcceptance, ...] = ()
    score_adjustments: tuple[DimensionValue, ...] = ()
    integration_penalty: float = Field(ge=0, le=25)

    @model_validator(mode="after")
    def selections_are_unique(self) -> "BundleTemplate":
        planes = [item.plane for item in self.plane_selections]
        components = [
            item.component_id for item in self.component_selections
        ]
        requirements = [
            item.requirement_id for item in self.requirement_acceptance
        ]
        dimensions = [
            item.dimension_id for item in self.score_adjustments
        ]
        for label, values in (
            ("plane", planes),
            ("component", components),
            ("requirement", requirements),
            ("dimension", dimensions),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"bundle {label} selections must be unique")
        return self


class ScoreDimension(VersionedRecord):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    higher_is_better: Literal[True] = True


class DimensionWeight(FrozenModel):
    dimension_id: StableId
    weight: float = Field(gt=0, le=1)


class ScoreProfile(VersionedRecord):
    name: str = Field(min_length=1)
    weights: tuple[DimensionWeight, ...]
    conditional_penalty: float = Field(ge=0, le=25)

    @model_validator(mode="after")
    def weights_are_complete_and_normalized(self) -> "ScoreProfile":
        ids = [item.dimension_id for item in self.weights]
        if len(ids) != len(set(ids)):
            raise ValueError("score profile dimension weights must be unique")
        if abs(sum(item.weight for item in self.weights) - 1.0) > 1e-9:
            raise ValueError("score profile weights must sum to 1")
        return self


class RequirementCapabilityRule(VersionedRecord):
    name: str = Field(min_length=1)
    requirement_id: StableId
    operator: Literal[
        "equals",
        "greater_than_or_equal",
        "contains",
    ]
    value: RequirementValue
    target_component_ids: tuple[StableId, ...]
    required_capability: str = Field(min_length=1)
    rationale: str = Field(min_length=1)

    _sort_targets = field_validator("target_component_ids")(_sorted_unique)


class ComponentOffering(FrozenModel):
    component_id: StableId
    aws: str = Field(min_length=1)
    oss: str = Field(min_length=1)
    saas: str = Field(min_length=1)
    byop: str = Field(min_length=1)


class DeployableCatalogDocument(FrozenModel):
    manifest: DeployableCatalogManifest | None = None
    interfaces: tuple[InterfaceContract, ...] = ()
    component_bindings: tuple[ComponentInterfaceBinding, ...] = ()
    providers: tuple[ProviderProfile, ...] = ()
    component_offerings: tuple[ComponentOffering, ...] = ()
    service_variants: tuple[ServiceVariant, ...] = ()
    bundle_templates: tuple[BundleTemplate, ...] = ()
    score_dimensions: tuple[ScoreDimension, ...] = ()
    score_profiles: tuple[ScoreProfile, ...] = ()
    capability_rules: tuple[RequirementCapabilityRule, ...] = ()


class DeployableCatalogRelease(DeployableCatalogManifest):
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validated_as_of: date
    interfaces: tuple[InterfaceContract, ...]
    component_bindings: tuple[ComponentInterfaceBinding, ...]
    providers: tuple[ProviderProfile, ...]
    service_variants: tuple[ServiceVariant, ...]
    bundle_templates: tuple[BundleTemplate, ...]
    score_dimensions: tuple[ScoreDimension, ...]
    score_profiles: tuple[ScoreProfile, ...]
    capability_rules: tuple[RequirementCapabilityRule, ...]


class BundleSelection(FrozenModel):
    component_id: StableId
    service_variant_id: StableId
    service_name: str = Field(min_length=1)
    provider_class: ProviderClass
    delivery_model: DeliveryModel


class CompatibilityFinding(FrozenModel):
    finding_id: StableId
    status: CompatibilityStatus
    severity: FindingSeverity
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    component_ids: tuple[StableId, ...] = ()
    interface_id: StableId | None = None
    requirement_id: StableId | None = None

    _sort_components = field_validator("component_ids")(_sorted_unique)


class DimensionScore(FrozenModel):
    dimension_id: StableId
    score: float = Field(ge=0, le=100)


class TradeOff(FrozenModel):
    tradeoff_id: StableId
    kind: TradeOffKind
    statement: str = Field(min_length=1)
    dimension_id: StableId | None = None
    impact: float | None = None


class CandidateBundle(FrozenModel):
    bundle_id: StableId
    template_id: StableId
    name: str = Field(min_length=1)
    deployment_family_id: StableId
    compatibility_status: CompatibilityStatus
    selections: tuple[BundleSelection, ...]
    findings: tuple[CompatibilityFinding, ...]
    dimension_scores: tuple[DimensionScore, ...]
    weighted_score: float = Field(ge=0, le=100)
    tradeoffs: tuple[TradeOff, ...]
    rank: int = Field(ge=1)
    pareto_optimal: bool


class Recommendation(FrozenModel):
    state: RecommendationState
    candidate_id: StableId | None = None
    rationale: str = Field(min_length=1)


class SensitivityIndicator(FrozenModel):
    dimension_id: StableId
    baseline_candidate_id: StableId
    challenger_candidate_id: StableId | None = None
    baseline_weight: float = Field(gt=0, le=1)
    switch_weight: float | None = Field(default=None, gt=0, le=1)
    winner_changes: bool
    score_margin_at_baseline: float = Field(ge=0)


class DeployableDecisionMatrix(FrozenModel):
    schema_version: Literal["3.0-r0.2"] = "3.0-r0.2"
    workspace_revision_id: StableId
    workspace_revision_number: int = Field(ge=1)
    workspace_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    logical_catalog_id: StableId
    logical_catalog_version: SemanticVersion
    logical_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    deployable_catalog_id: StableId
    deployable_catalog_version: SemanticVersion
    deployable_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    score_profile_id: StableId
    candidates: tuple[CandidateBundle, ...]
    pareto_candidate_ids: tuple[StableId, ...]
    recommendation: Recommendation
    sensitivity: tuple[SensitivityIndicator, ...]
    result_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def result_hash_matches_content(self) -> "DeployableDecisionMatrix":
        payload = self.model_dump(
            mode="json",
            exclude={"result_hash"},
        )
        if self.result_hash != content_hash(payload):
            raise ValueError(
                "deployable result_hash does not match matrix content"
            )
        return self
