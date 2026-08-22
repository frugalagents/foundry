from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api.routers.admin import list_admin_sessions


class AdminSessionsTests(unittest.TestCase):
    def test_admin_receives_all_sessions_across_customers(self) -> None:
        user = {
            "sub": "admin-sub",
            "cognito:groups": ["admin"],
        }
        customers = [
            {
                "customer_id": "cust-a",
                "name": "Workspace A",
                "created_by": "user-a",
                "created_at": "2026-08-22T10:00:00+00:00",
                "updated_at": "2026-08-22T10:00:00+00:00",
            },
            {
                "customer_id": "cust-b",
                "name": "Workspace B",
                "created_by": "user-b",
                "created_at": "2026-08-22T11:00:00+00:00",
                "updated_at": "2026-08-22T11:00:00+00:00",
            },
        ]
        sessions_by_customer = {
            "cust-a": [
                {
                    "session_id": "sess-a1",
                    "customer_id": "cust-a",
                    "title": "A1",
                    "status": "active",
                    "current_step": 0,
                    "created_by": "user-a",
                    "created_at": "2026-08-22T10:01:00+00:00",
                    "updated_at": "2026-08-22T10:02:00+00:00",
                },
            ],
            "cust-b": [
                {
                    "session_id": "sess-b1",
                    "customer_id": "cust-b",
                    "title": "B1",
                    "status": "active",
                    "current_step": 0,
                    "created_by": "user-b",
                    "created_at": "2026-08-22T11:01:00+00:00",
                    "updated_at": "2026-08-22T11:03:00+00:00",
                },
            ],
        }

        with (
            patch("api.routers.admin.db.list_customers", return_value=customers),
            patch(
                "api.routers.admin.db.list_sessions",
                side_effect=lambda customer_id, created_by=None: sessions_by_customer[customer_id],
            ),
        ):
            rows = asyncio.run(list_admin_sessions(user))

        self.assertEqual([row.session.session_id for row in rows], ["sess-b1", "sess-a1"])
        self.assertEqual(rows[0].customer.name, "Workspace B")
        self.assertEqual(rows[1].customer.name, "Workspace A")

    def test_non_admin_is_rejected(self) -> None:
        user = {
            "sub": "regular-sub",
            "cognito:groups": ["user"],
        }

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(list_admin_sessions(user))

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail, "Admin access required")


if __name__ == "__main__":
    unittest.main()
