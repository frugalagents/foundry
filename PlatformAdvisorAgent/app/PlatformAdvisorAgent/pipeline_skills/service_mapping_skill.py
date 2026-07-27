"""Step 6 — Service Mapping: map components to concrete AWS services.

LLM enhancement (Strands Agent + BedrockModel) ranks workshop relevance
and discovers workshop URLs from the Bedrock Knowledge Base when configured.
Static fallback tables are used when neither KB nor LLM is available.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import AsyncIterator

from strands import Agent
from strands.models import BedrockModel

from agent_core_engine.graph_loader import get_graph
from . import kb_utils
from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_card_add,
    make_panel_complete,
    make_step_transition,
)

logger = logging.getLogger(__name__)

# Fallback mapping when graph doesn't have primary_aws_service
CATEGORY_TO_AWS: dict[str, dict] = {
    "AI/ML":          {"service": "Amazon Bedrock",           "category": "AI/ML"},
    "Data Lake":      {"service": "Amazon S3 + Glue",         "category": "Storage"},
    "Governance":     {"service": "AWS Lake Formation",       "category": "Governance"},
    "Orchestration":  {"service": "Amazon MWAA (Airflow)",    "category": "Compute"},
    "Streaming":      {"service": "Amazon Kinesis Data Streams","category": "Streaming"},
    "Warehouse":      {"service": "Amazon Redshift",          "category": "Analytics"},
    "Search":         {"service": "Amazon OpenSearch Service","category": "Analytics"},
    "Identity":       {"service": "AWS IAM Identity Center",  "category": "Security"},
    "Monitoring":     {"service": "Amazon CloudWatch",        "category": "Operations"},
    "Catalog":        {"service": "AWS Glue Data Catalog",    "category": "Governance"},
    "Security":       {"service": "AWS Security Hub",         "category": "Security"},
    "Networking":     {"service": "Amazon VPC",               "category": "Networking"},
    "Container":      {"service": "Amazon EKS",               "category": "Compute"},
    "Serverless":     {"service": "AWS Lambda",               "category": "Compute"},
    "API":            {"service": "Amazon API Gateway",       "category": "Networking"},
    "Queue":          {"service": "Amazon SQS",               "category": "Messaging"},
    "Cache":          {"service": "Amazon ElastiCache",       "category": "Storage"},
    "NoSQL":          {"service": "Amazon DynamoDB",          "category": "Storage"},
    "Core":           {"service": "Amazon Bedrock",           "category": "AI/ML"},
}

SERVICE_WORKSHOP_LINKS: dict[str, str] = {
    "Amazon Bedrock":             "https://catalog.workshops.aws/amazon-bedrock",
    "Amazon S3 + Glue":           "https://catalog.workshops.aws/aws-glue",
    "AWS Lake Formation":         "https://catalog.workshops.aws/lake-formation",
    "Amazon MWAA (Airflow)":      "https://catalog.workshops.aws/amazon-mwaa",
    "Amazon Kinesis Data Streams":"https://catalog.workshops.aws/kinesis",
    "Amazon Redshift":            "https://catalog.workshops.aws/redshift",
    "Amazon OpenSearch Service":  "https://catalog.workshops.aws/opensearch",
    "AWS IAM Identity Center":    "https://catalog.workshops.aws/iam",
    "Amazon CloudWatch":          "https://catalog.workshops.aws/cloudwatch",
    "AWS Glue Data Catalog":      "https://catalog.workshops.aws/aws-glue",
    "Amazon EKS":                 "https://catalog.workshops.aws/eks",
    "AWS Lambda":                 "https://catalog.workshops.aws/lambda",
    "Amazon DynamoDB":            "https://catalog.workshops.aws/dynamodb",
}

_WORKSHOP_SYSTEM_PROMPT = """You are an AWS solutions architect. Given a list of AWS services and optional
knowledge base context, for each service provide:
1. The most relevant AWS Workshop Studio URL (catalog.workshops.aws)
2. A one-sentence description of why this workshop is useful

Return a JSON array. Each element must have:
  {"aws_service": "...", "workshop_url": "https://...", "workshop_desc": "..."}
