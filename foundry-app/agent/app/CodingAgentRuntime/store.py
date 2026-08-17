"""DynamoDB persistence for chat messages and architecture canvas snapshots.

Mirrors the key scheme used by the FastAPI backend (api/db/dynamodb.py) so both
sides read/write the same foundry-app-main table:
  Message : PK=CUSTOMER#{customer_id}  SK=MSG#{session_id}#{iso_ts}#{rand}
  Canvas  : PK=CUSTOMER#{customer_id}  SK=CANVAS#{session_id}
"""
from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, timezone

import boto3

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "foundry-app-main")
_REGION = os.environ.get("AWS_REGION", "us-east-1")

_table = None


def _get_table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb", region_name=_REGION).Table(TABLE_NAME)
    return _table


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def put_message(customer_id: str, session_id: str, role: str, content: str) -> None:
    if not content:
        return
    now = _now()
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"MSG#{session_id}#{now}#{uuid.uuid4().hex[:8]}",
        "session_id": session_id,
        "customer_id": customer_id,
        "role": role,
        "content": content,
        "created_at": now,
    }
    _get_table().put_item(Item=item)


def put_canvas_snapshot(
    customer_id: str,
    session_id: str,
    nodes: list,
    edges: list,
    stage: str = "",
) -> None:
    now = _now()
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        # Timestamped SK preserves every intermediate stage (skeleton →
        # compliance → full) instead of overwriting a single row.
        "SK": f"CANVAS#{session_id}#{now}",
        "session_id": session_id,
        "customer_id": customer_id,
        "nodes_json": json.dumps(nodes),
        "edges_json": json.dumps(edges),
        "stage": stage,
        "created_at": now,
        "updated_at": now,
    }
    _get_table().put_item(Item=item)


def put_session_note(customer_id: str, session_id: str, note: str) -> None:
    if not note:
        return
    now = _now()
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"NOTE#{session_id}#{now}#{uuid.uuid4().hex[:8]}",
        "session_id": session_id,
        "customer_id": customer_id,
        "note": note,
        "created_at": now,
    }
    _get_table().put_item(Item=item)
