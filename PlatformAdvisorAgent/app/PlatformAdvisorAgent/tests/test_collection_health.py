from __future__ import annotations

from datetime import datetime, timedelta, timezone

from advisor_core.knowledge import (
    CollectionAttempt,
    ReviewMetadata,
    SourceRegistryEntry,
    SourceTerms,
    StructuralDiff,
    assess_collection_health,
)


NOW = datetime(2026, 8, 11, 18, tzinfo=timezone.utc)
HASH_A = f"sha256:{'a' * 64}"
HASH_B = f"sha256:{'b' * 64}"


def enabled_source(**overrides) -> SourceRegistryEntry:
    values = {
        "id": "source:example-docs",
        "name": "Example documentation",
        "publisher": "Example",
        "source_class": "official_product_documentation",
        "base_uri": "https://docs.example.com/product",
        "owner_id": "team:platform-advisor",
        "authority_tier": "tier_a_decision_authority",
        "cadence": "daily",
        "collector": "http",
        "parser": "html",
        "freshness_days": 2,
        "enabled": True,
        "terms": SourceTerms(
            status="approved",
            allows_automated_collection=True,
            allows_snapshot_retention=True,
            allows_derivative_claims=True,
            review=ReviewMetadata(
                status="approved",
                reviewer_ids=("person:source-reviewer",),
                reviewed_at=NOW,
            ),
        ),
    }
    values.update(overrides)
    return SourceRegistryEntry(**values)


def success(attempted_at: datetime) -> CollectionAttempt:
    return CollectionAttempt(
        attempted_at=attempted_at,
        outcome="success",
        snapshot_id="snapshot:example-docs-abc123",
    )


def failure(
    attempted_at: datetime,
    outcome: str,
) -> CollectionAttempt:
    return CollectionAttempt(
        attempted_at=attempted_at,
        outcome=outcome,
        detail=f"{outcome} while collecting source",
    )


def test_access_failure_generates_degraded_alert():
    assessment = assess_collection_health(
        enabled_source(),
        assessed_at=NOW,
        attempts=(
            success(NOW - timedelta(hours=1)),
            failure(NOW, "access_failure"),
        ),
    )

    assert assessment.health.status.value == "degraded"
    assert assessment.health.consecutive_failures == 1
    assert assessment.alerts[0].alert_type.value == "access_failure"
    assert assessment.alerts[0].severity.value == "warning"


def test_repeated_parser_failure_becomes_critical():
    assessment = assess_collection_health(
        enabled_source(),
        assessed_at=NOW,
        attempts=(
            failure(NOW - timedelta(hours=2), "parser_failure"),
            failure(NOW - timedelta(hours=1), "parser_failure"),
            failure(NOW, "parser_failure"),
        ),
    )

    assert assessment.health.status.value == "failing"
    assert assessment.alerts[0].alert_type.value == "parser_failure"
    assert assessment.alerts[0].severity.value == "critical"


def test_overdue_freshness_generates_alert():
    assessment = assess_collection_health(
        enabled_source(freshness_days=2),
        assessed_at=NOW,
        attempts=(success(NOW - timedelta(days=3)),),
    )

    assert assessment.health.status.value == "degraded"
    assert assessment.alerts[0].alert_type.value == "overdue_freshness"


def test_unexpected_deletion_is_critical():
    diff = StructuralDiff(
        source_id="source:example-docs",
        prior_snapshot_id="snapshot:example-prior",
        current_snapshot_id="snapshot:example-current",
        prior_content_hash=HASH_A,
        current_content_hash=HASH_B,
        prior_block_count=10,
        current_block_count=2,
        ignored_noise_blocks=0,
        changes=tuple(
            {
                "operation": "removed",
                "block_type": "paragraph",
                "before": f"Removed block {index}",
                "significance": "informational",
                "reason": "descriptive content changed",
            }
            for index in range(8)
        ),
        diff_hash=HASH_A,
    )
    assessment = assess_collection_health(
        enabled_source(),
        assessed_at=NOW,
        attempts=(success(NOW),),
        latest_diff=diff,
    )

    assert assessment.health.status.value == "failing"
    assert assessment.alerts[0].alert_type.value == "unexpected_deletion"
    assert assessment.alerts[0].severity.value == "critical"


def test_disabled_source_is_paused_without_alerts():
    assessment = assess_collection_health(
        enabled_source(enabled=False),
        assessed_at=NOW,
    )

    assert assessment.health.status.value == "paused"
    assert assessment.alerts == ()
