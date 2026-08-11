"""KMS signing and immutable S3 publication for knowledge releases."""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime

from botocore.exceptions import ClientError
from pydantic import Field, model_validator

from .models import FrozenModel, StableId, StrEnum, content_hash
from .publication import (
    PrincipalType,
    PublicationAction,
    PublicationAuthorization,
)
from .release_artifacts import KnowledgeReleaseArtifacts


class KmsSigningAlgorithm(StrEnum):
    RSASSA_PSS_SHA_256 = "RSASSA_PSS_SHA_256"
    ECDSA_SHA_256 = "ECDSA_SHA_256"


class ReleasePublicationError(RuntimeError):
    pass


class ReleasePublicationConflictError(ReleasePublicationError):
    pass


class KnowledgeReleaseSignaturePayload(FrozenModel):
    schema_version: str = "1.0"
    release_id: StableId
    release_version: str = Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z.-]+)?$"
    )
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    key_id: str = Field(min_length=1)
    signing_algorithm: KmsSigningAlgorithm
    signed_at: datetime
    signature_base64: str = Field(min_length=1)


class KnowledgeReleaseSignature(KnowledgeReleaseSignaturePayload):
    signature_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def signature_hash_matches_metadata(self) -> "KnowledgeReleaseSignature":
        payload = self.model_dump(mode="json", exclude={"signature_hash"})
        if self.signature_hash != content_hash(payload):
            raise ValueError("release signature hash does not match content")
        return self


class PublishedReleaseObject(FrozenModel):
    key: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ReleasePublicationReceipt(FrozenModel):
    release_id: StableId
    release_version: str
    bucket: str = Field(min_length=1)
    prefix: str = Field(min_length=1)
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    signature_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    objects: tuple[PublishedReleaseObject, ...] = Field(min_length=1)
    receipt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def receipt_hash_matches_content(self) -> "ReleasePublicationReceipt":
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        if self.receipt_hash != content_hash(payload):
            raise ValueError("publication receipt hash does not match content")
        return self


class KmsReleaseSigner:
    def __init__(
        self,
        client,
        key_id: str,
        *,
        signing_algorithm: KmsSigningAlgorithm = (
            KmsSigningAlgorithm.RSASSA_PSS_SHA_256
        ),
    ) -> None:
        self.client = client
        self.key_id = key_id
        self.signing_algorithm = signing_algorithm

    @staticmethod
    def _digest(manifest_hash: str) -> bytes:
        return bytes.fromhex(manifest_hash.split(":", 1)[1])

    def sign(
        self,
        artifacts: KnowledgeReleaseArtifacts,
        *,
        signed_at: datetime,
    ) -> KnowledgeReleaseSignature:
        response = self.client.sign(
            KeyId=self.key_id,
            Message=self._digest(artifacts.manifest.manifest_hash),
            MessageType="DIGEST",
            SigningAlgorithm=self.signing_algorithm.value,
        )
        signature = bytes(response["Signature"])
        payload = KnowledgeReleaseSignaturePayload(
            release_id=artifacts.manifest.release_id,
            release_version=artifacts.manifest.release_version,
            manifest_hash=artifacts.manifest.manifest_hash,
            key_id=str(response.get("KeyId", self.key_id)),
            signing_algorithm=self.signing_algorithm,
            signed_at=signed_at,
            signature_base64=base64.b64encode(signature).decode("ascii"),
        )
        normalized = payload.model_dump(mode="json")
        return KnowledgeReleaseSignature(
            **normalized,
            signature_hash=content_hash(normalized),
        )

    def verify(self, signature: KnowledgeReleaseSignature) -> bool:
        response = self.client.verify(
            KeyId=signature.key_id,
            Message=self._digest(signature.manifest_hash),
            MessageType="DIGEST",
            SigningAlgorithm=signature.signing_algorithm.value,
            Signature=base64.b64decode(signature.signature_base64),
        )
        return bool(response.get("SignatureValid"))


class S3ReleasePublisher:
    def __init__(
        self,
        client,
        bucket: str,
        *,
        prefix: str = "knowledge/releases",
        kms_key_id: str | None = None,
    ) -> None:
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.kms_key_id = kms_key_id

    def _put_immutable(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        content_hash_value: str,
    ) -> None:
        arguments = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": content,
            "ContentType": content_type,
            "IfNoneMatch": "*",
            "Metadata": {
                "sha256": content_hash_value.split(":", 1)[1],
            },
        }
        if self.kms_key_id:
            arguments.update({
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": self.kms_key_id,
            })
        try:
            self.client.put_object(**arguments)
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
            if existing != content:
                raise ReleasePublicationConflictError(
                    f"immutable release object already differs: s3://"
                    f"{self.bucket}/{key}"
                ) from error

    def publish(
        self,
        artifacts: KnowledgeReleaseArtifacts,
        signature: KnowledgeReleaseSignature,
        authorization: PublicationAuthorization,
    ) -> ReleasePublicationReceipt:
        if (
            not authorization.authorized
            or authorization.principal_type is not PrincipalType.RELEASE_PIPELINE
            or authorization.action is not PublicationAction.PUBLISH_CATALOG
        ):
            raise ReleasePublicationError(
                "catalog publication requires release-pipeline authorization"
            )
        if signature.manifest_hash != artifacts.manifest.manifest_hash:
            raise ReleasePublicationError(
                "signature does not target the supplied release manifest"
            )

        release_slug = artifacts.manifest.release_id.replace(":", "/")
        release_prefix = (
            f"{self.prefix}/{release_slug}/"
            f"{artifacts.manifest.release_version}"
        )
        publication_objects: list[tuple[str, str, bytes, str]] = []
        for file in artifacts.files:
            publication_objects.append(
                (
                    file.path,
                    file.content_hash,
                    file.content.encode("utf-8"),
                    file.media_type,
                )
            )
        manifest_content = (
            json.dumps(
                artifacts.manifest.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        signature_content = (
            json.dumps(
                signature.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        publication_objects.extend((
            (
                "manifest.json",
                "sha256:" + hashlib.sha256(manifest_content).hexdigest(),
                manifest_content,
                "application/json",
            ),
            (
                "signature.json",
                "sha256:" + hashlib.sha256(signature_content).hexdigest(),
                signature_content,
                "application/json",
            ),
        ))

        records = []
        for relative_path, object_hash, content, media_type in sorted(
            publication_objects
        ):
            key = f"{release_prefix}/{relative_path}"
            self._put_immutable(
                key=key,
                content=content,
                content_type=media_type,
                content_hash_value=object_hash,
            )
            records.append(
                PublishedReleaseObject(
                    key=key,
                    content_hash=object_hash,
                    size_bytes=len(content),
                )
            )
        receipt_payload = {
            "release_id": artifacts.manifest.release_id,
            "release_version": artifacts.manifest.release_version,
            "bucket": self.bucket,
            "prefix": release_prefix,
            "manifest_hash": artifacts.manifest.manifest_hash,
            "signature_hash": signature.signature_hash,
            "objects": [
                record.model_dump(mode="json") for record in records
            ],
        }
        return ReleasePublicationReceipt(
            **receipt_payload,
            receipt_hash=content_hash(receipt_payload),
        )