Return only the JSON array — no markdown fences, no extra text."""


def _enrich_workshops_sync(
    service_entries: list[dict], kb_context: str
) -> dict[str, dict]:
    """Synchronous Strands Agent call — run in a thread via asyncio.to_thread."""
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-6", max_tokens=1024)
    agent = Agent(model=model, system_prompt=_WORKSHOP_SYSTEM_PROMPT)

    slim = [
        {"aws_service": e["aws_service"], "component_name": e["component_name"]}
        for e in service_entries
    ]
    prompt = (
        f"AWS services to enrich:\n{json.dumps(slim, indent=2)}\n\n"
        f"Knowledge base context:\n{kb_context or '(not available)'}\n\n"
        f"Return the JSON array with workshop_url and workshop_desc for each service."
    )

    try:
        raw = str(agent(prompt))
        start, end = raw.find("["), raw.rfind("]") + 1
        if start >= 0 and end > start:
            items = json.loads(raw[start:end])
            return {
                item["aws_service"]: {
                    "workshop_url": item.get("workshop_url", ""),
                    "workshop_desc": item.get("workshop_desc", ""),
                }
                for item in items
                if "aws_service" in item
            }
    except Exception as exc:
        logger.warning("Workshop LLM enrichment failed: %s", exc)
    return {}


async def run_service_mapping(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Map each component to its primary AWS service with workshop links.
    Workshop URLs are enriched via KB retrieval + Strands Agent ranking.

    Yields:
      - panel_update
      - card_add (per service mapping)
      - panel_complete (service map table data)
      - chat_message
      - step_transition (6 → 7)
    """
    ctx.current_step = 6
    graph = get_graph()

    yield make_panel_update(6, "service_map", {"status": "mapping", "progress": 10})

    service_entries: list[dict] = []
    seen_services: set[str] = set()

    total = max(len(ctx.components), 1)
    for i, comp in enumerate(ctx.components):
        progress = int(15 + (i / total) * 50)
        yield make_panel_update(6, "service_map", {
            "status": "mapping",
            "progress": progress,
            "current": comp["name"],
        })

        aws_service = comp.get("aws_service", "")
        if not aws_service:
            cat = comp.get("category", "Core")
            mapping = CATEGORY_TO_AWS.get(cat, CATEGORY_TO_AWS["Core"])
            aws_service = mapping["service"]

        if aws_service in seen_services:
            continue
        seen_services.add(aws_service)

        service_cat = "AI/ML"
        for cat_key, cat_map in CATEGORY_TO_AWS.items():
            if cat_map["service"] == aws_service:
                service_cat = cat_map["category"]
                break

        entry = {
            "component_id": comp["id"],
            "component_name": comp["name"],
            "component_layer": comp["layer"],
            "aws_service": aws_service,
            "service_category": service_cat,
            "tier": comp["final_tier"],
            "workshop_link": SERVICE_WORKSHOP_LINKS.get(aws_service, ""),
            "workshop_desc": "",
            "console_link": "https://console.aws.amazon.com/",
            "docs_link": "https://docs.aws.amazon.com/",
        }
        service_entries.append(entry)

    # KB retrieval for workshop discovery
    kb_context = ""
    if kb_utils.is_configured() and service_entries:
        kb_query = (
            "AWS Workshop Studio hands-on labs "
            + " ".join(e["aws_service"] for e in service_entries[:6])
        )
        kb_context = kb_utils.retrieve_text(kb_query, top_k=5)

    yield make_panel_update(6, "service_map", {"status": "mapping", "progress": 70})

    # LLM enrichment for workshop URL ranking
    if service_entries:
        try:
            enrichments = await asyncio.to_thread(
                _enrich_workshops_sync, service_entries, kb_context
            )
            for entry in service_entries:
                enrich = enrichments.get(entry["aws_service"], {})
                if enrich.get("workshop_url"):
                    entry["workshop_link"] = enrich["workshop_url"]
                if enrich.get("workshop_desc"):
                    entry["workshop_desc"] = enrich["workshop_desc"]
        except Exception as exc:
            logger.warning("Workshop enrichment skipped: %s", exc)

    ctx.service_map = service_entries

    for entry in service_entries:
        yield make_card_add(
            card_id=f"service:{entry['component_id']}",
            card_type="service_mapping",
            payload=entry,
        )

    yield make_panel_update(6, "service_map", {"status": "complete", "progress": 100})

    # Build per-component structure expected by ServiceMapData
    components_out: dict[str, dict] = {}
    for entry in service_entries:
        name = entry["component_name"]
        if name not in components_out:
            components_out[name] = {
                "name": name,
                "tier": entry["tier"],
                "aws_services": [],
                "workshops": [],
                "alternatives": [],
            }
        components_out[name]["aws_services"].append({
            "name": entry["aws_service"],
            "icon_url": "",
            "notes": entry.get("service_category", ""),
        })
        if entry.get("workshop_link"):
            components_out[name]["workshops"].append({
                "title": f"{entry['aws_service']} Workshop",
                "url": entry["workshop_link"],
            })

    categories = {entry["service_category"] for entry in service_entries}

    yield make_panel_complete(6, "service_map", {
        "components": list(components_out.values()),
    })

    yield make_chat_message("assistant",
        f"**{len(service_entries)} AWS services** mapped across {len(categories)} categories. "
        f"See Service Map →"
    )

    yield make_step_transition(6, 7, "Detecting anti-patterns...")
