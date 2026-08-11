"""Immutable human review state for extracted knowledge candidates."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from .candidates import ClaimCandidate
from .models import (
    CLAIM_REVIEW_POLICIES,
    FrozenModel,
    StableId,
    StrEnum,
    content_hash,
)


class KnowledgeReviewState(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    STALE = "stale"
    DISPUTED = "disputed"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    SUPERSEDE = "supersede"
    MARK_STALE = "mark_stale"
    DISPUTE = "dispute"


class ReviewTransitionError(ValueError):
    pass


class ReviewDecision(FrozenModel):
    decision_id: StableId
    candidate_id: StableId
    action: ReviewAction
    prior_state: KnowledgeReviewState
    resulting_state: KnowledgeReviewState
    reviewer_id: StableId
    decided_at: datetime
    rationale: str = Field(min_length=1)
    replacement_candidate_id: StableId | None = None


class KnowledgeReviewRecord(FrozenModel):
    candidate_id: StableId
    state: KnowledgeReviewState
    created_at: datetime
    updated_at: datetime
    decisions: tuple[ReviewDecision, ...] = ()
    replacement_candidate_id: StableId | None = None
    record_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("decisions")
    @classmethod
    def decisions_are_ordered_and_unique(
        cls,
        decisions: tuple[ReviewDecision, ...],
    ) -> tuple[ReviewDecision, ...]:
        identifiers = [decision.decision_id for decision in decisions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("review decision IDs must be unique")
        return tuple(sorted(decisions, key=lambda item: item.decided_at))


def _record_hash(
    *,
    candidate_id: str,
    state: KnowledgeReviewState,
    created_at: datetime,
    updated_at: datetime,
    decisions: tuple[ReviewDecision, ...],
    replacement_candidate_id: str | None,
) -> str:
    return content_hash(
        {
            "candidate_id": candidate_id,
            "state": state.value,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
            "decisions": [
                decision.model_dump(mode="json") for decision in decisions
            ],
            "replacement_candidate_id": replacement_candidate_id,
        }
    )


def initialize_review(
    candidate: ClaimCandidate,
    *,
    created_at: datetime,
) -> KnowledgeReviewRecord:
    state = KnowledgeReviewState.PROPOSED
    return KnowledgeReviewRecord(
        candidate_id=candidate.id,
        state=state,
        created_at=created_at,
        updated_at=created_at,
        decisions=(),
        record_hash=_record_hash(
            candidate_id=candidate.id,
            state=state,
            created_at=created_at,
            updated_at=created_at,
            decisions=(),
            replacement_candidate_id=None,
        ),
    )


def _required_approvals(candidate: ClaimCandidate) -> int:
    return CLAIM_REVIEW_POLICIES[candidate.claim_class].minimum_reviewers


def _approval_reviewers(
    record: KnowledgeReviewRecord,
) -> set[str]:
    return {
        decision.reviewer_id
        for decision in record.decisions
        if decision.action is ReviewAction.APPROVE
    }


def apply_review_action(
    record: KnowledgeReviewRecord,
    candidate: ClaimCandidate,
    *,
    action: ReviewAction | str,
    reviewer_id: str,
    decided_at: datetime,
    rationale: str,
    base_record_hash: str,
    replacement_candidate_id: str | None = None,
) -> KnowledgeReviewRecord:
    """Apply one optimistic, append-only review decision."""

    action = ReviewAction(action)
    if record.candidate_id != candidate.id:
        raise ReviewTransitionError(
            "review record does not belong to candidate"
        )
    if base_record_hash != record.record_hash:
        raise ReviewTransitionError("stale review record hash")
    if decided_at < record.updated_at:
        raise ReviewTransitionError(
            "review decision cannot precede current record"
        )
    if record.state in {
        KnowledgeReviewState.REJECTED,
        KnowledgeReviewState.SUPERSEDED,
    }:
        raise ReviewTransitionError(
            f"cannot transition terminal state {record.state.value}"
        )

    approval_reviewers = _approval_reviewers(record)
    resulting_state = record.state
    if action is ReviewAction.APPROVE:
        if record.state not in {
            KnowledgeReviewState.PROPOSED,
            KnowledgeReviewState.DISPUTED,
            KnowledgeReviewState.STALE,
        }:
            raise ReviewTransitionError(
                f"cannot approve state {record.state.value}"
            )
        if reviewer_id in approval_reviewers:
            raise ReviewTransitionError(
                "reviewer has already approved this candidate"
            )
        approval_reviewers.add(reviewer_id)
        resulting_state = (
            KnowledgeReviewState.APPROVED
            if len(approval_reviewers) >= _required_approvals(candidate)
            else record.state
        )
    elif action is ReviewAction.REJECT:
        resulting_state = KnowledgeReviewState.REJECTED
    elif action is ReviewAction.DISPUTE:
        resulting_state = KnowledgeReviewState.DISPUTED
    elif action is ReviewAction.MARK_STALE:
        resulting_state = KnowledgeReviewState.STALE
    elif action is ReviewAction.SUPERSEDE:
        if record.state not in {
            KnowledgeReviewState.APPROVED,
            KnowledgeReviewState.DISPUTED,
            KnowledgeReviewState.STALE,
        }:
            raise ReviewTransitionError(
                f"cannot supersede state {record.state.value}"
            )
        if replacement_candidate_id is None:
            raise ReviewTransitionError(
                "supersede requires replacement_candidate_id"
            )
        if replacement_candidate_id == candidate.id:
            raise ReviewTransitionError(
                "candidate cannot supersede itself"
            )
        resulting_state = KnowledgeReviewState.SUPERSEDED

    decision_payload = {
        "candidate_id": candidate.id,
        "action": action.value,
        "prior_state": record.state.value,
        "resulting_state": resulting_state.value,
        "reviewer_id": reviewer_id,
        "decided_at": decided_at.isoformat(),
        "rationale": rationale,
        "replacement_candidate_id": replacement_candidate_id,
        "base_record_hash": base_record_hash,
    }
    decision_hash = content_hash(decision_payload)
    decision = ReviewDecision(
        decision_id=f"review-decision:d-{decision_hash[7:27]}",
        candidate_id=candidate.id,
        action=action,
        prior_state=record.state,
        resulting_state=resulting_state,
        reviewer_id=reviewer_id,
        decided_at=decided_at,
        rationale=rationale,
        replacement_candidate_id=replacement_candidate_id,
    )
    decisions = (*record.decisions, decision)
    replacement = (
        replacement_candidate_id
        if resulting_state is KnowledgeReviewState.SUPERSEDED
        else record.replacement_candidate_id
    )
    return KnowledgeReviewRecord(
        candidate_id=candidate.id,
        state=resulting_state,
        created_at=record.created_at,
        updated_at=decided_at,
        decisions=decisions,
        replacement_candidate_id=replacement,
        record_hash=_record_hash(
            candidate_id=candidate.id,
            state=resulting_state,
            created_at=record.created_at,
            updated_at=decided_at,
            decisions=decisions,
            replacement_candidate_id=replacement,
        ),
    )
