"""Immutable contracts for the architecture-first Platform Advisor v3."""
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
        description="Namespaced, stable identifier such as component:model_gateway.",
    ),
]
SemanticVersion = Annotated[
    str,
    Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z.-]+)?$",
        description="Semantic version pinned into releases and revisions.",
    ),
]
JsonScalar = str | int | float | bool | None
RequirementValue = JsonScalar | tuple[JsonScalar, ...]


class FrozenModel(BaseModel):
    """Base contract that rejects unknown fields and in-place assignment."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class VersionedRecord(FrozenModel):
    id: StableId
    version: SemanticVersion


class StrEnum(str, Enum):
    pass


class EvidenceReviewStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RequirementValueType(StrEnum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"
    STRING_SET = "string_set"


class RequirementOperator(StrEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"


class ArchitecturePlane(StrEnum):
    EXPERIENCE = "experience"
    ACCESS = "access"
    ORCHESTRATION = "orchestration"
    MODEL = "model"
    TOOL = "tool"
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"
    GOVERNANCE = "governance"
    OBSERVABILITY = "observability"


class ComponentKind(StrEnum):
    LOGICAL = "logical"
    OVERLAY = "overlay"


class PatternRole(StrEnum):
    LOGICAL_REFERENCE = "logical_reference"
    DEPLOYMENT_FAMILY = "deployment_family"


class ArchitectureRelationship(StrEnum):
    DEPENDS_ON = "depends_on"


class RuleEffect(StrEnum):
    REQUIRE = "require"
    EXCLUDE = "exclude"
    RECOMMEND = "recommend"
    WARN = "warn"


class FeasibilityStatus(StrEnum):
    FEASIBLE = "feasible"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class RuleOutcome(StrEnum):
    SATISFIES = "satisfies"
    VIOLATES = "violates"
    UNKNOWN = "unknown"


def canonical_json(value: BaseModel | dict[str, object]) -> str:
    """Serialize a contract deterministically for hashing and replay."""

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
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def _sorted_unique(values: tuple[StableId, ...]) -> tuple[StableId, ...]:
    if len(values) != len(set(values)):
        raise ValueError("references must be unique")
    return tuple(sorted(values))


class EvidenceSource(VersionedRecord):
    title: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    retrieved_at: datetime
    snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class EvidenceClaim(VersionedRecord):
    source_id: StableId
    statement: str = Field(min_length=1)
    critical: bool = False
    review_status: EvidenceReviewStatus = EvidenceReviewStatus.DRAFT
    effective_on: date
    expires_on: date | None = None
    source_locator: str = Field(min_length=1)
    reviewer: str | None = None

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "EvidenceClaim":
        if self.expires_on is not None and self.expires_on < self.effective_on:
            raise ValueError("expires_on cannot precede effective_on")
        if self.review_status is EvidenceReviewStatus.APPROVED and not self.reviewer:
            raise ValueError("approved evidence requires a reviewer")
        return self


class RulePredicate(FrozenModel):
    requirement_id: StableId
    operator: RequirementOperator
    value: RequirementValue


class RequirementDefinition(VersionedRecord):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    value_type: RequirementValueType
    required: bool = False
    allowed_values: tuple[RequirementValue, ...] = ()
    ask_when: tuple[RulePredicate, ...] = ()
    evidence_claim_ids: tuple[StableId, ...] = ()

    _normalize_evidence = field_validator("evidence_claim_ids")(_sorted_unique)

    @field_validator("allowed_values")
    @classmethod
    def unique_allowed_values(
        cls, values: tuple[RequirementValue, ...]
    ) -> tuple[RequirementValue, ...]:
        serialized = [canonical_json({"value": value}) for value in values]
        if len(serialized) != len(set(serialized)):
            raise ValueError("allowed requirement values must be unique")
        return values

    @model_validator(mode="after")
    def allowed_values_match_type(self) -> "RequirementDefinition":
        validators = {
            RequirementValueType.BOOLEAN: lambda item: isinstance(item, bool),
            RequirementValueType.INTEGER: lambda item: (
                isinstance(item, int) and not isinstance(item, bool)
            ),
            RequirementValueType.NUMBER: lambda item: (
                isinstance(item, (int, float)) and not isinstance(item, bool)
            ),
            RequirementValueType.STRING: lambda item: isinstance(item, str),
            RequirementValueType.STRING_SET: lambda item: (
                isinstance(item, tuple)
                and all(isinstance(member, str) for member in item)
            ),
        }
        if any(
            value is None or not validators[self.value_type](value)
            for value in self.allowed_values
        ):
            raise ValueError(
                f"allowed values must match {self.value_type.value}"
            )
        return self

    @model_validator(mode="after")
    def cannot_depend_on_self(self) -> "RequirementDefinition":
        if any(
            predicate.requirement_id == self.id
            for predicate in self.ask_when
        ):
            raise ValueError("requirement ask_when cannot reference itself")
        return self


class ComponentDefinition(VersionedRecord):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    plane: ArchitecturePlane
    kind: ComponentKind = ComponentKind.LOGICAL
    dependency_ids: tuple[StableId, ...] = ()
    evidence_claim_ids: tuple[StableId, ...] = ()

    _normalize_dependencies = field_validator("dependency_ids")(_sorted_unique)
    _normalize_evidence = field_validator("evidence_claim_ids")(_sorted_unique)

    @model_validator(mode="after")
    def cannot_depend_on_self(self) -> "ComponentDefinition":
        if self.id in self.dependency_ids:
            raise ValueError(f"component {self.id} cannot depend on itself")
        return self


class ArchitecturePattern(VersionedRecord):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    role: PatternRole
    component_ids: tuple[StableId, ...]
    evidence_claim_ids: tuple[StableId, ...] = ()

    _normalize_components = field_validator("component_ids")(_sorted_unique)
    _normalize_evidence = field_validator("evidence_claim_ids")(_sorted_unique)


class DecisionRule(VersionedRecord):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    when: tuple[RulePredicate, ...]
    effect: RuleEffect
    target_component_ids: tuple[StableId, ...] = ()
    target_pattern_ids: tuple[StableId, ...] = ()
    depends_on_rule_ids: tuple[StableId, ...] = ()
    evidence_claim_ids: tuple[StableId, ...] = ()

    _normalize_components = field_validator("target_component_ids")(_sorted_unique)
    _normalize_patterns = field_validator("target_pattern_ids")(_sorted_unique)
    _normalize_rules = field_validator("depends_on_rule_ids")(_sorted_unique)
    _normalize_evidence = field_validator("evidence_claim_ids")(_sorted_unique)

    @model_validator(mode="after")
    def has_target_and_no_self_reference(self) -> "DecisionRule":
        if not self.target_component_ids and not self.target_pattern_ids:
            raise ValueError("decision rule must target a component or pattern")
        if self.target_component_ids and self.target_pattern_ids:
            raise ValueError(
                "decision rule cannot mix component and pattern targets"
            )
        if (
            self.target_pattern_ids
            and self.effect is not RuleEffect.EXCLUDE
        ):
            raise ValueError(
                "pattern-targeted rules must use the exclude effect"
            )
        if self.id in self.depends_on_rule_ids:
            raise ValueError(f"rule {self.id} cannot depend on itself")
        return self


class CatalogManifest(VersionedRecord):
    schema_version: Literal["3.0"] = "3.0"
    title: str = Field(min_length=1)
    effective_on: date


class CatalogDocument(FrozenModel):
    """One JSON catalog file; records may be split across many documents."""

    manifest: CatalogManifest | None = None
    evidence_sources: tuple[EvidenceSource, ...] = ()
    evidence_claims: tuple[EvidenceClaim, ...] = ()
    requirements: tuple[RequirementDefinition, ...] = ()
    components: tuple[ComponentDefinition, ...] = ()
    patterns: tuple[ArchitecturePattern, ...] = ()
    rules: tuple[DecisionRule, ...] = ()


class CatalogRelease(CatalogManifest):
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validated_as_of: date
    evidence_sources: tuple[EvidenceSource, ...] = ()
    evidence_claims: tuple[EvidenceClaim, ...] = ()
    requirements: tuple[RequirementDefinition, ...] = ()
    components: tuple[ComponentDefinition, ...] = ()
    patterns: tuple[ArchitecturePattern, ...] = ()
    rules: tuple[DecisionRule, ...] = ()

    def replay_json(self) -> str:
        return canonical_json(self)


class AssumptionMetadata(FrozenModel):
    rationale: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    owner: str = Field(min_length=1)
    source: str = Field(min_length=1)


class RequirementConstraint(FrozenModel):
    requirement_id: StableId
    value: RequirementValue
    source: Literal["user", "assumption", "derived", "imported"]
    assumption: AssumptionMetadata | None = None
    recorded_at: datetime

    @model_validator(mode="after")
    def assumption_metadata_matches_source(self) -> "RequirementConstraint":
        if self.source == "assumption" and self.assumption is None:
            raise ValueError("assumption constraints require assumption metadata")
        if self.source != "assumption" and self.assumption is not None:
            raise ValueError(
                "assumption metadata is only valid for assumption constraints"
            )
        return self


class RequirementPatch(FrozenModel):
    patch_id: StableId
    base_revision_number: int = Field(ge=0)
    changes: tuple[RequirementConstraint, ...] = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @field_validator("changes")
    @classmethod
    def unique_changes(
        cls, changes: tuple[RequirementConstraint, ...]
    ) -> tuple[RequirementConstraint, ...]:
        requirement_ids = [change.requirement_id for change in changes]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("requirement patch may change each requirement only once")
        return tuple(sorted(changes, key=lambda change: change.requirement_id))


class ArchitectureDelta(FrozenModel):
    added_component_ids: tuple[StableId, ...] = ()
    removed_component_ids: tuple[StableId, ...] = ()
    added_edge_ids: tuple[StableId, ...] = ()
    removed_edge_ids: tuple[StableId, ...] = ()
    activated_rule_ids: tuple[StableId, ...] = ()
    deactivated_rule_ids: tuple[StableId, ...] = ()

    _normalize_added = field_validator("added_component_ids")(_sorted_unique)
    _normalize_removed = field_validator("removed_component_ids")(_sorted_unique)
    _normalize_added_edges = field_validator("added_edge_ids")(_sorted_unique)
    _normalize_removed_edges = field_validator("removed_edge_ids")(_sorted_unique)
    _normalize_activated_rules = field_validator("activated_rule_ids")(_sorted_unique)
    _normalize_deactivated_rules = field_validator("deactivated_rule_ids")(
        _sorted_unique
    )


class RequirementChange(FrozenModel):
    requirement_id: StableId
    previous: RequirementConstraint | None = None
    current: RequirementConstraint | None = None

    @model_validator(mode="after")
    def constraints_match_and_change(self) -> "RequirementChange":
        if self.previous is None and self.current is None:
            raise ValueError("requirement change requires a previous or current value")
        for constraint in (self.previous, self.current):
            if (
                constraint is not None
                and constraint.requirement_id != self.requirement_id
            ):
                raise ValueError(
                    "requirement change constraints must match requirement_id"
                )
        if self.previous == self.current:
            raise ValueError("requirement change must alter the constraint")
        return self


class AnswerImpact(FrozenModel):
    answer: RequirementValue
    added_component_ids: tuple[StableId, ...] = ()
    removed_component_ids: tuple[StableId, ...] = ()
    added_edge_ids: tuple[StableId, ...] = ()
    removed_edge_ids: tuple[StableId, ...] = ()
    activated_rule_ids: tuple[StableId, ...] = ()
    deactivated_rule_ids: tuple[StableId, ...] = ()
    feasible_pattern_ids: tuple[StableId, ...] = ()
    rejected_pattern_ids: tuple[StableId, ...] = ()
    unknown_pattern_ids: tuple[StableId, ...] = ()

    _normalize_added = field_validator("added_component_ids")(_sorted_unique)
    _normalize_removed = field_validator("removed_component_ids")(_sorted_unique)
    _normalize_added_edges = field_validator("added_edge_ids")(_sorted_unique)
    _normalize_removed_edges = field_validator("removed_edge_ids")(_sorted_unique)
    _normalize_activated = field_validator("activated_rule_ids")(_sorted_unique)
    _normalize_deactivated = field_validator("deactivated_rule_ids")(_sorted_unique)
    _normalize_feasible_patterns = field_validator("feasible_pattern_ids")(
        _sorted_unique
    )
    _normalize_rejected_patterns = field_validator("rejected_pattern_ids")(
        _sorted_unique
    )
    _normalize_unknown_patterns = field_validator("unknown_pattern_ids")(
        _sorted_unique
    )


class QuestionCandidate(FrozenModel):
    question_id: StableId
    requirement_id: StableId
    prompt: str = Field(min_length=1)
    candidate_answers: tuple[RequirementValue, ...] = ()
    candidate_elimination_count: int = Field(ge=0)
    affected_component_ids: tuple[StableId, ...] = ()
    answer_impacts: tuple[AnswerImpact, ...] = ()
    hard_constraint_risk: bool = False
    information_gain: float = Field(ge=0)
    why_now: str = Field(min_length=1)

    _normalize_components = field_validator("affected_component_ids")(_sorted_unique)

    @model_validator(mode="after")
    def impacts_match_candidate_answers(self) -> "QuestionCandidate":
        answers = [
            canonical_json({"value": value}) for value in self.candidate_answers
        ]
        impact_answers = [
            canonical_json({"value": impact.answer})
            for impact in self.answer_impacts
        ]
        if self.answer_impacts and impact_answers != answers:
            raise ValueError("answer impacts must align with candidate answers")
        return self


class ArchitectureNode(FrozenModel):
    instance_id: StableId
    component_id: StableId


class ArchitectureEdge(FrozenModel):
    edge_id: StableId
    source_instance_id: StableId
    target_instance_id: StableId
    relationship: ArchitectureRelationship = ArchitectureRelationship.DEPENDS_ON


class ArchitectureState(FrozenModel):
    pattern_id: StableId
    nodes: tuple[ArchitectureNode, ...]
    edges: tuple[ArchitectureEdge, ...] = ()

    @field_validator("nodes")
    @classmethod
    def unique_nodes(
        cls, nodes: tuple[ArchitectureNode, ...]
    ) -> tuple[ArchitectureNode, ...]:
        instance_ids = [node.instance_id for node in nodes]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("architecture node instance IDs must be unique")
        return tuple(sorted(nodes, key=lambda node: node.instance_id))

    @field_validator("edges")
    @classmethod
    def unique_edges(
        cls, edges: tuple[ArchitectureEdge, ...]
    ) -> tuple[ArchitectureEdge, ...]:
        edge_ids = [edge.edge_id for edge in edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("architecture edge IDs must be unique")
        return tuple(sorted(edges, key=lambda edge: edge.edge_id))

    @model_validator(mode="after")
    def edges_reference_nodes(self) -> "ArchitectureState":
        node_ids = {node.instance_id for node in self.nodes}
        for edge in self.edges:
            if (
                edge.source_instance_id not in node_ids
                or edge.target_instance_id not in node_ids
            ):
                raise ValueError("architecture edges must reference existing nodes")
        return self


class RuleEvaluation(FrozenModel):
    evaluation_id: StableId
    rule_id: StableId
    effect: RuleEffect
    requirement_ids: tuple[StableId, ...]
    target_component_ids: tuple[StableId, ...] = ()
    target_pattern_ids: tuple[StableId, ...] = ()
    evidence_claim_ids: tuple[StableId, ...] = ()
    rationale: str = Field(min_length=1)

    _normalize_requirements = field_validator("requirement_ids")(_sorted_unique)
    _normalize_components = field_validator("target_component_ids")(_sorted_unique)
    _normalize_patterns = field_validator("target_pattern_ids")(_sorted_unique)
    _normalize_evidence = field_validator("evidence_claim_ids")(_sorted_unique)


class DecisionTraceTransition(FrozenModel):
    transition_id: StableId
    prior_revision_id: StableId
    prior_revision_number: int = Field(ge=1)
    prior_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    current_revision_id: StableId
    current_revision_number: int = Field(ge=2)
    current_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requirement_changes: tuple[RequirementChange, ...] = ()
    activated_rule_evaluations: tuple[RuleEvaluation, ...] = ()
    deactivated_rule_evaluations: tuple[RuleEvaluation, ...] = ()
    architecture_delta: ArchitectureDelta
    transition_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("requirement_changes")
    @classmethod
    def unique_sorted_requirement_changes(
        cls,
        changes: tuple[RequirementChange, ...],
    ) -> tuple[RequirementChange, ...]:
        requirement_ids = [change.requirement_id for change in changes]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("trace requirement changes must be unique")
        return tuple(sorted(changes, key=lambda item: item.requirement_id))

    @field_validator(
        "activated_rule_evaluations",
        "deactivated_rule_evaluations",
    )
    @classmethod
    def unique_sorted_rule_evaluations(
        cls,
        evaluations: tuple[RuleEvaluation, ...],
    ) -> tuple[RuleEvaluation, ...]:
        rule_ids = [evaluation.rule_id for evaluation in evaluations]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("trace rule evaluations must be unique")
        return tuple(sorted(evaluations, key=lambda item: item.rule_id))

    @model_validator(mode="after")
    def linkage_and_hash_are_valid(self) -> "DecisionTraceTransition":
        if self.current_revision_number != self.prior_revision_number + 1:
            raise ValueError("decision trace revisions must be contiguous")
        activated = {
            evaluation.rule_id
            for evaluation in self.activated_rule_evaluations
        }
        deactivated = {
            evaluation.rule_id
            for evaluation in self.deactivated_rule_evaluations
        }
        if activated != set(self.architecture_delta.activated_rule_ids):
            raise ValueError("activated trace rules must match architecture delta")
        if deactivated != set(self.architecture_delta.deactivated_rule_ids):
            raise ValueError("deactivated trace rules must match architecture delta")
        expected = content_hash({
            "transition_id": self.transition_id,
            "prior_revision_id": self.prior_revision_id,
            "prior_revision_number": self.prior_revision_number,
            "prior_state_hash": self.prior_state_hash,
            "current_revision_id": self.current_revision_id,
            "current_revision_number": self.current_revision_number,
            "current_state_hash": self.current_state_hash,
            "requirement_changes": [
                change.model_dump(mode="json")
                for change in self.requirement_changes
            ],
            "activated_rule_evaluations": [
                evaluation.model_dump(mode="json")
                for evaluation in self.activated_rule_evaluations
            ],
            "deactivated_rule_evaluations": [
                evaluation.model_dump(mode="json")
                for evaluation in self.deactivated_rule_evaluations
            ],
            "architecture_delta": self.architecture_delta.model_dump(mode="json"),
        })
        if self.transition_hash != expected:
            raise ValueError(
                "decision trace transition_hash does not match trace content"
            )
        return self


class FeasibilityRuleEvaluation(FrozenModel):
    evaluation_id: StableId
    rule_id: StableId
    pattern_id: StableId
    outcome: RuleOutcome
    requirement_ids: tuple[StableId, ...]
    unknown_requirement_ids: tuple[StableId, ...] = ()
    evidence_claim_ids: tuple[StableId, ...] = ()
    rationale: str = Field(min_length=1)

    _normalize_requirements = field_validator("requirement_ids")(_sorted_unique)
    _normalize_unknowns = field_validator("unknown_requirement_ids")(
        _sorted_unique
    )
    _normalize_evidence = field_validator("evidence_claim_ids")(_sorted_unique)


class DeploymentFamilyEvaluation(FrozenModel):
    pattern_id: StableId
    status: FeasibilityStatus
    architecture: ArchitectureState
    component_rule_evaluations: tuple[RuleEvaluation, ...] = ()
    feasibility_rule_evaluations: tuple[FeasibilityRuleEvaluation, ...]
    rejection_rule_ids: tuple[StableId, ...] = ()
    blocking_requirement_ids: tuple[StableId, ...] = ()

    _normalize_rejections = field_validator("rejection_rule_ids")(_sorted_unique)
    _normalize_blockers = field_validator("blocking_requirement_ids")(
        _sorted_unique
    )

    @field_validator("component_rule_evaluations")
    @classmethod
    def sort_component_evaluations(
        cls,
        evaluations: tuple[RuleEvaluation, ...],
    ) -> tuple[RuleEvaluation, ...]:
        return tuple(sorted(evaluations, key=lambda item: item.evaluation_id))

    @field_validator("feasibility_rule_evaluations")
    @classmethod
    def sort_feasibility_evaluations(
        cls,
        evaluations: tuple[FeasibilityRuleEvaluation, ...],
    ) -> tuple[FeasibilityRuleEvaluation, ...]:
        if not evaluations:
            raise ValueError("deployment family requires feasibility rule coverage")
        return tuple(sorted(evaluations, key=lambda item: item.evaluation_id))

    @model_validator(mode="after")
    def status_matches_rule_outcomes(self) -> "DeploymentFamilyEvaluation":
        if self.architecture.pattern_id != self.pattern_id:
            raise ValueError("family architecture must use the evaluated pattern")
        if self.status is FeasibilityStatus.REJECTED:
            if not self.rejection_rule_ids:
                raise ValueError("rejected family requires a rejection rule")
        elif self.rejection_rule_ids:
            raise ValueError("non-rejected family cannot contain rejection rules")
        if self.status is FeasibilityStatus.UNKNOWN:
            if not self.blocking_requirement_ids:
                raise ValueError("unknown family requires a blocking requirement")
        elif self.blocking_requirement_ids:
            raise ValueError("resolved family cannot contain blocking requirements")
        return self


class DeploymentFeasibilityAssessment(FrozenModel):
    baseline_pattern_id: StableId
    workspace_revision_id: StableId
    catalog_release_id: StableId
    catalog_release_version: SemanticVersion
    catalog_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    family_evaluations: tuple[DeploymentFamilyEvaluation, ...]
    result_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("family_evaluations")
    @classmethod
    def unique_sorted_families(
        cls,
        evaluations: tuple[DeploymentFamilyEvaluation, ...],
    ) -> tuple[DeploymentFamilyEvaluation, ...]:
        pattern_ids = [evaluation.pattern_id for evaluation in evaluations]
        if len(pattern_ids) != len(set(pattern_ids)):
            raise ValueError("deployment family evaluations must be unique")
        return tuple(sorted(evaluations, key=lambda item: item.pattern_id))

    @model_validator(mode="after")
    def result_hash_matches_content(self) -> "DeploymentFeasibilityAssessment":
        expected = content_hash({
            "baseline_pattern_id": self.baseline_pattern_id,
            "workspace_revision_id": self.workspace_revision_id,
            "catalog_release_id": self.catalog_release_id,
            "catalog_release_version": self.catalog_release_version,
            "catalog_content_hash": self.catalog_content_hash,
            "family_evaluations": [
                evaluation.model_dump(mode="json")
                for evaluation in self.family_evaluations
            ],
        })
        if expected != self.result_hash:
            raise ValueError(
                "feasibility result_hash does not match assessment content"
            )
        return self


class WorkspaceRevision(FrozenModel):
    revision_id: StableId
    revision_number: int = Field(ge=1)
    parent_revision_id: StableId | None = None
    catalog_release_id: StableId
    catalog_release_version: SemanticVersion
    catalog_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requirements: tuple[RequirementConstraint, ...]
    architecture: ArchitectureState
    rule_evaluations: tuple[RuleEvaluation, ...] = ()
    delta: ArchitectureDelta = Field(default_factory=ArchitectureDelta)
    created_at: datetime
    state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("requirements")
    @classmethod
    def unique_requirements(
        cls,
        requirements: tuple[RequirementConstraint, ...],
    ) -> tuple[RequirementConstraint, ...]:
        requirement_ids = [
            requirement.requirement_id for requirement in requirements
        ]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("revision requirement IDs must be unique")
        return tuple(
            sorted(
                requirements,
                key=lambda requirement: requirement.requirement_id,
            )
        )

    @field_validator("rule_evaluations")
    @classmethod
    def unique_rule_evaluations(
        cls, evaluations: tuple[RuleEvaluation, ...]
    ) -> tuple[RuleEvaluation, ...]:
        evaluation_ids = [
            evaluation.evaluation_id for evaluation in evaluations
        ]
        if len(evaluation_ids) != len(set(evaluation_ids)):
            raise ValueError("rule evaluation IDs must be unique")
        return tuple(
            sorted(evaluations, key=lambda evaluation: evaluation.evaluation_id)
        )

    @model_validator(mode="after")
    def state_hash_matches_content(self) -> "WorkspaceRevision":
        expected = content_hash({
            "catalog_content_hash": self.catalog_content_hash,
            "requirements": [
                {
                    "requirement_id": requirement.requirement_id,
                    "value": requirement.value,
                    "source": requirement.source,
                }
                for requirement in self.requirements
            ],
            "architecture": self.architecture.model_dump(mode="json"),
        })
        if self.state_hash != expected:
            raise ValueError("revision state_hash does not match revision content")
        return self


class ArchitectureWorkspace(FrozenModel):
    workspace_id: StableId
    current_revision_id: StableId
    revisions: tuple[WorkspaceRevision, ...]

    @model_validator(mode="after")
    def revision_chain_is_replayable(self) -> "ArchitectureWorkspace":
        if not self.revisions:
            raise ValueError("workspace must contain at least one revision")
        numbers = [revision.revision_number for revision in self.revisions]
        if numbers != list(range(1, len(self.revisions) + 1)):
            raise ValueError("workspace revisions must be ordered and contiguous")
        by_id = {revision.revision_id: revision for revision in self.revisions}
        if len(by_id) != len(self.revisions):
            raise ValueError("workspace revision IDs must be unique")
        if self.current_revision_id != self.revisions[-1].revision_id:
            raise ValueError("current_revision_id must identify the latest revision")
        for index, revision in enumerate(self.revisions):
            expected_parent = None if index == 0 else self.revisions[index - 1].revision_id
            if revision.parent_revision_id != expected_parent:
                raise ValueError("workspace revision parent chain is invalid")
        return self
