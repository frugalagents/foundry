"""Deterministic Git pull-request bundles for knowledge review."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path, PurePosixPath

from pydantic import Field, field_validator, model_validator

from .candidates import ClaimCandidate
from .contradictions import ContradictionReport
from .models import FrozenModel, StableId, content_hash
from .source_registry import SourceRegistryEntry
from .structural_diff import ChangeSignificance, StructuralDiff


class ReviewBundleConflictError(RuntimeError):
    pass


class AffectedEntity(FrozenModel):
    entity_id: StableId
    roles: tuple[str, ...] = Field(min_length=1)

    @field_validator("roles")
    @classmethod
    def unique_sorted_roles(cls, roles: tuple[str, ...]) -> tuple[str, ...]:
        if len(roles) != len(set(roles)):
            raise ValueError("affected entity roles must be unique")
        return tuple(sorted(roles))


class GeneratedReviewFile(FrozenModel):
    path: str = Field(min_length=1)
    content: str
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def path_and_hash_are_safe(self) -> "GeneratedReviewFile":
        path = PurePosixPath(self.path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("generated review file path must be relative")
        if self.content_hash != content_hash({"content": self.content}):
            raise ValueError("generated review file hash does not match content")
        return self


class KnowledgePullRequestBundle(FrozenModel):
    review_id: StableId
    generated_at: datetime
    source_id: StableId
    title: str = Field(min_length=1)
    branch_name: str = Field(pattern=r"^knowledge/[a-z0-9._/-]+$")
    commit_message: str = Field(min_length=1)
    body_markdown: str = Field(min_length=1)
    candidate_ids: tuple[StableId, ...] = Field(min_length=1)
    affected_entities: tuple[AffectedEntity, ...]
    files: tuple[GeneratedReviewFile, ...] = Field(min_length=1)
    bundle_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("candidate_ids")
    @classmethod
    def unique_sorted_candidates(
        cls,
        candidate_ids: tuple[StableId, ...],
    ) -> tuple[StableId, ...]:
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate IDs must be unique")
        return tuple(sorted(candidate_ids))

    @field_validator("affected_entities")
    @classmethod
    def unique_sorted_entities(
        cls,
        entities: tuple[AffectedEntity, ...],
    ) -> tuple[AffectedEntity, ...]:
        identifiers = [entity.entity_id for entity in entities]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("affected entities must be unique")
        return tuple(sorted(entities, key=lambda entity: entity.entity_id))

    @field_validator("files")
    @classmethod
    def unique_sorted_files(
        cls,
        files: tuple[GeneratedReviewFile, ...],
    ) -> tuple[GeneratedReviewFile, ...]:
        paths = [file.path for file in files]
        if len(paths) != len(set(paths)):
            raise ValueError("generated review file paths must be unique")
        return tuple(sorted(files, key=lambda file: file.path))


def _json_text(value: object) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )


def _generated_file(path: str, content: str) -> GeneratedReviewFile:
    return GeneratedReviewFile(
        path=path,
        content=content,
        content_hash=content_hash({"content": content}),
    )


def _affected_entities(
    candidates: tuple[ClaimCandidate, ...],
) -> tuple[AffectedEntity, ...]:
    roles: dict[str, set[str]] = {}
    for candidate in candidates:
        roles.setdefault(candidate.subject_id, set()).add("claim_subject")
        if candidate.object_id is not None:
            roles.setdefault(candidate.object_id, set()).add("claim_object")
        for relationship in candidate.proposed_relationships:
            roles.setdefault(relationship.target_id, set()).add(
                "relationship_target"
            )
    return tuple(
        AffectedEntity(entity_id=entity_id, roles=tuple(entity_roles))
        for entity_id, entity_roles in sorted(roles.items())
    )


def _reviewer_guide(
    source: SourceRegistryEntry,
    diff: StructuralDiff,
    candidates: tuple[ClaimCandidate, ...],
    entities: tuple[AffectedEntity, ...],
    contradictions: ContradictionReport | None,
) -> str:
    relevant_changes = sum(
        1
        for change in diff.changes
        if change.significance is ChangeSignificance.DECISION_RELEVANT
    )
    lines = [
        f"# Knowledge review: {source.name}",
        "",
        "## Source Change",
        "",
        f"- Source: `{source.id}`",
        f"- Prior snapshot: `{diff.prior_snapshot_id}`",
        f"- Current snapshot: `{diff.current_snapshot_id}`",
        f"- Structural changes: {len(diff.changes)}",
        f"- Decision-relevant changes: {relevant_changes}",
        f"- Ignored navigation/noise blocks: {diff.ignored_noise_blocks}",
        "",
        "## Proposed Claims",
        "",
        "| Candidate | Class | Confidence | Warnings |",
        "|---|---|---:|---|",
    ]
    for candidate in candidates:
        warnings = ", ".join(
            warning.value for warning in candidate.warnings
        ) or "none"
        lines.append(
            f"| `{candidate.id}` | `{candidate.claim_class.value}` | "
            f"{candidate.confidence:.2f} | {warnings} |"
        )
    lines.extend(
        [
            "",
            "## Affected Entities",
            "",
        ]
    )
    for entity in entities:
        lines.append(
            f"- `{entity.entity_id}`: {', '.join(entity.roles)}"
        )
    lines.extend(
        [
            "",
            "## Contradictions",
            "",
        ]
    )
    if contradictions is None:
        lines.append("- Not evaluated.")
    elif not contradictions.contradictions:
        lines.append("- No active-claim contradictions detected.")
    else:
        for contradiction in contradictions.contradictions:
            lines.append(
                f"- **{contradiction.severity.value}** "
                f"`{contradiction.contradiction_type.value}`: "
                f"{', '.join(contradiction.claim_ids)}"
            )
    lines.extend(
        [
            "",
            "## Reviewer Guide",
            "",
            "- [ ] Confirm each exact excerpt exists at its source locator.",
            "- [ ] Confirm provider, product, variant, version, region, and "
            "configuration scope.",
            "- [ ] Confirm claim class and source authority are admissible.",
            "- [ ] Resolve low-confidence, ambiguity, and truncation warnings.",
            "- [ ] Validate proposed entity identities and relationships.",
            "- [ ] Resolve every blocking contradiction.",
            "- [ ] Confirm freshness and effective dates.",
            "- [ ] Approve or reject through the review workflow; do not edit "
            "compiled catalogs directly.",
            "",
        ]
    )
    return "\n".join(lines)


def build_knowledge_pull_request(
    source: SourceRegistryEntry,
    diff: StructuralDiff,
    candidates: tuple[ClaimCandidate, ...],
    *,
    generated_at: datetime,
    contradictions: ContradictionReport | None = None,
) -> KnowledgePullRequestBundle:
    """Build files and metadata for a human-reviewed knowledge PR."""

    if not candidates:
        raise ValueError("knowledge review requires at least one candidate")
    if diff.source_id != source.id:
        raise ValueError("source diff does not belong to registry source")
    current_snapshot_ids = {
        candidate.locator.source_snapshot_id for candidate in candidates
    }
    if current_snapshot_ids != {diff.current_snapshot_id}:
        raise ValueError(
            "all candidates must reference the current source snapshot"
        )

    candidates = tuple(sorted(candidates, key=lambda candidate: candidate.id))
    entities = _affected_entities(candidates)
    core_payload = {
        "source_id": source.id,
        "diff_hash": diff.diff_hash,
        "candidate_ids": [candidate.id for candidate in candidates],
        "candidate_payloads": [
            candidate.model_dump(mode="json") for candidate in candidates
        ],
        "contradiction_report_hash": (
            contradictions.report_hash if contradictions is not None else None
        ),
        "generated_at": generated_at.isoformat(),
    }
    core_hash = content_hash(core_payload)
    source_slug = source.id.split(":", 1)[1]
    review_id = f"review-request:{source_slug}-{core_hash[7:19]}"
    review_slug = review_id.split(":", 1)[1]
    timestamp = generated_at.strftime("%Y%m%d-%H%M%S")
    branch_name = f"knowledge/{source_slug}/{timestamp}-{core_hash[7:15]}"
    body = _reviewer_guide(
        source,
        diff,
        candidates,
        entities,
        contradictions,
    )
    root = f"knowledge/review-requests/{review_slug}"
    files = [
        _generated_file(
            f"{root}/source-diff.json",
            _json_text(diff.model_dump(mode="json")),
        ),
        _generated_file(
            f"{root}/affected-entities.json",
            _json_text(
                [entity.model_dump(mode="json") for entity in entities]
            ),
        ),
        _generated_file(f"{root}/reviewer-guide.md", body),
    ]
    files.extend(
        _generated_file(
            (
                f"{root}/candidates/"
                f"{candidate.id.split(':', 1)[1]}.json"
            ),
            _json_text(candidate.model_dump(mode="json")),
        )
        for candidate in candidates
    )
    if contradictions is not None:
        files.append(
            _generated_file(
                f"{root}/contradiction-report.json",
                _json_text(contradictions.model_dump(mode="json")),
            )
        )
    bundle_payload = {
        **core_payload,
        "review_id": review_id,
        "branch_name": branch_name,
        "affected_entities": [
            entity.model_dump(mode="json") for entity in entities
        ],
        "files": [
            {"path": file.path, "content_hash": file.content_hash}
            for file in files
        ],
    }
    return KnowledgePullRequestBundle(
        review_id=review_id,
        generated_at=generated_at,
        source_id=source.id,
        title=f"Knowledge update: {source.name}",
        branch_name=branch_name,
        commit_message=f"knowledge: review update for {source.id}",
        body_markdown=body,
        candidate_ids=tuple(candidate.id for candidate in candidates),
        affected_entities=entities,
        files=tuple(files),
        bundle_hash=content_hash(bundle_payload),
    )


def write_review_bundle(
    root: Path,
    bundle: KnowledgePullRequestBundle,
) -> None:
    """Write a generated bundle without replacing divergent review files."""

    for file in bundle.files:
        path = root / file.path
        path.parent.mkdir(parents=True, exist_ok=True)
        value = file.content.encode("utf-8")
        try:
            with path.open("xb") as stream:
                stream.write(value)
        except FileExistsError:
            if path.read_bytes() != value:
                raise ReviewBundleConflictError(
                    f"review file already exists with different content: {path}"
                ) from None
