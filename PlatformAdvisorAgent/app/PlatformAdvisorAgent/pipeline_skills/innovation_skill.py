"""Step 4 — Innovation Overlay: match pain points to emerging capabilities.

LLM enhancement (Strands Agent + BedrockModel) verifies GA status and adds
relevance notes for each innovation.  When AWS_DOCS_MCP_ENDPOINT is set the
Strands Agent is equipped with MCP tools for live AWS documentation lookup;
otherwise it relies on KB context injected from the prompt.
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
from mcp_client.client import get_streamable_http_mcp_client, is_mcp_configured
from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_card_add,
    make_panel_complete,
    make_step_transition,
)

logger = logging.getLogger(__name__)

STATUS_BADGE = {
    "ga":       "GA",
    "preview":  "Preview",
    "emerging": "Emerging",
}

_ENRICH_SYSTEM_PROMPT = """You are an AWS architecture expert specializing in emerging AI/ML services.
Given a list of innovations and background knowledge, for each innovation:
1. Verify its current release status based on the knowledge provided
2. Write a single-sentence relevance note connecting it to the customer pain points

Return a JSON array. Each element must have exactly:
  {"id": "...", "verified_status": "ga|preview|emerging", "relevance_note": "..."}
Return only the JSON array — no markdown fences, no extra text."""


def _build_enrich_prompt(
    innovations: list[dict], pain_points: list[str], kb_context: str
) -> str:
    slim = [
        {
            "id": i["id"],
            "name": i["name"],
            "status": i["status"],
            "constraint_solved": i["constraint_solved"],
        }
        for i in innovations
    ]
    return (
        f"Customer pain points: {json.dumps(pain_points)}\n\n"
        f"Innovations to verify and enrich:\n{json.dumps(slim, indent=2)}\n\n"
        f"AWS knowledge base context:\n{kb_context or '(not available)'}\n\n"
        f"Return the enriched JSON array."
    )


def _enrich_sync(
    innovations: list[dict], pain_points: list[str], kb_context: str
) -> tuple[dict[str, dict], bool]:
    """Synchronous Strands Agent call — runs in a thread via asyncio.to_thread.

    Returns (enrichments_by_id, mcp_was_active).
    """
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-6", max_tokens=1024)
    prompt = _build_enrich_prompt(innovations, pain_points, kb_context)

    # Attempt MCP-equipped enrichment first
    if is_mcp_configured():
        try:
            with get_streamable_http_mcp_client() as mcp_client:
                tools = mcp_client.list_tools_sync()
                agent = Agent(
                    model=model,
                    system_prompt=_ENRICH_SYSTEM_PROMPT,
                    tools=tools,
                )
                raw = str(agent(prompt))
            return _parse_enrichments(raw, mcp_active=True), True
        except Exception as exc:
            logger.warning("MCP-equipped enrichment failed, falling back: %s", exc)

    # Fallback: KB context only (no MCP tools)
    agent = Agent(model=model, system_prompt=_ENRICH_SYSTEM_PROMPT)
    raw = str(agent(prompt))
    return _parse_enrichments(raw, mcp_active=False), False


def _parse_enrichments(raw: str, mcp_active: bool) -> dict[str, dict]:
    start, end = raw.find("["), raw.rfind("]") + 1
    if start < 0 or end <= start:
        return {}
    try:
        items = json.loads(raw[start:end])
        return {
            item["id"]: {
                "verified_status": item.get("verified_status", ""),
                "relevance_note": item.get("relevance_note", ""),
                "verified_via_mcp": mcp_active,
            }
            for item in items
            if "id" in item
        }
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Failed to parse enrichment JSON: %s", exc)
        return {}


async def run_innovation(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Identify applicable innovations from the knowledge graph and enrich them
    using a Strands Agent backed by Bedrock Knowledge Base context.

    Yields:
      - panel_update
      - card_add (per innovation)
      - panel_complete
      - chat_message
      - step_transition (4 → 5)
    """
    ctx.current_step = 4
    graph = get_graph()

    yield make_panel_update(4, "innovation_overlay", {"status": "scanning", "progress": 10})

    innovations = graph.get_innovations_for_pain_points(ctx.pain_points, ctx.pattern_id)
    ctx.innovations = innovations

    # Retrieve KB context for the batch of innovations
    kb_context = ""
    if kb_utils.is_configured() and innovations:
        kb_query = (
            "AWS service GA status " + " ".join(i["name"] for i in innovations[:5])
        )
        kb_context = kb_utils.retrieve_text(kb_query, top_k=5)

    yield make_panel_update(4, "innovation_overlay", {"status": "scanning", "progress": 25})

    # LLM enrichment (Strands Agent + optional MCP tools)
    enrichments: dict[str, dict] = {}
    if innovations:
        try:
            enrichments, _ = await asyncio.to_thread(
                _enrich_sync, innovations, ctx.pain_points, kb_context
            )
        except Exception as exc:
            logger.warning("Innovation LLM enrichment skipped: %s", exc)

    total = max(len(innovations), 1)
    for i, inn in enumerate(innovations):
        progress = int(40 + (i / total) * 45)
        yield make_panel_update(4, "innovation_overlay", {
            "status": "scanning",
            "progress": progress,
            "current": inn["name"],
        })

        enrich = enrichments.get(inn["id"], {})
        verified_status = enrich.get("verified_status") or inn["status"]

        yield make_card_add(
            card_id=inn["id"],
            card_type="innovation",
            payload={
                "name": inn["name"],
                "date_emerged": inn["date_emerged"],
                "constraint_solved": inn["constraint_solved"],
                "replaces": inn.get("replaces"),
                "enables": inn.get("enables"),
                "aws_implementation": inn["aws_implementation"],
                "status": STATUS_BADGE.get(verified_status, verified_status.upper()),
                "relevance_note": enrich.get("relevance_note", ""),
                "verified_via_mcp": enrich.get("verified_via_mcp", bool(kb_context)),
                "enabled": inn.get("enabled", True),
            },
        )

    yield make_panel_update(4, "innovation_overlay", {"status": "complete", "progress": 100})

    ga_count = sum(1 for i in innovations if i["status"] == "ga")
    preview_count = sum(1 for i in innovations if i["status"] == "preview")
    emerging_count = sum(1 for i in innovations if i["status"] == "emerging")

    yield make_panel_complete(4, "innovation_overlay", {
        "innovations": innovations,
        "counts": {
            "total": len(innovations),
            "ga": ga_count,
            "preview": preview_count,
            "emerging": emerging_count,
        },
        "before_architecture": _build_arch_diagram(ctx.components, ctx.pattern_id),
        "after_architecture": _build_after_arch(ctx, innovations),
    })

    yield make_chat_message("assistant",
        f"**{len(innovations)} innovations** identified for your pain points. "
        f"See Innovations panel →"
    )

    yield make_step_transition(4, 5, "Running compliance analysis...")


