"""Versioned input and output contracts for the v2 advisor."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class StrEnum(str, Enum):
    pass


class Audience(StrEnum):
    EMPLOYEES = "employees"
    INTERNAL_BUILDERS = "internal_builders"
    EXTERNAL_CUSTOMERS = "external_customers"
    THIRD_PARTIES = "third_parties"


class Workload(StrEnum):
    CODING = "coding"
    INTERNAL_COPILOT = "internal_copilot"
    HOSTING = "hosting"
    CUSTOMER_FACING = "customer_facing"
    PROCESS_AUTOMATION = "process_automation"
    MARKETPLACE = "marketplace"


class Ownership(StrEnum):
    CENTRAL = "central"
    SHARED = "shared"
    DOMAIN = "domain"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class Impact(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class Autonomy(StrEnum):
    SUGGEST = "suggest"
    APPROVAL = "approval"
    AUTONOMOUS = "autonomous"
    UNKNOWN = "unknown"


class DataClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PHI = "phi"
    PCI = "pci"


class Residency(StrEnum):
    SINGLE_REGION = "single_region"
    MULTI_REGION = "multi_region"
    COUNTRY_BOUND = "country_bound"
    HYBRID = "hybrid"
    MULTI_CLOUD = "multi_cloud"
    UNKNOWN = "unknown"


class Isolation(StrEnum):
    SHARED_RBAC = "shared_rbac"
    NAMESPACE = "namespace"
    ACCOUNT = "account"
    DEDICATED_STACK = "dedicated_stack"
    UNKNOWN = "unknown"


class Maturity(StrEnum):
    GREENFIELD = "greenfield"
    PILOT = "pilot"
    PRODUCTION = "production"
    SCALED = "scaled"


class VolumeRange(BaseModel):
    low: float = Field(ge=0)
    expected: float = Field(ge=0)
    high: float = Field(ge=0)
    unit: str

    @model_validator(mode="after")
    def ordered(self) -> "VolumeRange":
        if not self.low <= self.expected <= self.high:
            raise ValueError("volume range must satisfy low <= expected <= high")
        return self


class CodingProfile(BaseModel):
    kind: Literal["coding"] = "coding"
    developers: VolumeRange | None = None
    repositories: int | None = Field(default=None, ge=0)
    concurrent_sessions: VolumeRange | None = None
    monthly_model_calls: VolumeRange | None = None
    tokens_per_call: VolumeRange | None = None
    code_boundary: Literal["vpc_only", "approved_saas", "no_constraint", "unknown"] = "unknown"
    execution_sandbox: bool | None = None


class InternalCopilotProfile(BaseModel):
    kind: Literal["internal_copilot"] = "internal_copilot"
    employees: int | None = Field(default=None, ge=0)
    monthly_active_users: VolumeRange | None = None
    data_domains: int | None = Field(default=None, ge=0)
    monthly_queries: VolumeRange | None = None
    tokens_per_query: VolumeRange | None = None
    action_enabled: bool | None = None


class HostingProfile(BaseModel):
    kind: Literal["hosting"] = "hosting"
    builder_teams: int | None = Field(default=None, ge=0)
    tenants: VolumeRange | None = None
    deployed_agents: VolumeRange | None = None
    monthly_model_calls: VolumeRange | None = None
    tokens_per_call: VolumeRange | None = None
    self_service: Literal["full", "approval", "central", "unknown"] = "unknown"


class CustomerFacingProfile(BaseModel):
    kind: Literal["customer_facing"] = "customer_facing"
    tenants: VolumeRange | None = None
    monthly_active_users: VolumeRange | None = None
    average_rps: VolumeRange | None = None
    peak_rps: float | None = Field(default=None, ge=0)
    monthly_model_calls: VolumeRange | None = None
    tokens_per_call: VolumeRange | None = None


class ProcessAutomationProfile(BaseModel):
    kind: Literal["process_automation"] = "process_automation"
    workflows: int | None = Field(default=None, ge=0)
    monthly_executions: VolumeRange | None = None
    tokens_per_execution: VolumeRange | None = None
    average_duration_minutes: float | None = Field(default=None, ge=0)
    exception_rate_pct: float | None = Field(default=None, ge=0, le=100)
    approval_required: bool | None = None


class MarketplaceProfile(BaseModel):
    kind: Literal["marketplace"] = "marketplace"
    publishers: VolumeRange | None = None
    consumers: VolumeRange | None = None
    listed_agents: VolumeRange | None = None
    monthly_transactions: VolumeRange | None = None
    tokens_per_transaction: VolumeRange | None = None
    external_agents: bool | None = None
    billing_model: Literal["none", "per_call", "per_outcome", "subscription", "unknown"] = "unknown"


WorkloadProfile = Annotated[
    CodingProfile
    | InternalCopilotProfile
    | HostingProfile
    | CustomerFacingProfile
    | ProcessAutomationProfile
    | MarketplaceProfile,
    Field(discriminator="kind"),
]


class OwnershipInput(BaseModel):
    platform_owner: Ownership = Ownership.UNKNOWN
    funding_owner: Ownership = Ownership.UNKNOWN
    policy_owner: Ownership = Ownership.UNKNOWN
    identity_owner: Ownership = Ownership.UNKNOWN
    agent_delivery_owner: Ownership = Ownership.UNKNOWN
    runtime_operations_owner: Ownership = Ownership.UNKNOWN
    incident_accountability: Ownership = Ownership.UNKNOWN


class RiskInput(BaseModel):
    autonomy: Autonomy = Autonomy.UNKNOWN
    failure_impact: Impact = Impact.UNKNOWN
    reversible_actions: bool | None = None
    human_approval_required: bool | None = None
    regulator_facing_audit: bool | None = None


class DataComplianceInput(BaseModel):
    classifications: list[DataClass] = Field(default_factory=list)
    residency: Residency = Residency.UNKNOWN
    regulations: list[str] = Field(default_factory=list)
    data_locations: list[str] = Field(default_factory=list)
    crosses_trust_boundaries: bool | None = None


class NfrInput(BaseModel):
    tenant_isolation: Isolation = Isolation.UNKNOWN
    availability_pct: float | None = Field(default=None, ge=0, le=100)
    p95_latency_ms: int | None = Field(default=None, ge=0)
    rto_hours: float | None = Field(default=None, ge=0)
    rpo_hours: float | None = Field(default=None, ge=0)
    regions: int | None = Field(default=None, ge=1)


class CurrentCapabilities(BaseModel):
    maturity: Maturity = Maturity.GREENFIELD
    identity: Literal["oidc", "iam", "multiple_idps", "greenfield"] = "greenfield"
    observability: Literal["enterprise", "cloud_native", "fragmented", "greenfield"] = "greenfield"
    cicd: Literal["standardized", "team_specific", "manual", "greenfield"] = "greenfield"
    reusable_gateway: bool = False
    reusable_data_platform: bool = False


class EconomicsInput(BaseModel):
    monthly_budget_usd: float | None = Field(default=None, ge=0)
    target_months: int | None = Field(default=None, ge=1)
    priority: Literal["cost", "performance", "predictability", "outcomes", "unknown"] = "unknown"


class AssessmentInput(BaseModel):
    schema_version: Literal["2.0"] = "2.0"
    audience: Audience
    primary_workload: Workload
    secondary_workloads: list[Workload] = Field(default_factory=list)
    ownership: OwnershipInput
    risk: RiskInput
    data: DataComplianceInput
    nfr: NfrInput
    current: CurrentCapabilities = Field(default_factory=CurrentCapabilities)
    economics: EconomicsInput = Field(default_factory=EconomicsInput)
    workload_profile: WorkloadProfile

    @model_validator(mode="after")
    def workload_matches_profile(self) -> "AssessmentInput":
        if self.primary_workload.value != self.workload_profile.kind:
            raise ValueError("primary_workload must match workload_profile.kind")
        if self.primary_workload in self.secondary_workloads:
            raise ValueError("primary_workload cannot also be a secondary workload")
        return self


class EvidenceGap(BaseModel):
    field: str
    reason: str
    critical: bool = True
    question_id: str | None = None


class TraceRecord(BaseModel):
    decision: str
    rule_id: str
    evidence: list[str]
    outcome: str


class CapabilityOwnership(BaseModel):
    capability: str
    owner: Ownership
    evidence: list[str]


class Requirement(BaseModel):
    id: str
    category: str
    statement: str
    evidence: list[str]
    hard: bool = False


class TopologyDecision(BaseModel):
    control_plane: str
    runtime_placement: str
    isolation_boundary: str
    regional_model: str
    modifiers: list[str] = Field(default_factory=list)


class ComponentDecision(BaseModel):
    id: str
    name: str
    layer: str
    scope: str
    activation_requirements: list[str]
    dependencies: list[str] = Field(default_factory=list)
    aws_services: list[str] = Field(default_factory=list)


class ControlDecision(BaseModel):
    id: str
    name: str
    source: str
    implementation: str
    requirement_ids: list[str] = Field(default_factory=list)


class RiskDecision(BaseModel):
    id: str
    scenario: str
    inherent: Impact
    exposure: str
    controls: list[str]
    residual: Impact
    owner: Ownership
    treatment: str


class RoadmapPhase(BaseModel):
    id: str
    name: str
    duration_weeks: tuple[int, int]
    component_ids: list[str]
    exit_criteria: list[str]
    dependencies: list[str] = Field(default_factory=list)


class CostScenario(BaseModel):
    monthly_usd: float
    annual_usd: float


class CostEstimate(BaseModel):
    currency: Literal["USD"] = "USD"
    price_catalog_date: str
    low: CostScenario
    base: CostScenario
    high: CostScenario
    assumptions: list[str]
    line_items: list[dict]


class OverrideRecord(BaseModel):
    decision_path: str
    engine_value: str
    override_value: str
    rationale: str = Field(min_length=10)
    author: str
    timestamp: str


class AssessmentResult(BaseModel):
    schema_version: Literal["2.0"] = "2.0"
    methodology_version: str
    catalog_version: str
    status: Literal["needs_information", "complete", "overridden"]
    evidence_coverage: float = Field(ge=0, le=1)
    missing_evidence: list[EvidenceGap] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    ownership_matrix: list[CapabilityOwnership] = Field(default_factory=list)
    operating_model: str | None = None
    requirements: list[Requirement] = Field(default_factory=list)
    topology: TopologyDecision | None = None
    components: list[ComponentDecision] = Field(default_factory=list)
    controls: list[ControlDecision] = Field(default_factory=list)
    risks: list[RiskDecision] = Field(default_factory=list)
    roadmap: list[RoadmapPhase] = Field(default_factory=list)
    cost: CostEstimate | None = None
    trace: list[TraceRecord] = Field(default_factory=list)
    overrides: list[OverrideRecord] = Field(default_factory=list)
