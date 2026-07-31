"""GitLab/CI-linked outcome observability plan builder."""
from __future__ import annotations

from .models import (
    AssuranceCatalog,
    MeasurementHorizon,
    OutcomeEventContract,
    OutcomeMetric,
    OutcomeObservabilityPlan,
)


def build_outcome_plan(
    assurance_catalog: AssuranceCatalog,
) -> OutcomeObservabilityPlan:
    events = tuple(
        OutcomeEventContract(
            event_id=item.id,
            event_type=item.event_type,
            producer=item.producer,
            description=item.description,
            required_fields=item.required_fields,
            correlation_fields=item.correlation_fields,
        )
        for item in assurance_catalog.outcome_events
    )
    metrics = tuple(
        OutcomeMetric(
            metric_id=item.id,
            name=item.name,
            formula=item.formula,
            unit=item.unit,
            source_event_ids=item.source_event_ids,
            source_systems=item.source_systems,
            denominator=item.denominator,
        )
        for item in assurance_catalog.outcome_metrics
    )
    metric_ids = tuple(item.metric_id for item in metrics)
    return OutcomeObservabilityPlan(
        join_path=(
            "advisor decision",
            "coding-agent task",
            "model/tool/runtime spans",
            "GitLab issue and commit",
            "GitLab merge request",
            "GitLab CI pipeline",
            "review and merge",
            "deployment and production outcome",
        ),
        event_contract=events,
        metrics=metrics,
        measurement_horizons=(
            MeasurementHorizon(
                horizon="baseline",
                objective="Establish pre-platform delivery, quality, cost, and risk.",
                metric_ids=metric_ids,
                activities=(
                    "Backfill 30-90 days of GitLab issue, merge-request, and CI data.",
                    "Record current engineering effort, incidents, and platform cost.",
                    "Validate correlation-key coverage before launch.",
                ),
            ),
            MeasurementHorizon(
                horizon="day_30",
                objective="Validate instrumentation and early adoption without ranking.",
                metric_ids=metric_ids,
                activities=(
                    "Reconcile agent tasks to GitLab and CI records.",
                    "Report missing joins, policy failures, and forecast variance.",
                    "Do not treat recommendation acceptance as outcome evidence.",
                ),
            ),
            MeasurementHorizon(
                horizon="day_90",
                objective="Measure sustained delivery, quality, reliability, and cost.",
                metric_ids=metric_ids,
                activities=(
                    "Compare cohort results against the baseline.",
                    "Review failed tasks, rework, rollbacks, and control exceptions.",
                    "Adjudicate material deviations with platform and security owners.",
                ),
            ),
            MeasurementHorizon(
                horizon="day_180",
                objective="Validate durable outcomes and feed governed learning.",
                metric_ids=metric_ids,
                activities=(
                    "Compare forecast to actual cost and implementation effort.",
                    "Assess incidents per million executions and accepted-change quality.",
                    "Propose catalog changes only with architect-reviewed outcome evidence.",
                ),
            ),
        ),
        gitlab_ci_mapping={
            "project_id": "CI_PROJECT_ID or GitLab project.id",
            "issue_iid": "GitLab issue.iid",
            "commit_sha": "CI_COMMIT_SHA",
            "merge_request_iid": "CI_MERGE_REQUEST_IID or merge_request.iid",
            "pipeline_id": "CI_PIPELINE_ID",
            "pipeline_url": "CI_PIPELINE_URL",
            "job_id": "CI_JOB_ID",
            "deployment_id": "GitLab deployment.id",
            "deployment_timestamp": "CI_JOB_STARTED_AT or deployment.created_at",
        },
    )
