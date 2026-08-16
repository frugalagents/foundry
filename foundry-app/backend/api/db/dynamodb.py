"""DynamoDB single-table operations for foundry-app."""
from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "foundry-app-main")
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT")  # local dev override

_dynamodb = None


def _get_table():
    global _dynamodb
    if _dynamodb is None:
        kwargs: dict = {"region_name": os.environ.get("AWS_REGION", "us-east-1")}
        if DYNAMODB_ENDPOINT:
            kwargs["endpoint_url"] = DYNAMODB_ENDPOINT
        _dynamodb = boto3.resource("dynamodb", **kwargs).Table(TABLE_NAME)
    return _dynamodb


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _is_conditional_failure(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


# ── Customers ─────────────────────────────────────────────────────────────────

def list_customers(
    created_by: str | None = None,
    include_demo: bool = True,
) -> list[dict]:
    table = _get_table()
    filter_parts = ["begins_with(SK, :sk_prefix)"]
    expr_values: dict[str, Any] = {":sk_prefix": "CUSTOMER#"}
    if created_by:
        filter_parts.append("created_by = :created_by")
        expr_values[":created_by"] = created_by
    if not include_demo:
        filter_parts.append("attribute_not_exists(demo_data) OR demo_data = :f")
        expr_values[":f"] = False

    resp = table.scan(
        FilterExpression=" AND ".join(filter_parts),
        ExpressionAttributeValues=expr_values,
    )
    return resp.get("Items", [])


def create_customer(name: str, created_by: str) -> dict:
    table = _get_table()
    now = _now()
    customer_id = _new_id("cust")
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"CUSTOMER#{customer_id}",
        "customer_id": customer_id,
        "name": name,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    table.put_item(Item=item)
    return item


def get_customer(customer_id: str) -> dict | None:
    table = _get_table()
    resp = table.get_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"CUSTOMER#{customer_id}"}
    )
    return resp.get("Item")


def update_customer(
    customer_id: str,
    updates: dict[str, Any],
    owner_id: str | None = None,
) -> dict | None:
    table = _get_table()
    updates["updated_at"] = _now()
    set_parts = [f"#f_{k} = :v_{k}" for k in updates]
    expr_names = {f"#f_{k}": k for k in updates}
    expr_values = {f":v_{k}": v for k, v in updates.items()}
    cond = "attribute_exists(PK)"
    if owner_id:
        cond += " AND created_by = :owner"
        expr_values[":owner"] = owner_id
    try:
        resp = table.update_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"CUSTOMER#{customer_id}"},
            UpdateExpression=f"SET {', '.join(set_parts)}",
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ConditionExpression=cond,
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")
    except ClientError as exc:
        if _is_conditional_failure(exc):
            return None
        raise


def delete_customer(customer_id: str, owner_id: str | None = None) -> bool:
    table = _get_table()
    cond = "attribute_exists(PK)"
    expr_values: dict = {}
    if owner_id:
        cond += " AND created_by = :owner"
        expr_values[":owner"] = owner_id
    try:
        table.delete_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"CUSTOMER#{customer_id}"},
            ConditionExpression=cond,
            ExpressionAttributeValues=expr_values or None,
        )
        return True
    except ClientError as exc:
        if _is_conditional_failure(exc):
            return False
        raise


# ── Sessions ──────────────────────────────────────────────────────────────────

def list_sessions(
    customer_id: str,
    created_by: str | None = None,
) -> list[dict]:
    table = _get_table()
    filter_parts = ["PK = :pk", "begins_with(SK, :sk_prefix)"]
    expr_values: dict[str, Any] = {
        ":pk": f"CUSTOMER#{customer_id}",
        ":sk_prefix": "SESSION#",
    }
    if created_by:
        filter_parts.append("created_by = :created_by")
        expr_values[":created_by"] = created_by

    resp = table.scan(
        FilterExpression=" AND ".join(filter_parts),
        ExpressionAttributeValues=expr_values,
    )
    items = resp.get("Items", [])
    items.sort(key=lambda i: i.get("updated_at", ""), reverse=True)
    return items


def create_session(
    customer_id: str,
    created_by: str,
    title: str = "",
    description: str = "",
    module_id: str | None = None,
) -> dict:
    table = _get_table()
    now = _now()
    session_id = _new_id("sess")
    item: dict[str, Any] = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"SESSION#{session_id}",
        "session_id": session_id,
        "customer_id": customer_id,
        "title": title or "New conversation",
        "description": description,
        "status": "active",
        "current_step": 0,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if module_id:
        item["module_id"] = module_id
    table.put_item(Item=item)
    return item


def get_session(customer_id: str, session_id: str) -> dict | None:
    table = _get_table()
    resp = table.get_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"}
    )
    return resp.get("Item")


def update_session(
    customer_id: str,
    session_id: str,
    updates: dict[str, Any],
    owner_id: str | None = None,
) -> dict | None:
    table = _get_table()
    updates = {k: v for k, v in updates.items() if v is not None}
    updates["updated_at"] = _now()
    set_parts = [f"#f_{k} = :v_{k}" for k in updates]
    expr_names = {f"#f_{k}": k for k in updates}
    expr_values = {f":v_{k}": v for k, v in updates.items()}
    cond = "attribute_exists(PK)"
    if owner_id:
        cond += " AND created_by = :owner"
        expr_values[":owner"] = owner_id
    try:
        resp = table.update_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"},
            UpdateExpression=f"SET {', '.join(set_parts)}",
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ConditionExpression=cond,
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")
    except ClientError as exc:
        if _is_conditional_failure(exc):
            return None
        raise


def delete_session(
    customer_id: str,
    session_id: str,
    owner_id: str | None = None,
) -> bool:
    table = _get_table()
    cond = "attribute_exists(PK)"
    expr_values: dict = {}
    if owner_id:
        cond += " AND created_by = :owner"
        expr_values[":owner"] = owner_id
    try:
        table.delete_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"},
            ConditionExpression=cond,
            ExpressionAttributeValues=expr_values or None,
        )
        return True
    except ClientError as exc:
        if _is_conditional_failure(exc):
            return False
        raise
