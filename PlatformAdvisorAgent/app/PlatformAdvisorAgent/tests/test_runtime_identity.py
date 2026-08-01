import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import main


def test_cognito_token_header_is_in_runtime_allowlist():
    config_path = Path(__file__).parents[3] / "agentcore" / "agentcore.json"
    config = json.loads(config_path.read_text())
    runtime = config["runtimes"][0]

    assert main._COGNITO_TOKEN_HEADER in {
        header.lower() for header in runtime["requestHeaderAllowlist"]
    }


def test_runtime_actor_id_verifies_forwarded_cognito_token(monkeypatch):
    context = SimpleNamespace(
        request_headers={
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Cognito-Id-Token": "jwt",
        },
    )
    signing_key = SimpleNamespace(key="public-key")
    jwk_client = SimpleNamespace(get_signing_key_from_jwt=lambda token: signing_key)
    monkeypatch.setattr(main, "_COGNITO_USER_POOL_ID", "us-east-1_pool")
    monkeypatch.setattr(main, "_COGNITO_CLIENT_ID", "client-id")
    monkeypatch.setattr(main, "_cognito_jwk_client", lambda: jwk_client)
    monkeypatch.setattr(
        main.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "cognito-user-123",
            "token_use": "id",
        },
    )

    assert main._runtime_actor_id(context) == "cognito-user-123"


def test_runtime_tenant_id_uses_trusted_claim_then_actor_fallback():
    assert main._runtime_tenant_id(
        {"custom:tenant_id": "tenant-one"},
        "actor-one",
    ) == "tenant-one"
    assert main._runtime_tenant_id({}, "actor-one") == "actor-one"


def test_runtime_actor_id_rejects_access_token(monkeypatch):
    context = SimpleNamespace(
        request_headers={
            "x-amzn-bedrock-agentcore-runtime-custom-cognito-id-token": "jwt",
        },
    )
    signing_key = SimpleNamespace(key="public-key")
    jwk_client = SimpleNamespace(get_signing_key_from_jwt=lambda token: signing_key)
    monkeypatch.setattr(main, "_COGNITO_USER_POOL_ID", "us-east-1_pool")
    monkeypatch.setattr(main, "_COGNITO_CLIENT_ID", "client-id")
    monkeypatch.setattr(main, "_cognito_jwk_client", lambda: jwk_client)
    monkeypatch.setattr(
        main.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "cognito-user-123",
            "token_use": "access",
        },
    )

    assert main._runtime_actor_id(context) is None


def test_runtime_actor_id_fails_closed_without_trusted_identity():
    context = SimpleNamespace(request_headers={})

    assert main._runtime_actor_id(context) is None


def test_entrypoint_dispatches_versioned_v3_action_without_v2_agent(
    monkeypatch,
):
    calls = {}

    class FakeAdapter:
        def __init__(self, table, **scope):
            calls["table"] = table
            calls["scope"] = scope

        def execute(self, request):
            calls["request"] = request
            return {
                "contract_version": "3.0",
                "action": "architecture.v3.workspace",
                "operation": "get",
                "projection": {"schema_version": "3.0"},
            }

    table = object()
    ddb = SimpleNamespace(Table=lambda name: table)
    monkeypatch.setattr(
        main,
        "_runtime_identity_claims",
        lambda context: {
            "sub": "actor-one",
            "custom:tenant_id": "tenant-one",
        },
    )
    monkeypatch.setattr(main, "_session_is_owned", lambda *args: True)
    monkeypatch.setattr(main, "_get_ddb", lambda: ddb)
    monkeypatch.setattr(main, "ArchitectureV3RuntimeAdapter", FakeAdapter)

    async def collect():
        return [
            event
            async for event in main.invoke(
                {
                    "action": "architecture.v3.workspace",
                    "customer_id": "cust-one",
                    "session_id": "sess-one",
                    "architecture_v3": {
                        "schema_version": "3.0",
                        "operation": "get",
                    },
                },
                SimpleNamespace(session_id="runtime-session"),
            )
        ]

    events = asyncio.run(collect())

    assert events[0].startswith("event: architecture_v3_complete\n")
    assert events[1].startswith("event: complete\n")
    assert calls == {
        "table": table,
        "scope": {
            "tenant_id": "tenant-one",
            "owner_id": "actor-one",
            "customer_id": "cust-one",
            "session_id": "sess-one",
        },
        "request": {
            "schema_version": "3.0",
            "operation": "get",
        },
    }


def test_existing_v2_questionnaire_protocol_is_unchanged():
    async def collect():
        return [
            event
            async for event in main.invoke(
                {
                    "action": "questionnaire",
                    "customer_id": "cust-one",
                    "session_id": "sess-one",
                    "primary_workload": "coding",
                },
                SimpleNamespace(session_id="runtime-session"),
            )
        ]

    events = asyncio.run(collect())
    payload = json.loads(events[0].split("data: ", 1)[1])

    assert events[0].startswith("event: panel_complete\n")
    assert payload["data"]["panel_type"] == "intake"
    assert payload["data"]["data"]["schema_version"] == "2.0"
    assert events[1].startswith("event: complete\n")
