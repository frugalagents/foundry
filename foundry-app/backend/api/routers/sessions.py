"""Session CRUD endpoints."""
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, status

from api.middleware.auth import (
    authorize_owned_resource,
    get_current_user,
    get_user_id,
    is_admin,
)
from api.db import dynamodb as db
from api.db.models import Session, SessionCreate, SessionUpdate

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
