from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from advisor_core.knowledge import (
    KmsReleaseSigner,
    KnowledgeReleaseArtifacts,
    KnowledgeReleaseManifest,
    PublicationAuthorization,
    ReleaseArtifactFile,
    ReleasePublicationConflictError,
    ReleasePublicationError,
    S3ReleasePublisher,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
RELEASE_ROOT = (
    REPOSITORY_ROOT
    / "knowledge"
    / "releases"
    / "coding-platform"
    / "1.5.0"
)
SIGNED_AT = datetime.fromisoformat("2026-08-11T13:00:00+00:00")


class FakeKmsClient:
    key_id = "arn:aws:kms:eu-central-1:111122223333:key/release-signing"

    def sign(self, **request):
        assert request["MessageType"] == "DIGEST"
        assert len(request["Message"]) == 32
        return {
            "KeyId": self.key_id,
            "Signature": b"signed:" + request["Message"],
        }

    def verify(self, **request):
        return {
            "SignatureValid": (
                request["Signature"] == b"signed:" + request["Message"]
            )
        }


class FakeBody:
    def __init__(self, value: bytes):
        self.value = value

    def read(self) -> bytes:
        return self.value


class FakeS3Client:
    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, **request):
        identity = (request["Bucket"], request["Key"])
        if identity in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "PutObject",
            )
        self.objects[identity] = bytes(request["Body"])
        return {"ETag": '"example"'}

    def get_object(self, **request):
        return {
            "Body": FakeBody(
                self.objects[(request["Bucket"], request["Key"])]
            )
        }


def checked_release() -> KnowledgeReleaseArtifacts:
    manifest = KnowledgeReleaseManifest.model_validate_json(
        (RELEASE_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    return KnowledgeReleaseArtifacts(
        manifest=manifest,
        files=tuple(
            ReleaseArtifactFile(
                path=record.path,
                media_type=record.media_type,
                content=(RELEASE_ROOT / record.path).read_text(
                    encoding="utf-8"
                ),
                content_hash=record.content_hash,
                size_bytes=record.size_bytes,
            )
            for record in manifest.files
        ),
    )


def authorization(*, authorized: bool = True) -> PublicationAuthorization:
    return PublicationAuthorization(
        principal_id="pipeline:knowledge-release",
        principal_type="release_pipeline",
        action="publish_catalog",
        authorized=authorized,
        reason="Release validation and review gates passed.",
    )


def test_kms_signature_verifies_manifest_digest():
    artifacts = checked_release()
    signer = KmsReleaseSigner(FakeKmsClient(), FakeKmsClient.key_id)

    signature = signer.sign(artifacts, signed_at=SIGNED_AT)

    assert signature.manifest_hash == artifacts.manifest.manifest_hash
    assert signer.verify(signature)


def test_s3_publication_is_immutable_and_idempotent():
    artifacts = checked_release()
    signer = KmsReleaseSigner(FakeKmsClient(), FakeKmsClient.key_id)
    signature = signer.sign(artifacts, signed_at=SIGNED_AT)
    client = FakeS3Client()
    publisher = S3ReleasePublisher(
        client,
        "knowledge-release-bucket",
        kms_key_id="alias/knowledge-release-storage",
    )

    first = publisher.publish(
        artifacts,
        signature,
        authorization(),
    )
    second = publisher.publish(
        artifacts,
        signature,
        authorization(),
    )

    assert first == second
    assert len(first.objects) == len(artifacts.files) + 2
    assert first.prefix.endswith(
        "/release/coding-platform-knowledge/1.5.0"
    )

    signature_key = next(
        record.key
        for record in first.objects
        if record.key.endswith("/signature.json")
    )
    client.objects[(client.objects.keys().__iter__().__next__()[0], signature_key)] = (
        b"conflict"
    )
    with pytest.raises(
        ReleasePublicationConflictError,
        match="already differs",
    ):
        publisher.publish(artifacts, signature, authorization())


def test_publication_rejects_unauthorized_or_mismatched_signature():
    artifacts = checked_release()
    signer = KmsReleaseSigner(FakeKmsClient(), FakeKmsClient.key_id)
    signature = signer.sign(artifacts, signed_at=SIGNED_AT)
    publisher = S3ReleasePublisher(FakeS3Client(), "release-bucket")

    with pytest.raises(
        ReleasePublicationError,
        match="release-pipeline authorization",
    ):
        publisher.publish(
            artifacts,
            signature,
            authorization(authorized=False),
        )

    payload = signature.model_dump(mode="json", exclude={"signature_hash"})
    payload["manifest_hash"] = f"sha256:{'f' * 64}"
    payload["signature_hash"] = "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    forged = signature.model_construct(**payload)
    with pytest.raises(
        ReleasePublicationError,
        match="does not target",
    ):
        publisher.publish(artifacts, forged, authorization())
