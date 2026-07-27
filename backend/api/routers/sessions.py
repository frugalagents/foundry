"""Session CRUD + panel state endpoints."""
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, status

from api.middleware.auth import get_current_user, get_user_id
from api.db import dynamodb as db
from api.db.models import Session, SessionCreate, SessionUpdate, PanelStateUpdate

router = APIRouter(prefix="/customers/{customer_id}/sessions", tags=["sessions"])

CurrentUser = Annotated[dict, Depends(get_current_user)]


@router.get("", response_model=list[Session])
async def list_sessions(customer_id: str, user: CurrentUser):
    items = db.list_sessions(customer_id)
    return [_to_session(i) for i in items]


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_session(customer_id: str, body: SessionCreate, user: CurrentUser):
    # Verify customer exists
    cust = db.get_customer(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    item = db.create_session(
        customer_id=customer_id,
        created_by=get_user_id(user),
        title=body.title or "",
        notes=body.notes or "",
    )
    return _to_session(item)


@router.get("/{session_id}", response_model=Session)
async def get_session(customer_id: str, session_id: str, user: CurrentUser):
    item = db.get_session(customer_id, session_id)
    if not item:
        raise HTTPException(status_code=404, detail="Session not found")
    return _to_session(item)


@router.patch("/{session_id}", response_model=Session)
async def update_session(customer_id: str, session_id: str,
                         body: SessionUpdate, user: CurrentUser):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    item = db.update_session(customer_id, session_id, updates)
    if not item:
        raise HTTPException(status_code=404, detail="Session not found")
    return _to_session(item)


@router.get("/{session_id}/panels")
async def get_panel_states(customer_id: str, session_id: str, user: CurrentUser):
    panels = db.get_panel_states(session_id)
    return {"panels": panels}


@router.put("/{session_id}/panels/{step}")
async def save_panel_state(customer_id: str, session_id: str,
                           step: int, body: PanelStateUpdate, user: CurrentUser):
    db.save_panel_state(session_id, step, body.panel_type, body.data)
    return {"ok": True}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(customer_id: str, session_id: str, user: CurrentUser):
    ok = db.delete_session(customer_id, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")


@router.put("/{session_id}/inputs", status_code=status.HTTP_204_NO_CONTENT)
async def save_inputs(customer_id: str, session_id: str, body: dict, user: CurrentUser):
    """Persist intake answers for a session."""
    answers = body.get("answers", {})
    db.update_session(customer_id, session_id, {"intake_answers": answers})


def _to_session(item: dict) -> Session:
    return Session(
        session_id=item["session_id"],
        customer_id=item["customer_id"],
        title=item.get("title", "Untitled"),
        status=item.get("status", "active"),
        current_step=int(item.get("current_step", 0)),
        notes=item.get("notes"),
        intake_answers=item.get("intake_answers"),
        created_by=item.get("created_by", ""),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
    )
