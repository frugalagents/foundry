"""Public access requests and admin approval workflow."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.db import dynamodb as db
from api.db.models import (
    AccessRequestActivateIn,
    AccessRequestCreate,
    AccessRequestCreatedOut,
    AccessRequestDecisionIn,
    AccessRequestSecretIn,
    AccessRequestStatusOut,
    AdminAccessRequestOut,
)
from api.middleware.auth import get_current_user, get_user_id, guest_access_window_closed, is_admin

logger = logging.getLogger(__name__)
router = APIRouter(tags=["access"])

CurrentUser = Annotated[dict, Depends(get_current_user)]

REGION = os.environ.get("COGNITO_REGION", "us-east-1")
USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
ACCESS_REQUEST_TOPIC_ARN = os.environ.get("ACCESS_REQUEST_TOPIC_ARN", "")
GUEST_GROUP_NAME = os.environ.get("GUEST_GROUP_NAME", "foundry-guests")
REQUEST_TTL_DAYS = 7
REQUEST_RATE_LIMIT_PER_HOUR = 3
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REQUEST_ID_PATTERN = re.compile(r"^req_[a-f0-9]{32}$")


@lru_cache(maxsize=1)
def _cognito_client():
    return boto3.client("cognito-idp", region_name=REGION)


@lru_cache(maxsize=1)
def _sns_client():
    return boto3.client("sns", region_name=REGION)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_email(value: str) -> str:
    normalized = _normalize_email(value)
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter a valid email address",
        )
    return normalized


def _validate_request_id(value: str) -> None:
    if not REQUEST_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_valid_secret(item: dict, request_secret: str) -> None:
    expected = str(item.get("request_secret_hash") or "")
    supplied = _hash_secret(request_secret)
    if not expected or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")


def _require_not_expired(item: dict) -> None:
    if int(item.get("expires_at_epoch") or 0) <= int(_now().timestamp()):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This access request expired. Submit a new request.",
        )


def _require_admin(user: dict) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def _require_guest_access_open() -> None:
    if guest_access_window_closed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest access for this event has ended",
        )


def _validate_password(value: str) -> None:
    missing: list[str] = []
    if len(value) < 12:
        missing.append("at least 12 characters")
    if not any(char.islower() for char in value):
        missing.append("a lowercase letter")
    if not any(char.isupper() for char in value):
        missing.append("an uppercase letter")
    if not any(char.isdigit() for char in value):
        missing.append("a number")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must contain {', '.join(missing)}",
        )


def _status_out(item: dict) -> AccessRequestStatusOut:
    return AccessRequestStatusOut(
        request_id=item["request_id"],
        email=item["email"],
        status=item["status"],
        requested_at=item["requested_at"],
        updated_at=item["updated_at"],
        expires_at=item["expires_at"],
        decision_note=item.get("decision_note", ""),
        can_activate=item.get("status") == "approved",
    )


def _admin_out(item: dict) -> AdminAccessRequestOut:
    return AdminAccessRequestOut(
        request_id=item["request_id"],
        name=item["name"],
        email=item["email"],
        reason=item["reason"],
        status=item["status"],
        requested_at=item["requested_at"],
        updated_at=item["updated_at"],
        expires_at=item["expires_at"],
        decision_note=item.get("decision_note", ""),
        reviewed_by=item.get("reviewed_by", ""),
        reviewed_at=item.get("reviewed_at", ""),
        activated_at=item.get("activated_at", ""),
    )


def _get_request(request_id: str) -> dict:
    _validate_request_id(request_id)
    item = db.get_access_request(request_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    return item


def _notify_admin(item: dict) -> None:
    if not ACCESS_REQUEST_TOPIC_ARN:
        return
    message = (
        "A user requested access to Enterprise AI Foundry.\n\n"
        f"Name: {item['name']}\n"
        f"Email: {item['email']}\n"
        f"Reason: {item['reason']}\n"
        f"Request ID: {item['request_id']}\n\n"
        "Sign in to Foundry and open Admin Console > Access requests to review it."
    )
    try:
        _sns_client().publish(
            TopicArn=ACCESS_REQUEST_TOPIC_ARN,
            Subject="Foundry access request",
            Message=message,
        )
    except ClientError:
        logger.exception("Failed to publish access request notification for %s", item["request_id"])


@router.post(
    "/access-requests",
    response_model=AccessRequestCreatedOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_access_request(body: AccessRequestCreate, request: Request):
    _require_guest_access_open()
    if body.website.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request could not be submitted")

    email = _validate_email(body.email)
    source = f"{request.client.host if request.client else ''}|{request.headers.get('user-agent', '')}"
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    one_hour_ago = _iso(_now() - timedelta(hours=1))
    if db.count_recent_access_requests(source_hash, one_hour_ago) >= REQUEST_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many access requests were submitted from this browser. Try again later.",
        )
    if db.find_open_access_request(email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An access request for this email is already awaiting activation",
        )

    now = _now()
    expires_at = now + timedelta(days=REQUEST_TTL_DAYS)
    request_id = f"req_{secrets.token_hex(16)}"
    request_secret = secrets.token_urlsafe(32)
    item = {
        "PK": f"ACCESS_REQUEST#{request_id}",
        "SK": f"ACCESS_REQUEST#{request_id}",
        "request_id": request_id,
        "request_secret_hash": _hash_secret(request_secret),
        "name": body.name.strip(),
        "email": email,
        "reason": body.reason.strip(),
        "status": "pending",
        "requested_at": _iso(now),
        "updated_at": _iso(now),
        "expires_at": _iso(expires_at),
        "expires_at_epoch": int(expires_at.timestamp()),
        "source_hash": source_hash,
    }
    db.create_access_request(item)
    _notify_admin(item)
    return AccessRequestCreatedOut(
        request_id=request_id,
        request_secret=request_secret,
        status="pending",
        expires_at=item["expires_at"],
    )


@router.post("/access-requests/status", response_model=AccessRequestStatusOut)
async def get_access_request_status(body: AccessRequestSecretIn):
    item = _get_request(body.request_id)
    _require_valid_secret(item, body.request_secret)
    _require_not_expired(item)
    return _status_out(item)


@router.post("/access-requests/activate", response_model=AccessRequestStatusOut)
async def activate_access_request(body: AccessRequestActivateIn):
    _require_guest_access_open()
    item = _get_request(body.request_id)
    _require_valid_secret(item, body.request_secret)
    _require_not_expired(item)
    if item.get("status") == "activated":
        return _status_out(item)
    if item.get("status") != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This access request is not ready for activation",
        )
    _validate_password(body.password)

    username = item.get("cognito_username")
    if not username or not USER_POOL_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The approved account is missing its Cognito identity",
        )

    _cognito_client().admin_set_user_password(
        UserPoolId=USER_POOL_ID,
        Username=username,
        Password=body.password,
        Permanent=True,
    )
    now = _iso(_now())
    updated = db.update_access_request(
        body.request_id,
        {
            "status": "activated",
            "activated_at": now,
            "updated_at": now,
        },
        expected_status="approved",
    )
    if not updated:
        latest = _get_request(body.request_id)
        if latest.get("status") == "activated":
            return _status_out(latest)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Access request changed while it was being activated",
        )
    return _status_out(updated)


@router.get("/admin/access-requests", response_model=list[AdminAccessRequestOut])
async def list_admin_access_requests(user: CurrentUser):
    _require_admin(user)
    return [_admin_out(item) for item in db.list_access_requests()]


@router.post(
    "/admin/access-requests/{request_id}/approve",
    response_model=AdminAccessRequestOut,
)
async def approve_access_request(
    request_id: str,
    body: AccessRequestDecisionIn,
    user: CurrentUser,
):
    _require_admin(user)
    item = _get_request(request_id)
    _require_not_expired(item)
    if item.get("status") in {"approved", "activated"}:
        return _admin_out(item)
    if item.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending access requests can be approved",
        )
    if not USER_POOL_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cognito user pool is not configured",
        )

    email = item["email"]
    existing = _cognito_client().list_users(
        UserPoolId=USER_POOL_ID,
        Filter=f'email = "{email}"',
        Limit=2,
    ).get("Users", [])
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A Cognito account already exists for this email",
        )

    temporary_password = f"Foundry-{secrets.token_hex(10)}Aa1!"
    created_username = ""
    try:
        created = _cognito_client().admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            TemporaryPassword=temporary_password,
            MessageAction="SUPPRESS",
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "name", "Value": item["name"]},
            ],
        )["User"]
        created_username = created["Username"]
        _cognito_client().admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=created_username,
            GroupName=GUEST_GROUP_NAME,
        )
        attributes = {
            attribute["Name"]: attribute["Value"]
            for attribute in created.get("Attributes", [])
        }
        now = _iso(_now())
        updated = db.update_access_request(
            request_id,
            {
                "status": "approved",
                "decision_note": body.note.strip(),
                "reviewed_by": get_user_id(user),
                "reviewed_at": now,
                "updated_at": now,
                "cognito_username": created_username,
                "cognito_sub": attributes.get("sub", created_username),
            },
            expected_status="pending",
        )
        if not updated:
            raise RuntimeError("Access request changed while it was being approved")
        return _admin_out(updated)
    except Exception:
        if created_username:
            try:
                _cognito_client().admin_delete_user(
                    UserPoolId=USER_POOL_ID,
                    Username=created_username,
                )
            except ClientError:
                logger.exception("Failed to roll back Cognito user %s", created_username)
        raise


@router.post(
    "/admin/access-requests/{request_id}/reject",
    response_model=AdminAccessRequestOut,
)
async def reject_access_request(
    request_id: str,
    body: AccessRequestDecisionIn,
    user: CurrentUser,
):
    _require_admin(user)
    item = _get_request(request_id)
    _require_not_expired(item)
    if item.get("status") == "rejected":
        return _admin_out(item)
    if item.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending access requests can be rejected",
        )
    now = _iso(_now())
    updated = db.update_access_request(
        request_id,
        {
            "status": "rejected",
            "decision_note": body.note.strip(),
            "reviewed_by": get_user_id(user),
            "reviewed_at": now,
            "updated_at": now,
        },
        expected_status="pending",
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Access request changed while it was being rejected",
        )
    return _admin_out(updated)
