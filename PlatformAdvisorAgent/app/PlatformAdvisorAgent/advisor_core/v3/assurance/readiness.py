"""Fail-closed decision-readiness assessment for assurance packets."""
from __future__ import annotations

from datetime import date

from ..deployable.models import (
    CandidateBundle,
    CompatibilityStatus,
    DeployableDecisionMatrix,
)
from ..engine import evaluate_revision_deployment_families
from ..models import (
    CatalogRelease,
    EvidenceReviewStatus,
    FeasibilityStatus,
    WorkspaceRevision,
)
from .models import (
    DecisionReadiness,
    EconomicsPlan,
    EvidenceReadinessSignal,
    ExpertReviewReadinessSignal,
    FreshnessReadinessSignal,
    SecurityAssurancePlan,
    StabilityReadinessSignal,
)


def _selected_candidate(
    matrix: DeployableDecisionMatrix,
    selected_bundle_id: str | None,
) -> CandidateBundle | None:
    if selected_bundle_id is None:
        return None
    return next(
        (
            candidate
            for candidate in matrix.candidates
            if candidate.bundle_id == selected_bundle_id
        ),
        None,
    )


def _evidence_signals(
    revision: WorkspaceRevision,
    catalog: CatalogRelease,
    matrix: DeployableDecisionMatrix,
    candidate: CandidateBundle | None,
    *,
    as_of: date,
) -> tuple[EvidenceReadinessSignal, FreshnessReadinessSignal]:
    claim_by_id = {claim.id: claim for claim in catalog.evidence_claims}
    component_by_id = {
        component.id: component for component in catalog.components
    }
    pattern_by_id = {pattern.id: pattern for pattern in catalog.patterns}
    claim_ids: set[str] = set()
    unevidenced: set[str] = set()

    if candidate is None:
        unevidenced.add("decision-input:bundle-selection")
    else:
        pattern = pattern_by_id[candidate.deployment_family_id]
        if pattern.evidence_claim_ids:
            claim_ids.update(pattern.evidence_claim_ids)
        else:
            unevidenced.add(pattern.id)

        selected_component_ids = {
            selection.component_id for selection in candidate.selections
        }
        for component_id in sorted(selected_component_ids):
            component = component_by_id[component_id]
            if component.evidence_claim_ids:
                claim_ids.update(component.evidence_claim_ids)
            else:
                unevidenced.add(component.id)

        evaluations = {
            item.pattern_id: item
            for item in evaluate_revision_deployment_families(
                revision,
                catalog,
            )
        }
        family = evaluations[candidate.deployment_family_id]
        for evaluation in (
            *family.component_rule_evaluations,
            *family.feasibility_rule_evaluations,
        ):
            if evaluation.evidence_claim_ids:
                claim_ids.update(evaluation.evidence_claim_ids)
            else:
                unevidenced.add(evaluation.rule_id)

        # R0.2 deployable scoring and offering records have no evidence-link
        # fields. Record that gap rather than implying catalog support.
        unevidenced.add(candidate.template_id)
        unevidenced.add(matrix.score_profile_id)
        unevidenced.update(
            selection.service_variant_id
            for selection in candidate.selections
        )

    verified: set[str] = set()
    unverified: set[str] = set()
    stale: set[str] = set()
    for claim_id in sorted(claim_ids):
        claim = claim_by_id.get(claim_id)
        if (
            claim is None
            or claim.review_status is not EvidenceReviewStatus.APPROVED
            or not claim.reviewer
            or claim.effective_on > as_of
        ):
            unverified.add(claim_id)
        elif claim.expires_on is not None and claim.expires_on < as_of:
            stale.add(claim_id)
        else:
            verified.add(claim_id)

    if unverified or stale:
        evidence_status = "unverified"
    elif unevidenced:
        evidence_status = "incomplete"
    else:
        evidence_status = "complete"
    if stale:
        freshness_status = "stale"
    elif unverified or not claim_ids:
        freshness_status = "unknown"
    else:
        freshness_status = "current"

    return (
        EvidenceReadinessSignal(
            status=evidence_status,
            verified_claim_ids=tuple(verified),
            unverified_claim_ids=tuple(unverified | stale),
            unevidenced_input_ids=tuple(unevidenced),
        ),
        FreshnessReadinessSignal(
            status=freshness_status,
            evaluated_as_of=as_of,
            stale_claim_ids=tuple(stale),
        ),
    )


