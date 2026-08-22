from __future__ import annotations

import unittest
from unittest.mock import patch

from api.db import dynamodb as db


class FakeTable:
    def __init__(self) -> None:
        self.scan_calls = 0
        self.query_calls = 0

    def scan(self, **kwargs):
        self.scan_calls += 1
        if self.scan_calls == 1:
            return {
                "Items": [],
                "LastEvaluatedKey": {"PK": "page-1", "SK": "page-1"},
            }
        return {
            "Items": [
                {
                    "customer_id": "cust-1",
                    "name": "Workspace 1",
                    "created_by": "user-1",
                    "created_at": "2026-08-22T10:00:00+00:00",
                    "updated_at": "2026-08-22T10:00:00+00:00",
                },
            ],
        }

    def query(self, **kwargs):
        self.query_calls += 1
        if self.query_calls == 1:
            return {
                "Items": [
                    {
                        "session_id": "sess-1",
                        "customer_id": "cust-1",
                        "title": "First",
                        "updated_at": "2026-08-22T10:01:00+00:00",
                    },
                ],
                "LastEvaluatedKey": {"PK": "page-1", "SK": "page-1"},
            }
        return {
            "Items": [
                {
                    "session_id": "sess-2",
                    "customer_id": "cust-1",
                    "title": "Second",
                    "updated_at": "2026-08-22T10:02:00+00:00",
                },
            ],
        }


class DynamoPaginationTests(unittest.TestCase):
    def test_list_customers_consumes_all_scan_pages(self) -> None:
        table = FakeTable()
        with patch("api.db.dynamodb._get_table", return_value=table):
            customers = db.list_customers(created_by=None, include_demo=True)

        self.assertEqual(table.scan_calls, 2)
        self.assertEqual([c["customer_id"] for c in customers], ["cust-1"])

    def test_list_sessions_consumes_all_query_pages_and_sorts(self) -> None:
        table = FakeTable()
        with patch("api.db.dynamodb._get_table", return_value=table):
            sessions = db.list_sessions("cust-1", created_by=None)

        self.assertEqual(table.query_calls, 2)
        self.assertEqual([s["session_id"] for s in sessions], ["sess-2", "sess-1"])


if __name__ == "__main__":
    unittest.main()
