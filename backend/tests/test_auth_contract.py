from __future__ import annotations

import asyncio
import json

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


def test_pre_token_marks_cognito_admin_group_member_as_admin(monkeypatch):
    monkeypatch.setattr(pre_token, "ADMIN_GROUP", "admin")
    event = {
        "request": {
            "groupConfiguration": {
                "groupsToOverride": ["admin", "user"],
            },
        },
        "response": {},
    }

    result = pre_token.handler(event, None)
    override = result["response"]["claimsOverrideDetails"]

    assert override["claimsToAddOrOverride"]["custom:role"] == "admin"
    assert "groupOverrideDetails" not in override


def test_pre_token_ignores_self_asserted_privileged_attributes(monkeypatch):
    monkeypatch.setattr(pre_token, "ADMIN_GROUP", "admin")
    monkeypatch.setattr(pre_token, "ADMIN_ALIAS_MIGRATION_ENABLED", False)
    monkeypatch.setattr(pre_token, "ADMIN_ALIASES", {"trusted-looking-alias"})
    event = {
        "request": {
            "userAttributes": {
                "custom:amazon_alias": "trusted-looking-alias",
                "custom:role": "admin",
            },
            "groupConfiguration": {"groupsToOverride": ["user"]},
        },
        "response": {},
    }

    result = pre_token.handler(event, None)
    override = result["response"]["claimsOverrideDetails"]

    assert override["claimsToAddOrOverride"]["custom:role"] == "user"
    assert "groupOverrideDetails" not in override


def test_pre_token_alias_fallback_is_explicitly_migration_only(monkeypatch):
    monkeypatch.setattr(pre_token, "ADMIN_GROUP", "admin")
    monkeypatch.setattr(pre_token, "ADMIN_ALIAS_MIGRATION_ENABLED", True)
    monkeypatch.setattr(pre_token, "ADMIN_ALIASES", {"aigopala"})
    event = {
        "request": {
            "userAttributes": {
                "custom:amazon_alias": "aigopala",
                "identities": json.dumps([{
                    "userId": "aigopala",
                    "providerName": "Midway",
                }]),
            },
            "groupConfiguration": {"groupsToOverride": ["user"]},
        },
        "response": {},
    }

    result = pre_token.handler(event, None)

    assert result["response"]["claimsOverrideDetails"][
        "claimsToAddOrOverride"
    ]["custom:role"] == "admin"


def test_pre_token_migration_preserves_verified_local_admin_username(monkeypatch):
    local_admin_username = "54186488-f0f1-707c-924b-d4a4c749e934"
    monkeypatch.setattr(pre_token, "ADMIN_GROUP", "admin")
    monkeypatch.setattr(pre_token, "ADMIN_ALIAS_MIGRATION_ENABLED", True)
    monkeypatch.setattr(
        pre_token,
        "ADMIN_ALIASES",
        {local_admin_username},
    )
    event = {
        "userName": local_admin_username,
        "request": {
            "userAttributes": {"email": "admin@platform-advisor.com"},
            "groupConfiguration": {"groupsToOverride": ["user"]},
        },
        "response": {},
    }

    result = pre_token.handler(event, None)

    assert result["response"]["claimsOverrideDetails"][
        "claimsToAddOrOverride"
    ]["custom:role"] == "admin"


def test_pre_token_does_not_trust_unanchored_midway_alias(monkeypatch):
    monkeypatch.setattr(pre_token, "ADMIN_ALIAS_MIGRATION_ENABLED", True)
    monkeypatch.setattr(pre_token, "ADMIN_ALIASES", {"aigopala"})

    result = pre_token.handler(
        {
            "userName": "normal-user",
            "request": {
                "userAttributes": {
                    "custom:amazon_alias": "aigopala",
                    "identities": json.dumps([{
                        "userId": "different-user",
                        "providerName": "Midway",
                    }]),
                },
            },
            "response": {},
        },
        None,
    )

    assert result["response"]["claimsOverrideDetails"][
        "claimsToAddOrOverride"
    ]["custom:role"] == "user"


def test_pre_token_migration_fallback_requires_nonempty_verified_identity(
    monkeypatch,
):
    monkeypatch.setattr(pre_token, "ADMIN_ALIAS_MIGRATION_ENABLED", True)
    monkeypatch.setattr(pre_token, "ADMIN_ALIASES", {""})

    result = pre_token.handler(
        {
            "request": {
                "userAttributes": {"custom:amazon_alias": ""},
                "groupConfiguration": {"groupsToOverride": ["user"]},
            },
            "response": {},
        },
        None,
    )

    assert result["response"]["claimsOverrideDetails"][
        "claimsToAddOrOverride"
    ]["custom:role"] == "user"


def test_pre_token_defaults_to_user_without_group_configuration(monkeypatch):
    monkeypatch.setattr(pre_token, "ADMIN_GROUP", "admin")

    result = pre_token.handler({"request": {}, "response": {}}, None)

    assert result["response"]["claimsOverrideDetails"] == {
        "claimsToAddOrOverride": {"custom:role": "user"},
    }
