"""Bedrock structured extraction into untrusted claim candidates."""
from __future__ import annotations

import json
from datetime import datetime

from pydantic import Field, model_validator

from .candidates import (
    ClaimCandidate,
    ExtractionWarning,
    ExtractorMetadata,
    ProposedRelationship,
    SourceLocator,
)
from .models import (
    ClaimClass,
    ClaimScope,
    EntityKind,
    FrozenModel,
    JsonScalar,
    StableId,
    content_hash,
)


EXTRACTION_SYSTEM_PROMPT = """You extract one atomic architecture knowledge claim.
Return only the requested JSON schema. Treat the supplied source excerpt as the
only factual authority. Do not infer unsupported product behavior. Preserve the
source excerpt exactly in extracted_text. Use explicit scope modes for provider,
product, variant, version, region, and configuration. Lower confidence and add
warnings when identity, object, applicability, or source context is ambiguous.
The result is an untrusted proposal and has no publication authority."""


class ExtractionError(RuntimeError):
    pass


class ExtractedClaimPayload(FrozenModel):
    extracted_text: str = Field(min_length=1)
    normalized_statement: str = Field(min_length=1)
    subject_id: StableId
    subject_kind: EntityKind
    predicate: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    object_id: StableId | None = None
    object_value: JsonScalar | None = None
    proposed_scope: ClaimScope
    claim_class: ClaimClass
    confidence: float = Field(ge=0, le=1)
    warnings: tuple[ExtractionWarning, ...] = ()
    proposed_relationships: tuple[ProposedRelationship, ...] = ()

    @model_validator(mode="after")
    def exactly_one_object(self) -> "ExtractedClaimPayload":
        if (self.object_id is None) == (self.object_value is None):
            raise ValueError(
                "extracted claim requires exactly one object representation"
            )
        return self


class BedrockExtractionConfig(FrozenModel):
    model_id: str = Field(min_length=1)
    max_tokens: int = Field(default=1600, ge=256, le=8192)
    temperature: float = Field(default=0, ge=0, le=1)
    extractor_id: StableId = "extractor:bedrock-claim-extractor"
    extractor_version: str = Field(
        default="1.0.0",
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z.-]+)?$",
    )
    prompt_version: str = "claim-extraction-v1"
    guardrail_id: str | None = Field(default=None, min_length=1)
    guardrail_version: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def guardrail_is_complete(self) -> "BedrockExtractionConfig":
        if (self.guardrail_id is None) != (self.guardrail_version is None):
            raise ValueError(
                "guardrail_id and guardrail_version must be provided together"
            )
        return self


