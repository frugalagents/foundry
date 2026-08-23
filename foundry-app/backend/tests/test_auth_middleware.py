from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from api.middleware import auth


class AuthMiddlewareTests(unittest.TestCase):
    def test_guest_tokens_are_rejected_after_event_cutoff(self) -> None:
        request = Request({"type": "http", "query_string": b""})
        creds = type("Creds", (), {"credentials": "token"})()
        guest_payload = {
            "sub": "guest-sub",
            "client_id": "client-id",
            "token_use": "access",
            "cognito:groups": ["foundry-guests"],
        }

        with (
            patch.object(auth, "DEV_MODE", False),
            patch("api.middleware.auth._decode_cognito_token", return_value=guest_payload),
            patch("api.middleware.auth.guest_access_window_closed", return_value=True),
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(auth.get_current_user(request, creds))

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail, "Guest access for this event has ended")


if __name__ == "__main__":
    unittest.main()