def _build_arch_diagram(components: list[dict], pattern_id: str) -> dict:
    """Convert component list to ArchitectureDiagramData shape."""
    layers: dict[str, list] = {}
    for comp in components:
        layers.setdefault(comp.get("layer", "Foundation"), []).append({
            "name": comp["name"],
            "base_tier": comp.get("base_tier", comp.get("final_tier", 1)),
            "final_tier": comp.get("final_tier", 1),
            "elevation_reason": comp.get("elevation_reason"),
            "category": comp.get("category", ""),
        })
    return {
        "layers": [{"name": layer, "components": comps} for layer, comps in layers.items()],
        "pattern": pattern_id,
        "streaming": False,
    }


def _build_after_arch(ctx: PipelineContext, innovations: list[dict]) -> dict:
    """After-innovation architecture — same base with any enabled components added."""
    base = _build_arch_diagram(ctx.components, ctx.pattern_id)
    enabled_comps = [
        {
            "name": inn["enables"],
            "base_tier": 3,
            "final_tier": 3,
            "elevation_reason": f"Enabled by {inn['name']}",
            "category": "Innovation",
        }
        for inn in innovations
        if inn.get("enables")
    ]
    if enabled_comps:
        return {**base, "layers": base["layers"] + [{"name": "Innovations", "components": enabled_comps}]}
    return base
