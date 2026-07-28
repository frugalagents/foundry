"""Pydantic models for API request/response bodies."""
from __future__ import annotations
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


# ── Customers ────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str
    industry: str
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class Customer(BaseModel):
    customer_id: str
    name: str
    industry: str
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str
    session_count: int = 0


# ── Sessions ──────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=500)


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=500)
    status: Optional[str] = None
    current_step: Optional[int] = Field(default=None, ge=0, le=10)
    recommendation: Optional[str] = None
    evidence_state: Optional[str] = None


class Session(BaseModel):
    session_id: str
    customer_id: str
    title: str
    description: str = ""
    status: str = "active"
    current_step: int = 0
    intake_answers: Optional[dict] = None
    primary_workload: Optional[str] = None
    recommendation: Optional[str] = None
    evidence_state: str = "not_started"
    created_by: str
    created_at: str
    updated_at: str


# ── Panel States ──────────────────────────────────────────────────────────────

class PanelStateUpdate(BaseModel):
    step: int
    panel_type: str
    data: dict[str, Any]


# ── Stream ────────────────────────────────────────────────────────────────────

class StreamStartRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    industry: str = ""
    pain_points: list[str] = Field(default_factory=list)


class ConfirmationRequest(BaseModel):
    choice: str


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminMetrics(BaseModel):
    total_customers: int
    total_sessions: int
    active_sessions: int
    sessions_today: int
    top_patterns: list[dict]
    top_industries: list[dict]


class GraphConfigUpdate(BaseModel):
    node_id: str
    props: dict[str, Any]
