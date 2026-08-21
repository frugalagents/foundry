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
    options: list[ConsultingAssumptionOptionOut] = Field(default_factory=list)


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
