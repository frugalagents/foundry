"""DynamoDB single-table operations for foundry-app."""
from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import boto3
from boto3.dynamodb.conditions import Key
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


def _scan_all(table, **kwargs) -> list[dict]:
    items: list[dict] = []
    resp = table.scan(**kwargs)
    items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **kwargs)
        items.extend(resp.get("Items", []))
    return items


def _query_all(table, **kwargs) -> list[dict]:
    items: list[dict] = []
    resp = table.query(**kwargs)
    items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = table.query(ExclusiveStartKey=resp["LastEvaluatedKey"], **kwargs)
        items.extend(resp.get("Items", []))
    return items


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

    return _scan_all(
        table,
        FilterExpression=" AND ".join(filter_parts),
        ExpressionAttributeValues=expr_values,
    )


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
    query_kwargs: dict[str, Any] = {
        "KeyConditionExpression": (
            Key("PK").eq(f"CUSTOMER#{customer_id}") &
            Key("SK").begins_with("SESSION#")
        ),
    }
    if created_by:
        query_kwargs["FilterExpression"] = "created_by = :created_by"
        query_kwargs["ExpressionAttributeValues"] = {":created_by": created_by}

    items = _query_all(table, **query_kwargs)
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


# ── Messages & canvas (written by the CodingAgentRuntime agent) ───────────────

def list_messages(customer_id: str, session_id: str) -> list[dict]:
    table = _get_table()
    resp = table.query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}") &
            Key("SK").begins_with(f"MSG#{session_id}#")
        ),
    )
    items = resp.get("Items", [])
    items.sort(key=lambda i: i.get("created_at", ""))
    return items


def get_canvas(customer_id: str, session_id: str) -> dict | None:
    """Return the most recent canvas snapshot for this session."""
    table = _get_table()
    resp = table.query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}") &
            Key("SK").begins_with(f"CANVAS#{session_id}#")
        ),
        ScanIndexForward=False,  # newest first
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def get_workspace(customer_id: str, session_id: str) -> dict | None:
    table = _get_table()
    resp = table.get_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"WORKSPACE#{session_id}"}
    )
    return resp.get("Item")


# ── Feedback & admin analytics ───────────────────────────────────────────────

def get_session_feedback(
    customer_id: str,
    session_id: str,
    user_id: str,
) -> dict | None:
    table = _get_table()
    resp = table.get_item(
        Key={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"FEEDBACK#{session_id}#{user_id}",
        }
    )
    return resp.get("Item")


def upsert_session_feedback(
    customer_id: str,
    session_id: str,
    user_id: str,
    user_name: str,
    payload: dict[str, Any],
) -> dict:
    table = _get_table()
    now = _now()
    existing = get_session_feedback(customer_id, session_id, user_id)
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"FEEDBACK#{session_id}#{user_id}",
        "customer_id": customer_id,
        "session_id": session_id,
        "user_id": user_id,
        "user_name": user_name,
        "rating": int(payload.get("rating") or 0),
        "most_useful": payload.get("most_useful") or "",
        "missing": payload.get("missing") or "",
        "additional_comments": payload.get("additional_comments") or "",
        "reused_in_doc_or_meeting": payload.get("reused_in_doc_or_meeting"),
        "agreed_with_recommendation": payload.get("agreed_with_recommendation"),
        "would_reuse": payload.get("would_reuse"),
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
    }
    table.put_item(Item=item)
    return item


def list_feedback_for_session(customer_id: str, session_id: str) -> list[dict]:
    table = _get_table()
    items = _query_all(
        table,
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}")
            & Key("SK").begins_with(f"FEEDBACK#{session_id}#")
        ),
    )
    items.sort(key=lambda i: i.get("updated_at", ""), reverse=True)
    return items


def list_all_feedback() -> list[dict]:
    table = _get_table()
    items = _scan_all(
        table,
        FilterExpression="begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={":sk_prefix": "FEEDBACK#"},
    )
    items.sort(key=lambda i: i.get("updated_at", ""), reverse=True)
    return items


def list_workspaces() -> list[dict]:
    table = _get_table()
    items = _scan_all(
        table,
        FilterExpression="begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={":sk_prefix": "WORKSPACE#"},
    )
    items.sort(key=lambda i: i.get("updated_at", ""), reverse=True)
    return items


def list_canvases() -> list[dict]:
    table = _get_table()
    items = _scan_all(
        table,
        FilterExpression="begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={":sk_prefix": "CANVAS#"},
    )
    items.sort(key=lambda i: i.get("updated_at", i.get("created_at", "")), reverse=True)
    return items


# ── Access requests ───────────────────────────────────────────────────────────

def create_access_request(item: dict[str, Any]) -> dict:
    table = _get_table()
    table.put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(PK)",
    )
    return item


def get_access_request(request_id: str) -> dict | None:
    table = _get_table()
    resp = table.get_item(
        Key={
            "PK": f"ACCESS_REQUEST#{request_id}",
            "SK": f"ACCESS_REQUEST#{request_id}",
        }
    )
    return resp.get("Item")


def list_access_requests() -> list[dict]:
    table = _get_table()
    items = _scan_all(
        table,
        FilterExpression="begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={":sk_prefix": "ACCESS_REQUEST#"},
    )
    items.sort(key=lambda item: item.get("requested_at", ""), reverse=True)
    return items


def find_open_access_request(email: str) -> dict | None:
    normalized = email.strip().lower()
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    for item in list_access_requests():
        if item.get("email") != normalized:
            continue
        if int(item.get("expires_at_epoch") or 0) <= now_epoch:
            continue
        if item.get("status") in {"pending", "approved"}:
            return item
    return None


def count_recent_access_requests(source_hash: str, since_iso: str) -> int:
    return sum(
        1
        for item in list_access_requests()
        if item.get("source_hash") == source_hash
        and item.get("requested_at", "") >= since_iso
    )


def update_access_request(
    request_id: str,
    updates: dict[str, Any],
    *,
    expected_status: str | None = None,
) -> dict | None:
    table = _get_table()
    updates = {key: value for key, value in updates.items() if value is not None}
    if not updates:
        return get_access_request(request_id)

    set_parts = [f"#field_{index} = :value_{index}" for index, _ in enumerate(updates)]
    expr_names = {
        f"#field_{index}": field
        for index, field in enumerate(updates)
    }
    expr_values = {
        f":value_{index}": value
        for index, value in enumerate(updates.values())
    }
    condition = "attribute_exists(PK)"
    if expected_status:
        condition += " AND #request_status = :expected_status"
        expr_names["#request_status"] = "status"
        expr_values[":expected_status"] = expected_status

    try:
        resp = table.update_item(
            Key={
                "PK": f"ACCESS_REQUEST#{request_id}",
                "SK": f"ACCESS_REQUEST#{request_id}",
            },
            UpdateExpression=f"SET {', '.join(set_parts)}",
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ConditionExpression=condition,
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")
    except ClientError as exc:
        if _is_conditional_failure(exc):
            return None
        raise
