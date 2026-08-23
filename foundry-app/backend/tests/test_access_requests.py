from __future__ import annotations

import asyncio
import hashlib
import unittest
from unittest.mock import MagicMock, patch

from starlette.requests import Request

from api.db.models import (
    AccessRequestActivateIn,
    AccessRequestCreate,
    AccessRequestDecisionIn,
)
from api.routers import access_requests


REQUEST_ID = "req_0123456789abcdef0123456789abcdef"
REQUEST_SECRET = "request-secret-that-is-long-enough-for-validation"


def request_item(status: str = "pending") -> dict:
    return {
        "PK": f"ACCESS_REQUEST#{REQUEST_ID}",
        "SK": f"ACCESS_REQUEST#{REQUEST_ID}",
        "request_id": REQUEST_ID,
        "request_secret_hash": hashlib.sha256(REQUEST_SECRET.encode()).hexdigest(),
        "name": "New User",
        "email": "new.user@example.com",
        "reason": "I need to evaluate the Foundry workflow.",
        "status": status,
        "requested_at": "2026-08-23T12:00:00+00:00",
        "updated_at": "2026-08-23T12:00:00+00:00",
        "expires_at": "2026-08-30T12:00:00+00:00",
        "expires_at_epoch": 1788091200,
    }


class AccessRequestTests(unittest.TestCase):
    def test_create_access_request_stores_only_secret_hash(self) -> None:
        captured: dict = {}

        def save(item: dict) -> dict:
            captured.update(item)
            return item

        request = Request({
            "type": "http",
            "client": ("127.0.0.1", 12345),
            "headers": [(b"user-agent", b"unit-test")],
        })
        body = AccessRequestCreate(
            name="New User",
            email=" New.User@Example.com ",
            reason="I need to evaluate the Foundry workflow.",
        )

        with (
            patch("api.routers.access_requests.db.count_recent_access_requests", return_value=0),
            patch("api.routers.access_requests.db.find_open_access_request", return_value=None),
            patch("api.routers.access_requests.db.create_access_request", side_effect=save),
            patch("api.routers.access_requests._notify_admin"),
        ):
            result = asyncio.run(access_requests.create_access_request(body, request))

        self.assertEqual(captured["email"], "new.user@example.com")
        self.assertEqual(captured["status"], "pending")
        self.assertNotEqual(captured["request_secret_hash"], result.request_secret)
        self.assertEqual(
            captured["request_secret_hash"],
            hashlib.sha256(result.request_secret.encode()).hexdigest(),
        )

    def test_approve_creates_native_user_without_sending_cognito_email(self) -> None:
        item = request_item()
        fake_cognito = MagicMock()
        fake_cognito.list_users.return_value = {"Users": []}
        fake_cognito.admin_create_user.return_value = {
            "User": {
                "Username": "native-user-id",
                "Attributes": [{"Name": "sub", "Value": "native-user-id"}],
            }
        }

        def update(_request_id: str, updates: dict, **_kwargs):
            return {**item, **updates}

        user = {"sub": "admin-sub", "cognito:groups": ["admin"]}
        with (
            patch.object(access_requests, "USER_POOL_ID", "pool-id"),
            patch("api.routers.access_requests._cognito_client", return_value=fake_cognito),
            patch("api.routers.access_requests.db.get_access_request", return_value=item),
            patch("api.routers.access_requests.db.update_access_request", side_effect=update),
        ):
            result = asyncio.run(
                access_requests.approve_access_request(
                    REQUEST_ID,
                    AccessRequestDecisionIn(note="Approved for pilot"),
                    user,
                )
            )

        self.assertEqual(result.status, "approved")
        create_call = fake_cognito.admin_create_user.call_args.kwargs
        self.assertEqual(create_call["Username"], "new.user@example.com")
        self.assertEqual(create_call["MessageAction"], "SUPPRESS")

    def test_activation_sets_permanent_password(self) -> None:
        item = {
            **request_item("approved"),
            "cognito_username": "native-user-id",
        }
        fake_cognito = MagicMock()

        def update(_request_id: str, updates: dict, **_kwargs):
            return {**item, **updates}

        with (
            patch.object(access_requests, "USER_POOL_ID", "pool-id"),
            patch("api.routers.access_requests._cognito_client", return_value=fake_cognito),
            patch("api.routers.access_requests.db.get_access_request", return_value=item),
            patch("api.routers.access_requests.db.update_access_request", side_effect=update),
        ):
            result = asyncio.run(
                access_requests.activate_access_request(
                    AccessRequestActivateIn(
                        request_id=REQUEST_ID,
                        request_secret=REQUEST_SECRET,
                        password="SecureFoundry2026",
                    )
                )
            )

        self.assertEqual(result.status, "activated")
        fake_cognito.admin_set_user_password.assert_called_once_with(
            UserPoolId="pool-id",
            Username="native-user-id",
            Password="SecureFoundry2026",
            Permanent=True,
        )


if __name__ == "__main__":
    unittest.main()
