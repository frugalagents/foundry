"""Tests for DynamoDB persistence — the engine's core "does the conversation
survive" guarantee. Uses moto to mock DynamoDB rather than a live table.
"""
from __future__ import annotations
import json
import os

import boto3
import pytest
from moto import mock_aws

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

    resp = table.get_item(Key={"PK": "CUSTOMER#cust1", "SK": "CANVAS#sess1"})
    item = resp["Item"]
    assert json.loads(item["nodes_json"]) == nodes
    assert json.loads(item["edges_json"]) == edges
    assert item["stage"] == "skeleton"


def test_put_canvas_snapshot_overwrites_previous_snapshot_for_same_session(table):
    from store import put_canvas_snapshot

    put_canvas_snapshot("cust1", "sess1", [{"id": "a"}], [], stage="skeleton")
    put_canvas_snapshot("cust1", "sess1", [{"id": "a"}, {"id": "b"}], [], stage="full")

    resp = table.get_item(Key={"PK": "CUSTOMER#cust1", "SK": "CANVAS#sess1"})
    item = resp["Item"]
    assert json.loads(item["nodes_json"]) == [{"id": "a"}, {"id": "b"}]
    assert item["stage"] == "full"
