from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from email.message import Message

import pytest
from pydantic import ValidationError

from advisor_core.knowledge import (
    CollectionError,
    ReviewMetadata,
    SourceRegistryEntry,
    SourceTerms,
    collect_http,
    normalize_body,
)


RETRIEVED_AT = datetime(2026, 8, 11, 14, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        final_uri: str = "https://docs.example.com/final",
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        self.body = body
        self.status = status
        self.final_uri = final_uri
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["ETag"] = '"abc123"'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, amount: int) -> bytes:
        return self.body[:amount]

    def geturl(self) -> str:
        return self.final_uri


def enabled_source(**overrides) -> SourceRegistryEntry:
    values = {
        "id": "source:example-docs",
        "name": "Example documentation",
        "publisher": "Example",
        "source_class": "official_product_documentation",
        "base_uri": "https://docs.example.com/product",
        "owner_id": "team:platform-advisor",
        "authority_tier": "tier_a_decision_authority",
        "cadence": "weekly",
        "collector": "http",
        "parser": "html",
        "freshness_days": 14,
        "enabled": True,
        "terms": SourceTerms(
            status="approved",
            allows_automated_collection=True,
            allows_snapshot_retention=True,
            allows_derivative_claims=True,
            review=ReviewMetadata(
                status="approved",
                reviewer_ids=("person:source-reviewer",),
                reviewed_at=RETRIEVED_AT,
            ),
        ),
    }
    values.update(overrides)
    return SourceRegistryEntry(**values)


def test_http_collection_preserves_response_and_normalizes_html():
    body = (
        b"<html><head><style>hidden</style></head>"
        b"<body><h1>Runtime</h1><script>ignored()</script>"
        b"<p>Supports   governed execution.</p></body></html>"
    )
    response = FakeResponse(body)

    document = collect_http(
        enabled_source(),
        retrieved_at=RETRIEVED_AT,
        fetcher=lambda request, timeout: response,
    )

    expected_hash = hashlib.sha256(body).hexdigest()
    assert document.raw_body == body
    assert document.raw_content_hash == f"sha256:{expected_hash}"
    assert document.normalized_body == (
        "Runtime\nSupports governed execution."
    )
    assert document.final_uri == "https://docs.example.com/final"
    assert document.media_type == "text/html"
    assert [(header.name, header.value) for header in document.headers] == [
        ("content-type", "text/html; charset=utf-8"),
        ("etag", '"abc123"'),
    ]


def test_json_normalization_is_deterministic():
    first = normalize_body(b'{"b": 2, "a": 1}', parser="json")
    second = normalize_body(b'{\n"a":1,"b":2\n}', parser="json")

    assert first == '{"a":1,"b":2}'
    assert first == second


def test_rss_collection_preserves_structural_text():
    body = (
        b"<rss><channel><title>Releases</title>"
        b"<item><title>Version 2</title><guid>v2</guid></item>"
        b"</channel></rss>"
    )
    response = FakeResponse(
        body,
        content_type="application/rss+xml; charset=utf-8",
    )

    document = collect_http(
        enabled_source(collector="rss", parser="rss"),
        retrieved_at=RETRIEVED_AT,
        fetcher=lambda request, timeout: response,
    )

    assert document.media_type == "application/rss+xml"
    assert document.normalized_body.splitlines() == [
        "rss",
        "channel",
        "title Releases",
        "item",
        "title Version 2",
        "guid v2",
    ]


def test_collection_rejects_disabled_source():
    with pytest.raises(CollectionError, match="source collection is disabled"):
        collect_http(
            enabled_source(enabled=False),
            retrieved_at=RETRIEVED_AT,
            fetcher=lambda request, timeout: FakeResponse(b"unused"),
        )


def test_collection_rejects_oversized_body():
    with pytest.raises(CollectionError, match="source body exceeds 4 bytes"):
        collect_http(
            enabled_source(parser="text"),
            retrieved_at=RETRIEVED_AT,
            max_body_bytes=4,
            fetcher=lambda request, timeout: FakeResponse(
                b"12345",
                content_type="text/plain",
            ),
        )


def test_collection_rejects_non_success_status():
    with pytest.raises(CollectionError, match="HTTP status 503"):
        collect_http(
            enabled_source(),
            retrieved_at=RETRIEVED_AT,
            fetcher=lambda request, timeout: FakeResponse(
                b"Unavailable",
                status=503,
            ),
        )


def test_collected_document_rejects_mismatched_content_hash():
    collected = collect_http(
        enabled_source(),
        retrieved_at=RETRIEVED_AT,
        fetcher=lambda request, timeout: FakeResponse(b"<h1>Runtime</h1>"),
    )
    values = collected.model_dump()
    values["raw_body"] = b"tampered"

    with pytest.raises(
        ValidationError,
        match="raw_content_hash does not match raw_body",
    ):
        type(collected)(**values)
