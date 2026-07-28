from __future__ import annotations

from api.db import dynamodb as db


class FakeTable:
    def __init__(self, items):
        self.items = {
            (item["PK"], item["SK"]): dict(item)
            for item in items
        }

    def get_item(self, *, Key, **_kwargs):
        item = self.items.get((Key["PK"], Key["SK"]))
        return {"Item": dict(item)} if item else {}

    def query(self, *, ExpressionAttributeValues, **_kwargs):
        partition_key = ExpressionAttributeValues[":pk"]
        items = [
            dict(item)
            for (pk, _sk), item in self.items.items()
            if pk == partition_key
        ]
        return {"Items": items}

    def batch_writer(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def delete_item(self, *, Key):
        self.items.pop((Key["PK"], Key["SK"]), None)

    def update_item(self, *, Key, ExpressionAttributeValues, **_kwargs):
        item = self.items.get((Key["PK"], Key["SK"]))
        if item:
            item["session_count"] += ExpressionAttributeValues[":neg"]


def _portfolio_items():
    return [
        {
            "PK": "CUSTOMER#cust_delete",
            "SK": "METADATA",
            "customer_id": "cust_delete",
            "session_count": 2,
        },
        {
            "PK": "CUSTOMER#cust_delete",
            "SK": "SESSION#sess_one",
            "session_id": "sess_one",
        },
        {
            "PK": "CUSTOMER#cust_delete",
            "SK": "SESSION#sess_two",
            "session_id": "sess_two",
        },
        {"PK": "SESSION#sess_one", "SK": "PANEL#01"},
        {"PK": "SESSION#sess_one", "SK": "PANEL#02"},
        {"PK": "SESSION#sess_two", "SK": "PANEL#01"},
        {"PK": "CUSTOMER#other", "SK": "METADATA", "customer_id": "other"},
    ]


def test_delete_customer_removes_sessions_and_panels(monkeypatch):
    table = FakeTable(_portfolio_items())
    monkeypatch.setattr(db, "_get_table", lambda: table)

    assert db.delete_customer("cust_delete") is True
    assert set(table.items) == {("CUSTOMER#other", "METADATA")}


def test_delete_customer_returns_false_when_customer_does_not_exist(monkeypatch):
    table = FakeTable(_portfolio_items())
    monkeypatch.setattr(db, "_get_table", lambda: table)

    assert db.delete_customer("missing") is False
    assert len(table.items) == len(_portfolio_items())


def test_delete_session_removes_panels_and_updates_customer_count(monkeypatch):
    table = FakeTable(_portfolio_items())
    monkeypatch.setattr(db, "_get_table", lambda: table)

    assert db.delete_session("cust_delete", "sess_one") is True
    assert ("CUSTOMER#cust_delete", "SESSION#sess_one") not in table.items
    assert not any(pk == "SESSION#sess_one" for pk, _sk in table.items)
    assert table.items[("CUSTOMER#cust_delete", "METADATA")]["session_count"] == 1
    assert ("CUSTOMER#cust_delete", "SESSION#sess_two") in table.items
