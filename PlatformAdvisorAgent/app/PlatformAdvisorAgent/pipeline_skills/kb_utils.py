"""Bedrock Knowledge Base retrieval utilities for pipeline skills.

Uses the KNOWLEDGE_BASE_ID env var (matches strands_tools convention).
Returns empty results gracefully when the KB is not configured so all
skills degrade safely in local dev without a deployed KB.
"""
from __future__ import annotations
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-agent-runtime", region_name=REGION)
    return _client


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Query Bedrock KB and return a list of {text, score, source} dicts."""
    if not KNOWLEDGE_BASE_ID:
        return []
    try:
        resp = _get_client().retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": top_k}
            },
        )
        return [
            {
                "text": r["content"]["text"],
                "score": round(r.get("score", 0.0), 3),
                "source": (r.get("location") or {}).get("s3Location", {}).get("uri", ""),
            }
            for r in resp.get("retrievalResults", [])
        ]
    except ClientError as exc:
        logger.warning("KB retrieve failed: %s", exc)
        return []


def retrieve_text(query: str, top_k: int = 5) -> str:
    """Return retrieved passages joined by separators, ready for prompt injection."""
    return "\n\n---\n\n".join(r["text"] for r in retrieve(query, top_k))


def is_configured() -> bool:
    return bool(KNOWLEDGE_BASE_ID)