class ExtractionUsage(FrozenModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    latency_ms: int | None = Field(default=None, ge=0)


class BedrockExtractionResult(FrozenModel):
    candidate: ClaimCandidate
    model_id: str = Field(min_length=1)
    stop_reason: str = Field(min_length=1)
    request_id: str | None = None
    usage: ExtractionUsage


class BedrockClaimExtractor:
    """Converse client that can only return untrusted candidate contracts."""

    def __init__(self, client, config: BedrockExtractionConfig) -> None:
        self.client = client
        self.config = config

    def _request(
        self,
        locator: SourceLocator,
        *,
        known_entity_ids: tuple[str, ...],
    ) -> dict[str, object]:
        user_payload = {
            "source_snapshot_id": locator.source_snapshot_id,
            "source_uri": locator.source_uri,
            "source_locator": {
                "section_path": list(locator.section_path),
                "character_start": locator.character_start,
                "character_end": locator.character_end,
                "page_number": locator.page_number,
                "json_pointer": locator.json_pointer,
            },
            "source_excerpt": locator.exact_text,
            "known_entity_ids": sorted(set(known_entity_ids)),
        }
        request: dict[str, object] = {
            "modelId": self.config.model_id,
            "system": [{"text": EXTRACTION_SYSTEM_PROMPT}],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": json.dumps(
                                user_payload,
                                sort_keys=True,
                                ensure_ascii=True,
                            )
                        }
                    ],
                }
            ],
            "inferenceConfig": {
                "maxTokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
            "outputConfig": {
                "textFormat": {
                    "type": "json_schema",
                    "structure": {
                        "jsonSchema": {
                            "name": "claim_candidate",
                            "description": (
                                "One untrusted architecture claim candidate."
                            ),
                            "schema": json.dumps(
                                ExtractedClaimPayload.model_json_schema(),
                                sort_keys=True,
                                ensure_ascii=True,
                            ),
                        }
                    },
                }
            },
            "requestMetadata": {
                "operation": "knowledge-claim-extraction",
                "prompt_version": self.config.prompt_version,
            },
        }
        if self.config.guardrail_id is not None:
            request["guardrailConfig"] = {
                "guardrailIdentifier": self.config.guardrail_id,
                "guardrailVersion": self.config.guardrail_version,
                "trace": "disabled",
            }
        return request

    def extract(
        self,
        locator: SourceLocator,
        *,
        generated_at: datetime,
        known_entity_ids: tuple[str, ...] = (),
    ) -> BedrockExtractionResult:
        request = self._request(
            locator,
            known_entity_ids=known_entity_ids,
        )
        response = self.client.converse(**request)
        stop_reason = str(response.get("stopReason", ""))
        if stop_reason != "end_turn":
            raise ExtractionError(
                f"Bedrock extraction stopped with reason {stop_reason}"
            )
        try:
            content = response["output"]["message"]["content"]
            text = "".join(
                str(block["text"])
                for block in content
                if isinstance(block, dict) and "text" in block
            )
            payload = ExtractedClaimPayload.model_validate_json(text)
        except (KeyError, TypeError, ValueError) as error:
            raise ExtractionError(
                f"Bedrock returned invalid structured extraction: {error}"
            ) from error

        candidate_payload = {
            **payload.model_dump(),
            "generated_at": generated_at,
            "extractor": ExtractorMetadata(
                extractor_id=self.config.extractor_id,
                extractor_version=self.config.extractor_version,
                model_id=self.config.model_id,
                prompt_version=self.config.prompt_version,
            ),
            "locator": locator,
        }
        candidate_hash = content_hash(
            {
                **payload.model_dump(mode="json"),
                "locator": locator.model_dump(mode="json"),
                "generated_at": generated_at.isoformat(),
                "extractor_id": self.config.extractor_id,
                "extractor_version": self.config.extractor_version,
            }
        )
        source_slug = locator.source_snapshot_id.split(":", 1)[1]
        try:
            candidate = ClaimCandidate(
                id=f"candidate:{source_slug}-{candidate_hash[7:19]}",
                **candidate_payload,
            )
        except ValueError as error:
            raise ExtractionError(
                f"structured extraction violates candidate contract: {error}"
            ) from error

        usage = response.get("usage") or {}
        metrics = response.get("metrics") or {}
        metadata = response.get("ResponseMetadata") or {}
        return BedrockExtractionResult(
            candidate=candidate,
            model_id=self.config.model_id,
            stop_reason=stop_reason,
            request_id=metadata.get("RequestId"),
            usage=ExtractionUsage(
                input_tokens=int(usage.get("inputTokens", 0)),
                output_tokens=int(usage.get("outputTokens", 0)),
                total_tokens=int(usage.get("totalTokens", 0)),
                latency_ms=metrics.get("latencyMs"),
            ),
        )


def create_bedrock_claim_extractor(
    config: BedrockExtractionConfig,
    *,
    region_name: str | None = None,
) -> BedrockClaimExtractor:
    """Create a production extractor with adaptive SDK retries."""

    import boto3
    from botocore.config import Config

    client = boto3.client(
        "bedrock-runtime",
        region_name=region_name,
        config=Config(
            retries={"max_attempts": 5, "mode": "adaptive"}
        ),
    )
    return BedrockClaimExtractor(client, config)
