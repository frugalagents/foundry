from __future__ import annotations

import json
from typing import Any, Mapping

_LIST_FIELDS = {
    "assumptions",
    "facts",
    "open_questions",
    "decisions",
    "risks",
    "implementation_plan",
}

_REASONING_DRIVER_FIELDS = (
    "facts",
    "assumptions",
    "operating_model",
    "open_questions",
    "decisions",
    "risks",
)

_REASONING_DERIVED_FIELDS = (
    "recommendation",
    "open_questions",
    "decisions",
    "risks",
    "implementation_plan",
    "blueprint_markdown",
    "advisory_case",
)

_HEAVY_ARTIFACT_DRIVER_FIELDS = (
    "recommendation",
    "implementation_plan",
)

_HEAVY_ARTIFACT_FIELDS = (
    "blueprint_markdown",
    "advisory_case",
)

_STAGES = {"discovery", "solutioning", "blueprint"}


def _canonicalize(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _value_changed(existing_value: Any, next_value: Any) -> bool:
    return _canonicalize(existing_value) != _canonicalize(next_value)


def _empty_value_for(field: str) -> Any:
    if field in _LIST_FIELDS:
        return []
    if field == "advisory_case":
        return None
    return ""


def _default_value(existing: Mapping[str, Any], field: str) -> Any:
    if field in _LIST_FIELDS:
        return existing.get(field, []) or []
    if field == "advisory_case":
        return existing.get(field) or None
    return existing.get(field, "") or ""


def _has_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(_has_content(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_content(item) for item in value)
    return bool(value)


def _resolve_stage(
    requested_stage: str,
    existing_stage: str,
    workspace: Mapping[str, Any],
) -> str:
    stage = requested_stage if requested_stage in _STAGES else existing_stage if existing_stage in _STAGES else ""
    if not stage:
        if workspace.get("recommendation") or workspace.get("decisions") or workspace.get("risks"):
            stage = "solutioning"
        else:
            stage = "discovery"

    if stage == "blueprint":
        if (
            workspace.get("open_questions")
            or not _has_content(workspace.get("recommendation"))
            or not _has_content(workspace.get("implementation_plan"))
            or not _has_content(workspace.get("blueprint_markdown"))
            or not _has_content(workspace.get("advisory_case"))
        ):
            return "solutioning" if (
                workspace.get("facts")
                or workspace.get("assumptions")
                or workspace.get("recommendation")
                or workspace.get("decisions")
                or workspace.get("risks")
            ) else "discovery"

    if stage == "solutioning":
        if not (
            workspace.get("facts")
            or workspace.get("assumptions")
            or workspace.get("recommendation")
            or workspace.get("decisions")
            or workspace.get("risks")
        ):
            return "discovery"

    return stage


def build_workspace_state(
    existing: Mapping[str, Any] | None,
    *,
    recommendation: str | None = None,
    blueprint_markdown: str | None = None,
    assumptions: list[dict] | None = None,
    facts: list[str] | None = None,
    operating_model: str | None = None,
    open_questions: list[str] | None = None,
    decisions: list[str] | None = None,
    risks: list[str] | None = None,
    implementation_plan: list[str] | None = None,
    advisory_case: dict | None = None,
    stage: str = "",
) -> tuple[dict[str, Any], list[str], list[str]]:
    current = dict(existing or {})
    explicit_updates: dict[str, Any] = {}
    if recommendation is not None:
        explicit_updates["recommendation"] = recommendation
    if blueprint_markdown is not None:
        explicit_updates["blueprint_markdown"] = blueprint_markdown
    if assumptions is not None:
        explicit_updates["assumptions"] = assumptions
    if facts is not None:
        explicit_updates["facts"] = facts
    if operating_model is not None:
        explicit_updates["operating_model"] = operating_model
    if open_questions is not None:
        explicit_updates["open_questions"] = open_questions
    if decisions is not None:
        explicit_updates["decisions"] = decisions
    if risks is not None:
        explicit_updates["risks"] = risks
    if implementation_plan is not None:
        explicit_updates["implementation_plan"] = implementation_plan
    if advisory_case is not None:
        explicit_updates["advisory_case"] = advisory_case

    reasoning_changes = [
        field
        for field in _REASONING_DRIVER_FIELDS
        if field in explicit_updates and _value_changed(_default_value(current, field), explicit_updates[field])
    ]
    heavy_artifact_driver_changes = [
        field
        for field in _HEAVY_ARTIFACT_DRIVER_FIELDS
        if field in explicit_updates and _value_changed(_default_value(current, field), explicit_updates[field])
    ]
    stage_changed = bool(stage) and stage != _default_value(current, "stage")

    invalidated_fields: list[str] = []
    if reasoning_changes:
        for field in _REASONING_DERIVED_FIELDS:
            if field in explicit_updates:
                continue
            explicit_updates[field] = _empty_value_for(field)
            invalidated_fields.append(field)
    elif heavy_artifact_driver_changes or (stage_changed and stage in {"discovery", "solutioning"}):
        for field in _HEAVY_ARTIFACT_FIELDS:
            if field in explicit_updates:
                continue
            explicit_updates[field] = _empty_value_for(field)
            invalidated_fields.append(field)

    workspace = {
        "recommendation": _default_value(current, "recommendation") if "recommendation" not in explicit_updates else explicit_updates["recommendation"],
        "blueprint_markdown": _default_value(current, "blueprint_markdown") if "blueprint_markdown" not in explicit_updates else explicit_updates["blueprint_markdown"],
        "assumptions": _default_value(current, "assumptions") if "assumptions" not in explicit_updates else explicit_updates["assumptions"],
        "facts": _default_value(current, "facts") if "facts" not in explicit_updates else explicit_updates["facts"],
        "operating_model": _default_value(current, "operating_model") if "operating_model" not in explicit_updates else explicit_updates["operating_model"],
        "open_questions": _default_value(current, "open_questions") if "open_questions" not in explicit_updates else explicit_updates["open_questions"],
        "decisions": _default_value(current, "decisions") if "decisions" not in explicit_updates else explicit_updates["decisions"],
        "risks": _default_value(current, "risks") if "risks" not in explicit_updates else explicit_updates["risks"],
        "implementation_plan": _default_value(current, "implementation_plan") if "implementation_plan" not in explicit_updates else explicit_updates["implementation_plan"],
        "advisory_case": _default_value(current, "advisory_case") if "advisory_case" not in explicit_updates else explicit_updates["advisory_case"],
    }
    workspace["stage"] = _resolve_stage(stage, _default_value(current, "stage"), workspace)
    return workspace, invalidated_fields, reasoning_changes
