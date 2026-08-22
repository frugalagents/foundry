"""Admin-only session inventory endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.middleware.auth import get_current_user, is_admin
from api.db import dynamodb as db
from api.db.models import ConversationRowOut, Customer, Session

router = APIRouter(prefix="/admin", tags=["admin"])

CurrentUser = Annotated[dict, Depends(get_current_user)]


@router.get("/sessions", response_model=list[ConversationRowOut])
async def list_admin_sessions(user: CurrentUser):
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    customers = db.list_customers(created_by=None, include_demo=True)
    rows: list[ConversationRowOut] = []

    for customer_item in customers:
        customer = _to_customer(customer_item)
        for session_item in db.list_sessions(customer.customer_id, created_by=None):
            rows.append(
                ConversationRowOut(
                    customer=customer,
                    session=_to_session(session_item),
                ),
            )

    rows.sort(key=lambda row: row.session.updated_at, reverse=True)
    return rows


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
