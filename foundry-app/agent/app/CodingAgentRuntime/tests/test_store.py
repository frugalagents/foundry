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
    from store import put_workspace_snapshot

    put_workspace_snapshot(
        "cust1",
        "sess1",
        stage="discovery",
        facts=["Brownfield tools already in use"],
        operating_model="multi_harness_governed",
        open_questions=["Which harness is default for general developers?"],
    )

    resp = table.get_item(Key={"PK": "CUSTOMER#cust1", "SK": "WORKSPACE#sess1"})
    item = resp["Item"]
    assert item["stage"] == "discovery"
    assert item["facts"] == ["Brownfield tools already in use"]
    assert item["operating_model"] == "multi_harness_governed"
    assert item["open_questions"] == ["Which harness is default for general developers?"]
