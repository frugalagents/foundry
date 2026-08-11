"""Immutable storage for raw, normalized, and manifest snapshot artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from botocore.exceptions import ClientError
from pydantic import Field

from .collection import CollectedDocument, ResponseHeader
from .models import FrozenModel, StableId, content_hash


class SnapshotConflictError(RuntimeError):
    pass


class SnapshotManifest(FrozenModel):
    schema_version: str = "1.0"
    snapshot_id: StableId
    source_id: StableId
    retrieved_at: str = Field(min_length=1)
    final_uri: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    headers: tuple[ResponseHeader, ...]
    raw_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    raw_object_key: str = Field(min_length=1)
    normalized_object_key: str = Field(min_length=1)
    manifest_object_key: str = Field(min_length=1)
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class SnapshotStore(Protocol):
    def write(self, document: CollectedDocument) -> SnapshotManifest:
        ...


def _snapshot_keys(
    document: CollectedDocument,
    *,
    prefix: str,
) -> tuple[str, str, str]:
    date_path = document.retrieved_at.strftime("%Y/%m/%d")
    source_slug = document.source_id.split(":", 1)[1]
    root = "/".join(
        part.strip("/")
        for part in (
            prefix,
            source_slug,
            date_path,
            document.snapshot_id,
        )
        if part.strip("/")
    )
    return (
        f"{root}/raw",
        f"{root}/normalized.txt",
        f"{root}/manifest.json",
    )


def build_snapshot_manifest(
    document: CollectedDocument,
    *,
    prefix: str = "knowledge/snapshots",
) -> SnapshotManifest:
    raw_key, normalized_key, manifest_key = _snapshot_keys(
        document,
        prefix=prefix,
    )
    payload = {
        "schema_version": "1.0",
        "snapshot_id": document.snapshot_id,
        "source_id": document.source_id,
        "retrieved_at": document.retrieved_at.isoformat(),
        "final_uri": document.final_uri,
        "media_type": document.media_type,
        "headers": [
            header.model_dump(mode="json") for header in document.headers
        ],
        "raw_content_hash": document.raw_content_hash,
        "normalized_content_hash": document.normalized_content_hash,
        "raw_object_key": raw_key,
        "normalized_object_key": normalized_key,
        "manifest_object_key": manifest_key,
    }
    return SnapshotManifest(
        **payload,
        manifest_hash=content_hash(payload),
    )


def _manifest_bytes(manifest: SnapshotManifest) -> bytes:
    return (
        json.dumps(
            manifest.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


class FilesystemSnapshotStore:
    def __init__(
        self,
        root: Path,
        *,
        prefix: str = "knowledge/snapshots",
    ) -> None:
        self.root = root
        self.prefix = prefix

    def _path(self, key: str) -> Path:
        return self.root / key

    def _write_immutable(self, path: Path, value: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as stream:
                stream.write(value)
        except FileExistsError:
            if path.read_bytes() != value:
                raise SnapshotConflictError(
                    f"immutable snapshot object already exists: {path}"
                ) from None

    def write(self, document: CollectedDocument) -> SnapshotManifest:
        manifest = build_snapshot_manifest(
            document,
            prefix=self.prefix,
        )
        self._write_immutable(
            self._path(manifest.raw_object_key),
            document.raw_body,
        )
        self._write_immutable(
            self._path(manifest.normalized_object_key),
            document.normalized_body.encode("utf-8"),
        )
        self._write_immutable(
            self._path(manifest.manifest_object_key),
            _manifest_bytes(manifest),
        )
        return manifest


class S3SnapshotStore:
    def __init__(
        self,
        client,
        bucket: str,
        *,
        prefix: str = "knowledge/snapshots",
    ) -> None:
        self.client = client
        self.bucket = bucket
        self.prefix = prefix

    def _write_immutable(
        self,
        key: str,
        value: bytes,
        *,
        content_type: str,
    ) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=value,
                ContentType=content_type,
                IfNoneMatch="*",
            )
        except ClientError as error:
            status = error.response.get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            )
            code = error.response.get("Error", {}).get("Code")
            if status != 412 and code not in {
                "PreconditionFailed",
                "ConditionalRequestConflict",
            }:
                raise
            existing = self.client.get_object(
                Bucket=self.bucket,
                Key=key,
            )["Body"].read()
            if existing != value:
                raise SnapshotConflictError(
                    f"immutable S3 snapshot object already exists: {key}"
                ) from error

    def write(self, document: CollectedDocument) -> SnapshotManifest:
        manifest = build_snapshot_manifest(
            document,
            prefix=self.prefix,
        )
        self._write_immutable(
            manifest.raw_object_key,
            document.raw_body,
            content_type=document.media_type,
        )
        self._write_immutable(
            manifest.normalized_object_key,
            document.normalized_body.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )
        self._write_immutable(
            manifest.manifest_object_key,
            _manifest_bytes(manifest),
            content_type="application/json",
        )
        return manifest
