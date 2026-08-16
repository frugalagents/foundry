"""Module registry endpoint — returns available Foundry platform modules."""
from __future__ import annotations
import os
import json
import logging
from typing import Annotated

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends

from api.middleware.auth import get_current_user
from api.db.models import Module

router = APIRouter(prefix="/modules", tags=["modules"])

CurrentUser = Annotated[dict, Depends(get_current_user)]

logger = logging.getLogger(__name__)

# ── Default module registry ───────────────────────────────────────────────────
# Loaded from DynamoDB CONFIG#MODULES if present; falls back to this static list.

_DEFAULTS: list[dict] = [
    {
        "id": "coding-agent",
        "name": "Coding Agent Platform",
        "description": "Design and deploy an enterprise coding agent platform — harness, execution, gateway, access, and ops.",
        "icon": "Code2",
        "color": "#6366f1",
    },
    {
        "id": "product-platform",
        "name": "Product Platform",
        "description": "AI-powered product discovery, roadmapping, and delivery intelligence for enterprise teams.",
        "icon": "Package",
        "color": "#22c55e",
    },
    {
        "id": "fabric",
        "name": "Fabric",
        "description": "Multi-cloud AI fabric — unified model gateway, policy enforcement, and cross-provider orchestration.",
        "icon": "Network",
        "color": "#f59e0b",
    },
]

_TABLE = os.environ.get("DYNAMODB_TABLE", "foundry-app-main")
_REGION = os.environ.get("AWS_REGION", "us-east-1")
_cached: list[dict] | None = None


def _load_from_ddb() -> list[dict] | None:
    global _cached
    if _cached is not None:
        return _cached
    try:
        table = boto3.resource("dynamodb", region_name=_REGION).Table(_TABLE)
        resp = table.get_item(Key={"PK": "CONFIG#MODULES", "SK": "MODULES#v1"})
        item = resp.get("Item")
        if item and isinstance(item.get("modules"), list):
            _cached = item["modules"]
            return _cached
    except Exception as exc:
        logger.debug("Could not load modules from DynamoDB: %s", exc)
    return None


@router.get("", response_model=list[Module])
async def list_modules(user: CurrentUser):
    modules = _load_from_ddb() or _DEFAULTS
    return [Module(**m) for m in modules]
