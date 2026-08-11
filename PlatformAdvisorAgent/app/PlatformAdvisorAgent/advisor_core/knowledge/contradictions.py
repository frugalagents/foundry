"""Conservative contradiction detection for reviewed active claims."""
from __future__ import annotations

from datetime import date

from pydantic import Field

from .models import (
    Claim,
    ClaimClass,
    ClaimCriticality,
    FrozenModel,
    ReviewStatus,
    ScopeDimension,
    ScopeMode,
    StrEnum,
    canonical_json,
    content_hash,
)


class ContradictionType(StrEnum):
    DIRECT_VALUE_CONFLICT = "direct_value_conflict"
    NEGATED_RELATIONSHIP = "negated_relationship"


class ContradictionSeverity(StrEnum):
    WARNING = "warning"
    BLOCKING = "blocking"


class ClaimContradiction(FrozenModel):
    contradiction_type: ContradictionType
    severity: ContradictionSeverity
    claim_ids: tuple[str, str]
    subject_id: str = Field(min_length=1)
    predicates: tuple[str, str]
    rationale: str = Field(min_length=1)


class ContradictionReport(FrozenModel):
    as_of: date
    evaluated_claim_ids: tuple[str, ...]
    contradictions: tuple[ClaimContradiction, ...]
    report_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


NEGATED_PREDICATES = {
    "available_in": "not_available_in",
    "compatible_with": "incompatible_with",
    "requires": "does_not_require",
    "supports_interface": "does_not_support_interface",
}
NEGATED_PREDICATE_PAIRS = {
    frozenset((positive, negative))
    for positive, negative in NEGATED_PREDICATES.items()
}
SINGLE_OBJECT_PREDICATES = {
    "availability_status",
    "default_interface",
    "default_model",
    "deployment_model",
    "lifecycle_status",
}
BLOCKING_CLAIM_CLASSES = {
    ClaimClass.COMPATIBILITY,
    ClaimClass.PRICING_OR_QUOTA,
    ClaimClass.SECURITY_CONTROL,
}


def _dimension_overlaps(
    left: ScopeDimension,
    right: ScopeDimension,
) -> bool:
    if (
        left.mode is ScopeMode.NOT_APPLICABLE
        or right.mode is ScopeMode.NOT_APPLICABLE
    ):
        return (
            left.mode is ScopeMode.NOT_APPLICABLE
            and right.mode is ScopeMode.NOT_APPLICABLE
        )
    if left.mode is ScopeMode.ALL or right.mode is ScopeMode.ALL:
        return True
    return bool(set(left.values) & set(right.values))


def _scope_overlaps(left: Claim, right: Claim) -> bool:
    return all(
        _dimension_overlaps(
            getattr(left.scope, dimension),
            getattr(right.scope, dimension),
        )
        for dimension in (
            "provider",
            "product",
            "variant",
            "version",
            "region",
            "configuration",
        )
    )


def _time_overlaps(left: Claim, right: Claim) -> bool:
    left_end = left.effective_until or date.max
    right_end = right.effective_until or date.max
    return (
        left.effective_from <= right_end
        and right.effective_from <= left_end
    )


def _object_key(claim: Claim) -> str:
    return canonical_json(
        {
            "object_id": claim.object_id,
            "object_value": claim.object_value,
        }
    )


def _active_on(claim: Claim, as_of: date) -> bool:
    return (
        claim.lifecycle.value == "active"
        and claim.review.status is ReviewStatus.APPROVED
        and claim.effective_from <= as_of
        and (
            claim.effective_until is None
            or claim.effective_until >= as_of
        )
    )


def _severity(left: Claim, right: Claim) -> ContradictionSeverity:
    if (
        left.criticality is ClaimCriticality.CRITICAL
        or right.criticality is ClaimCriticality.CRITICAL
        or left.claim_class in BLOCKING_CLAIM_CLASSES
        or right.claim_class in BLOCKING_CLAIM_CLASSES
    ):
        return ContradictionSeverity.BLOCKING
    return ContradictionSeverity.WARNING


def _direct_value_conflict(left: Claim, right: Claim) -> bool:
    if left.predicate != right.predicate:
        return False
    if _object_key(left) == _object_key(right):
        return False
    if left.object_value is not None and right.object_value is not None:
        return True
    return left.predicate in SINGLE_OBJECT_PREDICATES


def _negated_relationship(left: Claim, right: Claim) -> bool:
    if frozenset((left.predicate, right.predicate)) not in (
        NEGATED_PREDICATE_PAIRS
    ):
        return False
    return _object_key(left) == _object_key(right)


def detect_contradictions(
    claims: tuple[Claim, ...],
    *,
    as_of: date,
) -> ContradictionReport:
    active = tuple(
        sorted(
            (claim for claim in claims if _active_on(claim, as_of)),
            key=lambda claim: claim.id,
        )
    )
    contradictions: list[ClaimContradiction] = []
    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            if left.subject_id != right.subject_id:
                continue
            if not _scope_overlaps(left, right) or not _time_overlaps(left, right):
                continue
            contradiction_type = None
            rationale = None
            if _direct_value_conflict(left, right):
                contradiction_type = ContradictionType.DIRECT_VALUE_CONFLICT
                rationale = (
                    "Claims assign different values to the same subject, "
                    "predicate, scope, and effective period."
                )
            elif _negated_relationship(left, right):
                contradiction_type = ContradictionType.NEGATED_RELATIONSHIP
                rationale = (
                    "Claims assert and deny the same relationship over an "
                    "overlapping scope and effective period."
                )
            if contradiction_type is None or rationale is None:
                continue
            contradictions.append(
                ClaimContradiction(
                    contradiction_type=contradiction_type,
                    severity=_severity(left, right),
                    claim_ids=(left.id, right.id),
                    subject_id=left.subject_id,
                    predicates=tuple(
                        sorted((left.predicate, right.predicate))
                    ),
                    rationale=rationale,
                )
            )

    payload = {
        "as_of": as_of.isoformat(),
        "evaluated_claim_ids": [claim.id for claim in active],
        "contradictions": [
            contradiction.model_dump(mode="json")
            for contradiction in contradictions
        ],
    }
    return ContradictionReport(
        as_of=as_of,
        evaluated_claim_ids=tuple(payload["evaluated_claim_ids"]),
        contradictions=tuple(contradictions),
        report_hash=content_hash(payload),
    )
