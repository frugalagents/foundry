from __future__ import annotations

import json
import re
from typing import Any, Mapping

_LIST_FIELDS = {
    "assumptions",
    "facts",
    "open_questions",
    "decisions",
    "risks",
    "implementation_plan",
    "question_state",
}

_MAPPING_FIELDS = {
    "recommendation_state",
    "artifact_status",
}

_REASONING_DRIVER_FIELDS = (
    "facts",
    "assumptions",
    "operating_model",
    "question_state",
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
_CONFIRMED_FACT_SOURCES = {"customer", "customer_confirmed", "explicit_constraint", "operating_model"}


def _canonicalize(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _value_changed(existing_value: Any, next_value: Any) -> bool:
    return _canonicalize(existing_value) != _canonicalize(next_value)


def _empty_value_for(field: str) -> Any:
    if field in _LIST_FIELDS:
        return []
    if field in _MAPPING_FIELDS:
        return {}
    if field == "advisory_case":
        return None
    return ""


def _default_value(existing: Mapping[str, Any], field: str) -> Any:
    if field in _LIST_FIELDS:
        return existing.get(field, []) or []
    if field in _MAPPING_FIELDS:
        return existing.get(field) or {}
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


def _normalize_text_list(value: Any) -> list[str]:
    items = value if isinstance(value, list) else []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip() if item is not None else ""
        if not text:
            continue
        key = re.sub(r"\s+", " ", text).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(re.sub(r"\s+", " ", text).strip())
    return normalized


def _slugify_question_id(text: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = slug[:64] if slug else f"question-{index + 1}"
    return slug or f"question-{index + 1}"


def _normalize_operating_model(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    if not normalized or normalized == "undecided":
        return "undecided"
    if normalized in {"single_standard", "one_standard", "single_tool_standard"}:
        return "single_standard"
    if normalized in {
        "multi_harness_governed",
        "multi_harness_portfolio",
        "governed_multi_harness",
        "governed_multi_harness_portfolio",
        "approved_portfolio",
    }:
        return "multi_harness_governed"
    if normalized in {
        "default_plus_exceptions",
        "default_with_exceptions",
        "default_harness_with_exceptions",
        "one_default_with_exceptions",
        "formal_exception_paths",
    }:
        return "default_plus_exceptions"
    return normalized


def _normalize_question_state(
    question_state: Any,
    open_questions: Any,
    existing: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    existing_items = existing.get("question_state") if isinstance(existing, Mapping) else []
    if not isinstance(existing_items, list):
        existing_items = []

    normalized_existing: list[dict[str, Any]] = []
    for index, item in enumerate(existing_items):
        if not isinstance(item, Mapping):
            continue
        text = re.sub(r"\s+", " ", str(item.get("text") or item.get("question") or "").strip())
        if not text:
            continue
        status = str(item.get("status") or "open").strip().lower()
        if status not in {"open", "answered", "deferred", "invalidated"}:
            status = "open"
        answer = re.sub(r"\s+", " ", str(item.get("answer") or "").strip())
        if answer and status == "open":
            status = "answered"
        normalized_existing.append(
            {
                "id": str(item.get("id") or _slugify_question_id(text, index)),
                "text": text,
                "why_it_matters": re.sub(r"\s+", " ", str(item.get("why_it_matters") or "").strip()),
                "blocking": bool(item.get("blocking", True)),
                "decision_domain": str(item.get("decision_domain") or "").strip(),
                "status": status,
                "answer": answer,
                "source": str(item.get("source") or "engine").strip() or "engine",
            }
        )

    existing_by_id = {item["id"]: item for item in normalized_existing}
    existing_by_text = {item["text"].lower(): item for item in normalized_existing}

    raw_items: list[Any] | None = None
    if isinstance(question_state, list) and question_state:
        raw_items = question_state
    elif open_questions is not None:
        raw_items = [{"text": text} for text in _normalize_text_list(open_questions)]
    elif isinstance(question_state, list):
        raw_items = question_state
    elif normalized_existing:
        return normalized_existing
    else:
        return []

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()

    for index, item in enumerate(raw_items):
        if isinstance(item, Mapping):
            text = re.sub(r"\s+", " ", str(item.get("text") or item.get("question") or "").strip())
            if not text:
                continue
            match = existing_by_id.get(str(item.get("id") or "")) or existing_by_text.get(text.lower())
            status = str(item.get("status") or (match or {}).get("status") or "open").strip().lower()
            if status not in {"open", "answered", "deferred", "invalidated"}:
                status = "open"
            answer = re.sub(r"\s+", " ", str(item.get("answer") or (match or {}).get("answer") or "").strip())
            if answer and status == "open":
                status = "answered"
            normalized_item = {
                "id": str(item.get("id") or (match or {}).get("id") or _slugify_question_id(text, index)),
                "text": text,
                "why_it_matters": re.sub(r"\s+", " ", str(item.get("why_it_matters") or (match or {}).get("why_it_matters") or "").strip()),
                "blocking": bool(item.get("blocking", (match or {}).get("blocking", True))),
                "decision_domain": str(item.get("decision_domain") or (match or {}).get("decision_domain") or "").strip(),
                "status": status,
                "answer": answer,
                "source": str(item.get("source") or (match or {}).get("source") or "engine").strip() or "engine",
            }
        else:
            text = re.sub(r"\s+", " ", str(item or "").strip())
            if not text:
                continue
            match = existing_by_text.get(text.lower())
            normalized_item = {
                "id": (match or {}).get("id") or _slugify_question_id(text, index),
                "text": text,
                "why_it_matters": (match or {}).get("why_it_matters", ""),
                "blocking": bool((match or {}).get("blocking", True)),
                "decision_domain": (match or {}).get("decision_domain", ""),
                "status": "open",
                "answer": "",
                "source": (match or {}).get("source", "engine"),
            }

        if normalized_item["id"] in seen_ids or normalized_item["text"].lower() in seen_texts:
            continue
        seen_ids.add(normalized_item["id"])
        seen_texts.add(normalized_item["text"].lower())
        normalized.append(normalized_item)

    for item in normalized_existing:
        if item["id"] in seen_ids:
            continue
        if item["status"] in {"answered", "deferred"} or item.get("answer"):
            normalized.append(item)
            seen_ids.add(item["id"])
            continue
        normalized.append({**item, "status": "invalidated"})
        seen_ids.add(item["id"])

    return normalized


def _derive_open_questions(question_state: list[dict[str, Any]], fallback: Any) -> list[str]:
    open_items = [item["text"] for item in question_state if item.get("status") == "open"]
    return open_items if open_items or fallback is not None else _normalize_text_list(fallback)


def _confirmed_structured_facts(workspace: Mapping[str, Any]) -> list[dict[str, Any]]:
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    structured = (
        traversal_state.get("customer_confirmed_facts")
        if isinstance(traversal_state.get("customer_confirmed_facts"), list)
        else traversal_state.get("structured_facts")
        if isinstance(traversal_state.get("structured_facts"), list)
        else []
    )
    confirmed: list[dict[str, Any]] = []
    for item in structured:
        if not isinstance(item, Mapping):
            continue
        source = str(item.get("source") or "").strip().lower()
        if source and source not in _CONFIRMED_FACT_SOURCES:
            continue
        confirmed.append(dict(item))
    return confirmed


def _facts_from_confirmed_structured_facts(workspace: Mapping[str, Any]) -> list[str]:
    facts: list[str] = []
    seen: set[str] = set()
    for item in _confirmed_structured_facts(workspace):
        text = re.sub(r"\s+", " ", str(item.get("fact_text") or "").strip())
        if not text:
            key = str(item.get("key") or "").strip()
            value = item.get("value")
            if key and value not in (None, "", []):
                rendered = ", ".join(str(entry) for entry in value) if isinstance(value, list) else str(value)
                text = f"{key}: {rendered}".strip()
        if not text:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        facts.append(text)
    return facts


def _normalize_advisory_recommendation(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    confidence = str(raw.get("confidence") or "").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = ""
    return {
        "summary": str(raw.get("summary") or "").strip(),
        "why_this": str(raw.get("why_this") or "").strip(),
        "why_not": str(raw.get("why_not") or "").strip(),
        "confidence": confidence,
        "confidence_reason": str(raw.get("confidence_reason") or "").strip(),
        "change_triggers": _normalize_text_list(raw.get("change_triggers")),
    }


def _normalize_alternative(value: Any) -> dict[str, Any] | None:
    raw = value if isinstance(value, Mapping) else None
    if raw is None:
        return None
    title = str(raw.get("title") or "").strip()
    identifier = str(raw.get("id") or "").strip() or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not title:
        return None
    position = str(raw.get("position") or "").strip().lower()
    if position not in {"recommended", "viable", "deferred"}:
        position = ""
    return {
        "id": identifier or "option",
        "title": title,
        "position": position,
        "summary": str(raw.get("summary") or "").strip(),
        "benefits": _normalize_text_list(raw.get("benefits")),
        "risks": _normalize_text_list(raw.get("risks")),
        "operational_burden": str(raw.get("operational_burden") or "").strip(),
        "governance_implications": str(raw.get("governance_implications") or "").strip(),
        "best_fit_conditions": _normalize_text_list(raw.get("best_fit_conditions")),
    }


def _normalize_advisory_case(value: Any, workspace: Mapping[str, Any]) -> dict[str, Any] | None:
    raw = value if isinstance(value, Mapping) else {}
    recommendation = _normalize_advisory_recommendation(raw.get("recommendation"))
    recommendation_state = workspace.get("recommendation_state") if isinstance(workspace.get("recommendation_state"), Mapping) else {}
    if not recommendation["summary"]:
        recommendation["summary"] = str(workspace.get("recommendation") or recommendation_state.get("primary_recommendation") or "").strip()

    alternatives = []
    if isinstance(raw.get("alternatives"), list):
        alternatives = [item for item in (_normalize_alternative(value) for value in raw.get("alternatives")) if item]
    if not alternatives:
        candidate_options = recommendation_state.get("candidate_options") if isinstance(recommendation_state, Mapping) else []
        if isinstance(candidate_options, list):
            for index, option in enumerate(candidate_options):
                if not isinstance(option, Mapping):
                    continue
                title = str(option.get("title") or "").strip()
                if not title:
                    continue
                path = str(option.get("path") or "option")
                position = "recommended" if index == 0 else "viable"
                alternatives.append(
                    {
                        "id": path,
                        "title": title,
                        "position": position,
                        "summary": str(option.get("summary") or option.get("description") or "").strip(),
                        "benefits": _normalize_text_list(option.get("benefits")),
                        "risks": _normalize_text_list(option.get("risks")),
                        "operational_burden": str(option.get("operational_burden") or "").strip(),
                        "governance_implications": str(option.get("governance_implications") or "").strip(),
                        "best_fit_conditions": _normalize_text_list(option.get("best_fit_conditions")),
                    }
                )
                if len(alternatives) >= 3:
                    break

    decisions = []
    if isinstance(raw.get("decisions"), list):
        for item in raw.get("decisions"):
            if not isinstance(item, Mapping):
                continue
            statement = str(item.get("statement") or "").strip()
            if not statement:
                continue
            decisions.append(
                {
                    "statement": statement,
                    "options_considered": _normalize_text_list(item.get("options_considered")),
                    "recommendation": str(item.get("recommendation") or recommendation["summary"]).strip(),
                    "why": str(item.get("why") or "").strip(),
                    "tradeoffs_accepted": _normalize_text_list(item.get("tradeoffs_accepted")),
                    "owner": str(item.get("owner") or "").strip(),
                    "open_dependency": str(item.get("open_dependency") or "").strip(),
                }
            )
    if not decisions:
        for item in _normalize_text_list(workspace.get("decisions")):
            decisions.append(
                {
                    "statement": item,
                    "options_considered": [],
                    "recommendation": recommendation["summary"],
                    "why": "",
                    "tradeoffs_accepted": [],
                    "owner": "",
                    "open_dependency": "",
                }
            )

    risks = []
    if isinstance(raw.get("risks"), list):
        for item in raw.get("risks"):
            if not isinstance(item, Mapping):
                continue
            risk = str(item.get("risk") or "").strip()
            if not risk:
                continue
            severity = str(item.get("severity") or "").strip().lower()
            if severity not in {"low", "medium", "high"}:
                severity = ""
            risks.append(
                {
                    "category": str(item.get("category") or "").strip(),
                    "severity": severity,
                    "risk": risk,
                    "mitigation": str(item.get("mitigation") or "").strip(),
                }
            )
    if not risks:
        for item in _normalize_text_list(workspace.get("risks")):
            risks.append({"category": "", "severity": "", "risk": item, "mitigation": ""})

    maturity = []
    if isinstance(raw.get("maturity"), list):
        for item in raw.get("maturity"):
            if not isinstance(item, Mapping):
                continue
            domain = str(item.get("domain") or "").strip()
            if not domain:
                continue
            maturity.append(
                {
                    "domain": domain,
                    "current_state": str(item.get("current_state") or "").strip(),
                    "target_state": str(item.get("target_state") or "").strip(),
                    "gap": str(item.get("gap") or "").strip(),
                }
            )

    next_best_question = raw.get("next_best_question") if isinstance(raw.get("next_best_question"), Mapping) else {}
    next_best_question_payload = None
    question_text = str(next_best_question.get("question") or recommendation_state.get("next_best_question") or "").strip()
    if not question_text:
        open_questions = _derive_open_questions(_normalize_question_state(workspace.get("question_state"), workspace.get("open_questions"), workspace), workspace.get("open_questions"))
        question_text = open_questions[0] if open_questions else ""
    if question_text:
        next_best_question_payload = {
            "question": question_text,
            "why_it_matters": str(next_best_question.get("why_it_matters") or "This answer most directly changes the recommendation and architecture.").strip(),
        }

    readout = raw.get("readout") if isinstance(raw.get("readout"), Mapping) else {}
    output_pack = raw.get("output_pack") if isinstance(raw.get("output_pack"), Mapping) else {}
    open_questions = _normalize_text_list(output_pack.get("open_questions")) or _derive_open_questions(
        _normalize_question_state(workspace.get("question_state"), workspace.get("open_questions"), workspace),
        workspace.get("open_questions"),
    )

    normalized_case = {
        "recommendation": recommendation,
        "alternatives": alternatives,
        "decisions": decisions,
        "risks": risks,
        "maturity": maturity,
        "readout": {
            "current_recommendation": str(readout.get("current_recommendation") or recommendation["summary"]).strip(),
            "important_decisions": _normalize_text_list(readout.get("important_decisions")) or _normalize_text_list(workspace.get("decisions"))[:5],
            "biggest_risks": _normalize_text_list(readout.get("biggest_risks")) or _normalize_text_list(workspace.get("risks"))[:5],
            "open_questions": _normalize_text_list(readout.get("open_questions")) or open_questions[:3],
            "rollout_summary": str(readout.get("rollout_summary") or "").strip(),
            "architecture_snapshot": str(readout.get("architecture_snapshot") or "").strip(),
        },
        "next_best_question": next_best_question_payload,
        "output_pack": {
            "executive_summary": str(output_pack.get("executive_summary") or "").strip(),
            "recommendation_memo": str(output_pack.get("recommendation_memo") or "").strip(),
            "architecture_narrative": str(output_pack.get("architecture_narrative") or "").strip(),
            "key_decisions": _normalize_text_list(output_pack.get("key_decisions")) or _normalize_text_list(workspace.get("decisions")),
            "risks_and_mitigations": [
                {
                    "risk": str(item.get("risk") or "").strip(),
                    "mitigation": str(item.get("mitigation") or "").strip(),
                }
                for item in output_pack.get("risks_and_mitigations", [])
                if isinstance(item, Mapping) and str(item.get("risk") or "").strip()
            ],
            "open_questions": open_questions,
            "rollout_30_90_180": [
                {
                    "horizon": str(item.get("horizon") or "").strip(),
                    "outcome": str(item.get("outcome") or "").strip(),
                }
                for item in output_pack.get("rollout_30_90_180", [])
                if isinstance(item, Mapping) and str(item.get("horizon") or "").strip()
            ],
            "operating_principles": _normalize_text_list(output_pack.get("operating_principles")),
            "control_checklist": _normalize_text_list(output_pack.get("control_checklist")),
        },
        "delta": raw.get("delta") if isinstance(raw.get("delta"), Mapping) else None,
    }

    return normalized_case if _has_content(normalized_case) else None


def _normalize_recommendation_state(
    value: Any,
    workspace: Mapping[str, Any],
    reasoning_changes: list[str] | None = None,
) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), Mapping) else {}
    advisory_recommendation = advisory_case.get("recommendation") if isinstance(advisory_case.get("recommendation"), Mapping) else {}
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    prefer_traversal = bool(reasoning_changes)

    primary_recommendation = str(
        raw.get("primary_recommendation")
        or advisory_recommendation.get("summary")
        or workspace.get("recommendation")
        or ""
    ).strip()
    confidence = str(raw.get("confidence") or advisory_recommendation.get("confidence") or "").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = ""

    candidate_options = (
        traversal_state.get("candidate_options", [])
        if prefer_traversal or not isinstance(raw.get("candidate_options"), list)
        else raw.get("candidate_options")
    )
    normalized_options: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, item in enumerate(candidate_options if isinstance(candidate_options, list) else []):
        if not isinstance(item, Mapping):
            continue
        title = str(item.get("title") or "").strip()
        path = str(item.get("path") or title or f"option-{index + 1}").strip()
        if not title or path in seen_paths:
            continue
        seen_paths.add(path)
        normalized_options.append(
            {
                "path": path,
                "title": title,
                "summary": str(item.get("summary") or item.get("description") or "").strip(),
                "decision_domain": str(item.get("decision_domain") or "").strip(),
                "position": str(item.get("position") or ("recommended" if index == 0 else "viable")).strip(),
            }
        )

    missing_evidence = None if prefer_traversal else raw.get("missing_evidence")
    if not isinstance(missing_evidence, list):
        traversal_missing = traversal_state.get("missing_evidence", [])
        missing_evidence = []
        if isinstance(traversal_missing, list):
            for item in traversal_missing:
                if isinstance(item, Mapping):
                    text = str(item.get("question") or item.get("text") or "").strip()
                    if text:
                        missing_evidence.append(text)
                else:
                    text = str(item or "").strip()
                    if text:
                        missing_evidence.append(text)
    missing_evidence = _normalize_text_list(missing_evidence)

    next_best_question = str(
        traversal_state.get("next_best_question")
        if prefer_traversal
        else (raw.get("next_best_question") or traversal_state.get("next_best_question") or "")
    ).strip()
    if not next_best_question:
        open_questions = _derive_open_questions(
            _normalize_question_state(workspace.get("question_state"), workspace.get("open_questions"), workspace),
            workspace.get("open_questions"),
        )
        next_best_question = open_questions[0] if open_questions else ""

    return {
        "primary_recommendation": primary_recommendation,
        "confidence": confidence,
        "candidate_options": normalized_options,
        "missing_evidence": missing_evidence,
        "next_best_question": next_best_question,
        "last_reasoning_change_fields": list(reasoning_changes or []),
    }


def _advisory_case_is_ready(advisory_case: Mapping[str, Any] | None) -> bool:
    if not isinstance(advisory_case, Mapping):
        return False
    recommendation = advisory_case.get("recommendation") if isinstance(advisory_case.get("recommendation"), Mapping) else {}
    alternatives = advisory_case.get("alternatives") if isinstance(advisory_case.get("alternatives"), list) else []
    return bool(
        str(recommendation.get("summary") or "").strip()
        and str(recommendation.get("why_this") or "").strip()
        and str(recommendation.get("why_not") or "").strip()
        and str(recommendation.get("confidence") or "").strip()
        and len(alternatives) >= 2
    )


def _question_state_status(question_state: list[dict[str, Any]]) -> str:
    if any(item.get("status") == "open" for item in question_state):
        return "ready"
    if question_state:
        return "ready"
    return "missing"


def _build_artifact_status(
    workspace: Mapping[str, Any],
    *,
    invalidated_fields: list[str] | None = None,
    reasoning_changes: list[str] | None = None,
) -> dict[str, Any]:
    invalidated = set(invalidated_fields or [])
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), Mapping) else None
    recommendation_state = workspace.get("recommendation_state") if isinstance(workspace.get("recommendation_state"), Mapping) else {}
    recommendation_summary = str(
        workspace.get("recommendation")
        or recommendation_state.get("primary_recommendation")
        or ((advisory_case or {}).get("recommendation") or {}).get("summary")
        or ""
    ).strip()
    open_questions = _derive_open_questions(
        _normalize_question_state(workspace.get("question_state"), workspace.get("open_questions"), workspace),
        workspace.get("open_questions"),
    )

    recommendation_status = "missing"
    if recommendation_summary:
        recommendation_status = "ready"
    elif _has_content(workspace.get("facts")) or _has_content(workspace.get("assumptions")):
        recommendation_status = "draft"

    advisory_status = "missing"
    if invalidated and "advisory_case" in invalidated:
        advisory_status = "stale"
    elif _advisory_case_is_ready(advisory_case):
        advisory_status = "ready"
    elif _has_content(advisory_case) or recommendation_summary:
        advisory_status = "draft"

    blueprint_status = "missing"
    if invalidated and "blueprint_markdown" in invalidated:
        blueprint_status = "stale"
    elif _has_content(workspace.get("blueprint_markdown")):
        blueprint_status = "ready"
    elif recommendation_summary:
        blueprint_status = "draft"

    return {
        "recommendation": recommendation_status,
        "question_state": _question_state_status(_normalize_question_state(workspace.get("question_state"), workspace.get("open_questions"), workspace)),
        "advisory_case": advisory_status,
        "blueprint": blueprint_status,
        "blocking_question_count": len(open_questions),
        "stale_fields": list(invalidated_fields or []),
        "reasoning_changes": list(reasoning_changes or []),
    }


def _resolve_stage(
    requested_stage: str,
    existing_stage: str,
    workspace: Mapping[str, Any],
) -> str:
    requested = requested_stage if requested_stage in _STAGES else ""
    existing = existing_stage if existing_stage in _STAGES else ""
    advisory_ready = _advisory_case_is_ready(workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), Mapping) else None)
    recommendation_ready = _has_content(workspace.get("recommendation")) or advisory_ready
    blueprint_ready = _has_content(workspace.get("blueprint_markdown"))
    has_solution_material = bool(
        recommendation_ready
        or _has_content(workspace.get("decisions"))
        or _has_content(workspace.get("risks"))
        or _has_content(workspace.get("implementation_plan"))
        or _has_content(workspace.get("advisory_case"))
    )
    has_discovery_material = bool(
        _has_content(workspace.get("facts"))
        or _has_content(workspace.get("assumptions"))
        or _has_content(workspace.get("question_state"))
        or _has_content(workspace.get("open_questions"))
        or has_solution_material
    )

    if recommendation_ready and blueprint_ready:
        return "blueprint"
    if has_solution_material:
        return "solutioning"
    if (requested in {"solutioning", "blueprint"} or existing in {"solutioning", "blueprint"}) and has_discovery_material:
        return "solutioning"
    if has_discovery_material:
        return "discovery"
    return "discovery"


