"""Deterministic lexical search projection for approved knowledge."""
from __future__ import annotations

import re
from datetime import date

from pydantic import Field, field_validator, model_validator

from .models import (
    Capability,
    Claim,
    Component,
    DecisionPattern,
    EntityKind,
    FrozenModel,
    Interface,
    KnowledgeEntity,
    KnowledgeLifecycle,
    Offering,
    OutcomeObservation,
    ReviewStatus,
    StableId,
    Variant,
    content_hash,
)
from .okf import OkfCorpus


TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]+")


class SearchProjectionCompilationError(ValueError):
    pass


class SearchDocument(FrozenModel):
    id: StableId
    entity_id: StableId
    entity_kind: EntityKind
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    terms: tuple[str, ...] = Field(min_length=1)
    evidence_snapshot_ids: tuple[StableId, ...] = ()
    document_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("terms")
    @classmethod
    def terms_are_unique_and_sorted(
        cls,
        terms: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(terms) != len(set(terms)):
            raise ValueError("search document terms must be unique")
        return tuple(sorted(terms))


class SearchTermPosting(FrozenModel):
    term: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    document_ids: tuple[StableId, ...] = Field(min_length=1)

    @field_validator("document_ids")
    @classmethod
    def documents_are_unique_and_sorted(
        cls,
        document_ids: tuple[StableId, ...],
    ) -> tuple[StableId, ...]:
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("search posting document IDs must be unique")
        return tuple(sorted(document_ids))


class KnowledgeSearchProjection(FrozenModel):
    schema_version: str = "1.0"
    as_of: date
    documents: tuple[SearchDocument, ...]
    postings: tuple[SearchTermPosting, ...]
    projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def projection_hash_matches_content(self) -> "KnowledgeSearchProjection":
        payload = self.model_dump(mode="json", exclude={"projection_hash"})
        if self.projection_hash != content_hash(payload):
            raise ValueError(
                "search projection hash does not match projection content"
            )
        return self


def _entity_text(entity: KnowledgeEntity) -> tuple[str, ...]:
    values: list[str] = [entity.title, entity.summary, *entity.tags]
    if isinstance(entity, Capability):
        values.extend((entity.category, *entity.desired_outcomes))
    elif isinstance(entity, Component):
        values.extend((
            entity.plane.value,
            entity.component_kind,
            entity.responsibility,
            entity.boundary,
        ))
    elif isinstance(entity, Offering):
        values.extend((
            entity.provider,
            entity.product,
            entity.offering_type.value,
        ))
    elif isinstance(entity, Variant):
        values.extend((
            entity.provider,
            entity.product,
            entity.deployment_model,
            *entity.regions,
        ))
    elif isinstance(entity, Interface):
        values.extend((
            entity.protocol,
            entity.protocol_version or "",
            *entity.transports,
            *entity.authentication_methods,
        ))
    elif isinstance(entity, Claim):
        values.extend((entity.statement, entity.predicate))
    elif isinstance(entity, DecisionPattern):
        values.extend((
            entity.decision,
            *entity.recommended_when,
            *entity.avoid_when,
            *entity.tradeoffs,
        ))
    elif isinstance(entity, OutcomeObservation):
        values.extend((entity.metric_name, entity.unit))
    return tuple(value for value in values if value)


def compile_search_projection(
    *,
    entities: tuple[KnowledgeEntity, ...],
    as_of: date,
    okf_corpus: OkfCorpus | None = None,
) -> KnowledgeSearchProjection:
    """Compile only approved, active, current knowledge into a lexical index."""

    body_by_id = (
        {
            document.record.id: document.body
            for document in okf_corpus.documents
        }
        if okf_corpus is not None
        else {}
    )
    documents: list[SearchDocument] = []
    postings: dict[str, set[str]] = {}
    for entity in sorted(entities, key=lambda item: item.id):
        if (
            entity.lifecycle is not KnowledgeLifecycle.ACTIVE
            or entity.review.status is not ReviewStatus.APPROVED
            or as_of < entity.effective_from
            or (
                entity.effective_until is not None
                and as_of > entity.effective_until
            )
            or as_of > entity.stale_after
        ):
            continue
        text = "\n\n".join(
            (*_entity_text(entity), body_by_id.get(entity.id, ""))
        ).strip()
        terms = tuple(sorted(set(TOKEN_PATTERN.findall(text.lower()))))
        if not terms:
            raise SearchProjectionCompilationError(
                f"approved entity has no searchable terms: {entity.id}"
            )
        evidence_snapshot_ids = (
            tuple(
                sorted(
                    evidence.source_snapshot_id
                    for evidence in entity.evidence
                )
            )
            if isinstance(entity, Claim)
            else ()
        )
        document_payload = {
            "id": f"search-document:{entity.id.replace(':', '-')}",
            "entity_id": entity.id,
            "entity_kind": entity.kind,
            "title": entity.title,
            "text": text,
            "terms": list(terms),
            "evidence_snapshot_ids": list(evidence_snapshot_ids),
        }
        document = SearchDocument(
            **document_payload,
            document_hash=content_hash(document_payload),
        )
        documents.append(document)
        for term in terms:
            postings.setdefault(term, set()).add(document.id)

    posting_records = tuple(
        SearchTermPosting(
            term=term,
            document_ids=tuple(document_ids),
        )
        for term, document_ids in sorted(postings.items())
    )
    payload = {
        "schema_version": "1.0",
        "as_of": as_of.isoformat(),
        "documents": [
            document.model_dump(mode="json") for document in documents
        ],
        "postings": [
            posting.model_dump(mode="json") for posting in posting_records
        ],
    }
    return KnowledgeSearchProjection(
        **payload,
        projection_hash=content_hash(payload),
    )
