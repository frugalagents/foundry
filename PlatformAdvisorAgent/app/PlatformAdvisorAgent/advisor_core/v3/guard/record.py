"""The Decision Record — the answer to the honest risk.

An agentic system that hardens over time accumulates historical
recommendations made before a given check existed, and temp-0 agents are not
bit-reproducible across model versions. So instead of promising deterministic
replay, we persist a full provenance record per generation: what was proposed,
what the guard checked, what was cited, and under which knowledge/model
versions. That makes every agentic decision forensically reconstructable and
turns "recommendations made before check X existed" into a queryable
remediation backlog rather than a silent liability.
"""
from __future__ import annotations

from .models import FrozenModel, GuardVerdict, Proposal


class Citation(FrozenModel):
    claim_or_source_id: str
    locator: str = ""
    uri: str = ""
    retrieval_score: float | None = None


class ModelStamp(FrozenModel):
    """Exactly which model/prompt produced the agentic parts."""

    model_id: str
    model_version: str = ""
    prompt_hash: str = ""
    temperature: float | None = None


class DecisionRecord(FrozenModel):
    """Immutable provenance for one 'generate my architecture' event.

    Persisted alongside the workspace state. `guard_version`, `catalog_hash`,
    and the model stamp are what let a future check answer "would today's guard
    veto this?" without re-running the original agents.
    """

    record_id: str
    workspace_id: str
    created_at: str                      # ISO-8601, supplied by the caller
    # what the user told us at generation time
    answers: dict[str, object]
    # what the agent proposed (chosen + alternatives + reasoning per box)
    proposal: Proposal
    # what the deterministic guard concluded
    guard_verdict: GuardVerdict
    # what the narrative was grounded on
    citations: tuple[Citation, ...] = ()
    # exactly which knowledge + model versions were in force
    catalog_hash: str = ""
    guard_version: str = ""
    model_stamp: ModelStamp | None = None
    # reproducibility posture, stated honestly in the record itself
    reproducibility: str = "reproducible-with-trace, not bit-identical"


def revalidate(
    record: DecisionRecord,
    current_verdict: GuardVerdict,
) -> dict[str, object]:
    """Compare a stored record against a fresh guard run on reopen.

    Returns a small summary the UI turns into a non-blocking banner when a
    now-existing check would veto a decision that shipped under an older guard.
    """
    stale_guard = record.guard_verdict.guard_version != current_verdict.guard_version
    newly_vetoed = current_verdict.vetoed and not record.guard_verdict.vetoed
    return {
        "stale_guard": stale_guard,
        "recorded_guard_version": record.guard_verdict.guard_version,
        "current_guard_version": current_verdict.guard_version,
        "newly_vetoed": newly_vetoed,
        "new_violations": [v.model_dump() for v in current_verdict.violations],
        "needs_review": stale_guard and (newly_vetoed or current_verdict.vetoed),
    }
