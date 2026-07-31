"""Security, control-verification, and best-practice assurance builder."""
from __future__ import annotations

from datetime import date

from .models import (
    AssuranceCatalog,
    BestPracticePlanItem,
    ControlEvidence,
    ControlPlanItem,
    SecurityAssurancePlan,
    SelectedBundleContext,
    ThreatAssessment,
)


def _rating(score: float) -> str:
    if score >= 20:
        return "critical"
    if score >= 12:
        return "high"
    if score >= 6:
        return "moderate"
    return "low"


def _accepted_evidence(
    evidence: ControlEvidence,
    *,
    as_of: date,
) -> bool:
    return (
        evidence.status == "pass"
        and evidence.observed_at.date() <= as_of
        and (evidence.expires_on is None or evidence.expires_on >= as_of)
    )


def build_security_plan(
    assurance_catalog: AssuranceCatalog,
    active_component_ids: set[str],
    *,
    selected_bundle: SelectedBundleContext | None,
    as_of: date,
) -> SecurityAssurancePlan:
    evidence_by_control: dict[str, list[ControlEvidence]] = {}
    if selected_bundle is not None:
        for evidence in selected_bundle.control_evidence:
            evidence_by_control.setdefault(evidence.control_id, []).append(evidence)

    applicable_threats = tuple(
        threat
        for threat in assurance_catalog.threats
        if active_component_ids.intersection(threat.component_ids)
    )
    applicable_threat_ids = {threat.id for threat in applicable_threats}
    applicable_controls = tuple(
        control
        for control in assurance_catalog.controls
        if (
            applicable_threat_ids.intersection(control.threat_ids)
            and active_component_ids.intersection(control.component_ids)
        )
    )

    control_items: list[ControlPlanItem] = []
    verified_control_ids: set[str] = set()
    for control in applicable_controls:
        evidence = sorted(
            evidence_by_control.get(control.id, ()),
            key=lambda item: (item.observed_at, item.evidence_id),
        )
        accepted = tuple(
            item for item in evidence if _accepted_evidence(item, as_of=as_of)
        )
        if accepted:
            status = "verified"
            verified_control_ids.add(control.id)
        elif any(item.status == "fail" for item in evidence):
            status = "failed"
        else:
            status = "planned"
        control_items.append(
            ControlPlanItem(
                control_id=control.id,
                title=control.title,
                status=status,
                applicable_component_ids=tuple(
                    sorted(active_component_ids.intersection(control.component_ids))
                ),
                threat_ids=tuple(
                    sorted(applicable_threat_ids.intersection(control.threat_ids))
                ),
                effectiveness=control.effectiveness,
                verification=control.verification,
                evidence_ids=tuple(sorted(item.evidence_id for item in accepted)),
            )
        )

    controls_by_threat: dict[str, list[object]] = {}
    for control in applicable_controls:
        for threat_id in control.threat_ids:
            controls_by_threat.setdefault(threat_id, []).append(control)

    threat_items: list[ThreatAssessment] = []
    for threat in applicable_threats:
        inherent = float(threat.likelihood * threat.impact)
        controls = sorted(
            controls_by_threat.get(threat.id, ()),
            key=lambda item: item.id,
        )
        verified = [
            control for control in controls if control.id in verified_control_ids
        ]
        multiplier = 1.0
        for control in verified:
            multiplier *= 1.0 - control.effectiveness
        residual = round(inherent * multiplier, 2)
        threat_items.append(
            ThreatAssessment(
                threat_id=threat.id,
                title=threat.title,
                category=threat.category,
                applicable_component_ids=tuple(
                    sorted(active_component_ids.intersection(threat.component_ids))
                ),
                inherent_score=inherent,
                required_control_ids=tuple(control.id for control in controls),
                verified_control_ids=tuple(control.id for control in verified),
                residual_score=residual,
                residual_rating=_rating(residual),
            )
        )

    practice_items: list[BestPracticePlanItem] = []
    for practice in assurance_catalog.best_practices:
        components = tuple(
            sorted(active_component_ids.intersection(practice.component_ids))
        )
        if not components:
            continue
        relevant_controls = tuple(
            sorted(
                control_id
                for control_id in practice.control_ids
                if any(item.control_id == control_id for item in control_items)
            )
        )
        verified = bool(relevant_controls) and set(relevant_controls).issubset(
            verified_control_ids
        )
        practice_items.append(
            BestPracticePlanItem(
                practice_id=practice.id,
                title=practice.title,
                status="verified" if verified else "planned",
                rationale=practice.rationale,
                implementation=practice.implementation,
                applicable_component_ids=components,
                control_ids=relevant_controls,
            )
        )

    threat_items = sorted(threat_items, key=lambda item: item.threat_id)
    return SecurityAssurancePlan(
        threats=tuple(threat_items),
        controls=tuple(sorted(control_items, key=lambda item: item.control_id)),
        best_practices=tuple(
            sorted(practice_items, key=lambda item: item.practice_id)
        ),
        inherent_risk_total=round(
            sum(item.inherent_score for item in threat_items), 2
        ),
        residual_risk_total=round(
            sum(item.residual_score for item in threat_items), 2
        ),
        verified_control_count=len(verified_control_ids),
        high_or_critical_residual_count=sum(
            item.residual_rating in {"high", "critical"} for item in threat_items
        ),
    )
