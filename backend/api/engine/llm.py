"""Thin Bedrock converse wrapper for the engine agents.

Mirrors the pipeline_skills pattern: direct boto3 bedrock-runtime, graceful
degradation when Bedrock is unavailable so the engine still returns a
deterministic result (no hard dependency on the model being reachable).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os

logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get(
    "ADVISOR_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
TEMPERATURE = 0.3

_client = None


def _bedrock():
    global _client
    if _client is None:
        import boto3
        _client = boto3.client("bedrock-runtime", region_name=REGION)
    return _client


def prompt_hash(system: str, user: str) -> str:
    return "sha256:" + hashlib.sha256(f"{system}\0{user}".encode()).hexdigest()


def converse(system: str, user: str, *, max_tokens: int = 1200) -> str | None:
    """Return model text, or None if Bedrock is unavailable (caller falls back)."""
    try:
        resp = _bedrock().converse(
            modelId=MODEL_ID,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": TEMPERATURE},
        )
        blocks = resp.get("output", {}).get("message", {}).get("content", [])
        text = "".join(b.get("text", "") for b in blocks).strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 — degrade, never crash the endpoint
        logger.warning("Bedrock converse failed, falling back: %s", exc)
        return None


def converse_json(system: str, user: str, *, max_tokens: int = 1200) -> dict | None:
    """Converse and parse a JSON object from the reply (tolerant of fences)."""
    text = converse(system, user, max_tokens=max_tokens)
    if not text:
        return None
    # strip markdown fences if present
    if "```" in text:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        logger.warning("Model did not return valid JSON; falling back")
        return None
