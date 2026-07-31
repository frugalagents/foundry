from __future__ import annotations

import json
from decimal import Decimal

from memory.context_store import load_context, save_context, session_is_owned
from pipeline_skills.base import PipelineContext


class FakeTable:
    def __init__(self, items=None):
        self.items = items or {}
        self.update_calls = []

    def get_item(self, *, Key, **_kwargs):
        return {"Item": self.items.get((Key["PK"], Key["SK"]))}

    def update_item(self, **kwargs):
        self.update_calls.append(kwargs)
        return {}


def test_save_context_updates_existing_api_session_with_condition():
    table = FakeTable()
    ctx = PipelineContext(session_id="sess_1", customer_id="cust_1")
    ctx.current_step = 3
    ctx.confidence = 0.75
    ctx.schema_version = "2.0"
    ctx.assessment_input = {"primary_workload": "coding"}
    ctx.assessment_result = {
        "status": "complete",
        "operating_model": "centralized",
    }

    save_context(table, ctx)

    call = table.update_calls[0]
    assert call["Key"] == {
        "PK": "CUSTOMER#cust_1",
        "SK": "SESSION#sess_1",
    }
    assert call["ConditionExpression"] == (
        "attribute_exists(PK) AND attribute_exists(SK)"
    )
    assert call["ExpressionAttributeValues"][":ctx"]["schema_version"] == "2.0"
    assert call["ExpressionAttributeValues"][":ctx"]["confidence"] == Decimal("0.75")


def test_load_context_prefers_api_session_aggregate():
    table = FakeTable({
        ("CUSTOMER#cust_1", "SESSION#sess_1"): {
            "pipeline_ctx": {
                "session_id": "sess_1",
                "customer_id": "cust_1",
                "schema_version": "2.0",
                "current_step": 4,
                "confidence": Decimal("0.75"),
            },
        },
        ("CUST#cust_1", "SESSION#sess_1#PIPELINE_CTX"): {
            "ctx_json": json.dumps({"current_step": 1}),
        },
    })

    ctx = load_context(table, "cust_1", "sess_1")

    assert ctx is not None
    assert ctx.current_step == 4
    assert ctx.schema_version == "2.0"
    assert ctx.confidence == 0.75


def test_load_context_reads_legacy_item_for_compatibility():
    table = FakeTable({
        ("CUST#cust_1", "SESSION#sess_1#PIPELINE_CTX"): {
            "ctx_json": json.dumps({
                "session_id": "sess_1",
                "customer_id": "cust_1",
                "schema_version": "1.0",
                "pattern_id": "pattern:federated",
            }),
        },
    })

    ctx = load_context(table, "cust_1", "sess_1")

    assert ctx is not None
    assert ctx.pattern_id == "pattern:federated"
    assert ctx.schema_version == "1.0"


def test_context_access_and_write_are_bound_to_session_owner():
    table = FakeTable({
        ("CUSTOMER#cust_1", "SESSION#sess_1"): {
            "created_by": "owner-user",
            "pipeline_ctx": {
                "session_id": "sess_1",
                "customer_id": "cust_1",
            },
        },
    })
    ctx = PipelineContext(session_id="sess_1", customer_id="cust_1")

    assert session_is_owned(
        table,
        "cust_1",
        "sess_1",
        "owner-user",
    )
    assert not session_is_owned(
        table,
        "cust_1",
        "sess_1",
        "other-user",
    )
    assert load_context(
        table,
        "cust_1",
        "sess_1",
        owner_id="other-user",
    ) is None

    save_context(table, ctx, owner_id="owner-user")
    call = table.update_calls[-1]
    assert "#created_by = :owner_id" in call["ConditionExpression"]
    assert call["ExpressionAttributeValues"][":owner_id"] == "owner-user"
