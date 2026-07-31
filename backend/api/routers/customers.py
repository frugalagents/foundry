"""Customer CRUD endpoints."""
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
from api.db.models import Customer, CustomerCreate, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])

CurrentUser = Annotated[dict, Depends(get_current_user)]


@router.get("", response_model=list[Customer])
async def list_customers(user: CurrentUser):
    actor_id = get_user_id(user)
    items = db.list_customers(
        created_by=None if is_admin(user) else actor_id,
        include_demo=not is_admin(user),
    )
    if not is_admin(user):
        items = [
            item
            for item in items
            if item.get("created_by") == actor_id or item.get("demo_data") is True
        ]
    return [_to_customer(i) for i in items]


@router.post("", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer(body: CustomerCreate, user: CurrentUser):
    item = db.create_customer(
        name=body.name,
        industry=body.industry,
        contact_email=body.contact_email,
        created_by=get_user_id(user),
        notes=body.notes or "",
    )
    return _to_customer(item)


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str, user: CurrentUser):
    item = authorize_owned_resource(
        user,
        db.get_customer(customer_id),
        resource_name="Customer",
    )
    return _to_customer(item)


@router.patch("/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, body: CustomerUpdate, user: CurrentUser):
    authorize_owned_resource(
        user,
        db.get_customer(customer_id),
        resource_name="Customer",
        write=True,
    )
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    item = db.update_customer(customer_id, updates, owner_id=get_user_id(user))
    if not item:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _to_customer(item)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: str, user: CurrentUser):
    authorize_owned_resource(
        user,
        db.get_customer(customer_id),
        resource_name="Customer",
        write=True,
    )
    ok = db.delete_customer(customer_id, owner_id=get_user_id(user))
    if not ok:
        raise HTTPException(status_code=404, detail="Customer not found")


def _to_customer(item: dict) -> Customer:
    return Customer(
        customer_id=item["customer_id"],
        name=item["name"],
        industry=item["industry"],
        contact_email=item.get("contact_email"),
        notes=item.get("notes"),
        created_by=item.get("created_by", ""),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
        session_count=int(item.get("session_count", 0)),
    )
