"""Transparent token and platform economics builder."""
from __future__ import annotations

from datetime import date

from ..models import WorkspaceRevision
from .models import (
    AssuranceCatalog,
    EconomicAssumption,
    EconomicsPlan,
    EconomicsTotals,
    NumericRange,
    SelectedBundleContext,
    UnitCostInput,
)


def _rounded(low: float, high: float) -> NumericRange:
    return NumericRange(low=round(low, 6), high=round(high, 6))


def build_economics_plan(
    revision: WorkspaceRevision,
    assurance_catalog: AssuranceCatalog,
    *,
    selected_bundle: SelectedBundleContext | None,
    as_of: date,
) -> EconomicsPlan:
    requirement_values = {
        item.requirement_id: item.value for item in revision.requirements
    }
    assumptions: list[EconomicAssumption] = [
        EconomicAssumption(
            assumption_id=item.id,
            name=item.name,
            unit=item.unit,
            value_range=item.value_range,
            rationale=item.rationale,
            source="catalog_default",
        )
        for item in assurance_catalog.economic_assumptions
    ]
    developer_count = requirement_values.get("requirement:developer-count")
    if isinstance(developer_count, int) and not isinstance(developer_count, bool):
        assumptions.append(
            EconomicAssumption(
                assumption_id="economic-assumption:developer-count",
                name="Developer population",
                unit="developers",
                value_range=NumericRange(
                    low=float(developer_count),
                    high=float(developer_count),
                ),
                rationale="Confirmed or assumed workspace scale requirement.",
                source="workspace_requirement",
            )
        )

    assumptions_by_id = {item.assumption_id: item for item in assumptions}
    overrides = {
        item.cost_id: item
        for item in (selected_bundle.unit_cost_overrides if selected_bundle else ())
    }
    unit_costs: list[UnitCostInput] = []
    for definition in assurance_catalog.unit_costs:
        override = overrides.get(definition.id)
        if override is None:
            unit_costs.append(
                UnitCostInput(
                    cost_id=definition.id,
                    name=definition.name,
                    unit=definition.unit,
                    value_range=definition.value_range,
                    effective_on=definition.effective_on,
                    status=definition.status,
                    source=definition.source,
                )
            )
        else:
            if override.effective_on > as_of:
                raise ValueError(
                    f"unit-cost override {override.cost_id} is not yet effective"
                )
            unit_costs.append(
                UnitCostInput(
                    cost_id=definition.id,
                    name=definition.name,
                    unit=definition.unit,
                    value_range=override.value_range,
                    effective_on=override.effective_on,
                    status=(
                        "evidence_backed"
                        if override.evidence_status == "approved"
                        else "unverified_override"
                    ),
                    source=override.source,
                )
            )
    costs = {item.cost_id: item.value_range for item in unit_costs}

    def assumption(identifier: str) -> NumericRange:
        return assumptions_by_id[identifier].value_range

    turns = assumption("economic-assumption:turns-per-task")
    input_tokens = assumption("economic-assumption:input-tokens-per-turn")
    output_tokens = assumption("economic-assumption:output-tokens-per-turn")
    cache_ratio = assumption("economic-assumption:cache-hit-ratio")
    retries = assumption("economic-assumption:retry-rate")
    runtime_hours = assumption("economic-assumption:runtime-hours-per-task")
    storage = assumption("economic-assumption:storage-gb-month-per-task")
    network = assumption("economic-assumption:network-gb-per-task")
    telemetry = assumption("economic-assumption:telemetry-gb-per-task")
    success_rate = assumption("economic-assumption:successful-task-rate")
    accepted_rate = assumption("economic-assumption:accepted-pr-per-success")
    tasks_per_developer = assumption(
        "economic-assumption:tasks-per-developer-month"
    )
    developers = assumptions_by_id.get("economic-assumption:developer-count")
    developer_range = (
        developers.value_range
        if developers is not None
        else NumericRange(low=100, high=1000)
    )

    input_cost = costs["unit-cost:model-input-million-tokens"]
    cached_cost = costs["unit-cost:model-cached-input-million-tokens"]
    output_cost = costs["unit-cost:model-output-million-tokens"]
    model_low = turns.low * (
        input_tokens.low
        * (
            (1 - cache_ratio.high) * input_cost.low
            + cache_ratio.high * cached_cost.low
        )
        + output_tokens.low * output_cost.low
    ) / 1_000_000
    model_high = turns.high * (
        input_tokens.high
        * (
            (1 - cache_ratio.low) * input_cost.high
            + cache_ratio.low * cached_cost.high
        )
        + output_tokens.high * output_cost.high
    ) / 1_000_000
    platform_low = (
        runtime_hours.low * costs["unit-cost:runtime-hour"].low
        + storage.low * costs["unit-cost:storage-gb-month"].low
        + network.low * costs["unit-cost:network-gb"].low
        + telemetry.low * costs["unit-cost:observability-gb"].low
        + costs["unit-cost:control-overhead-task"].low
    )
    platform_high = (
        runtime_hours.high * costs["unit-cost:runtime-hour"].high
        + storage.high * costs["unit-cost:storage-gb-month"].high
        + network.high * costs["unit-cost:network-gb"].high
        + telemetry.high * costs["unit-cost:observability-gb"].high
        + costs["unit-cost:control-overhead-task"].high
    )
    requested_low = (model_low + platform_low) * (1 + retries.low)
    requested_high = (model_high + platform_high) * (1 + retries.high)
    successful = _rounded(
        requested_low / success_rate.high,
        requested_high / success_rate.low,
    )
    accepted = _rounded(
        requested_low / (success_rate.high * accepted_rate.high),
        requested_high / (success_rate.low * accepted_rate.low),
    )
    monthly_tasks = NumericRange(
        low=developer_range.low * tasks_per_developer.low,
        high=developer_range.high * tasks_per_developer.high,
    )
    monthly = _rounded(
        requested_low * monthly_tasks.low,
        requested_high * monthly_tasks.high,
    )

    return EconomicsPlan(
        assumptions=tuple(
            sorted(assumptions, key=lambda item: item.assumption_id)
        ),
        unit_costs=tuple(sorted(unit_costs, key=lambda item: item.cost_id)),
        formulas={
            "model_cost_per_task": (
                "turns * ((input_tokens * blended_cached_input_rate) + "
                "(output_tokens * output_rate)) / 1,000,000"
            ),
            "cost_per_requested_task": (
                "(model + runtime + storage + network + observability + "
                "control_overhead) * (1 + retry_rate)"
            ),
            "cost_per_successful_task": (
                "cost_per_requested_task / successful_task_rate"
            ),
            "cost_per_accepted_pull_request": (
                "cost_per_requested_task / "
                "(successful_task_rate * accepted_pr_per_success)"
            ),
            "monthly_platform_cost": (
                "developer_count * tasks_per_developer_month * "
                "cost_per_requested_task"
            ),
        },
        totals=EconomicsTotals(
            cost_per_requested_task=_rounded(requested_low, requested_high),
            cost_per_successful_task=successful,
            cost_per_accepted_pull_request=accepted,
            monthly_platform_cost=monthly,
            monthly_cost_per_developer=_rounded(
                requested_low * tasks_per_developer.low,
                requested_high * tasks_per_developer.high,
            ),
        ),
        sensitivity_drivers=(
            "model routing and input/output token rates",
            "turns and context tokens per task",
            "cache hit ratio",
            "retry and task success rates",
            "accepted pull-request rate",
            "runtime duration and concurrency",
        ),
        pricing_warning=(
            "Placeholder ranges are planning inputs, not provider quotes. "
            "Replace them with approved, dated evidence before a decision is ready."
        ),
    )
