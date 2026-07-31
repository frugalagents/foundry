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
