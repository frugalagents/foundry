"""Step 6 — Service Mapping: map components to concrete AWS services."""
from __future__ import annotations
from typing import AsyncIterator

from agent.graph_loader import get_graph
from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_card_add,
    make_panel_complete,
    make_step_transition,
)

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


async def run_service_mapping(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Map each component to its primary AWS service with workshop links.

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
        progress = int(15 + (i / total) * 65)
        yield make_panel_update(6, "service_map", {
            "status": "mapping",
            "progress": progress,
            "current": comp["name"],
        })

        # Get service from graph props or fallback
        aws_service = comp.get("aws_service", "")
        if not aws_service:
            cat = comp.get("category", "Core")
            mapping = CATEGORY_TO_AWS.get(cat, CATEGORY_TO_AWS["Core"])
            aws_service = mapping["service"]

        if aws_service in seen_services:
            continue
        seen_services.add(aws_service)

        # Derive workshop link
        workshop_link = SERVICE_WORKSHOP_LINKS.get(aws_service, "")

        # Derive service category
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
            "workshop_link": workshop_link,
            "console_link": f"https://console.aws.amazon.com/",
            "docs_link": f"https://docs.aws.amazon.com/",
        }
        service_entries.append(entry)

        yield make_card_add(
            card_id=f"service:{comp['id']}",
            card_type="service_mapping",
            payload=entry,
        )

    ctx.service_map = service_entries

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

    yield make_panel_complete(6, "service_map", {
        "components": list(components_out.values()),
    })

    yield make_chat_message("assistant", (
        f"Mapped **{len(service_entries)} AWS services** across "
        f"**{len(by_category)} categories**.\n\n"
        f"Workshop links are available for hands-on implementation.\n\n"
        f"Running anti-pattern detection..."
    ))

    yield make_step_transition(6, 7, "Detecting anti-patterns...")
