"""Admin-only session inventory and analytics endpoints."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.middleware.auth import get_current_user, is_admin
from api.db import dynamodb as db
from api.db.models import (
    AdminAnalyticsOut,
    AdminCountOut,
    AdminFeedbackRowOut,
    AdminRecentActivityOut,
    ConversationRowOut,
    Customer,
    Session,
    SessionFeedbackOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])

CurrentUser = Annotated[dict, Depends(get_current_user)]


@router.get("/sessions", response_model=list[ConversationRowOut])
async def list_admin_sessions(user: CurrentUser):
    _require_admin(user)
    rows = _load_all_session_rows()
    rows.sort(key=lambda row: row.session.updated_at, reverse=True)
    return rows


@router.get("/feedback", response_model=list[AdminFeedbackRowOut])
async def list_admin_feedback(user: CurrentUser):
    _require_admin(user)

    rows_by_key = {
        (row.customer.customer_id, row.session.session_id): row
        for row in _load_all_session_rows()
    }
    items = db.list_all_feedback()
    rows: list[AdminFeedbackRowOut] = []

    for item in items:
        key = (item.get("customer_id", ""), item.get("session_id", ""))
        row = rows_by_key.get(key)
        if not row:
            continue
        rows.append(
            AdminFeedbackRowOut(
                customer=row.customer,
                session=row.session,
                feedback=_to_feedback(item),
            )
        )

    rows.sort(key=lambda row: row.feedback.updated_at, reverse=True)
    return rows


@router.get("/analytics", response_model=AdminAnalyticsOut)
async def get_admin_analytics(user: CurrentUser):
    _require_admin(user)

    customers = [_to_customer(item) for item in db.list_customers(created_by=None, include_demo=True)]
    session_rows = _load_all_session_rows(customers)
    feedback_items = db.list_all_feedback()
    workspace_items = db.list_workspaces()
    canvas_items = db.list_canvases()

    unique_users = {
        row.session.created_by
        for row in session_rows
        if row.session.created_by
    }
    unique_users.update(
        item.get("user_id", "")
        for item in feedback_items
        if item.get("user_id")
    )

    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=7)
    active_sessions_7d = 0
    for row in session_rows:
        updated_at = _parse_iso(row.session.updated_at)
        if updated_at and updated_at >= recent_cutoff:
            active_sessions_7d += 1

    feedback_scores = [int(item.get("rating") or 0) for item in feedback_items if item.get("rating") is not None]
    average_feedback_score = round(sum(feedback_scores) / len(feedback_scores), 1) if feedback_scores else 0.0

    module_counts = Counter(
        row.session.module_id or "unassigned"
        for row in session_rows
    )
    customer_counts = Counter(
        row.customer.name or row.customer.customer_id
        for row in session_rows
    )
    stage_counts = Counter(
        (item.get("stage") or "unknown").strip() or "unknown"
        for item in workspace_items
    )

    sessions_with_workspace = {
        item.get("session_id", "")
        for item in workspace_items
        if item.get("session_id")
    }
    sessions_with_architecture = {
        item.get("session_id", "")
        for item in canvas_items
        if item.get("session_id")
    }
    stage_by_session = {
        item.get("session_id", ""): item.get("stage") or ""
        for item in workspace_items
        if item.get("session_id")
    }

    recent_activity = [
        AdminRecentActivityOut(
            customer_id=row.customer.customer_id,
            customer_name=row.customer.name,
            session_id=row.session.session_id,
            session_title=row.session.title,
            created_by=row.session.created_by,
            updated_at=row.session.updated_at,
            status=row.session.status,
            module_id=row.session.module_id,
            stage=stage_by_session.get(row.session.session_id, ""),
        )
        for row in sorted(session_rows, key=lambda entry: entry.session.updated_at, reverse=True)[:12]
    ]

    return AdminAnalyticsOut(
        total_customers=len(customers),
        total_sessions=len(session_rows),
        unique_users=len(unique_users),
        active_sessions_7d=active_sessions_7d,
        sessions_with_workspace=len(sessions_with_workspace),
        sessions_with_architecture=len(sessions_with_architecture),
        feedback_submissions=len(feedback_items),
        average_feedback_score=average_feedback_score,
        module_breakdown=_top_counts(module_counts),
        stage_breakdown=_top_counts(stage_counts),
        top_customers=_top_counts(customer_counts),
        recent_activity=recent_activity,
    )


def _require_admin(user: dict) -> None:
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def _load_all_session_rows(customers: list[Customer] | None = None) -> list[ConversationRowOut]:
    if customers is None:
        customers = [_to_customer(item) for item in db.list_customers(created_by=None, include_demo=True)]
    rows: list[ConversationRowOut] = []
    for customer in customers:
        for session_item in db.list_sessions(customer.customer_id, created_by=None):
            rows.append(
                ConversationRowOut(
                    customer=customer,
                    session=_to_session(session_item),
                )
            )
    return rows


def _top_counts(counter: Counter[str], limit: int = 8) -> list[AdminCountOut]:
    return [
        AdminCountOut(label=label, value=value)
        for label, value in counter.most_common(limit)
    ]


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_customer(item: dict) -> Customer:
    return Customer(
        customer_id=item["customer_id"],
        name=item["name"],
        created_by=item.get("created_by", ""),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
        demo_data=item.get("demo_data"),
    )


def _to_session(item: dict) -> Session:
    return Session(
        session_id=item["session_id"],
        customer_id=item["customer_id"],
        module_id=item.get("module_id"),
        title=item.get("title") or "New conversation",
        description=item.get("description") or "",
        status=item.get("status", "active"),
        current_step=int(item.get("current_step") or 0),
        recommendation=item.get("recommendation"),
        evidence_state=item.get("evidence_state"),
        created_by=item.get("created_by", ""),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
    )


def _to_feedback(item: dict) -> SessionFeedbackOut:
    return SessionFeedbackOut(
        customer_id=item["customer_id"],
        session_id=item["session_id"],
        user_id=item.get("user_id", ""),
        user_name=item.get("user_name", ""),
        rating=int(item.get("rating") or 0),
        most_useful=item.get("most_useful") or "",
        missing=item.get("missing") or "",
        additional_comments=item.get("additional_comments") or "",
        reused_in_doc_or_meeting=item.get("reused_in_doc_or_meeting"),
        agreed_with_recommendation=item.get("agreed_with_recommendation"),
        would_reuse=item.get("would_reuse"),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
    )
