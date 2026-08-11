from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from io import BytesIO

import pytest
from botocore.exceptions import ClientError

from advisor_core.knowledge import (
    CollectedDocument,
    FilesystemSnapshotStore,
    ResponseHeader,
    S3SnapshotStore,
    SnapshotConflictError,
)


RETRIEVED_AT = datetime(2026, 8, 11, 16, tzinfo=timezone.utc)


def document(raw_body: bytes = b"<h1>Runtime</h1>") -> CollectedDocument:
    normalized_body = "Runtime"
    return CollectedDocument(
        snapshot_id="snapshot:example-docs-abc123def456",
        source_id="source:example-docs",
        requested_uri="https://docs.example.com/runtime",
        final_uri="https://docs.example.com/runtime",
        status_code=200,
        retrieved_at=RETRIEVED_AT,
        headers=(
            ResponseHeader(name="content-type", value="text/html"),
        ),
        media_type="text/html",
        raw_body=raw_body,
        normalized_body=normalized_body,
        raw_content_hash=(
            f"sha256:{hashlib.sha256(raw_body).hexdigest()}"
        ),
        normalized_content_hash=(
            "sha256:"
            f"{hashlib.sha256(normalized_body.encode('utf-8')).hexdigest()}"
        ),
    )


def test_filesystem_store_writes_raw_normalized_and_manifest(tmp_path):
    store = FilesystemSnapshotStore(tmp_path)

    manifest = store.write(document())

    assert (tmp_path / manifest.raw_object_key).read_bytes() == (
        b"<h1>Runtime</h1>"
    )
    assert (tmp_path / manifest.normalized_object_key).read_text(
        encoding="utf-8"
    ) == "Runtime"
    manifest_text = (tmp_path / manifest.manifest_object_key).read_text(
        encoding="utf-8"
    )
    assert manifest.manifest_hash in manifest_text


def test_filesystem_store_is_idempotent_for_identical_snapshot(tmp_path):
    store = FilesystemSnapshotStore(tmp_path)
    first = store.write(document())
    second = store.write(document())

    assert first == second


def test_filesystem_store_rejects_destructive_overwrite(tmp_path):
    store = FilesystemSnapshotStore(tmp_path)
    manifest = store.write(document())
    (tmp_path / manifest.raw_object_key).write_bytes(b"tampered")

    with pytest.raises(
        SnapshotConflictError,
        match="immutable snapshot object already exists",
    ):
        store.write(document())


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, **kwargs):
        identity = (kwargs["Bucket"], kwargs["Key"])
        value = kwargs["Body"]
        if identity in self.objects:
            raise ClientError(
                {
                    "Error": {
                        "Code": "PreconditionFailed",
                        "Message": "Object exists",
                    },
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "PutObject",
            )
        self.objects[identity] = value
        return {"ETag": '"example"'}

    def get_object(self, **kwargs):
        identity = (kwargs["Bucket"], kwargs["Key"])
        return {"Body": BytesIO(self.objects[identity])}


def test_s3_store_uses_conditional_idempotent_writes():
    client = FakeS3Client()
    store = S3SnapshotStore(client, "knowledge-bucket")

    manifest = store.write(document())
    repeated = store.write(document())

    assert manifest == repeated
    assert len(client.objects) == 3
    assert (
        "knowledge-bucket",
        manifest.manifest_object_key,
    ) in client.objects
