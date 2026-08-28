"""Pydantic models for API request/response bodies."""
from __future__ import annotations
from typing import Any, Optional
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


class ConversationRowOut(BaseModel):
    session: Session
    customer: Customer


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
    architecture_artifact: Optional[dict[str, Any]] = None
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
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    operating_model: str = ""
    question_state: list[dict[str, Any]] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    implementation_plan: list[str] = Field(default_factory=list)
    advisory_case: Optional[dict[str, Any]] = None
    architecture_case: Optional[dict[str, Any]] = None
    recommendation_state: Optional[dict[str, Any]] = None
    artifact_status: Optional[dict[str, Any]] = None
    updated_at: Optional[str] = None


class SessionHistory(BaseModel):
    messages: list[MessageOut]
    canvas: Optional[CanvasOut] = None
    workspace: Optional[ConsultingWorkspaceOut] = None


class SessionFeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    most_useful: str = Field(default="", max_length=2000)
    missing: str = Field(default="", max_length=2000)
    additional_comments: str = Field(default="", max_length=4000)
    reused_in_doc_or_meeting: Optional[bool] = None
    agreed_with_recommendation: Optional[bool] = None
    would_reuse: Optional[bool] = None


class SessionFeedbackOut(BaseModel):
    customer_id: str
    session_id: str
    user_id: str
    user_name: str = ""
    rating: int
    most_useful: str = ""
    missing: str = ""
    additional_comments: str = ""
    reused_in_doc_or_meeting: Optional[bool] = None
    agreed_with_recommendation: Optional[bool] = None
    would_reuse: Optional[bool] = None
    created_at: str
    updated_at: str


class AdminFeedbackRowOut(BaseModel):
    customer: Customer
    session: Session
    feedback: SessionFeedbackOut


class JudgeDeterministicFindingOut(BaseModel):
    component: str = ""
    severity: str = ""
    title: str = ""
    detail: str = ""


class JudgeRecommendationReviewOut(BaseModel):
    score: int = 0
    is_correct_for_customer: Optional[bool] = None
    assessment: str = ""
    evidence: list[str] = Field(default_factory=list)


class JudgeArchitectureReviewOut(BaseModel):
    score: int = 0
    is_complete_enough: Optional[bool] = None
    assessment: str = ""
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class JudgeBlueprintReviewOut(BaseModel):
    score: int = 0
    is_complete_enough: Optional[bool] = None
    assessment: str = ""
    missing_elements: list[str] = Field(default_factory=list)


class JudgeUiAccuracyReviewOut(BaseModel):
    component: str = ""
    status: str = ""
    score: int = 0
    assessment: str = ""
    suggested_improvements: list[str] = Field(default_factory=list)


class JudgeOpenItemOut(BaseModel):
    severity: str = ""
    title: str = ""
    reason: str = ""
    suggested_fix: str = ""


class JudgeSuggestedFeatureOut(BaseModel):
    name: str = ""
    priority: str = ""
    why_it_matters: str = ""
    implementation_hint: str = ""


class JudgeReportOut(BaseModel):
    judge_report_id: str
    customer_id: str
    session_id: str
    session_title: str = ""
    simulation_file: str = ""
    overall_verdict: str = ""
    judge_confidence: str = ""
    summary: str = ""
    recommendation_review: JudgeRecommendationReviewOut = Field(default_factory=JudgeRecommendationReviewOut)
    architecture_review: JudgeArchitectureReviewOut = Field(default_factory=JudgeArchitectureReviewOut)
    blueprint_review: JudgeBlueprintReviewOut = Field(default_factory=JudgeBlueprintReviewOut)
    ui_accuracy_review: list[JudgeUiAccuracyReviewOut] = Field(default_factory=list)
    deterministic_findings: list[JudgeDeterministicFindingOut] = Field(default_factory=list)
    open_items: list[JudgeOpenItemOut] = Field(default_factory=list)
    suggested_features: list[JudgeSuggestedFeatureOut] = Field(default_factory=list)
    response_text: str = ""
    report_dir: str = ""
    created_at: str
    updated_at: str


class AdminJudgeReportRowOut(BaseModel):
    customer: Customer
    session: Session
    report: JudgeReportOut


class AdminCountOut(BaseModel):
    label: str
    value: int


class AdminRecentActivityOut(BaseModel):
    customer_id: str
    customer_name: str
    session_id: str
    session_title: str
    created_by: str
    updated_at: str
    status: str = ""
    module_id: Optional[str] = None
    stage: str = ""


class AdminAnalyticsOut(BaseModel):
    total_customers: int = 0
    total_sessions: int = 0
    unique_users: int = 0
    active_sessions_7d: int = 0
    sessions_with_workspace: int = 0
    sessions_with_architecture: int = 0
    feedback_submissions: int = 0
    average_feedback_score: float = 0.0
    module_breakdown: list[AdminCountOut] = Field(default_factory=list)
    stage_breakdown: list[AdminCountOut] = Field(default_factory=list)
    top_customers: list[AdminCountOut] = Field(default_factory=list)
    recent_activity: list[AdminRecentActivityOut] = Field(default_factory=list)


# ── Access requests ───────────────────────────────────────────────────────────

class AccessRequestCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=320)
    reason: str = Field(min_length=5, max_length=2000)
    website: str = Field(default="", max_length=200)


class AccessRequestCreatedOut(BaseModel):
    request_id: str
    request_secret: str
    status: str
    expires_at: str


class AccessRequestSecretIn(BaseModel):
    request_id: str = Field(min_length=8, max_length=80)
    request_secret: str = Field(min_length=32, max_length=200)


class AccessRequestActivateIn(AccessRequestSecretIn):
    password: str = Field(min_length=12, max_length=128)


class AccessRequestStatusOut(BaseModel):
    request_id: str
    email: str
    status: str
    requested_at: str
    updated_at: str
    expires_at: str
    decision_note: str = ""
    can_activate: bool = False


class AccessRequestDecisionIn(BaseModel):
    note: str = Field(default="", max_length=1000)


class AdminAccessRequestOut(BaseModel):
    request_id: str
    name: str
    email: str
    reason: str
    status: str
    requested_at: str
    updated_at: str
    expires_at: str
    decision_note: str = ""
    reviewed_by: str = ""
    reviewed_at: str = ""
    activated_at: str = ""


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
