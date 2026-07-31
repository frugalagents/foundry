"""Agentic engine for the Platform Advisor: propose → guard → generate →
critic, producing a solution stack, grounded rationale, and a Decision Record."""
from __future__ import annotations

import hashlib
import json

from advisor_core.v3.guard import (
    Citation,
    DecisionRecord,
    ModelStamp,
)

from . import agents, domain
from .llm import TEMPERATURE


def _stack(proposal) -> list[dict]:
    out = []
    for c in proposal.components:
        out.append({
            "box_id": c.box_id,
            "component_id": c.component_id,
            "chosen": c.chosen_label or c.component_id,
            "alternatives": list(c.alternatives),
        })
    return out


def generate_architecture(
    *,
    workspace_id: str,
    answers: dict,
    boxes: list[str],
    created_at: str,
) -> dict:
    """Run the full engine and return the strategy output + Decision Record.

    `created_at` is supplied by the caller (no clock in the pure core).
    """
    result = agents.propose(answers, boxes)
    proposal = result["proposal"]
    verdict = result["verdict"]

    gen = agents.generate(proposal, answers)
    concerns = agents.critique(gen["rationale"]) if gen["rationale"] else []

    record_id = "rec-" + hashlib.sha256(
        json.dumps({"w": workspace_id, "a": answers, "t": created_at},
                   sort_keys=True).encode()
    ).hexdigest()[:16]

    record = DecisionRecord(
        record_id=record_id,
        workspace_id=workspace_id,
        created_at=created_at,
        answers=answers,
        proposal=proposal,
        guard_verdict=verdict,
        citations=tuple(
            Citation(claim_or_source_id=c.get("source", "") or "kb",
                     uri=c.get("source", ""),
                     retrieval_score=c.get("score"))
            for c in gen["citations"]
        ),
        catalog_hash="",  # filled from catalog release when wired to v3 engine
        guard_version=verdict.guard_version,
        model_stamp=ModelStamp(
            model_id=result["model_id"],
            prompt_hash=result["prompt_hash"],
            temperature=TEMPERATURE,
        ),
    )

    return {
        "stack": _stack(proposal),
        "rationale": gen["rationale"],
        "grounded": gen["grounded"],
        "citations": gen["citations"],
        "cascades": result["cascades"],
        "critic_concerns": concerns,
        "guard": {
            "passed": verdict.passed,
            "guard_version": verdict.guard_version,
            "violations": [v.model_dump() for v in verdict.violations],
        },
        "source": result["source"],
        "decision_record": record.model_dump(mode="json"),
    }


__all__ = ["generate_architecture", "domain"]
