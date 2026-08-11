from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from advisor_core.knowledge import (
    BedrockClaimExtractor,
    BedrockExtractionConfig,
    ExtractionError,
    SourceLocator,
)


GENERATED_AT = datetime(2026, 8, 11, 20, tzinfo=timezone.utc)
SOURCE_TEXT = "The managed runtime supports MCP over HTTP."


def locator() -> SourceLocator:
    return SourceLocator(
        source_snapshot_id="snapshot:runtime-docs-abc123",
        source_uri="https://docs.example.com/runtime/mcp",
        source_content_hash=f"sha256:{'a' * 64}",
        exact_text=SOURCE_TEXT,
        section_path=("Tool integration", "MCP"),
    )


def structured_payload() -> dict[str, object]:
    return {
        "extracted_text": SOURCE_TEXT,
        "normalized_statement": (
            "Example Managed Runtime supports MCP over HTTP."
        ),
        "subject_id": "offering:example-managed-runtime",
        "subject_kind": "Offering",
        "predicate": "supports_interface",
        "object_id": "interface:mcp-http",
        "object_value": None,
        "proposed_scope": {
            "provider": {
                "mode": "specified",
                "values": ["Example Provider"],
            },
            "product": {
                "mode": "specified",
                "values": ["Managed Runtime"],
            },
            "variant": {"mode": "not_applicable", "values": []},
            "version": {"mode": "all", "values": []},
            "region": {"mode": "all", "values": []},
            "configuration": {"mode": "all", "values": []},
        },
        "claim_class": "product_fact",
        "confidence": 0.91,
        "warnings": [],
        "proposed_relationships": [
            {
                "relationship_type": "IMPLEMENTS",
                "target_id": "capability:governed-tool-access",
                "target_kind": "Capability",
                "cardinality": "many_to_many",
                "confidence": 0.8,
                "rationale": "MCP is a governed tool integration interface.",
            }
        ],
    }


class FakeBedrockClient:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    def converse(self, **request):
        self.requests.append(request)
        return self.response


def response(payload: object, *, stop_reason: str = "end_turn"):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            }
        },
        "stopReason": stop_reason,
        "usage": {
            "inputTokens": 500,
            "outputTokens": 220,
            "totalTokens": 720,
        },
        "metrics": {"latencyMs": 830},
        "ResponseMetadata": {"RequestId": "request-123"},
    }


def config(**overrides) -> BedrockExtractionConfig:
    values = {
        "model_id": "us.example.model-v1",
        "max_tokens": 1200,
        "temperature": 0,
    }
    values.update(overrides)
    return BedrockExtractionConfig(**values)


def test_bedrock_extractor_uses_structured_output_and_trusted_metadata():
    client = FakeBedrockClient(response(structured_payload()))
    extractor = BedrockClaimExtractor(client, config())

    result = extractor.extract(
        locator(),
        generated_at=GENERATED_AT,
        known_entity_ids=(
            "offering:example-managed-runtime",
            "interface:mcp-http",
        ),
    )

    request = client.requests[0]
    assert request["modelId"] == "us.example.model-v1"
    assert request["inferenceConfig"] == {
        "maxTokens": 1200,
        "temperature": 0.0,
    }
    text_format = request["outputConfig"]["textFormat"]
    assert text_format["type"] == "json_schema"
    schema = json.loads(
        text_format["structure"]["jsonSchema"]["schema"]
    )
    assert schema["title"] == "ExtractedClaimPayload"
    assert request["requestMetadata"]["operation"] == (
        "knowledge-claim-extraction"
    )
    assert result.candidate.extractor.model_id == "us.example.model-v1"
    assert result.candidate.locator == locator()
    assert result.candidate.normalized_statement == (
        "Example Managed Runtime supports MCP over HTTP."
    )
    assert result.usage.total_tokens == 720


def test_guardrail_is_pinned_and_trace_is_disabled():
    client = FakeBedrockClient(response(structured_payload()))
    extractor = BedrockClaimExtractor(
        client,
        config(
            guardrail_id="guardrail-123",
            guardrail_version="7",
        ),
    )

    extractor.extract(locator(), generated_at=GENERATED_AT)

    assert client.requests[0]["guardrailConfig"] == {
        "guardrailIdentifier": "guardrail-123",
        "guardrailVersion": "7",
        "trace": "disabled",
    }


def test_extractor_rejects_truncated_model_output():
    client = FakeBedrockClient(
        response(structured_payload(), stop_reason="max_tokens")
    )
    extractor = BedrockClaimExtractor(client, config())

    with pytest.raises(
        ExtractionError,
        match="stopped with reason max_tokens",
    ):
        extractor.extract(locator(), generated_at=GENERATED_AT)


def test_extractor_rejects_invalid_json():
    client = FakeBedrockClient(response("not-json"))
    extractor = BedrockClaimExtractor(client, config())

    with pytest.raises(
        ExtractionError,
        match="invalid structured extraction",
    ):
        extractor.extract(locator(), generated_at=GENERATED_AT)


def test_model_cannot_change_exact_source_text():
    payload = structured_payload()
    payload["extracted_text"] = "The runtime supports every protocol."
    client = FakeBedrockClient(response(payload))
    extractor = BedrockClaimExtractor(client, config())

    with pytest.raises(
        ExtractionError,
        match="violates candidate contract",
    ):
        extractor.extract(locator(), generated_at=GENERATED_AT)
