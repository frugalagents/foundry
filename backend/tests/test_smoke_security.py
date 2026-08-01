from __future__ import annotations

import json
from pathlib import Path

import pytest

import smoke_test


class _SecretClient:
    def __init__(self, secret: dict[str, str]):
        self.secret = secret
        self.requested_secret_id = None

    def get_secret_value(self, *, SecretId: str) -> dict[str, str]:
        self.requested_secret_id = SecretId
        return {"SecretString": json.dumps(self.secret)}


class _S3Client:
    def get_bucket_versioning(self, *, Bucket: str) -> dict[str, str]:
        assert Bucket == smoke_test.S3_BUCKET
        return {"Status": "Enabled"}

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        assert Bucket == smoke_test.S3_BUCKET
        assert Key == smoke_test.FRONTEND_ENTRY_KEY
        return {
            "ContentLength": 321,
            "VersionId": "entry-version-2",
            "Metadata": {"deployment-sha256": "a" * 64},
        }


def test_smoke_credentials_have_no_built_in_defaults(monkeypatch):
    monkeypatch.delenv("TEST_SECRET_ID", raising=False)
    monkeypatch.delenv("TEST_EMAIL", raising=False)
    monkeypatch.delenv("TEST_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="Smoke credentials are required"):
        smoke_test.load_test_credentials()


def test_smoke_credentials_can_be_injected_by_environment(monkeypatch):
    monkeypatch.delenv("TEST_SECRET_ID", raising=False)
    monkeypatch.setenv("TEST_EMAIL", "smoke@example.com")
    monkeypatch.setenv("TEST_PASSWORD", "injected-password")

    assert smoke_test.load_test_credentials() == (
        "smoke@example.com",
        "injected-password",
    )


def test_smoke_secret_takes_precedence_over_environment(monkeypatch):
    monkeypatch.setenv("TEST_SECRET_ID", "platform-advisor/dev/smoke")
    monkeypatch.setenv("TEST_EMAIL", "ignored@example.com")
    monkeypatch.setenv("TEST_PASSWORD", "ignored-password")
    client = _SecretClient({
        "username": "secret@example.com",
        "password": "secret-password",
    })

    credentials = smoke_test.load_test_credentials(secret_client=client)

    assert credentials == ("secret@example.com", "secret-password")
    assert client.requested_secret_id == "platform-advisor/dev/smoke"


def test_frontend_smoke_requires_versioned_hash_marked_entry_object():
    detail = smoke_test.require_frontend_deployment_controls(
        s3_client=_S3Client()
    )

    assert "entry-version-2" in detail
    assert "a" * 12 in detail


def test_frontend_smoke_rejects_unversioned_bucket():
    class _UnversionedS3Client(_S3Client):
        def get_bucket_versioning(self, *, Bucket: str) -> dict[str, str]:
            return {}

    with pytest.raises(AssertionError, match="versioning"):
        smoke_test.require_frontend_deployment_controls(
            s3_client=_UnversionedS3Client()
        )


def test_smoke_validates_customer_cascade_without_direct_workspace_delete():
    source = Path(smoke_test.__file__).read_text(encoding="utf-8")

    assert "delete_architecture_workspace" not in source
    assert ".delete_item(" not in source
    assert "architecture_workspace_exists" in source
    assert "Verify architecture workspace cascade" in source


def test_admin_forbidden_response_is_not_counted_as_smoke_success():
    source = Path(smoke_test.__file__).read_text(encoding="utf-8")

    assert "skipped (non-admin" not in source
    assert 'api("GET", "/admin/metrics", token)' in source
    assert 'api("GET", "/admin/engine", token)' in source
