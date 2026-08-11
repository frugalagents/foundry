from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from advisor_core.knowledge import (
    ReviewMetadata,
    SourceHealth,
    SourceRegistry,
    SourceRegistryEntry,
    SourceTerms,
)


REVIEWED_AT = datetime(2026, 8, 11, 12, tzinfo=timezone.utc)


def approved_terms(**overrides) -> SourceTerms:
    values = {
        "status": "approved",
        "allows_automated_collection": True,
        "allows_snapshot_retention": True,
        "allows_derivative_claims": True,
        "terms_uri": "https://example.com/terms",
        "review": ReviewMetadata(
            status="approved",
            reviewer_ids=("person:source-governance-reviewer",),
            reviewed_at=REVIEWED_AT,
        ),
    }
    values.update(overrides)
    return SourceTerms(**values)


def source_entry(**overrides) -> SourceRegistryEntry:
    values = {
        "id": "source:example-product-docs",
        "name": "Example product documentation",
        "publisher": "Example Provider",
        "source_class": "official_product_documentation",
        "base_uri": "https://docs.example.com/product",
        "owner_id": "team:platform-advisor",
        "authority_tier": "tier_a_decision_authority",
        "cadence": "weekly",
        "collector": "http",
        "parser": "html",
        "freshness_days": 14,
        "enabled": True,
        "terms": approved_terms(),
        "tags": ("product", "runtime"),
    }
    values.update(overrides)
    return SourceRegistryEntry(**values)


def test_enabled_source_records_governance_and_collection_contract():
    source = source_entry()

    assert source.enabled is True
    assert source.authority_tier.value == "tier_a_decision_authority"
    assert source.tags == ("product", "runtime")
    assert source.health.status.value == "never_checked"


def test_enabled_source_fails_closed_without_approved_terms():
    terms = approved_terms(
        status="review_required",
        review=ReviewMetadata(status="in_review"),
    )

    with pytest.raises(
        ValidationError,
        match="enabled source requires approved terms",
    ):
        source_entry(terms=terms)


def test_automated_collection_requires_snapshot_retention_permission():
    with pytest.raises(
        ValidationError,
        match="requires snapshot retention permission",
    ):
        source_entry(
            terms=approved_terms(allows_snapshot_retention=False),
        )


def test_manual_cadence_requires_manual_collector():
    with pytest.raises(
        ValidationError,
        match="manual cadence requires the manual_upload collector",
    ):
        source_entry(cadence="manual", collector="http")


def test_healthy_source_requires_success_and_zero_failures():
    with pytest.raises(
        ValidationError,
        match="healthy source requires last_success_at and zero failures",
    ):
        SourceHealth(
            status="healthy",
            last_checked_at=REVIEWED_AT,
            consecutive_failures=1,
        )


def test_registry_rejects_duplicate_source_identifiers():
    source = source_entry(enabled=False)

    with pytest.raises(
        ValidationError,
        match="source registry IDs must be unique",
    ):
        SourceRegistry(sources=(source, source))


def test_registry_loader_rejects_non_object_document(tmp_path: Path):
    path = tmp_path / "sources.yaml"
    path.write_text("- not-an-object\n", encoding="utf-8")

    from advisor_core.knowledge import load_source_registry

    with pytest.raises(
        ValueError,
        match="source registry document must be an object",
    ):
        load_source_registry(path)
