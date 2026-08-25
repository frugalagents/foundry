"""DynamoDB persistence for chat messages and advisory runtime snapshots.

Mirrors the key scheme used by the FastAPI backend (api/db/dynamodb.py) so both
sides read/write the same foundry-app-main table:
  Message : PK=CUSTOMER#{customer_id}  SK=MSG#{session_id}#{iso_ts}#{rand}
  Canvas  : PK=CUSTOMER#{customer_id}  SK=CANVAS#{session_id}
  Case    : PK=CUSTOMER#{customer_id}  SK=CASE#{session_id}#{iso_ts}
"""
from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

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
    baseline_node_ids: list[str] | None = None,
    architecture_artifact: dict | None = None,
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
        "baseline_node_ids_json": json.dumps(baseline_node_ids or []),
        "architecture_artifact_json": json.dumps(architecture_artifact or {}),
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


def put_workspace_snapshot(
    customer_id: str,
    session_id: str,
    *,
    stage: str = "",
    recommendation: str = "",
    blueprint_markdown: str = "",
    assumptions: list[dict] | None = None,
    facts: list[str] | None = None,
    operating_model: str = "",
    question_state: list[dict] | None = None,
    open_questions: list[str] | None = None,
    decisions: list[str] | None = None,
    risks: list[str] | None = None,
    implementation_plan: list[str] | None = None,
    advisory_case: dict | None = None,
    recommendation_state: dict | None = None,
    artifact_status: dict | None = None,
    traversal_state: dict | None = None,
) -> None:
    now = _now()
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"WORKSPACE#{session_id}",
        "session_id": session_id,
        "customer_id": customer_id,
        "stage": stage,
        "recommendation": recommendation,
        "blueprint_markdown": blueprint_markdown,
        "assumptions_json": json.dumps(assumptions or []),
        "facts": facts or [],
        "operating_model": operating_model,
        "question_state_json": json.dumps(question_state or []),
        "open_questions": open_questions or [],
        "decisions": decisions or [],
        "risks": risks or [],
        "implementation_plan": implementation_plan or [],
        "advisory_case_json": json.dumps(advisory_case or {}),
        "recommendation_state_json": json.dumps(recommendation_state or {}),
        "artifact_status_json": json.dumps(artifact_status or {}),
        "traversal_state_json": json.dumps(traversal_state or {}),
        "updated_at": now,
    }
    _get_table().put_item(Item=item)


def put_architecture_case_snapshot(
    customer_id: str,
    session_id: str,
    architecture_case: dict,
) -> None:
    now = _now()
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"CASE#{session_id}#{now}",
        "session_id": session_id,
        "customer_id": customer_id,
        "revision": int(architecture_case.get("revision") or 1),
        "case_id": architecture_case.get("case_id", ""),
        "okf_release_id": architecture_case.get("okf_release_id", ""),
        "architecture_case_json": json.dumps(architecture_case or {}),
        "created_at": now,
        "updated_at": now,
    }
    _get_table().put_item(Item=item)


def get_workspace_snapshot(customer_id: str, session_id: str) -> dict | None:
    resp = _get_table().get_item(
        Key={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"WORKSPACE#{session_id}",
        }
    )
    item = resp.get("Item")
    if not item:
        return None

    return {
        "stage": item.get("stage", ""),
        "recommendation": item.get("recommendation", ""),
        "blueprint_markdown": item.get("blueprint_markdown", ""),
        "assumptions": json.loads(item.get("assumptions_json", "[]") or "[]"),
        "facts": item.get("facts", []) or [],
        "operating_model": item.get("operating_model", ""),
        "question_state": json.loads(item.get("question_state_json", "[]") or "[]"),
        "open_questions": item.get("open_questions", []) or [],
        "decisions": item.get("decisions", []) or [],
        "risks": item.get("risks", []) or [],
        "implementation_plan": item.get("implementation_plan", []) or [],
        "advisory_case": json.loads(item.get("advisory_case_json", "{}") or "{}") or None,
        "recommendation_state": json.loads(item.get("recommendation_state_json", "{}") or "{}") or {},
        "artifact_status": json.loads(item.get("artifact_status_json", "{}") or "{}") or {},
        "traversal_state": json.loads(item.get("traversal_state_json", "{}") or "{}") or None,
        "updated_at": item.get("updated_at", ""),
    }


def get_latest_architecture_case(customer_id: str, session_id: str) -> dict | None:
    resp = _get_table().query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}")
            & Key("SK").begins_with(f"CASE#{session_id}#")
        ),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return None

    item = items[0]
    architecture_case = json.loads(item.get("architecture_case_json", "{}") or "{}") or None
    if isinstance(architecture_case, dict):
        architecture_case.setdefault("revision", int(item.get("revision") or 1))
        architecture_case.setdefault("case_id", item.get("case_id", ""))
        architecture_case.setdefault("okf_release_id", item.get("okf_release_id", ""))
    return architecture_case


def get_recent_messages(customer_id: str, session_id: str, *, limit: int = 12) -> list[dict]:
    resp = _get_table().query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}")
            & Key("SK").begins_with(f"MSG#{session_id}#")
        ),
        ScanIndexForward=False,
        Limit=max(1, limit),
    )
    items = list(reversed(resp.get("Items", [])))
    return [
        {
            "role": item.get("role", ""),
            "content": item.get("content", ""),
            "created_at": item.get("created_at", ""),
        }
        for item in items
        if item.get("content")
    ]


def get_latest_canvas_snapshot(customer_id: str, session_id: str) -> dict | None:
    resp = _get_table().query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}")
            & Key("SK").begins_with(f"CANVAS#{session_id}#")
        ),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return None

    item = items[0]
    return {
        "nodes": json.loads(item.get("nodes_json", "[]") or "[]"),
        "edges": json.loads(item.get("edges_json", "[]") or "[]"),
        "stage": item.get("stage", ""),
        "baseline_node_ids": json.loads(item.get("baseline_node_ids_json", "[]") or "[]"),
        "architecture_artifact": json.loads(item.get("architecture_artifact_json", "{}") or "{}") or None,
        "updated_at": item.get("updated_at", ""),
    }
