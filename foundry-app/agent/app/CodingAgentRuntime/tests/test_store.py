"""Tests for DynamoDB persistence — the engine's core "does the conversation
survive" guarantee. Uses moto to mock DynamoDB rather than a live table.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json
import os

import boto3
import pytest

moto = pytest.importorskip("moto")
try:
    from moto import mock_aws
except ImportError:
    mock_aws = getattr(moto, "mock_dynamodb", None) or getattr(moto, "mock_dynamodb2", None)
    if mock_aws is None:
        pytest.skip("No DynamoDB mock available in installed moto package", allow_module_level=True)

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def table():
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="foundry-app-main",
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        import store
        store._table = None  # force re-resolve against the mocked table
        yield boto3.resource("dynamodb", region_name="us-east-1").Table("foundry-app-main")


def _latest_canvas_item(table, customer_id: str, session_id: str) -> dict:
    resp = table.query(
        KeyConditionExpression=(
            boto3.dynamodb.conditions.Key("PK").eq(f"CUSTOMER#{customer_id}")
            & boto3.dynamodb.conditions.Key("SK").begins_with(f"CANVAS#{session_id}#")
        ),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp["Items"]
    assert items
    return items[0]


def test_put_message_writes_expected_item(table):
    from store import put_message

    put_message("cust1", "sess1", "user", "hello there")
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("PK").eq("CUSTOMER#cust1")
    )
    items = resp["Items"]
    assert len(items) == 1
    item = items[0]
    assert item["SK"].startswith("MSG#sess1#")
    assert item["role"] == "user"
    assert item["content"] == "hello there"
    assert item["customer_id"] == "cust1"
    assert item["session_id"] == "sess1"


def test_put_message_skips_empty_content(table):
    from store import put_message

    put_message("cust1", "sess1", "agent", "")
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("PK").eq("CUSTOMER#cust1")
    )
    assert resp["Items"] == []


def test_put_message_preserves_turn_order_via_sort_key(table):
    from store import put_message

    put_message("cust1", "sess1", "user", "first")
    put_message("cust1", "sess1", "agent", "second")
    put_message("cust1", "sess1", "user", "third")

    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("PK").eq("CUSTOMER#cust1")
    )
    items = sorted(resp["Items"], key=lambda i: i["SK"])
    assert [i["content"] for i in items] == ["first", "second", "third"]


def test_put_canvas_snapshot_writes_serialized_nodes_and_edges(table):
    from store import put_canvas_snapshot

    nodes = [{"id": "dev", "label": "Developer"}]
    edges = [{"id": "e1", "source": "dev", "target": "surface"}]
    put_canvas_snapshot("cust1", "sess1", nodes, edges, stage="skeleton")

    item = _latest_canvas_item(table, "cust1", "sess1")
    assert json.loads(item["nodes_json"]) == nodes
    assert json.loads(item["edges_json"]) == edges
    assert item["stage"] == "skeleton"


def test_put_canvas_snapshot_overwrites_previous_snapshot_for_same_session(table):
    from store import put_canvas_snapshot

    put_canvas_snapshot("cust1", "sess1", [{"id": "a"}], [], stage="skeleton")
    put_canvas_snapshot("cust1", "sess1", [{"id": "a"}, {"id": "b"}], [], stage="full")

    item = _latest_canvas_item(table, "cust1", "sess1")
    assert json.loads(item["nodes_json"]) == [{"id": "a"}, {"id": "b"}]
    assert item["stage"] == "full"


def test_put_workspace_snapshot_persists_operating_model(table):
    from store import get_workspace_snapshot, put_workspace_snapshot

    put_workspace_snapshot(
        "cust1",
        "sess1",
        stage="discovery",
        facts=["Brownfield tools already in use"],
        operating_model="multi_harness_governed",
        question_state=[{"id": "q1", "text": "Which harness is default for general developers?", "status": "open", "blocking": True}],
        open_questions=["Which harness is default for general developers?"],
        recommendation_state={"primary_recommendation": "Governed multi-harness portfolio."},
        artifact_status={"recommendation": "draft"},
        traversal_state={"active_decision": {"path": "harness-selection/multi-harness-governance"}},
    )

    resp = table.get_item(Key={"PK": "CUSTOMER#cust1", "SK": "WORKSPACE#sess1"})
    item = resp["Item"]
    assert item["stage"] == "discovery"
    assert item["facts"] == ["Brownfield tools already in use"]
    assert item["operating_model"] == "multi_harness_governed"
    assert json.loads(item["question_state_json"]) == [{"id": "q1", "text": "Which harness is default for general developers?", "status": "open", "blocking": True}]
    assert item["open_questions"] == ["Which harness is default for general developers?"]
    loaded = get_workspace_snapshot("cust1", "sess1")
    assert loaded is not None
    assert loaded["question_state"] == [{"id": "q1", "text": "Which harness is default for general developers?", "status": "open", "blocking": True}]
    assert loaded["recommendation_state"] == {"primary_recommendation": "Governed multi-harness portfolio."}
    assert loaded["artifact_status"] == {"recommendation": "draft"}
    assert loaded["traversal_state"] == {"active_decision": {"path": "harness-selection/multi-harness-governance"}}


def test_get_recent_messages_returns_latest_messages_in_chronological_order(table):
    from store import get_recent_messages, put_message

    put_message("cust1", "sess1", "user", "first")
    put_message("cust1", "sess1", "agent", "second")
    put_message("cust1", "sess1", "user", "third")

    messages = get_recent_messages("cust1", "sess1", limit=2)
    assert messages == [
        {"role": "agent", "content": "second", "created_at": messages[0]["created_at"]},
        {"role": "user", "content": "third", "created_at": messages[1]["created_at"]},
    ]


def test_get_latest_canvas_snapshot_returns_latest_version(table):
    from store import get_latest_canvas_snapshot, put_canvas_snapshot

    put_canvas_snapshot("cust1", "sess1", [{"id": "a"}], [], stage="skeleton")
    put_canvas_snapshot(
        "cust1",
        "sess1",
        [{"id": "a"}, {"id": "b"}],
        [{"id": "e1", "source": "a", "target": "b"}],
        stage="full",
        baseline_node_ids=["a"],
        architecture_artifact={"executive_summary": "Latest"},
    )

    snapshot = get_latest_canvas_snapshot("cust1", "sess1")
    assert snapshot == {
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [{"id": "e1", "source": "a", "target": "b"}],
        "stage": "full",
        "baseline_node_ids": ["a"],
        "architecture_artifact": {"executive_summary": "Latest"},
        "updated_at": snapshot["updated_at"],
    }


def test_put_architecture_case_snapshot_preserves_latest_revision(table):
    from store import get_latest_architecture_case, put_architecture_case_snapshot

    put_architecture_case_snapshot(
        "cust1",
        "sess1",
        {
            "case_id": "cust1/sess1",
            "revision": 1,
            "okf_release_id": "okf.release.v1alpha1:abc123",
            "stage": "discovery",
        },
    )
    put_architecture_case_snapshot(
        "cust1",
        "sess1",
        {
            "case_id": "cust1/sess1",
            "revision": 2,
            "okf_release_id": "okf.release.v1alpha1:def456",
            "stage": "solutioning",
        },
    )

    latest = get_latest_architecture_case("cust1", "sess1")
    assert latest == {
        "case_id": "cust1/sess1",
        "revision": 2,
        "okf_release_id": "okf.release.v1alpha1:def456",
        "stage": "solutioning",
    }
