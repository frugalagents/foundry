"""Reviewed decision-pattern guidance and contextual workspace projection."""
from __future__ import annotations

from datetime import date

from pydantic import Field, field_validator, model_validator

from .models import (
    Claim,
    DecisionPattern,
    FrozenModel,
    KnowledgeEntity,
    KnowledgeLifecycle,
    ReviewStatus,
    StableId,
    content_hash,
)
from .snapshot_store import SnapshotManifest
from .source_registry import SourceRegistry


TEMPLATE_TAG_PREFIX = "bundle-template:"


class DecisionGuidanceCompilationError(ValueError):
    """Raised when reviewed decision guidance cannot be compiled safely."""


class DecisionGuidanceEvidence(FrozenModel):
    claim_id: StableId
    statement: str = Field(min_length=1)
    review_status: str = Field(min_length=1)
    effective_from: date
    stale_after: date
    source_snapshot_id: StableId
    source_id: StableId
    source_name: str = Field(min_length=1)
    source_publisher: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    authority_tier: str = Field(min_length=1)


class ReviewedDecisionPattern(FrozenModel):
    pattern_id: StableId
    template_id: StableId
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    recommended_when: tuple[str, ...]
    avoid_when: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    reviewed_at: str = Field(min_length=1)
    reviewer_ids: tuple[StableId, ...] = Field(min_length=1)
    evidence: tuple[DecisionGuidanceEvidence, ...] = Field(min_length=1)

    @field_validator(
        "recommended_when",
        "avoid_when",
        "tradeoffs",
        "reviewer_ids",
    )
    @classmethod
    def values_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("decision guidance values must be unique")
        return values


class DecisionGuidanceProjection(FrozenModel):
    schema_version: str = "1.0"
    as_of: date
    patterns: tuple[ReviewedDecisionPattern, ...]
    projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def projection_hash_matches_content(self) -> "DecisionGuidanceProjection":
        payload = self.model_dump(mode="json", exclude={"projection_hash"})
        if self.projection_hash != content_hash(payload):
            raise ValueError(
                "decision guidance hash does not match projection content"
            )
        template_ids = [pattern.template_id for pattern in self.patterns]
        if len(template_ids) != len(set(template_ids)):
            raise ValueError(
                "decision guidance must contain at most one pattern per template"
            )
        return self


def _template_id(pattern: DecisionPattern) -> str:
    matches = tuple(
        tag for tag in pattern.tags if tag.startswith(TEMPLATE_TAG_PREFIX)
    )
    if len(matches) != 1:
        raise DecisionGuidanceCompilationError(
            f"{pattern.id} must have exactly one bundle-template tag"
        )
    return matches[0]


def compile_decision_guidance(
    *,
    entities: tuple[KnowledgeEntity, ...],
    source_registry: SourceRegistry,
    snapshots: tuple[SnapshotManifest, ...],
    as_of: date,
) -> DecisionGuidanceProjection:
    """Compile approved and current patterns into a cited runtime artifact."""

    claims = {
        entity.id: entity
        for entity in entities
        if isinstance(entity, Claim)
    }
    sources = {source.id: source for source in source_registry.sources}
    snapshots_by_id = {
        snapshot.snapshot_id: snapshot for snapshot in snapshots
    }
    compiled: list[ReviewedDecisionPattern] = []
    for pattern in sorted(
        (
            entity
            for entity in entities
            if isinstance(entity, DecisionPattern)
            and entity.lifecycle is KnowledgeLifecycle.ACTIVE
            and entity.review.status is ReviewStatus.APPROVED
            and entity.effective_from <= as_of <= entity.stale_after
            and (
                entity.effective_until is None
                or as_of <= entity.effective_until
            )
        ),
        key=lambda item: item.id,
    ):
        evidence: list[DecisionGuidanceEvidence] = []
        for claim_id in pattern.supporting_claim_ids:
            claim = claims.get(claim_id)
            if (
                claim is None
                or claim.lifecycle is not KnowledgeLifecycle.ACTIVE
                or claim.review.status is not ReviewStatus.APPROVED
                or not (
                    claim.effective_from <= as_of <= claim.stale_after
                )
                or (
                    claim.effective_until is not None
                    and as_of > claim.effective_until
                )
            ):
                raise DecisionGuidanceCompilationError(
                    f"{pattern.id} references unavailable claim {claim_id}"
                )
            for reference in claim.evidence:
                snapshot = snapshots_by_id.get(reference.source_snapshot_id)
                if snapshot is None:
                    raise DecisionGuidanceCompilationError(
                        f"{claim.id} references missing snapshot "
                        f"{reference.source_snapshot_id}"
                    )
                source = sources.get(snapshot.source_id)
                if source is None:
                    raise DecisionGuidanceCompilationError(
                        f"{snapshot.snapshot_id} references missing source "
                        f"{snapshot.source_id}"
                    )
                evidence.append(
                    DecisionGuidanceEvidence(
                        claim_id=claim.id,
                        statement=claim.statement,
                        review_status=claim.review.status.value,
                        effective_from=claim.effective_from,
                        stale_after=claim.stale_after,
                        source_snapshot_id=snapshot.snapshot_id,
                        source_id=source.id,
                        source_name=source.name,
                        source_publisher=source.publisher,
                        source_uri=str(source.base_uri),
                        source_locator=reference.source_locator,
                        authority_tier=reference.authority_tier.value,
                    )
                )
        compiled.append(
            ReviewedDecisionPattern(
                pattern_id=pattern.id,
                template_id=_template_id(pattern),
                title=pattern.title,
                summary=pattern.summary,
                decision=pattern.decision,
                recommended_when=pattern.recommended_when,
                avoid_when=pattern.avoid_when,
                tradeoffs=pattern.tradeoffs,
                reviewed_at=pattern.review.reviewed_at.isoformat(),
                reviewer_ids=pattern.review.reviewer_ids,
                evidence=tuple(
                    sorted(
                        evidence,
                        key=lambda item: (
                            item.claim_id,
                            item.source_snapshot_id,
                        ),
                    )
                ),
            )
        )
    payload = {
        "schema_version": "1.0",
        "as_of": as_of.isoformat(),
        "patterns": [
            pattern.model_dump(mode="json") for pattern in compiled
        ],
    }
    return DecisionGuidanceProjection(
        **payload,
        projection_hash=content_hash(payload),
    )


