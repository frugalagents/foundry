"""Collection health assessment and alert generation."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from .models import FrozenModel, StableId, StrEnum, content_hash
from .source_registry import (
    SourceHealth,
    SourceHealthStatus,
    SourceRegistryEntry,
)
from .structural_diff import ChangeOperation, StructuralDiff


class CollectionOutcome(StrEnum):
    SUCCESS = "success"
    ACCESS_FAILURE = "access_failure"
    PARSER_FAILURE = "parser_failure"


class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


class HealthAlertType(StrEnum):
    ACCESS_FAILURE = "access_failure"
    PARSER_FAILURE = "parser_failure"
    UNEXPECTED_DELETION = "unexpected_deletion"
    OVERDUE_FRESHNESS = "overdue_freshness"


class CollectionAttempt(FrozenModel):
    attempted_at: datetime
    outcome: CollectionOutcome
    snapshot_id: StableId | None = None
    detail: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def outcome_has_required_context(self) -> "CollectionAttempt":
        if (
            self.outcome is CollectionOutcome.SUCCESS
            and self.snapshot_id is None
        ):
            raise ValueError("successful attempt requires snapshot_id")
        if (
            self.outcome is not CollectionOutcome.SUCCESS
            and self.detail is None
        ):
            raise ValueError("failed attempt requires detail")
        return self


class CollectionHealthAlert(FrozenModel):
    alert_type: HealthAlertType
    severity: AlertSeverity
    detected_at: datetime
    message: str = Field(min_length=1)


class CollectionHealthAssessment(FrozenModel):
    source_id: StableId
    assessed_at: datetime
    health: SourceHealth
    alerts: tuple[CollectionHealthAlert, ...]
    assessment_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def _latest_success(
    attempts: tuple[CollectionAttempt, ...],
) -> CollectionAttempt | None:
    return next(
        (
            attempt
            for attempt in reversed(attempts)
            if attempt.outcome is CollectionOutcome.SUCCESS
        ),
        None,
    )


def _consecutive_failures(
    attempts: tuple[CollectionAttempt, ...],
) -> int:
    count = 0
    for attempt in reversed(attempts):
        if attempt.outcome is CollectionOutcome.SUCCESS:
            break
        count += 1
    return count


def _unexpected_deletion(diff: StructuralDiff | None) -> bool:
    if diff is None or diff.prior_block_count == 0:
        return False
    removed = sum(
        1
        for change in diff.changes
        if change.operation is ChangeOperation.REMOVED
    )
    remaining_ratio = diff.current_block_count / diff.prior_block_count
    return removed >= 3 and remaining_ratio < 0.5


def assess_collection_health(
    source: SourceRegistryEntry,
    *,
    assessed_at: datetime,
    attempts: tuple[CollectionAttempt, ...] = (),
    latest_diff: StructuralDiff | None = None,
) -> CollectionHealthAssessment:
    """Derive health and actionable alerts from attempts and content changes."""

    attempts = tuple(sorted(attempts, key=lambda item: item.attempted_at))
    alerts: list[CollectionHealthAlert] = []
    if not source.enabled:
        health = SourceHealth(status=SourceHealthStatus.PAUSED)
    elif not attempts:
        health = SourceHealth(status=SourceHealthStatus.NEVER_CHECKED)
    else:
        latest = attempts[-1]
        success = _latest_success(attempts)
        failures = _consecutive_failures(attempts)
        last_failure = next(
            (
                attempt
                for attempt in reversed(attempts)
                if attempt.outcome is not CollectionOutcome.SUCCESS
            ),
            None,
        )
        if latest.outcome is CollectionOutcome.ACCESS_FAILURE:
            alerts.append(
                CollectionHealthAlert(
                    alert_type=HealthAlertType.ACCESS_FAILURE,
                    severity=(
                        AlertSeverity.CRITICAL
                        if failures >= 3
                        else AlertSeverity.WARNING
                    ),
                    detected_at=assessed_at,
                    message=latest.detail or "Source access failed.",
                )
            )
        elif latest.outcome is CollectionOutcome.PARSER_FAILURE:
            alerts.append(
                CollectionHealthAlert(
                    alert_type=HealthAlertType.PARSER_FAILURE,
                    severity=(
                        AlertSeverity.CRITICAL
                        if failures >= 3
                        else AlertSeverity.WARNING
                    ),
                    detected_at=assessed_at,
                    message=latest.detail or "Source parsing failed.",
                )
            )

        status = (
            SourceHealthStatus.FAILING
            if failures >= 3
            else SourceHealthStatus.DEGRADED
            if failures
            else SourceHealthStatus.HEALTHY
        )
        if success is not None:
            overdue_seconds = (
                assessed_at - success.attempted_at
            ).total_seconds()
            freshness_seconds = source.freshness_days * 86400
            if overdue_seconds > freshness_seconds:
                alerts.append(
                    CollectionHealthAlert(
                        alert_type=HealthAlertType.OVERDUE_FRESHNESS,
                        severity=(
                            AlertSeverity.CRITICAL
                            if overdue_seconds > freshness_seconds * 2
                            else AlertSeverity.WARNING
                        ),
                        detected_at=assessed_at,
                        message=(
                            f"Last successful snapshot is older than "
                            f"{source.freshness_days} days."
                        ),
                    )
                )
                status = (
                    SourceHealthStatus.FAILING
                    if overdue_seconds > freshness_seconds * 2
                    else SourceHealthStatus.DEGRADED
                )
        health = SourceHealth(
            status=status,
            last_checked_at=latest.attempted_at,
            last_success_at=(
                success.attempted_at if success is not None else None
            ),
            last_failure_at=(
                last_failure.attempted_at
                if last_failure is not None
                else None
            ),
            consecutive_failures=failures,
            detail=latest.detail,
        )

    if _unexpected_deletion(latest_diff):
        alerts.append(
            CollectionHealthAlert(
                alert_type=HealthAlertType.UNEXPECTED_DELETION,
                severity=AlertSeverity.CRITICAL,
                detected_at=assessed_at,
                message=(
                    "Current snapshot removed most previously observed "
                    "structural content."
                ),
            )
        )
        health = health.model_copy(
            update={"status": SourceHealthStatus.FAILING}
        )

    payload = {
        "source_id": source.id,
        "assessed_at": assessed_at.isoformat(),
        "health": health.model_dump(mode="json"),
        "alerts": [alert.model_dump(mode="json") for alert in alerts],
    }
    return CollectionHealthAssessment(
        **payload,
        assessment_hash=content_hash(payload),
    )