def _normalize_workspace_values(raw: Mapping[str, Any], existing: Mapping[str, Any] | None = None) -> dict[str, Any]:
    workspace = {
        "stage": str(raw.get("stage") or "").strip(),
        "recommendation": str(raw.get("recommendation") or "").strip(),
        "blueprint_markdown": str(raw.get("blueprint_markdown") or "").strip(),
        "assumptions": raw.get("assumptions", []) or [],
        "facts": _normalize_text_list(raw.get("facts")),
        "operating_model": _normalize_operating_model(raw.get("operating_model")),
        "decisions": _normalize_text_list(raw.get("decisions")),
        "risks": _normalize_text_list(raw.get("risks")),
        "implementation_plan": _normalize_text_list(raw.get("implementation_plan")),
        "advisory_case": raw.get("advisory_case") if isinstance(raw.get("advisory_case"), Mapping) else None,
        "recommendation_state": raw.get("recommendation_state") if isinstance(raw.get("recommendation_state"), Mapping) else {},
        "artifact_status": raw.get("artifact_status") if isinstance(raw.get("artifact_status"), Mapping) else {},
        "traversal_state": raw.get("traversal_state") if isinstance(raw.get("traversal_state"), Mapping) else None,
    }
    question_state = _normalize_question_state(raw.get("question_state"), raw.get("open_questions"), existing or raw)
    workspace["question_state"] = question_state
    workspace["open_questions"] = _derive_open_questions(question_state, raw.get("open_questions"))
    if not workspace["recommendation"] and isinstance(workspace["advisory_case"], Mapping):
        recommendation = workspace["advisory_case"].get("recommendation")
        if isinstance(recommendation, Mapping):
            workspace["recommendation"] = str(recommendation.get("summary") or "").strip()
    return workspace