def contextualize_decision_guidance(
    projection: dict[str, object],
    guidance: DecisionGuidanceProjection,
) -> list[dict[str, object]]:
    """Attach reviewed guidance to each candidate using current customer facts."""

    patterns = {
        pattern.template_id: pattern for pattern in guidance.patterns
    }
    requirements = {
        str(item["requirement_id"]): item
        for item in projection.get("requirements", [])
        if isinstance(item, dict) and "requirement_id" in item
    }
    deployable = projection.get("deployable_solution")
    if not isinstance(deployable, dict):
        return []
    results: list[dict[str, object]] = []
    for candidate in deployable.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        template_id = candidate.get("template_id")
        if not isinstance(template_id, str):
            continue
        pattern = patterns.get(template_id)
        if pattern is None:
            continue
        matched = sorted(
            {
                str(finding["requirement_id"])
                for finding in candidate.get("findings", [])
                if (
                    isinstance(finding, dict)
                    and finding.get("status") == "compatible"
                    and finding.get("requirement_id") in requirements
                )
            }
        )
        conditions = sorted(
            {
                str(finding["requirement_id"])
                for finding in candidate.get("findings", [])
                if (
                    isinstance(finding, dict)
                    and finding.get("status") in {
                        "conditional",
                        "incompatible",
                    }
                    and finding.get("requirement_id") in requirements
                )
            }
        )
        status = str(candidate.get("compatibility_status", "conditional"))
        fit_summary = {
            "compatible": (
                "Fits the confirmed customer constraints. Validate the "
                "reviewed trade-offs and implementation evidence before "
                "acceptance."
            ),
            "conditional": (
                "Potential fit, but one or more customer decisions or "
                "implementation conditions remain unresolved."
            ),
            "incompatible": (
                "Does not fit the current customer constraints. Review the "
                "blocking findings before considering this pattern."
            ),
        }.get(status, "Fit has not been established.")
        results.append({
            "candidate_id": candidate.get("bundle_id"),
            "template_id": template_id,
            "pattern_id": pattern.pattern_id,
            "title": pattern.title,
            "summary": pattern.summary,
            "decision": pattern.decision,
            "fit": {
                "status": status,
                "summary": fit_summary,
                "matched_requirements": [
                    {
                        "requirement_id": requirement_id,
                        "name": requirements[requirement_id].get("name"),
                        "value": requirements[requirement_id].get("value"),
                    }
                    for requirement_id in matched
                ],
                "conditional_requirements": [
                    {
                        "requirement_id": requirement_id,
                        "name": requirements[requirement_id].get("name"),
                        "value": requirements[requirement_id].get("value"),
                    }
                    for requirement_id in conditions
                ],
            },
            "recommended_when": list(pattern.recommended_when),
            "avoid_when": list(pattern.avoid_when),
            "tradeoffs": list(pattern.tradeoffs),
            "reviewed_at": pattern.reviewed_at,
            "reviewer_ids": list(pattern.reviewer_ids),
            "evidence": [
                item.model_dump(mode="json") for item in pattern.evidence
            ],
            "advisory": True,
        })
    return sorted(results, key=lambda item: str(item["candidate_id"]))
