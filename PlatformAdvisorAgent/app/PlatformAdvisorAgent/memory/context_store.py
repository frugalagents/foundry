"""Persistence adapter for the API-owned session aggregate."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from pipeline_skills.base import PipelineContext


def context_to_dict(ctx: PipelineContext) -> dict[str, Any]:
    return {
        "session_id": ctx.session_id,
        "customer_id": ctx.customer_id,
        "answers": ctx.answers,
        "industry": ctx.industry,
        "pain_points": ctx.pain_points,
        "pattern_id": ctx.pattern_id,
        "confidence": ctx.confidence,
        "axis_scores": ctx.axis_scores,
        "topology": ctx.topology,
        "components": ctx.components,
        "innovations": ctx.innovations,
        "compliance_notes": ctx.compliance_notes,
        "service_map": ctx.service_map,
        "antipatterns": ctx.antipatterns,
        "phases": ctx.phases,
        "blueprint_md": ctx.blueprint_md,
        "customer_history": ctx.customer_history,
        "current_step": ctx.current_step,
        "cost_estimate": ctx.cost_estimate,
        "schema_version": ctx.schema_version,
        "assessment_input": ctx.assessment_input,
        "assessment_result": ctx.assessment_result,
        "overrides": ctx.overrides,
    }


def _to_dynamodb(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb(item) for item in value]
    if isinstance(value, tuple):
        return [_to_dynamodb(item) for item in value]
    return value


def _from_dynamodb(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {key: _from_dynamodb(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_from_dynamodb(item) for item in value]
    return value


def context_from_dict(
    data: dict[str, Any],
    *,
    session_id: str,
    customer_id: str,
) -> PipelineContext:
    data = _from_dynamodb(data)
    ctx = PipelineContext(
        session_id=data.get("session_id") or session_id,
        customer_id=data.get("customer_id") or customer_id,
    )
    ctx.answers = data.get("answers", {})
    ctx.industry = data.get("industry", "")
    ctx.pain_points = data.get("pain_points", [])
    ctx.pattern_id = data.get("pattern_id", "")
    ctx.confidence = data.get("confidence", 0.0)
    ctx.axis_scores = data.get("axis_scores", [])
    ctx.topology = data.get("topology", {})
    ctx.components = data.get("components", [])
    ctx.innovations = data.get("innovations", [])
    ctx.compliance_notes = data.get("compliance_notes", [])
    ctx.service_map = data.get("service_map", [])
    ctx.antipatterns = data.get("antipatterns", [])
    ctx.phases = data.get("phases", [])
    ctx.blueprint_md = data.get("blueprint_md", "")
    ctx.customer_history = data.get("customer_history", "")
    ctx.current_step = data.get("current_step", 0)
    ctx.cost_estimate = data.get("cost_estimate", {})
    ctx.schema_version = data.get("schema_version", "1.0")
    ctx.assessment_input = data.get("assessment_input", {})
    ctx.assessment_result = data.get("assessment_result", {})
    ctx.overrides = data.get("overrides", [])
    return ctx


def save_context(
    table: Any,
    ctx: PipelineContext,
    *,
    owner_id: str | None = None,
) -> None:
    """Update the existing API session; never create an orphan context item."""
    data = context_to_dict(ctx)
    result = data.get("assessment_result", {})
    evidence_state = {
        "needs_information": "provisional",
        "complete": "decision_ready",
        "overridden": "overridden",
    }.get(result.get("status"), "not_started")
    status = (
        "complete"
        if ctx.current_step >= 10 and evidence_state != "provisional"
        else "active"
    )

    expression_names = {"#status": "status"}
    expression_values = {
        ":ctx": _to_dynamodb(data),
        ":step": ctx.current_step,
        ":status": status,
        ":recommendation": result.get("operating_model") or ctx.pattern_id or "",
        ":evidence": evidence_state,
        ":workload": ctx.assessment_input.get("primary_workload", ""),
        ":updated": datetime.now(timezone.utc).isoformat(),
    }
    conditions = ["attribute_exists(PK)", "attribute_exists(SK)"]
    if owner_id is not None:
        expression_names["#created_by"] = "created_by"
        expression_values[":owner_id"] = owner_id
        conditions.append("#created_by = :owner_id")

    table.update_item(
        Key={
            "PK": f"CUSTOMER#{ctx.customer_id}",
            "SK": f"SESSION#{ctx.session_id}",
        },
        UpdateExpression=(
            "SET pipeline_ctx = :ctx, current_step = :step, #status = :status, "
            "recommendation = :recommendation, evidence_state = :evidence, "
            "primary_workload = :workload, updated_at = :updated"
        ),
        ConditionExpression=" AND ".join(conditions),
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values,
    )


def session_is_owned(
    table: Any,
    customer_id: str,
    session_id: str,
    owner_id: str,
) -> bool:
    session = table.get_item(
        Key={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"SESSION#{session_id}",
        },
        ConsistentRead=True,
    ).get("Item")
    return bool(session) and session.get("created_by") == owner_id


def load_context(
    table: Any,
    customer_id: str,
    session_id: str,
    *,
    owner_id: str | None = None,
) -> PipelineContext | None:
    session = table.get_item(
        Key={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"SESSION#{session_id}",
        }
    ).get("Item")
    if owner_id is not None and (
        not session or session.get("created_by") != owner_id
    ):
        return None
    if session and isinstance(session.get("pipeline_ctx"), dict):
        return context_from_dict(
            session["pipeline_ctx"],
            session_id=session_id,
            customer_id=customer_id,
        )

    # Read compatibility for contexts produced before the session aggregate was
    # unified. New writes never use this namespace.
    legacy = table.get_item(
        Key={
            "PK": f"CUST#{customer_id}",
            "SK": f"SESSION#{session_id}#PIPELINE_CTX",
        }
    ).get("Item")
    if not legacy:
        return None
    raw = legacy.get("ctx_json", "{}")
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict):
        return None
    return context_from_dict(
        data,
        session_id=session_id,
        customer_id=customer_id,
    )


def list_customer_contexts(
    table: Any,
    customer_id: str,
    *,
    owner_id: str | None = None,
) -> Iterable[dict[str, Any]]:
    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": f"CUSTOMER#{customer_id}",
            ":sk_prefix": "SESSION#",
        },
    )
    for item in response.get("Items", []):
        if owner_id is not None and item.get("created_by") != owner_id:
            continue
        data = item.get("pipeline_ctx")
        if isinstance(data, dict):
            yield data
