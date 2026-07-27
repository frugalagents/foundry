"""DynamoDB single-table operations for platform-advisor-main."""
from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "platform-advisor-main")
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT")  # for local dev

_dynamodb = None


def _get_table():
    global _dynamodb
    if _dynamodb is None:
        kwargs: dict = {"region_name": os.environ.get("AWS_REGION", "us-east-1")}
        if DYNAMODB_ENDPOINT:
            kwargs["endpoint_url"] = DYNAMODB_ENDPOINT
        resource = boto3.resource("dynamodb", **kwargs)
        _dynamodb = resource.Table(TABLE_NAME)
    return _dynamodb


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ── Customers ─────────────────────────────────────────────────────────────────

def create_customer(name: str, industry: str, contact_email: str,
                    created_by: str, notes: str = "") -> dict:
    table = _get_table()
    customer_id = _new_id("cust")
    now = _now()
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": "METADATA",
        "customer_id": customer_id,
        "name": name,
        "industry": industry,
        "contact_email": contact_email,
        "notes": notes,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "session_count": 0,
        "GSI1PK": "CUSTOMERS",
        "GSI1SK": now,
    }
    table.put_item(Item=item)
    return item


def get_customer(customer_id: str) -> Optional[dict]:
    table = _get_table()
    resp = table.get_item(Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"})
    return resp.get("Item")


def list_customers(limit: int = 50) -> list[dict]:
    table = _get_table()
    resp = table.query(
        IndexName="GSI1",
        KeyConditionExpression="GSI1PK = :pk",
        ExpressionAttributeValues={":pk": "CUSTOMERS"},
        Limit=limit,
        ScanIndexForward=False,
    )
    return resp.get("Items", [])


def update_customer(customer_id: str, updates: dict) -> Optional[dict]:
    table = _get_table()
    updates["updated_at"] = _now()
    expr_parts = [f"#{k} = :{k}" for k in updates]
    update_expr = "SET " + ", ".join(expr_parts)
    names = {f"#{k}": k for k in updates}
    values = {f":{k}": v for k, v in updates.items()}
    try:
        resp = table.update_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")
    except ClientError as exc:
        logger.error("update_customer error: %s", exc)
        return None


def delete_customer(customer_id: str) -> bool:
    table = _get_table()
    try:
        table.delete_item(Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"})
        return True
    except ClientError:
        return False


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(customer_id: str, created_by: str,
                   title: str = "", notes: str = "") -> dict:
    table = _get_table()
    session_id = _new_id("sess")
    now = _now()
    if not title:
        title = f"Session {now[:10]}"
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"SESSION#{session_id}",
        "session_id": session_id,
        "customer_id": customer_id,
        "title": title,
        "notes": notes,
        "status": "active",
        "current_step": 0,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "GSI1PK": "SESSIONS",
        "GSI1SK": now,
    }
    table.put_item(Item=item)
    # Increment customer session count
    try:
        table.update_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"},
            UpdateExpression="ADD session_count :one",
            ExpressionAttributeValues={":one": 1},
        )
    except ClientError:
        pass
    return item


def get_session(customer_id: str, session_id: str) -> Optional[dict]:
    table = _get_table()
    resp = table.get_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"}
    )
    return resp.get("Item")


def list_sessions(customer_id: str) -> list[dict]:
    table = _get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": f"CUSTOMER#{customer_id}",
            ":sk_prefix": "SESSION#",
        },
        ScanIndexForward=False,
    )
    return resp.get("Items", [])


def update_session(customer_id: str, session_id: str, updates: dict) -> Optional[dict]:
    table = _get_table()
    updates["updated_at"] = _now()
    expr_parts = [f"#{k} = :{k}" for k in updates]
    update_expr = "SET " + ", ".join(expr_parts)
    names = {f"#{k}": k for k in updates}
    values = {f":{k}": v for k, v in updates.items()}
    try:
        resp = table.update_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")
    except ClientError as exc:
        logger.error("update_session error: %s", exc)
        return None


def delete_session(customer_id: str, session_id: str) -> bool:
    table = _get_table()
    try:
        table.delete_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"}
        )
        # Decrement customer session count
        try:
            table.update_item(
                Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"},
                UpdateExpression="ADD session_count :neg",
                ExpressionAttributeValues={":neg": -1},
            )
        except ClientError:
            pass
        return True
    except ClientError:
        return False


# ── Panel States ──────────────────────────────────────────────────────────────

def save_panel_state(session_id: str, step: int, panel_type: str, data: dict) -> None:
    table = _get_table()
    now = _now()
    table.put_item(Item={
        "PK": f"SESSION#{session_id}",
        "SK": f"PANEL#{step:02d}",
        "session_id": session_id,
        "step": step,
        "panel_type": panel_type,
        "data": data,
        "updated_at": now,
    })


def get_panel_states(session_id: str) -> list[dict]:
    table = _get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": f"SESSION#{session_id}",
            ":sk_prefix": "PANEL#",
        },
    )
    return resp.get("Items", [])


# ── Admin metrics ─────────────────────────────────────────────────────────────

def get_admin_metrics() -> dict:
    """Scan-based metrics — acceptable for admin dashboard (low frequency)."""
    table = _get_table()
    try:
        customers = table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": "CUSTOMERS"},
            Select="COUNT",
        )
        sessions_all = table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": "SESSIONS"},
        )
        all_sessions = sessions_all.get("Items", [])
        today = _now()[:10]
        active = sum(1 for s in all_sessions if s.get("status") == "active")
        today_count = sum(1 for s in all_sessions if s.get("created_at", "")[:10] == today)

        return {
            "total_customers": customers.get("Count", 0),
            "total_sessions": len(all_sessions),
            "active_sessions": active,
            "sessions_today": today_count,
            "top_patterns": [],
            "top_industries": [],
        }
    except ClientError as exc:
        logger.error("get_admin_metrics error: %s", exc)
        return {
            "total_customers": 0, "total_sessions": 0,
            "active_sessions": 0, "sessions_today": 0,
            "top_patterns": [], "top_industries": [],
        }
