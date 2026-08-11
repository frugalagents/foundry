"""Immutable semantic contracts for reviewed architecture knowledge."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


StableId = Annotated[
    str,
    Field(
        pattern=r"^[a-z][a-z0-9_-]*(?::[a-z][a-z0-9_-]*)+$",
        description="Namespaced stable identifier such as capability:model-routing.",
    ),
]
SchemaVersion = Annotated[
    str,
    Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$"),
]
JsonScalar = str | int | float | bool


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StrEnum(str, Enum):
    pass


def canonical_json(value: BaseModel | dict[str, object]) -> str:
    payload = (
        value.model_dump(mode="json", exclude_none=True)
        if isinstance(value, BaseModel)
        else value
    )
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def content_hash(value: BaseModel | dict[str, object]) -> str:
    return (
        "sha256:"
        f"{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"
    )


class KnowledgeLifecycle(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ClaimCriticality(StrEnum):
    STANDARD = "standard"
    CRITICAL = "critical"


class ClaimClass(StrEnum):
    PRODUCT_FACT = "product_fact"
    COMPATIBILITY = "compatibility"
    PRICING_OR_QUOTA = "pricing_or_quota"
    SECURITY_CONTROL = "security_control"
    DECISION_GUIDANCE = "decision_guidance"
    COMPARATIVE_EVIDENCE = "comparative_evidence"
    OUTCOME_EVIDENCE = "outcome_evidence"


class SourceAuthorityTier(StrEnum):
    TIER_A = "tier_a_decision_authority"
    TIER_B = "tier_b_operational_guidance"
    TIER_C = "tier_c_comparative_evidence"
    TIER_D = "tier_d_proprietary_outcome"


class ScopeMode(StrEnum):
    ALL = "all"
    NOT_APPLICABLE = "not_applicable"
    SPECIFIED = "specified"


class ComponentPlane(StrEnum):
    EXPERIENCE = "experience"
    ACCESS = "access"
    ORCHESTRATION = "orchestration"
    MODEL = "model"
    TOOL = "tool"
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"
    GOVERNANCE = "governance"
    OBSERVABILITY = "observability"


class OfferingType(StrEnum):
    MANAGED_SERVICE = "managed_service"
    SAAS = "saas"
    OPEN_SOURCE = "open_source"
    COMMERCIAL_SOFTWARE = "commercial_software"


class EntityKind(StrEnum):
    CAPABILITY = "Capability"
    COMPONENT = "Component"
    OFFERING = "Offering"
    VARIANT = "Variant"
    INTERFACE = "Interface"
    CLAIM = "Claim"
    DECISION_PATTERN = "DecisionPattern"
    OUTCOME_OBSERVATION = "OutcomeObservation"


class RelationshipType(StrEnum):
    IMPLEMENTS = "IMPLEMENTS"
    REQUIRES = "REQUIRES"
    COMPATIBLE_WITH = "COMPATIBLE_WITH"
    INCOMPATIBLE_WITH = "INCOMPATIBLE_WITH"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    INTEGRATES_WITH = "INTEGRATES_WITH"
    RECOMMENDED_WHEN = "RECOMMENDED_WHEN"
    AVOID_WHEN = "AVOID_WHEN"
    SUPPORTED_BY = "SUPPORTED_BY"
    SUPERSEDES = "SUPERSEDES"


class RelationshipCardinality(StrEnum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class IdentifierTransitionType(StrEnum):
    RENAME = "rename"
    MERGE = "merge"
    SPLIT = "split"
    RETIRE = "retire"


class RelationshipSemantics(FrozenModel):
    directed: bool
    source_kinds: tuple[EntityKind, ...]
    target_kinds: tuple[EntityKind, ...]
    cardinalities: tuple[RelationshipCardinality, ...]


class ClaimReviewPolicy(FrozenModel):
    allowed_source_tiers: tuple[SourceAuthorityTier, ...]
    minimum_reviewers: int = Field(ge=1, le=2)
    requires_independent_corroboration: bool = False


ARCHITECTURE_KINDS = (
    EntityKind.CAPABILITY,
    EntityKind.COMPONENT,
    EntityKind.OFFERING,
    EntityKind.VARIANT,
    EntityKind.INTERFACE,
)
IMPLEMENTATION_KINDS = (
    EntityKind.COMPONENT,
    EntityKind.OFFERING,
    EntityKind.VARIANT,
)
RELATIONSHIP_SEMANTICS: dict[RelationshipType, RelationshipSemantics] = {
    RelationshipType.IMPLEMENTS: RelationshipSemantics(
        directed=True,
        source_kinds=IMPLEMENTATION_KINDS,
        target_kinds=(EntityKind.CAPABILITY,),
        cardinalities=(
            RelationshipCardinality.ONE_TO_MANY,
            RelationshipCardinality.MANY_TO_MANY,
        ),
    ),
    RelationshipType.REQUIRES: RelationshipSemantics(
        directed=True,
        source_kinds=ARCHITECTURE_KINDS,
        target_kinds=ARCHITECTURE_KINDS,
        cardinalities=(
            RelationshipCardinality.ONE_TO_ONE,
            RelationshipCardinality.ONE_TO_MANY,
            RelationshipCardinality.MANY_TO_MANY,
        ),
    ),
    RelationshipType.COMPATIBLE_WITH: RelationshipSemantics(
        directed=False,
        source_kinds=ARCHITECTURE_KINDS,
        target_kinds=ARCHITECTURE_KINDS,
        cardinalities=(RelationshipCardinality.MANY_TO_MANY,),
    ),
    RelationshipType.INCOMPATIBLE_WITH: RelationshipSemantics(
        directed=False,
        source_kinds=ARCHITECTURE_KINDS,
        target_kinds=ARCHITECTURE_KINDS,
        cardinalities=(RelationshipCardinality.MANY_TO_MANY,),
    ),
    RelationshipType.ALTERNATIVE_TO: RelationshipSemantics(
        directed=False,
        source_kinds=ARCHITECTURE_KINDS,
        target_kinds=ARCHITECTURE_KINDS,
        cardinalities=(RelationshipCardinality.MANY_TO_MANY,),
    ),
    RelationshipType.INTEGRATES_WITH: RelationshipSemantics(
        directed=False,
        source_kinds=ARCHITECTURE_KINDS,
        target_kinds=ARCHITECTURE_KINDS,
        cardinalities=(RelationshipCardinality.MANY_TO_MANY,),
    ),
    RelationshipType.RECOMMENDED_WHEN: RelationshipSemantics(
        directed=True,
        source_kinds=IMPLEMENTATION_KINDS,
        target_kinds=(EntityKind.DECISION_PATTERN,),
        cardinalities=(RelationshipCardinality.MANY_TO_MANY,),
    ),
    RelationshipType.AVOID_WHEN: RelationshipSemantics(
        directed=True,
        source_kinds=IMPLEMENTATION_KINDS,
        target_kinds=(EntityKind.DECISION_PATTERN,),
        cardinalities=(RelationshipCardinality.MANY_TO_MANY,),
    ),
    RelationshipType.SUPPORTED_BY: RelationshipSemantics(
        directed=True,
        source_kinds=(
            *ARCHITECTURE_KINDS,
            EntityKind.DECISION_PATTERN,
            EntityKind.OUTCOME_OBSERVATION,
        ),
        target_kinds=(EntityKind.CLAIM,),
        cardinalities=(RelationshipCardinality.MANY_TO_MANY,),
    ),
    RelationshipType.SUPERSEDES: RelationshipSemantics(
        directed=True,
        source_kinds=ARCHITECTURE_KINDS,
        target_kinds=ARCHITECTURE_KINDS,
        cardinalities=(
            RelationshipCardinality.ONE_TO_ONE,
            RelationshipCardinality.ONE_TO_MANY,
        ),
    ),
}
CLAIM_REVIEW_POLICIES: dict[ClaimClass, ClaimReviewPolicy] = {
    ClaimClass.PRODUCT_FACT: ClaimReviewPolicy(
        allowed_source_tiers=(SourceAuthorityTier.TIER_A,),
        minimum_reviewers=1,
    ),
    ClaimClass.COMPATIBILITY: ClaimReviewPolicy(
        allowed_source_tiers=(SourceAuthorityTier.TIER_A,),
        minimum_reviewers=2,
    ),
    ClaimClass.PRICING_OR_QUOTA: ClaimReviewPolicy(
        allowed_source_tiers=(SourceAuthorityTier.TIER_A,),
        minimum_reviewers=1,
    ),
    ClaimClass.SECURITY_CONTROL: ClaimReviewPolicy(
        allowed_source_tiers=(
            SourceAuthorityTier.TIER_A,
            SourceAuthorityTier.TIER_B,
        ),
        minimum_reviewers=2,
    ),
    ClaimClass.DECISION_GUIDANCE: ClaimReviewPolicy(
        allowed_source_tiers=(
            SourceAuthorityTier.TIER_A,
            SourceAuthorityTier.TIER_B,
            SourceAuthorityTier.TIER_C,
            SourceAuthorityTier.TIER_D,
        ),
        minimum_reviewers=1,
    ),
    ClaimClass.COMPARATIVE_EVIDENCE: ClaimReviewPolicy(
        allowed_source_tiers=(SourceAuthorityTier.TIER_C,),
        minimum_reviewers=1,
        requires_independent_corroboration=True,
    ),
    ClaimClass.OUTCOME_EVIDENCE: ClaimReviewPolicy(
        allowed_source_tiers=(SourceAuthorityTier.TIER_D,),
        minimum_reviewers=1,
    ),
}


def _sorted_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) != len(set(values)):
        raise ValueError("values must be unique")
    return tuple(sorted(values))


class ReviewMetadata(FrozenModel):
    status: ReviewStatus = ReviewStatus.DRAFT
    reviewer_ids: tuple[StableId, ...] = ()
    reviewed_at: datetime | None = None
    rationale: str | None = Field(default=None, min_length=1)

    _normalize_reviewers = field_validator("reviewer_ids")(_sorted_unique)

    @model_validator(mode="after")
    def approval_has_reviewer_and_time(self) -> "ReviewMetadata":
        if self.status is ReviewStatus.APPROVED:
            if not self.reviewer_ids or self.reviewed_at is None:
                raise ValueError(
                    "approved knowledge requires reviewer_ids and reviewed_at"
                )
        return self


class KnowledgeMetadata(FrozenModel):
    schema_version: SchemaVersion = "1.0"
    id: StableId
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    lifecycle: KnowledgeLifecycle = KnowledgeLifecycle.DRAFT
    owner_id: StableId
    aliases: tuple[StableId, ...] = ()
    tags: tuple[str, ...] = ()
    effective_from: date
    effective_until: date | None = None
    stale_after: date
    review: ReviewMetadata = Field(default_factory=ReviewMetadata)

    _normalize_aliases = field_validator("aliases")(_sorted_unique)
    _normalize_tags = field_validator("tags")(_sorted_unique)

    @model_validator(mode="after")
    def lifecycle_and_dates_are_consistent(self) -> "KnowledgeMetadata":
        if self.id in self.aliases:
            raise ValueError("an entity cannot alias its own identifier")
        if (
            self.effective_until is not None
            and self.effective_until < self.effective_from
        ):
            raise ValueError("effective_until must not precede effective_from")
        if self.stale_after < self.effective_from:
            raise ValueError("stale_after must not precede effective_from")
        if (
            self.lifecycle is KnowledgeLifecycle.ACTIVE
            and self.review.status is not ReviewStatus.APPROVED
        ):
            raise ValueError("active knowledge must be approved")
        return self


class Capability(KnowledgeMetadata):
    kind: Literal["Capability"] = "Capability"
    category: str = Field(min_length=1)
    desired_outcomes: tuple[str, ...] = ()

    _normalize_outcomes = field_validator("desired_outcomes")(_sorted_unique)


class Component(KnowledgeMetadata):
    kind: Literal["Component"] = "Component"
    plane: ComponentPlane
    component_kind: Literal["logical", "overlay"] = "logical"
    responsibility: str = Field(min_length=1)
    boundary: str = Field(min_length=1)


class Offering(KnowledgeMetadata):
    kind: Literal["Offering"] = "Offering"
    provider: str = Field(min_length=1)
    product: str = Field(min_length=1)
    offering_type: OfferingType
    homepage: str | None = Field(default=None, min_length=1)


class Variant(KnowledgeMetadata):
    kind: Literal["Variant"] = "Variant"
    provider: str = Field(min_length=1)
    product: str = Field(min_length=1)
    edition: str | None = Field(default=None, min_length=1)
    release: str | None = Field(default=None, min_length=1)
    deployment_model: str = Field(min_length=1)
    regions: tuple[str, ...] = ()
    configuration: dict[str, JsonScalar] = Field(default_factory=dict)

    _normalize_regions = field_validator("regions")(_sorted_unique)


class Interface(KnowledgeMetadata):
    kind: Literal["Interface"] = "Interface"
    protocol: str = Field(min_length=1)
    protocol_version: str | None = Field(default=None, min_length=1)
    transports: tuple[str, ...] = ()
    authentication_methods: tuple[str, ...] = ()

    _normalize_transports = field_validator("transports")(_sorted_unique)
    _normalize_authentication = field_validator("authentication_methods")(
        _sorted_unique
    )


class ScopeDimension(FrozenModel):
    mode: ScopeMode
    values: tuple[str, ...] = ()

    _normalize_values = field_validator("values")(_sorted_unique)

    @model_validator(mode="after")
    def values_match_mode(self) -> "ScopeDimension":
        if self.mode is ScopeMode.SPECIFIED and not self.values:
            raise ValueError("specified scope requires at least one value")
        if self.mode is not ScopeMode.SPECIFIED and self.values:
            raise ValueError(
                "all and not_applicable scope modes cannot include values"
            )
        return self


class ClaimScope(FrozenModel):
    provider: ScopeDimension
    product: ScopeDimension
    variant: ScopeDimension
    version: ScopeDimension
    region: ScopeDimension
    configuration: ScopeDimension


class EvidenceReference(FrozenModel):
    source_snapshot_id: StableId
    authority_tier: SourceAuthorityTier
    source_locator: str = Field(default="document", min_length=1)


class Claim(KnowledgeMetadata):
    kind: Literal["Claim"] = "Claim"
    statement: str = Field(min_length=1)
    subject_id: StableId
    predicate: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    object_id: StableId | None = None
    object_value: JsonScalar | None = None
    scope: ClaimScope
    claim_class: ClaimClass
    evidence: tuple[EvidenceReference, ...] = Field(min_length=1)
    criticality: ClaimCriticality = ClaimCriticality.STANDARD

    @field_validator("evidence")
    @classmethod
    def unique_sorted_evidence(
        cls,
        evidence: tuple[EvidenceReference, ...],
    ) -> tuple[EvidenceReference, ...]:
        snapshot_ids = [item.source_snapshot_id for item in evidence]
        if len(snapshot_ids) != len(set(snapshot_ids)):
            raise ValueError("claim evidence snapshots must be unique")
        return tuple(sorted(evidence, key=lambda item: item.source_snapshot_id))

    @model_validator(mode="after")
    def claim_is_authoritative_and_well_formed(self) -> "Claim":
        if (self.object_id is None) == (self.object_value is None):
            raise ValueError(
                "claim requires exactly one of object_id or object_value"
            )
        policy = CLAIM_REVIEW_POLICIES[self.claim_class]
        invalid_tiers = {
            item.authority_tier
            for item in self.evidence
            if item.authority_tier not in policy.allowed_source_tiers
        }
        if invalid_tiers:
            tiers = ", ".join(sorted(tier.value for tier in invalid_tiers))
            raise ValueError(
                f"{self.claim_class.value} does not allow source tiers: {tiers}"
            )
        minimum_reviewers = max(
            policy.minimum_reviewers,
            2 if self.criticality is ClaimCriticality.CRITICAL else 1,
        )
        if (
            self.review.status is ReviewStatus.APPROVED
            and len(self.review.reviewer_ids) < minimum_reviewers
        ):
            raise ValueError(
                f"{self.claim_class.value} requires at least "
                f"{minimum_reviewers} reviewers"
            )
        if (
            policy.requires_independent_corroboration
            and len(self.evidence) < 2
        ):
            raise ValueError(
                f"{self.claim_class.value} requires independent corroboration"
            )
        return self


class DecisionPattern(KnowledgeMetadata):
    kind: Literal["DecisionPattern"] = "DecisionPattern"
    decision: str = Field(min_length=1)
    recommended_when: tuple[str, ...] = ()
    avoid_when: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    supporting_claim_ids: tuple[StableId, ...] = Field(min_length=1)

    _normalize_recommended = field_validator("recommended_when")(_sorted_unique)
    _normalize_avoid = field_validator("avoid_when")(_sorted_unique)
    _normalize_tradeoffs = field_validator("tradeoffs")(_sorted_unique)
    _normalize_claims = field_validator("supporting_claim_ids")(_sorted_unique)


class OutcomeObservation(KnowledgeMetadata):
    kind: Literal["OutcomeObservation"] = "OutcomeObservation"
    workspace_id: StableId
    architecture_revision_id: StableId
    decision_pattern_ids: tuple[StableId, ...] = ()
    metric_name: str = Field(min_length=1)
    metric_value: float
    unit: str = Field(min_length=1)
    observed_from: datetime
    observed_until: datetime
    context: dict[str, JsonScalar] = Field(default_factory=dict)
    source_snapshot_ids: tuple[StableId, ...] = ()

    _normalize_patterns = field_validator("decision_pattern_ids")(_sorted_unique)
    _normalize_sources = field_validator("source_snapshot_ids")(_sorted_unique)

    @model_validator(mode="after")
    def observation_window_is_valid(self) -> "OutcomeObservation":
        if self.observed_until < self.observed_from:
            raise ValueError("observed_until must not precede observed_from")
        return self


class KnowledgeRelationship(KnowledgeMetadata):
    kind: Literal["Relationship"] = "Relationship"
    relationship_type: RelationshipType
    source_id: StableId
    source_kind: EntityKind
    target_id: StableId
    target_kind: EntityKind
    cardinality: RelationshipCardinality
    scope: ClaimScope
    supporting_claim_ids: tuple[StableId, ...] = Field(min_length=1)

    _normalize_claims = field_validator("supporting_claim_ids")(_sorted_unique)

    @model_validator(mode="after")
    def relationship_obeys_vocabulary(self) -> "KnowledgeRelationship":
        if self.source_id == self.target_id:
            raise ValueError("a relationship cannot reference itself")

        semantics = RELATIONSHIP_SEMANTICS[self.relationship_type]
        if self.source_kind not in semantics.source_kinds:
            raise ValueError(
                f"{self.relationship_type.value} does not allow source kind "
                f"{self.source_kind.value}"
            )
        if self.target_kind not in semantics.target_kinds:
            raise ValueError(
                f"{self.relationship_type.value} does not allow target kind "
                f"{self.target_kind.value}"
            )
        if self.cardinality not in semantics.cardinalities:
            raise ValueError(
                f"{self.relationship_type.value} does not allow cardinality "
                f"{self.cardinality.value}"
            )
        if not semantics.directed and self.source_id > self.target_id:
            raise ValueError(
                "symmetric relationships must store identifiers in lexical order"
            )
        if (
            self.relationship_type is RelationshipType.SUPERSEDES
            and self.source_kind is not self.target_kind
        ):
            raise ValueError("SUPERSEDES requires matching entity kinds")
        if (
            self.relationship_type is RelationshipType.SUPPORTED_BY
            and self.target_id not in self.supporting_claim_ids
        ):
            raise ValueError(
                "SUPPORTED_BY target must be included in supporting_claim_ids"
            )
        return self


class IdentifierTransition(FrozenModel):
    id: StableId
    transition_type: IdentifierTransitionType
    prior_ids: tuple[StableId, ...] = Field(min_length=1)
    successor_ids: tuple[StableId, ...] = ()
    effective_on: date
    rationale: str = Field(min_length=1)
    review: ReviewMetadata

    _normalize_prior = field_validator("prior_ids")(_sorted_unique)
    _normalize_successors = field_validator("successor_ids")(_sorted_unique)

    @model_validator(mode="after")
    def transition_shape_is_valid(self) -> "IdentifierTransition":
        if self.review.status is not ReviewStatus.APPROVED:
            raise ValueError("identifier transitions must be approved")
        if set(self.prior_ids) & set(self.successor_ids):
            raise ValueError("prior and successor identifiers must be disjoint")

        prior_count = len(self.prior_ids)
        successor_count = len(self.successor_ids)
        expected = {
            IdentifierTransitionType.RENAME: (1, 1),
            IdentifierTransitionType.MERGE: (2, 1),
            IdentifierTransitionType.SPLIT: (1, 2),
            IdentifierTransitionType.RETIRE: (1, 0),
        }
        minimum_prior, minimum_successor = expected[self.transition_type]
        if self.transition_type in {
            IdentifierTransitionType.MERGE,
            IdentifierTransitionType.SPLIT,
        }:
            valid = (
                prior_count >= minimum_prior
                and successor_count >= minimum_successor
                and (
                    self.transition_type is IdentifierTransitionType.MERGE
                    and successor_count == 1
                    or self.transition_type is IdentifierTransitionType.SPLIT
                    and prior_count == 1
                )
            )
        else:
            valid = (
                prior_count == minimum_prior
                and successor_count == minimum_successor
            )
        if not valid:
            raise ValueError(
                f"invalid identifier shape for {self.transition_type.value}"
            )
        return self


KnowledgeEntity = Annotated[
    Capability
    | Component
    | Offering
    | Variant
    | Interface
    | Claim
    | DecisionPattern
    | OutcomeObservation,
    Field(discriminator="kind"),
]
