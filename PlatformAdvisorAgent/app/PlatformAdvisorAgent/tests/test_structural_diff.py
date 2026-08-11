from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from advisor_core.knowledge import (
    CollectedDocument,
    ResponseHeader,
    compare_snapshots,
)


RETRIEVED_AT = datetime(2026, 8, 11, 17, tzinfo=timezone.utc)


def document(
    snapshot_id: str,
    raw_body: bytes,
    *,
    media_type: str = "text/html",
) -> CollectedDocument:
    normalized = raw_body.decode("utf-8")
    return CollectedDocument(
        snapshot_id=snapshot_id,
        source_id="source:example-docs",
        requested_uri="https://docs.example.com/product",
        final_uri="https://docs.example.com/product",
        status_code=200,
        retrieved_at=RETRIEVED_AT,
        headers=(
            ResponseHeader(name="content-type", value=media_type),
        ),
        media_type=media_type,
        raw_body=raw_body,
        normalized_body=normalized,
        raw_content_hash=(
            f"sha256:{hashlib.sha256(raw_body).hexdigest()}"
        ),
        normalized_content_hash=(
            "sha256:"
            f"{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"
        ),
    )


def test_navigation_noise_is_ignored():
    prior = document(
        "snapshot:example-prior",
        (
            b"<html><header>Old banner</header><nav>Docs A</nav>"
            b"<main><h1>Runtime</h1><p>Supports isolation.</p></main>"
            b"<footer>Old footer</footer></html>"
        ),
    )
    current = document(
        "snapshot:example-current",
        (
            b"<html><header>New banner</header><nav>Docs B</nav>"
            b"<main><h1>Runtime</h1><p>Supports isolation.</p></main>"
            b"<footer>New footer</footer></html>"
        ),
    )

    result = compare_snapshots(prior, current)

    assert result.changes == ()
    assert result.ignored_noise_blocks == 6


def test_table_pricing_change_is_preserved_as_decision_relevant():
    prior = document(
        "snapshot:example-prior",
        b"<table><tr><th>Unit</th><th>Price</th></tr>"
        b"<tr><td>Request</td><td>$0.01</td></tr></table>",
    )
    current = document(
        "snapshot:example-current",
        b"<table><tr><th>Unit</th><th>Price</th></tr>"
        b"<tr><td>Request</td><td>$0.02</td></tr></table>",
    )

    result = compare_snapshots(prior, current)

    assert len(result.changes) == 1
    change = result.changes[0]
    assert change.block_type == "table"
    assert change.before == "$0.01"
    assert change.after == "$0.02"
    assert change.significance.value == "decision_relevant"


def test_json_schema_change_is_preserved():
    prior = document(
        "snapshot:example-prior",
        b'{"schema":{"properties":{"mode":{"type":"string"}}}}',
        media_type="application/json",
    )
    current = document(
        "snapshot:example-current",
        (
            b'{"schema":{"properties":{"mode":{"type":"string"},'
            b'"region":{"type":"string"}}}}'
        ),
        media_type="application/json",
    )

    result = compare_snapshots(prior, current)

    assert len(result.changes) == 1
    assert result.changes[0].operation.value == "added"
    assert result.changes[0].block_type == "schema"
    assert result.changes[0].significance.value == "decision_relevant"


def test_descriptive_paragraph_change_remains_informational():
    prior = document(
        "snapshot:example-prior",
        b"<p>Use the runtime for asynchronous work.</p>",
    )
    current = document(
        "snapshot:example-current",
        b"<p>Use the runtime for asynchronous coding work.</p>",
    )

    result = compare_snapshots(prior, current)

    assert len(result.changes) == 1
    assert result.changes[0].significance.value == "informational"
