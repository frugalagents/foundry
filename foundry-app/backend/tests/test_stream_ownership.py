from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api.routers.stream import StreamRequest, stream_session


class StreamOwnershipTests(unittest.TestCase):
    def test_admin_cannot_stream_to_another_users_session(self) -> None:
        user = {
            "sub": "admin-sub",
            "cognito:groups": ["foundry-admins"],
            "_raw_token": "token",
        }
        customer = {
            "customer_id": "cust-other",
            "created_by": "other-sub",
        }
        session = {
            "session_id": "sess-other",
            "customer_id": "cust-other",
            "created_by": "other-sub",
            "module_id": "coding-agent",
        }

        with (
            patch("api.routers.stream.db.get_customer", return_value=customer),
            patch("api.routers.stream.db.get_session", return_value=session),
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    stream_session(
                        "cust-other",
                        "sess-other",
                        StreamRequest(message="hello"),
                        user,
                    ),
                )

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail, "Customer is read-only for admins")


if __name__ == "__main__":
    unittest.main()
