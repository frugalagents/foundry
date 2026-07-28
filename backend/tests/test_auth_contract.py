from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from api import pre_token
from api.middleware.auth import require_admin


def test_require_admin_accepts_custom_role():
    user = {"sub": "admin-user", "custom:role": "admin"}

    assert asyncio.run(require_admin(user)) == user


def test_require_admin_accepts_cognito_group():
    user = {"sub": "admin-user", "cognito:groups": ["admin", "user"]}

    assert asyncio.run(require_admin(user)) == user


def test_require_admin_rejects_normal_user():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(require_admin({
            "sub": "normal-user",
            "custom:role": "user",
            "cognito:groups": ["user"],
        }))

    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("amazon_alias", ["aigopala", "thandavm"])
def test_pre_token_marks_configured_alias_as_admin(monkeypatch, amazon_alias):
    monkeypatch.setattr(pre_token, "ADMIN_ALIASES", {"aigopala", "thandavm"})
    event = {
        "request": {
            "userAttributes": {
                "custom:amazon_alias": amazon_alias,
            },
        },
        "response": {},
    }

    result = pre_token.handler(event, None)
    override = result["response"]["claimsOverrideDetails"]

    assert override["claimsToAddOrOverride"]["custom:role"] == "admin"
    assert override["groupOverrideDetails"]["groupsToOverride"] == ["admin", "user"]


def test_pre_token_does_not_grant_admin_to_other_alias(monkeypatch):
    monkeypatch.setattr(pre_token, "ADMIN_ALIASES", {"aigopala", "thandavm"})
    event = {
        "request": {
            "userAttributes": {
                "custom:amazon_alias": "someone-else",
            },
        },
        "response": {},
    }

    result = pre_token.handler(event, None)
    override = result["response"]["claimsOverrideDetails"]

    assert override["claimsToAddOrOverride"]["custom:role"] == "user"
    assert "groupOverrideDetails" not in override
