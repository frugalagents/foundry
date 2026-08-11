"""Source registration contracts for controlled knowledge collection."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import AnyHttpUrl, Field, field_validator, model_validator

from .models import (
    FrozenModel,
    ReviewMetadata,
    ReviewStatus,
    SourceAuthorityTier,
    StableId,
    StrEnum,
)


class CollectionCadence(StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_RELEASE = "on_release"
    MANUAL = "manual"


class CollectorType(StrEnum):
    HTTP = "http"
    RSS = "rss"
    API = "api"
    GITHUB_RELEASES = "github_releases"
    GITHUB_REPOSITORY = "github_repository"
    MANUAL_UPLOAD = "manual_upload"


class ParserType(StrEnum):
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"
    RSS = "rss"
    PDF = "pdf"
    TEXT = "text"


class TermsStatus(StrEnum):
    APPROVED = "approved"
    REVIEW_REQUIRED = "review_required"
    PROHIBITED = "prohibited"


class SourceHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    PAUSED = "paused"
    NEVER_CHECKED = "never_checked"


class SourceTerms(FrozenModel):
    status: TermsStatus
    allows_automated_collection: bool
    allows_snapshot_retention: bool
    allows_derivative_claims: bool
    terms_uri: AnyHttpUrl | None = None
    review: ReviewMetadata

    @model_validator(mode="after")
    def approved_terms_have_approved_review(self) -> "SourceTerms":
        if (
            self.status is TermsStatus.APPROVED
            and self.review.status is not ReviewStatus.APPROVED
        ):
            raise ValueError("approved source terms require approved review")
        return self


class SourceHealth(FrozenModel):
    status: SourceHealthStatus = SourceHealthStatus.NEVER_CHECKED
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = Field(default=0, ge=0)
    detail: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def health_state_is_consistent(self) -> "SourceHealth":
        if self.status is SourceHealthStatus.HEALTHY:
            if self.last_success_at is None or self.consecutive_failures:
                raise ValueError(
                    "healthy source requires last_success_at and zero failures"
                )
        if (
            self.status is SourceHealthStatus.NEVER_CHECKED
            and self.last_checked_at is not None
        ):
            raise ValueError("never_checked source cannot have last_checked_at")
        return self


class SourceRegistryEntry(FrozenModel):
    id: StableId
    name: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    source_class: str = Field(min_length=1)
    base_uri: str = Field(
        min_length=1,
        pattern=r"^(?:https?://|repo:|s3://).+",
    )
    owner_id: StableId
    authority_tier: SourceAuthorityTier
    cadence: CollectionCadence
    collector: CollectorType
    parser: ParserType
    freshness_days: int = Field(ge=1, le=365)
    enabled: bool = False
    terms: SourceTerms
    health: SourceHealth = Field(default_factory=SourceHealth)
    tags: tuple[str, ...] = ()

    @field_validator("tags")
    @classmethod
    def unique_sorted_tags(cls, tags: tuple[str, ...]) -> tuple[str, ...]:
        if len(tags) != len(set(tags)):
            raise ValueError("source tags must be unique")
        return tuple(sorted(tags))

    @model_validator(mode="after")
    def enabled_collection_is_permitted(self) -> "SourceRegistryEntry":
        if not self.enabled:
            return self
        if self.terms.status is not TermsStatus.APPROVED:
            raise ValueError("enabled source requires approved terms")
        if not self.terms.allows_derivative_claims:
            raise ValueError(
                "enabled source must permit derivative claim authoring"
            )
        if self.collector is not CollectorType.MANUAL_UPLOAD:
            if not self.terms.allows_automated_collection:
                raise ValueError(
                    "automated collector requires collection permission"
                )
            if not self.terms.allows_snapshot_retention:
                raise ValueError(
                    "automated collector requires snapshot retention permission"
                )
        if (
            self.cadence is CollectionCadence.MANUAL
            and self.collector is not CollectorType.MANUAL_UPLOAD
        ):
            raise ValueError(
                "manual cadence requires the manual_upload collector"
            )
        return self


class SourceRegistry(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    sources: tuple[SourceRegistryEntry, ...] = Field(min_length=1)

    @field_validator("sources")
    @classmethod
    def unique_sources(
        cls,
        sources: tuple[SourceRegistryEntry, ...],
    ) -> tuple[SourceRegistryEntry, ...]:
        identifiers = [source.id for source in sources]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("source registry IDs must be unique")
        uris = [str(source.base_uri) for source in sources]
        if len(uris) != len(set(uris)):
            raise ValueError("source registry base URIs must be unique")
        return tuple(sorted(sources, key=lambda source: source.id))


def load_source_registry(path: Path) -> SourceRegistry:
    """Load and validate an authored YAML source registry."""

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("source registry document must be an object")
    return SourceRegistry.model_validate(document)
