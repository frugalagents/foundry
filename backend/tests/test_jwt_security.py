from __future__ import annotations

import asyncio
import base64
import json
import time

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from starlette.requests import Request

from api.middleware import auth


REGION = "us-east-1"
USER_POOL_ID = "us-east-1_security"
CLIENT_ID = "platform-advisor-client"
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
KID = "security-test-key"


def _base64url_uint(value: int) -> str:
    width = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(
        value.to_bytes(width, "big")
    ).decode().rstrip("=")


@pytest.fixture(scope="module")
def signing_material():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    public_jwk = {
        "kty": "RSA",
        "kid": KID,
        "use": "sig",
        "alg": "RS256",
        "n": _base64url_uint(public_numbers.n),
        "e": _base64url_uint(public_numbers.e),
    }
    return private_key, {"keys": [public_jwk]}


@pytest.fixture(autouse=True)
def cognito_config(monkeypatch, signing_material):
    _, jwks = signing_material
    monkeypatch.setattr(auth, "DEV_MODE", False)
    monkeypatch.setattr(auth, "COGNITO_REGION", REGION)
    monkeypatch.setattr(auth, "COGNITO_USER_POOL_ID", USER_POOL_ID)
    monkeypatch.setattr(auth, "COGNITO_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(auth, "COGNITO_REQUIRED_SCOPE", "")
    monkeypatch.setattr(auth, "_get_jwks", lambda: jwks)


def _claims(**overrides) -> dict:
    now = int(time.time())
    claims = {
        "sub": "trusted-actor",
        "iss": ISSUER,
        "exp": now + 300,
        "iat": now,
        "token_use": "access",
        "client_id": CLIENT_ID,
        "scope": "openid architecture:read",
        "custom:tenant_id": "trusted-tenant",
    }
    claims.update(overrides)
    return claims


def _token(private_key, *, omit_claims=(), **claim_overrides) -> str:
    claims = _claims(**claim_overrides)
    for claim in omit_claims:
        claims.pop(claim, None)
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": KID},
    )


def _request(*, gateway_claims: dict | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/protected",
        "headers": [],
        "query_string": b"",
    }
    if gateway_claims is not None:
        scope["aws.event"] = {
            "requestContext": {
                "authorizer": {"jwt": {"claims": gateway_claims}},
            },
        }
    return Request(scope)


def _authenticate(token: str) -> dict:
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    return asyncio.run(auth.get_current_user(_request(), credentials))


def _assert_rejected(token: str, status_code: int, detail: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _authenticate(token)

    assert exc_info.value.status_code == status_code
    assert detail in exc_info.value.detail


def _tamper_claim(token: str, claim: str, value: str) -> str:
    header, payload, signature = token.split(".")
    decoded = json.loads(
        base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    )
    decoded[claim] = value
    forged_payload = base64.urlsafe_b64encode(
        json.dumps(decoded, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    return f"{header}.{forged_payload}.{signature}"


def test_valid_cognito_access_token_is_accepted(signing_material):
    private_key, _ = signing_material

    user = _authenticate(_token(private_key))

    assert user["sub"] == "trusted-actor"
    assert user["custom:tenant_id"] == "trusted-tenant"


def test_id_token_cannot_be_used_as_an_access_token(signing_material):
    private_key, _ = signing_material

    _assert_rejected(
        _token(private_key, token_use="id", aud=CLIENT_ID),
        401,
        "Access token required",
    )


@pytest.mark.parametrize(
    ("overrides", "detail"),
    [
        ({"iss": f"{ISSUER}-other"}, "Invalid issuer"),
        ({"client_id": "another-client"}, "client_id does not match"),
    ],
)
def test_wrong_issuer_or_client_is_rejected(
    signing_material,
    overrides,
    detail,
):
    private_key, _ = signing_material

    _assert_rejected(_token(private_key, **overrides), 401, detail)


def test_expired_token_is_rejected(signing_material):
    private_key, _ = signing_material

    _assert_rejected(
        _token(private_key, exp=int(time.time()) - 1),
        401,
        "Signature has expired",
    )


@pytest.mark.parametrize("claim", ["exp", "iss", "sub"])
def test_required_identity_claims_cannot_be_omitted(signing_material, claim):
    private_key, _ = signing_material

    _assert_rejected(
        _token(private_key, omit_claims=(claim,)),
        401,
        f'missing required key "{claim}"',
    )


def test_missing_configured_scope_is_forbidden(monkeypatch, signing_material):
    private_key, _ = signing_material
    monkeypatch.setattr(auth, "COGNITO_REQUIRED_SCOPE", "architecture:write")

    _assert_rejected(
        _token(private_key, scope="openid architecture:read"),
        403,
        "Missing required scope: architecture:write",
    )


def test_configured_scope_is_accepted(monkeypatch, signing_material):
    private_key, _ = signing_material
    monkeypatch.setattr(auth, "COGNITO_REQUIRED_SCOPE", "architecture:read")

    assert _authenticate(_token(private_key))["sub"] == "trusted-actor"


@pytest.mark.parametrize(
    ("claim", "forged_value"),
    [
        ("sub", "forged-actor"),
        ("custom:tenant_id", "forged-tenant"),
    ],
)
def test_actor_and_tenant_claims_cannot_be_forged(
    signing_material,
    claim,
    forged_value,
):
    private_key, _ = signing_material
    forged = _tamper_claim(_token(private_key), claim, forged_value)

    _assert_rejected(forged, 401, "Signature verification failed")


def test_api_gateway_claims_do_not_bypass_backend_verification():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            auth.get_current_user(
                _request(gateway_claims=_claims()),
                None,
            )
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing token"


def test_production_authentication_fails_closed_without_configuration(
    monkeypatch,
    signing_material,
):
    private_key, _ = signing_material
    monkeypatch.setattr(auth, "COGNITO_CLIENT_ID", "")

    _assert_rejected(
        _token(private_key),
        401,
        "Cognito authentication is not configured",
    )


def test_malformed_jwks_fails_closed(monkeypatch, signing_material):
    private_key, _ = signing_material
    monkeypatch.setattr(auth, "_get_jwks", lambda: {"keys": "not-a-list"})

    _assert_rejected(_token(private_key), 401, "Invalid JWKS")
