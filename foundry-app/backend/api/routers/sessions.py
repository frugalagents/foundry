"""Session CRUD endpoints."""
from __future__ import annotations
import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, status

from api.middleware.auth import (
    authorize_owned_resource,
    get_current_user,
    get_user_id,
    is_admin,
)
from api.db import dynamodb as db
from api.db.models import (
    CanvasOut,
    ConsultingWorkspaceOut,
    MessageOut,
    Session,
    SessionCreate,
    SessionFeedbackIn,
    SessionFeedbackOut,
    SessionHistory,
    SessionUpdate,
)

router = APIRouter(prefix="/customers/{customer_id}/sessions", tags=["sessions"])

CurrentUser = Annotated[dict, Depends(get_current_user)]


def _get_customer(customer_id: str, user: dict, *, write: bool = False) -> dict:
    return authorize_owned_resource(
        user, db.get_customer(customer_id), resource_name="Customer", write=write
    )


def _get_session(customer_id: str, session_id: str, user: dict, *, write: bool = False) -> dict:
    _get_customer(customer_id, user, write=write)
    return authorize_owned_resource(
        user, db.get_session(customer_id, session_id), resource_name="Session", write=write
    )


@router.get("", response_model=list[Session])
async def list_sessions(customer_id: str, user: CurrentUser):
    customer = _get_customer(customer_id, user)
    actor_id = get_user_id(user)
    shared = customer.get("demo_data") is True
    items = db.list_sessions(
        customer_id,
        created_by=None if (is_admin(user) or shared) else actor_id,
    )
    if not is_admin(user) and not shared:
        items = [i for i in items if i.get("created_by") == actor_id]
    return [_to_session(i) for i in items]


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_session(customer_id: str, body: SessionCreate, user: CurrentUser):
    _get_customer(customer_id, user, write=True)
    item = db.create_session(
        customer_id=customer_id,
        created_by=get_user_id(user),
        title=body.title or "",
        description=body.description or "",
        module_id=body.module_id,
    )
    return _to_session(item)


@router.get("/{session_id}", response_model=Session)
async def get_session(customer_id: str, session_id: str, user: CurrentUser):
    item = _get_session(customer_id, session_id, user)
    return _to_session(item)


@router.patch("/{session_id}", response_model=Session)
async def update_session(
    customer_id: str, session_id: str, body: SessionUpdate, user: CurrentUser
):
    _get_session(customer_id, session_id, user, write=True)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    item = db.update_session(customer_id, session_id, updates, owner_id=get_user_id(user))
    if not item:
        raise HTTPException(status_code=404, detail="Session not found")
    return _to_session(item)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(customer_id: str, session_id: str, user: CurrentUser):
    _get_session(customer_id, session_id, user, write=True)
    if not db.delete_session(customer_id, session_id, owner_id=get_user_id(user)):
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/{session_id}/history", response_model=SessionHistory)
async def get_session_history(customer_id: str, session_id: str, user: CurrentUser):
    _get_session(customer_id, session_id, user)
    messages = db.list_messages(customer_id, session_id)
    canvas_item = db.get_canvas(customer_id, session_id)
    workspace_item = db.get_workspace(customer_id, session_id)
    canvas = None
    workspace = None
    if canvas_item:
        artifact = None
        if canvas_item.get("architecture_artifact_json"):
            artifact = json.loads(canvas_item.get("architecture_artifact_json") or "{}")
        canvas = CanvasOut(
            nodes=json.loads(canvas_item.get("nodes_json") or "[]"),
            edges=json.loads(canvas_item.get("edges_json") or "[]"),
            stage=canvas_item.get("stage") or "",
            baseline_node_ids=json.loads(canvas_item.get("baseline_node_ids_json") or "[]"),
            architecture_artifact=artifact,
            updated_at=canvas_item.get("updated_at"),
        )
    if workspace_item:
        assumptions = []
        advisory_case = None
        if workspace_item.get("assumptions_json"):
            assumptions = json.loads(workspace_item.get("assumptions_json") or "[]")
        if workspace_item.get("advisory_case_json"):
            advisory_case = json.loads(workspace_item.get("advisory_case_json") or "{}")
        workspace = ConsultingWorkspaceOut(
            stage=workspace_item.get("stage") or "",
            recommendation=workspace_item.get("recommendation") or "",
            blueprint_markdown=workspace_item.get("blueprint_markdown") or "",
            assumptions=assumptions,
            facts=workspace_item.get("facts") or [],
            operating_model=workspace_item.get("operating_model") or "",
            open_questions=workspace_item.get("open_questions") or [],
            decisions=workspace_item.get("decisions") or [],
            risks=workspace_item.get("risks") or [],
            implementation_plan=workspace_item.get("implementation_plan") or [],
            advisory_case=advisory_case,
            updated_at=workspace_item.get("updated_at"),
        )
    return SessionHistory(
        messages=[
            MessageOut(
                role=m.get("role", ""),
                content=m.get("content", ""),
                created_at=m.get("created_at", ""),
            )
            for m in messages
        ],
        canvas=canvas,
        workspace=workspace,
    )


@router.get("/{session_id}/feedback", response_model=SessionFeedbackOut | None)
async def get_session_feedback(customer_id: str, session_id: str, user: CurrentUser):
    _get_session(customer_id, session_id, user)
    item = db.get_session_feedback(customer_id, session_id, get_user_id(user))
    return _to_feedback(item) if item else None


@router.post("/{session_id}/feedback", response_model=SessionFeedbackOut)
async def upsert_session_feedback(
    customer_id: str,
    session_id: str,
    body: SessionFeedbackIn,
    user: CurrentUser,
):
    _get_session(customer_id, session_id, user)
    item = db.upsert_session_feedback(
        customer_id,
        session_id,
        get_user_id(user),
        _display_name(user),
        body.model_dump(),
    )
    return _to_feedback(item)


def _display_name(user: dict) -> str:
    return (
        str(user.get("name") or "").strip()
        or str(user.get("email") or "").strip()
        or str(user.get("cognito:username") or "").strip()
        or get_user_id(user)
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