def build_workspace_state(
    existing: Mapping[str, Any] | None,
    *,
    recommendation: str | None = None,
    blueprint_markdown: str | None = None,
    assumptions: list[dict] | None = None,
    facts: list[str] | None = None,
    operating_model: str | None = None,
    question_state: list[dict] | None = None,
    open_questions: list[str] | None = None,
    decisions: list[str] | None = None,
    risks: list[str] | None = None,
    implementation_plan: list[str] | None = None,
    advisory_case: dict | None = None,
    stage: str = "",
) -> tuple[dict[str, Any], list[str], list[str]]:
    current = _normalize_workspace_values(dict(existing or {}), dict(existing or {}))
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
    if question_state is not None:
        explicit_updates["question_state"] = question_state
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
    if question_state is None and open_questions is not None:
        explicit_updates["question_state"] = []

    preview_raw = dict(current)
    preview_raw.update(explicit_updates)
    preview_workspace = _normalize_workspace_values(preview_raw, current)

    reasoning_changes = [
        field
        for field in _REASONING_DRIVER_FIELDS
        if field in explicit_updates and _value_changed(_default_value(current, field), preview_workspace.get(field))
    ]
    heavy_artifact_driver_changes = [
        field
        for field in _HEAVY_ARTIFACT_DRIVER_FIELDS
        if field in explicit_updates and _value_changed(_default_value(current, field), preview_workspace.get(field))
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

    if "open_questions" in explicit_updates and "question_state" not in explicit_updates:
        explicit_updates["question_state"] = []

    final_raw = dict(current)
    final_raw.update(explicit_updates)
    workspace = _normalize_workspace_values(final_raw, current)
    workspace["stage"] = _resolve_stage(stage, _default_value(current, "stage"), workspace)
    return workspace, invalidated_fields, reasoning_changes


def reconcile_workspace_state(
    workspace: Mapping[str, Any],
    *,
    invalidated_fields: list[str] | None = None,
    reasoning_changes: list[str] | None = None,
) -> dict[str, Any]:
    reconciled = _normalize_workspace_values(dict(workspace), dict(workspace))
    confirmed_fact_texts = _facts_from_confirmed_structured_facts(reconciled)
    traversal_state = reconciled.get("traversal_state") if isinstance(reconciled.get("traversal_state"), Mapping) else {}
    has_structured_fact_contract = any(
        isinstance(traversal_state.get(field), list)
        for field in ("customer_confirmed_facts", "structured_facts")
    )
    if confirmed_fact_texts or has_structured_fact_contract:
        reconciled["facts"] = confirmed_fact_texts
    reconciled["recommendation_state"] = _normalize_recommendation_state(
        workspace.get("recommendation_state"),
        reconciled,
        reasoning_changes=reasoning_changes,
    )
    reconciled["advisory_case"] = _normalize_advisory_case(workspace.get("advisory_case"), reconciled)
    if not reconciled["recommendation"]:
        reconciled["recommendation"] = str(reconciled["recommendation_state"].get("primary_recommendation") or "").strip()
    if not reconciled["advisory_case"] and reconciled["recommendation"]:
        reconciled["advisory_case"] = _normalize_advisory_case({}, reconciled)
    reconciled["artifact_status"] = _build_artifact_status(
        reconciled,
        invalidated_fields=invalidated_fields,
        reasoning_changes=reasoning_changes,
    )
    reconciled["stage"] = _resolve_stage(str(reconciled.get("stage") or ""), str(reconciled.get("stage") or ""), reconciled)
    return reconciled