def build_decision_readiness(
    revision: WorkspaceRevision,
    catalog: CatalogRelease,
    matrix: DeployableDecisionMatrix,
    economics: EconomicsPlan,
    security: SecurityAssurancePlan,
    *,
    selected_bundle_id: str | None,
    as_of: date,
) -> DecisionReadiness:
    candidate = _selected_candidate(matrix, selected_bundle_id)
    evidence, freshness = _evidence_signals(
        revision,
        catalog,
        matrix,
        candidate,
        as_of=as_of,
    )

    winner_changes = tuple(
        item.dimension_id
        for item in matrix.sensitivity
        if (
            candidate is not None
            and item.baseline_candidate_id == candidate.bundle_id
            and item.winner_changes
        )
    )
    candidate_sensitivity = tuple(
        item
        for item in matrix.sensitivity
        if (
            candidate is not None
            and item.baseline_candidate_id == candidate.bundle_id
        )
    )
    if candidate is None or not candidate_sensitivity:
        stability_status = "unknown"
        score_margin = None
    elif winner_changes:
        stability_status = "sensitive"
        score_margin = min(
            item.score_margin_at_baseline for item in candidate_sensitivity
        )
    else:
        stability_status = "stable"
        score_margin = min(
            item.score_margin_at_baseline for item in candidate_sensitivity
        )
    stability = StabilityReadinessSignal(
        status=stability_status,
        selected_candidate_id=(
            candidate.bundle_id if candidate is not None else None
        ),
        winner_change_dimension_ids=winner_changes,
        score_margin=score_margin,
    )

    blockers: set[str] = set()
    expert_reasons: set[str] = set()
    needs_information = False
    if selected_bundle_id is None:
        blockers.add("bundle_selection_missing")
        needs_information = True
    elif candidate is None:
        blockers.add("bundle_selection_unrecognized")
        needs_information = True
    else:
        if candidate.family_feasibility_status is FeasibilityStatus.UNKNOWN:
            blockers.add("deployment_family_unresolved")
            needs_information = True
        elif candidate.family_feasibility_status is FeasibilityStatus.REJECTED:
            blockers.add("deployment_family_rejected")
            expert_reasons.add("deployment_family_rejected")
        if candidate.compatibility_status is CompatibilityStatus.INCOMPATIBLE:
            blockers.add("bundle_incompatible")
            expert_reasons.add("bundle_incompatible")
        elif candidate.compatibility_status is CompatibilityStatus.CONDITIONAL:
            blockers.add("bundle_conditional")

    if evidence.status != "complete":
        blockers.add("evidence_incomplete")
    if evidence.unverified_claim_ids:
        expert_reasons.add("claims_unverified")
    if freshness.status != "current":
        blockers.add("evidence_freshness_unresolved")
    if freshness.status == "stale":
        expert_reasons.add("claims_stale")
    if stability.status != "stable":
        blockers.add("recommendation_stability_unresolved")
    if any(cost.status != "evidence_backed" for cost in economics.unit_costs):
        blockers.add("economics_not_evidence_backed")
    if any(control.status == "failed" for control in security.controls):
        blockers.add("control_verification_failed")
        expert_reasons.add("control_verification_failed")

    expert_review = ExpertReviewReadinessSignal(
        required=bool(expert_reasons),
        reason_codes=tuple(expert_reasons),
    )
    if expert_review.required:
        state = "expert_review"
    elif needs_information:
        state = "needs_information"
    elif blockers:
        state = "conditional"
    else:
        state = "decision_ready"
    return DecisionReadiness(
        state=state,
        evidence=evidence,
        freshness=freshness,
        stability=stability,
        expert_review=expert_review,
        blocking_reason_codes=tuple(blockers),
    )
