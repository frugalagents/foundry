"""Immutable contracts for deterministic R0.3 assurance outputs."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from ..models import FrozenModel, StableId, content_hash


class NumericRange(FrozenModel):
    low: float = Field(ge=0)
    high: float = Field(ge=0)

    @model_validator(mode="after")
    def bounds_are_ordered(self) -> "NumericRange":
        if self.high < self.low:
            raise ValueError("range high must be greater than or equal to low")
        return self


class ThreatDefinition(FrozenModel):
    id: StableId
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1)
    component_ids: tuple[StableId, ...]
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)


class VerificationDefinition(FrozenModel):
    id: StableId
    method: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    acceptance_criteria: str = Field(min_length=1)
    frequency: str = Field(min_length=1)


class ControlDefinition(FrozenModel):
    id: StableId
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    threat_ids: tuple[StableId, ...]
    component_ids: tuple[StableId, ...]
    effectiveness: float = Field(gt=0, lt=1)
    verification: VerificationDefinition


class BestPracticeDefinition(FrozenModel):
    id: StableId
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    implementation: str = Field(min_length=1)
    component_ids: tuple[StableId, ...]
    control_ids: tuple[StableId, ...] = ()


class RoadmapDefinition(FrozenModel):
    owner_by_plane: dict[str, str]
    effort_days_by_plane: dict[str, NumericRange]
    dependency_effort_days: NumericRange
    control_verification_effort_days: NumericRange


class EconomicAssumptionDefinition(FrozenModel):
    id: StableId
    name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    value_range: NumericRange
    rationale: str = Field(min_length=1)


class UnitCostDefinition(FrozenModel):
    id: StableId
    name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    currency: Literal["USD"] = "USD"
    value_range: NumericRange
    effective_on: date
    status: Literal["placeholder", "evidence_backed"]
    source: str = Field(min_length=1)


class OutcomeEventDefinition(FrozenModel):
    id: StableId
    event_type: str = Field(pattern=r"^[a-z][a-z0-9_.-]+$")
    producer: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required_fields: tuple[str, ...]
    correlation_fields: tuple[str, ...]


class OutcomeMetricDefinition(FrozenModel):
    id: StableId
    name: str = Field(min_length=1)
    formula: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    source_event_ids: tuple[StableId, ...]
    source_systems: tuple[str, ...]
    denominator: str = Field(min_length=1)


class AssuranceCatalog(FrozenModel):
    schema_version: Literal["3.0"] = "3.0"
    catalog_id: StableId
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    effective_on: date
    threats: tuple[ThreatDefinition, ...]
    controls: tuple[ControlDefinition, ...]
    best_practices: tuple[BestPracticeDefinition, ...]
    roadmap: RoadmapDefinition
    economic_assumptions: tuple[EconomicAssumptionDefinition, ...]
    unit_costs: tuple[UnitCostDefinition, ...]
    outcome_events: tuple[OutcomeEventDefinition, ...]
    outcome_metrics: tuple[OutcomeMetricDefinition, ...]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class BundleImplementation(FrozenModel):
    component_id: StableId
    offering_id: StableId
    provider: str = Field(min_length=1)
    product: str = Field(min_length=1)


class ControlEvidence(FrozenModel):
    control_id: StableId
    evidence_id: StableId
    verification_id: StableId
    test_execution_id: StableId
    verifier: str = Field(min_length=1)
    artifact_uri: str = Field(min_length=1)
    artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: Literal["pass", "fail"]
    observed_at: datetime
    expires_on: date | None = None

    @model_validator(mode="after")
    def immutable_artifact_is_addressable(self) -> "ControlEvidence":
        if "://" not in self.artifact_uri:
            raise ValueError("control evidence artifact_uri must be absolute")
        if (
            self.expires_on is not None
            and self.expires_on < self.observed_at.date()
        ):
            raise ValueError("control evidence expires before it was observed")
        return self


class UnitCostOverride(FrozenModel):
    cost_id: StableId
    value_range: NumericRange
    effective_on: date
    source: str = Field(min_length=1)
    evidence_status: Literal["approved", "unverified"]


class SelectedBundleContext(FrozenModel):
    bundle_id: StableId
    implementations: tuple[BundleImplementation, ...] = ()
    control_evidence: tuple[ControlEvidence, ...] = ()
    unit_cost_overrides: tuple[UnitCostOverride, ...] = ()

    @field_validator("implementations")
    @classmethod
    def one_implementation_per_component(
        cls, values: tuple[BundleImplementation, ...]
    ) -> tuple[BundleImplementation, ...]:
        component_ids = [item.component_id for item in values]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("bundle may select one implementation per component")
        return tuple(sorted(values, key=lambda item: item.component_id))

    @model_validator(mode="after")
    def evidence_and_cost_inputs_are_unique(self) -> "SelectedBundleContext":
        evidence_ids = [item.evidence_id for item in self.control_evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("control evidence IDs must be unique")
        cost_ids = [item.cost_id for item in self.unit_cost_overrides]
        if len(cost_ids) != len(set(cost_ids)):
            raise ValueError("unit-cost overrides must be unique")
        return self


class ControlPlanItem(FrozenModel):
    control_id: StableId
    title: str
    status: Literal["planned", "verified", "failed"]
    applicable_component_ids: tuple[StableId, ...]
    threat_ids: tuple[StableId, ...]
    effectiveness: float
    verification: VerificationDefinition
    evidence_ids: tuple[StableId, ...] = ()


class ThreatAssessment(FrozenModel):
    threat_id: StableId
    title: str
    category: str
    applicable_component_ids: tuple[StableId, ...]
    inherent_score: float = Field(ge=0, le=25)
    required_control_ids: tuple[StableId, ...]
    verified_control_ids: tuple[StableId, ...]
    residual_score: float = Field(ge=0, le=25)
    residual_rating: Literal["low", "moderate", "high", "critical"]


class BestPracticePlanItem(FrozenModel):
    practice_id: StableId
    title: str
    status: Literal["planned", "verified"]
    rationale: str
    implementation: str
    applicable_component_ids: tuple[StableId, ...]
    control_ids: tuple[StableId, ...]


class SecurityAssurancePlan(FrozenModel):
    threats: tuple[ThreatAssessment, ...]
    controls: tuple[ControlPlanItem, ...]
    best_practices: tuple[BestPracticePlanItem, ...]
    inherent_risk_total: float
    residual_risk_total: float
    verified_control_count: int = Field(ge=0)
    high_or_critical_residual_count: int = Field(ge=0)


class WorkPackage(FrozenModel):
    package_id: StableId
    title: str
    kind: Literal["component", "control_verification"]
    component_id: StableId | None = None
    control_id: StableId | None = None
    offering_id: StableId | None = None
    owner: str
    effort_person_days: NumericRange
    dependency_package_ids: tuple[StableId, ...] = ()
    exit_criteria: tuple[str, ...]


class RoadmapPhase(FrozenModel):
    phase_id: StableId
    sequence: int = Field(ge=1)
    name: str
    work_packages: tuple[WorkPackage, ...]
    exit_criteria: tuple[str, ...]


class ImplementationRoadmap(FrozenModel):
    phases: tuple[RoadmapPhase, ...]
    total_effort_person_days: NumericRange
    critical_path_package_ids: tuple[StableId, ...]


class EconomicAssumption(FrozenModel):
    assumption_id: StableId
    name: str
    unit: str
    value_range: NumericRange
    rationale: str
    source: Literal["catalog_default", "workspace_requirement"]


class UnitCostInput(FrozenModel):
    cost_id: StableId
    name: str
    unit: str
    currency: Literal["USD"] = "USD"
    value_range: NumericRange
    effective_on: date
    status: Literal["placeholder", "evidence_backed", "unverified_override"]
    source: str


class EconomicsTotals(FrozenModel):
    cost_per_requested_task: NumericRange
    cost_per_successful_task: NumericRange
    cost_per_accepted_pull_request: NumericRange
    monthly_platform_cost: NumericRange
    monthly_cost_per_developer: NumericRange


class EconomicsPlan(FrozenModel):
    assumptions: tuple[EconomicAssumption, ...]
    unit_costs: tuple[UnitCostInput, ...]
    formulas: dict[str, str]
    totals: EconomicsTotals
    sensitivity_drivers: tuple[str, ...]
    pricing_warning: str


class OutcomeEventContract(FrozenModel):
    event_id: StableId
    event_type: str
    producer: str
    description: str
    required_fields: tuple[str, ...]
    correlation_fields: tuple[str, ...]


class OutcomeMetric(FrozenModel):
    metric_id: StableId
    name: str
    formula: str
    unit: str
    source_event_ids: tuple[StableId, ...]
    source_systems: tuple[str, ...]
    denominator: str


class MeasurementHorizon(FrozenModel):
    horizon: Literal["baseline", "day_30", "day_90", "day_180"]
    objective: str
    metric_ids: tuple[StableId, ...]
    activities: tuple[str, ...]


class OutcomeObservabilityPlan(FrozenModel):
    join_path: tuple[str, ...]
    event_contract: tuple[OutcomeEventContract, ...]
    metrics: tuple[OutcomeMetric, ...]
    measurement_horizons: tuple[MeasurementHorizon, ...]
    gitlab_ci_mapping: dict[str, str]


class EvidenceReadinessSignal(FrozenModel):
    status: Literal["complete", "incomplete", "unverified"]
    verified_claim_ids: tuple[StableId, ...] = ()
    unverified_claim_ids: tuple[StableId, ...] = ()
    unevidenced_input_ids: tuple[StableId, ...] = ()

    _sort_verified = field_validator("verified_claim_ids")(
        lambda values: tuple(sorted(set(values)))
    )
    _sort_unverified = field_validator("unverified_claim_ids")(
        lambda values: tuple(sorted(set(values)))
    )
    _sort_unevidenced = field_validator("unevidenced_input_ids")(
        lambda values: tuple(sorted(set(values)))
    )


class FreshnessReadinessSignal(FrozenModel):
    status: Literal["current", "stale", "unknown"]
    evaluated_as_of: date
    stale_claim_ids: tuple[StableId, ...] = ()

    _sort_stale = field_validator("stale_claim_ids")(
        lambda values: tuple(sorted(set(values)))
    )


class StabilityReadinessSignal(FrozenModel):
    status: Literal["stable", "sensitive", "unknown"]
    selected_candidate_id: StableId | None = None
    winner_change_dimension_ids: tuple[StableId, ...] = ()
    score_margin: float | None = Field(default=None, ge=0)

    _sort_dimensions = field_validator("winner_change_dimension_ids")(
        lambda values: tuple(sorted(set(values)))
    )


class ExpertReviewReadinessSignal(FrozenModel):
    required: bool
    reason_codes: tuple[str, ...] = ()

    @field_validator("reason_codes")
    @classmethod
    def unique_sorted_reasons(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(values)))

    @model_validator(mode="after")
    def reasons_match_requirement(self) -> "ExpertReviewReadinessSignal":
        if self.required != bool(self.reason_codes):
            raise ValueError("expert-review reasons must match required state")
        return self


class DecisionReadiness(FrozenModel):
    state: Literal[
        "decision_ready",
        "conditional",
        "needs_information",
        "expert_review",
    ]
    evidence: EvidenceReadinessSignal
    freshness: FreshnessReadinessSignal
    stability: StabilityReadinessSignal
    expert_review: ExpertReviewReadinessSignal
    blocking_reason_codes: tuple[str, ...] = ()

    @field_validator("blocking_reason_codes")
    @classmethod
    def unique_sorted_blockers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(values)))

    @model_validator(mode="after")
    def ready_has_no_blockers(self) -> "DecisionReadiness":
        if self.state == "decision_ready" and (
            self.blocking_reason_codes or self.expert_review.required
        ):
            raise ValueError("decision_ready cannot contain blockers")
        return self


class AssuranceOutputs(FrozenModel):
    schema_version: Literal["3.0"] = "3.0"
    workspace_id: StableId
    workspace_revision_id: StableId
    workspace_state_hash: str
    architecture_catalog_id: StableId
    architecture_catalog_version: str
    architecture_catalog_content_hash: str
    assurance_catalog_id: StableId
    assurance_catalog_version: str
    assurance_catalog_content_hash: str
    selected_bundle_id: StableId | None = None
    generated_as_of: date
    security: SecurityAssurancePlan
    roadmap: ImplementationRoadmap
    economics: EconomicsPlan
    outcomes: OutcomeObservabilityPlan
    readiness: DecisionReadiness
    packet_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def packet_hash_matches_content(self) -> "AssuranceOutputs":
        payload = self.model_dump(mode="json", exclude={"packet_hash"})
        if self.packet_hash != content_hash(payload):
            raise ValueError("packet_hash does not match assurance output content")
        return self
