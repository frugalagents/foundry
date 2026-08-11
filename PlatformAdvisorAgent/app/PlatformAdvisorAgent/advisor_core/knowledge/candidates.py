"""Untrusted extraction candidates that require review before publication."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .models import (
    ClaimClass,
    ClaimScope,
    EntityKind,
    FrozenModel,
    JsonScalar,
    RelationshipCardinality,
    RelationshipType,
    StableId,
    StrEnum,
)


class ExtractionWarning(StrEnum):
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_SUBJECT = "ambiguous_subject"
    AMBIGUOUS_OBJECT = "ambiguous_object"
    SCOPE_INCOMPLETE = "scope_incomplete"
    SOURCE_CONTEXT_TRUNCATED = "source_context_truncated"
    POSSIBLE_CONTRADICTION = "possible_contradiction"


class SourceLocator(FrozenModel):
    source_snapshot_id: StableId
    source_uri: str = Field(min_length=1)
    source_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exact_text: str = Field(min_length=1)
    section_path: tuple[str, ...] = ()
    character_start: int | None = Field(default=None, ge=0)
    character_end: int | None = Field(default=None, ge=1)
    page_number: int | None = Field(default=None, ge=1)
    json_pointer: str | None = Field(default=None, pattern=r"^/")

    @model_validator(mode="after")
    def locator_is_coherent(self) -> "SourceLocator":
        if (self.character_start is None) != (self.character_end is None):
            raise ValueError(
                "character_start and character_end must be provided together"
            )
        if (
            self.character_start is not None
            and self.character_end is not None
            and self.character_end <= self.character_start
        ):
            raise ValueError("character_end must be greater than character_start")
        if not (
            self.section_path
            or self.character_start is not None
            or self.page_number is not None
            or self.json_pointer is not None
        ):
            raise ValueError("source locator requires a structural position")
        return self


class ProposedRelationship(FrozenModel):
    relationship_type: RelationshipType
    target_id: StableId
    target_kind: EntityKind
    cardinality: RelationshipCardinality
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)


class ExtractorMetadata(FrozenModel):
    extractor_id: StableId
    extractor_version: str = Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z.-]+)?$"
    )
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)


class ClaimCandidate(FrozenModel):
    id: StableId
    generated_at: datetime
    extractor: ExtractorMetadata
    locator: SourceLocator
    extracted_text: str = Field(min_length=1)
    normalized_statement: str = Field(min_length=1)
    subject_id: StableId
    subject_kind: EntityKind
    predicate: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    object_id: StableId | None = None
    object_value: JsonScalar | None = None
    proposed_scope: ClaimScope
    claim_class: ClaimClass
    confidence: float = Field(ge=0, le=1)
    warnings: tuple[ExtractionWarning, ...] = ()
    proposed_relationships: tuple[ProposedRelationship, ...] = ()

    @field_validator("warnings")
    @classmethod
    def unique_sorted_warnings(
        cls,
        warnings: tuple[ExtractionWarning, ...],
    ) -> tuple[ExtractionWarning, ...]:
        if len(warnings) != len(set(warnings)):
            raise ValueError("extraction warnings must be unique")
        return tuple(sorted(warnings, key=lambda warning: warning.value))

    @field_validator("proposed_relationships")
    @classmethod
    def unique_sorted_relationships(
        cls,
        relationships: tuple[ProposedRelationship, ...],
    ) -> tuple[ProposedRelationship, ...]:
        identities = [
            (relationship.relationship_type, relationship.target_id)
            for relationship in relationships
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("proposed relationships must be unique")
        return tuple(
            sorted(
                relationships,
                key=lambda relationship: (
                    relationship.relationship_type.value,
                    relationship.target_id,
                ),
            )
        )

    @model_validator(mode="after")
    def candidate_preserves_extraction_uncertainty(self) -> "ClaimCandidate":
        if self.extracted_text != self.locator.exact_text:
            raise ValueError(
                "extracted_text must exactly match locator exact_text"
            )
        if (self.object_id is None) == (self.object_value is None):
            raise ValueError(
                "candidate requires exactly one of object_id or object_value"
            )
        if (
            self.confidence < 0.7
            and ExtractionWarning.LOW_CONFIDENCE not in self.warnings
        ):
            raise ValueError(
                "confidence below 0.7 requires low_confidence warning"
            )
        return self
