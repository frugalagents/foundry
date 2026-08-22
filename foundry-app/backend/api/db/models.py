"""Pydantic models for API request/response bodies."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── Customers ────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str


class CustomerUpdate(BaseModel):
    name: Optional[str] = None


class Customer(BaseModel):
    customer_id: str
    name: str
    created_by: str
    created_at: str
    updated_at: str
    demo_data: Optional[bool] = None


# ── Sessions ──────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    module_id: Optional[str] = None


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    module_id: Optional[str] = None
    status: Optional[str] = None
    current_step: Optional[int] = Field(default=None, ge=0)
    recommendation: Optional[str] = None
    evidence_state: Optional[str] = None


class Session(BaseModel):
    session_id: str
    customer_id: str
    module_id: Optional[str] = None
    title: str
    description: str = ""
    status: str = "active"
    current_step: int = 0
    recommendation: Optional[str] = None
    evidence_state: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str


# ── Modules ────────────────────────────────────────────────────────────────────

class Module(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    color: str


# ── Stream ────────────────────────────────────────────────────────────────────

class StreamRequest(BaseModel):
    message: str


# ── History (messages + canvas persisted by the agent runtime) ────────────────

class MessageOut(BaseModel):
    role: str
    content: str
    created_at: str


class CanvasOut(BaseModel):
    nodes: list = Field(default_factory=list)
    edges: list = Field(default_factory=list)
    stage: str = ""
    baseline_node_ids: list[str] = Field(default_factory=list)
    architecture_artifact: Optional["ArchitectureArtifactOut"] = None
    updated_at: Optional[str] = None


class ConsultingAssumptionOptionOut(BaseModel):
    id: str
    label: str
    prompt: str


class ConsultingAssumptionOut(BaseModel):
    id: str
    title: str
    assumed: str
    why: str = ""
    impact: str = ""
    confidence: str = "default"
    impact_level: str = ""
    drives_architecture: bool = False
    validation_priority: str = ""
    options: list[ConsultingAssumptionOptionOut] = Field(default_factory=list)


class AdvisoryRecommendationOut(BaseModel):
    summary: str = ""
    why_this: str = ""
    why_not: str = ""
    confidence: str = ""
    confidence_reason: str = ""
    change_triggers: list[str] = Field(default_factory=list)


class AdvisoryAlternativeOut(BaseModel):
    id: str
    title: str
    position: str = ""
    summary: str = ""
    benefits: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    operational_burden: str = ""
    governance_implications: str = ""
    best_fit_conditions: list[str] = Field(default_factory=list)


class AdvisoryDecisionOut(BaseModel):
    statement: str
    options_considered: list[str] = Field(default_factory=list)
    recommendation: str = ""
    why: str = ""
    tradeoffs_accepted: list[str] = Field(default_factory=list)
    owner: str = ""
    open_dependency: str = ""


class AdvisoryRiskOut(BaseModel):
    category: str = ""
    severity: str = ""
    risk: str
    mitigation: str = ""


class AdvisoryMaturityDomainOut(BaseModel):
    domain: str
    current_state: str = ""
    target_state: str = ""
    gap: str = ""


class AdvisoryReadoutOut(BaseModel):
    current_recommendation: str = ""
    important_decisions: list[str] = Field(default_factory=list)
    biggest_risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    rollout_summary: str = ""
    architecture_snapshot: str = ""


class AdvisoryNextBestQuestionOut(BaseModel):
    question: str = ""
    why_it_matters: str = ""


class AdvisoryPackRiskOut(BaseModel):
    risk: str
    mitigation: str = ""


class AdvisoryPackRolloutPhaseOut(BaseModel):
    horizon: str
    outcome: str = ""


class AdvisoryOutputPackOut(BaseModel):
    executive_summary: str = ""
    recommendation_memo: str = ""
    architecture_narrative: str = ""
    key_decisions: list[str] = Field(default_factory=list)
    risks_and_mitigations: list[AdvisoryPackRiskOut] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    rollout_30_90_180: list[AdvisoryPackRolloutPhaseOut] = Field(default_factory=list)
    operating_principles: list[str] = Field(default_factory=list)
    control_checklist: list[str] = Field(default_factory=list)


class AdvisoryDeltaOut(BaseModel):
    summary: str = ""
    recommendation_change: str = ""
    new_risks: list[str] = Field(default_factory=list)
    added_controls: list[str] = Field(default_factory=list)
    removed_controls: list[str] = Field(default_factory=list)
    cost_or_complexity_impact: str = ""
    changed_assumptions: list[str] = Field(default_factory=list)


class AdvisoryCaseOut(BaseModel):
    recommendation: AdvisoryRecommendationOut = Field(default_factory=AdvisoryRecommendationOut)
    alternatives: list[AdvisoryAlternativeOut] = Field(default_factory=list)
    decisions: list[AdvisoryDecisionOut] = Field(default_factory=list)
    risks: list[AdvisoryRiskOut] = Field(default_factory=list)
    maturity: list[AdvisoryMaturityDomainOut] = Field(default_factory=list)
    readout: AdvisoryReadoutOut = Field(default_factory=AdvisoryReadoutOut)
    next_best_question: Optional[AdvisoryNextBestQuestionOut] = None
    output_pack: AdvisoryOutputPackOut = Field(default_factory=AdvisoryOutputPackOut)
    delta: Optional[AdvisoryDeltaOut] = None


class ConsultingWorkspaceOut(BaseModel):
    stage: str = ""
    recommendation: str = ""
    blueprint_markdown: str = ""
    assumptions: list[ConsultingAssumptionOut] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    implementation_plan: list[str] = Field(default_factory=list)
    advisory_case: Optional[AdvisoryCaseOut] = None
    updated_at: Optional[str] = None


class SessionHistory(BaseModel):
    messages: list[MessageOut]
    canvas: Optional[CanvasOut] = None
    workspace: Optional[ConsultingWorkspaceOut] = None


class ArchitectureLayerSummaryOut(BaseModel):
    id: str
    label: str
    purpose: str = ""
    component_ids: list[str] = Field(default_factory=list)
    component_labels: list[str] = Field(default_factory=list)


class ArchitectureBaselineOut(BaseModel):
    name: str = ""
    layers: list[ArchitectureLayerSummaryOut] = Field(default_factory=list)


class ArchitectureCustomizationOut(BaseModel):
    id: str
    title: str
    layer: str = ""
    added_component_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    tradeoff: str = ""
    triggered_by: list[str] = Field(default_factory=list)


class ArchitectureDecisionRationaleOut(BaseModel):
    decision: str
    why: str = ""
    alternatives_rejected: list[str] = Field(default_factory=list)


class ArchitectureRiskOut(BaseModel):
    risk: str
    mitigation: str = ""


class ArchitectureRolloutPhaseOut(BaseModel):
    phase: str
    outcome: str = ""


class ArchitectureArtifactOut(BaseModel):
    executive_summary: str = ""
    baseline: ArchitectureBaselineOut = Field(default_factory=ArchitectureBaselineOut)
    customizations: list[ArchitectureCustomizationOut] = Field(default_factory=list)
    decisions: list[ArchitectureDecisionRationaleOut] = Field(default_factory=list)
    risks: list[ArchitectureRiskOut] = Field(default_factory=list)
    rollout: list[ArchitectureRolloutPhaseOut] = Field(default_factory=list)


CanvasOut.model_rebuild()
