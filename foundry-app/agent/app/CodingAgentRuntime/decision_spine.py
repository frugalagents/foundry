from __future__ import annotations

import re
from typing import Any, Mapping

from pydantic import BaseModel, Field, ValidationError

from knowledge_loader import KnowledgeBase, KnowledgeNode

_CONFIRMED_FACT_SOURCES = {"customer", "customer_confirmed", "explicit_constraint", "operating_model"}
_INFERRED_FACT_SOURCES = {"engine_inferred", "inferred", "okf_inferred"}

_COMPLIANCE_CLOSE_PHRASES = (
    "no compliance requirements",
    "no special compliance requirements",
    "no compliance constraints",
    "no regulatory constraints",
    "no regulatory requirements",
    "nothing regulated",
    "no regulated workloads",
    "no regulated repos",
    "no special regulations",
    "not regulated",
    "without compliance constraints",
)

_COMPLIANCE_NEGATED_TERMS = (
    "hipaa",
    "itar",
    "ear",
    "pci",
    "sox",
    "cmmc",
    "gdpr",
    "works council",
)


class FactRule(BaseModel):
    key: str
    value: Any = True
    status: str = "confirmed"
    source: str = "customer"
    match_any: list[str] = Field(default_factory=list)
    match_all: list[str] = Field(default_factory=list)
    min_trigger_pool_matches: int = 0
    value_from: str = ""
    label_map: dict[str, str] = Field(default_factory=dict)
    fact_text: str = ""


class ActivationRule(BaseModel):
    requires_facts_all: list[str] = Field(default_factory=list)
    requires_facts_any: list[str] = Field(default_factory=list)
    match_any: list[str] = Field(default_factory=list)
    match_all: list[str] = Field(default_factory=list)


class QuestionSpec(BaseModel):
    id: str
    text: str
    why_it_matters: str = ""
    decision_domain: str = ""
    blocking: bool = True


class CandidateOption(BaseModel):
    path: str
    title: str
    summary: str = ""
    decision_domain: str = ""
    position: str = ""


class OutputSpec(BaseModel):
    decision_focus: str = ""
    question: QuestionSpec | None = None
    recommendation: str = ""
    risks: list[str] = Field(default_factory=list)
    options: list[CandidateOption] = Field(default_factory=list)


class ResolutionRule(BaseModel):
    when_facts_all: list[str] = Field(default_factory=list)
    decision: str = ""
    recommendation: str = ""


class AdvisorySpec(BaseModel):
    slice: bool = False
    fact_rules: list[FactRule] = Field(default_factory=list)
    activate: ActivationRule = Field(default_factory=ActivationRule)
    output: OutputSpec = Field(default_factory=OutputSpec)
    resolutions: list[ResolutionRule] = Field(default_factory=list)


def build_turn_guidance(
    kb: KnowledgeBase,
    workspace: Mapping[str, Any] | None,
    user_message: str,
) -> dict[str, Any]:
    workspace = workspace or {}
    signal_text = _signal_text(user_message)
    fact_records = _seed_fact_records(workspace)

    advisory_nodes = _advisory_slice_nodes(kb)
    for node, spec in advisory_nodes:
        _apply_fact_rules(node, spec, signal_text, fact_records)

    closed_domains = _detect_closed_domains(signal_text, fact_records)

    decisions: list[str] = []
    resolved_paths: set[str] = set()
    resolution_recommendations: list[str] = []
    for node, spec in advisory_nodes:
        matched = _matched_resolutions(spec, fact_records)
        if not matched:
            continue
        resolved_paths.add(node.path)
        for resolution in matched:
            if resolution.decision:
                decisions.append(resolution.decision)
            if resolution.recommendation:
                resolution_recommendations.append(resolution.recommendation)

    active_candidates: list[tuple[int, KnowledgeNode, AdvisorySpec]] = []
    for node, spec in advisory_nodes:
        if node.path in resolved_paths:
            continue
        if _is_active(spec.activate, fact_records, signal_text):
            active_candidates.append((int(node.priority), node, spec))

    active_candidates.sort(key=lambda item: (-item[0], item[1].path))
    active_node: KnowledgeNode | None = active_candidates[0][1] if active_candidates else None
    active_spec: AdvisorySpec | None = active_candidates[0][2] if active_candidates else None

    facts = _fact_texts(fact_records)
    question_state: list[dict[str, Any]] = []
    risks: list[str] = []
    candidate_options: list[dict[str, Any]] = []
    missing_evidence: list[dict[str, Any]] = []
    decision_focus = ""
    next_best_question = ""
    recommendation = ""

    if active_spec is not None:
        output = active_spec.output
        decision_focus = output.decision_focus or (active_node.decision_domain if active_node else "")
        recommendation = output.recommendation
        risks = output.risks
        candidate_options = [option.model_dump() for option in output.options]
        if output.question is not None:
            question = output.question.model_dump()
            question["status"] = "open"
            question["source"] = "okf"
            if not question.get("decision_domain"):
                question["decision_domain"] = decision_focus
            question_state.append(question)
            next_best_question = question["text"]
            missing_evidence.append(
                {
                    "question": question["text"],
                    "decision_domain": question.get("decision_domain", ""),
                    "why_it_matters": question.get("why_it_matters", ""),
                    "blocking": bool(question.get("blocking", True)),
                }
            )
    elif resolution_recommendations:
        recommendation = resolution_recommendations[0]

    operating_model = _fact_value(fact_records, "operating_model")
    operating_model = str(operating_model).strip() if operating_model is not None else str(workspace.get("operating_model") or "").strip()
    confirmed_fact_records = _fact_records_for_sources(fact_records, _CONFIRMED_FACT_SOURCES)
    inferred_fact_records = _fact_records_for_sources(fact_records, _INFERRED_FACT_SOURCES)
    customer_confirmed_facts = _serialize_fact_records(confirmed_fact_records)
    engine_inferred_facts = _serialize_fact_records(inferred_fact_records)
    active_slice = _build_active_slice(active_node, active_spec, decision_focus)

    return {
        "facts": _fact_texts(confirmed_fact_records),
        "operating_model": operating_model or "undecided",
        "question_state": question_state,
        "open_questions": [item["text"] for item in question_state],
        "decisions": _dedupe_text_list(decisions),
        "risks": _dedupe_text_list(risks),
        "recommendation": recommendation,
        "decision_focus": decision_focus,
        "next_best_question": next_best_question,
        "candidate_options": candidate_options,
        "missing_evidence": missing_evidence,
        "closed_domains": closed_domains,
        "active_slice": active_slice,
        "customer_confirmed_facts": customer_confirmed_facts,
        "structured_facts": customer_confirmed_facts,
        "engine_inferred_facts": engine_inferred_facts,
        "engine_hypotheses": _build_engine_hypotheses(
            recommendation=recommendation,
            decision_focus=decision_focus,
            next_best_question=next_best_question,
            candidate_options=candidate_options,
        ),
    }


def render_turn_guidance_context(guidance: Mapping[str, Any]) -> str:
    if not guidance:
        return ""

    facts = _string_list(guidance.get("facts"))
    recommendation = str(guidance.get("recommendation") or "").strip()
    next_best_question = str(guidance.get("next_best_question") or "").strip()
    candidate_options = guidance.get("candidate_options") if isinstance(guidance.get("candidate_options"), list) else []
    risks = _string_list(guidance.get("risks"))
    decision_focus = str(guidance.get("decision_focus") or "").strip()

    if not any((facts, recommendation, next_best_question, candidate_options, risks, decision_focus)):
        return ""

    lines = ["## Deterministic Turn State"]
    if facts:
        lines.append("Customer facts already established:")
        lines.extend(f"- {fact}" for fact in facts[:5])
    if decision_focus:
        lines.append(f"Decision focus: {decision_focus}")
    if recommendation:
        lines.append(f"Working recommendation: {recommendation}")
    if risks:
        lines.append("Architecture pressures to challenge:")
        lines.extend(f"- {risk}" for risk in risks[:3])
    if next_best_question:
        lines.append(f"Ask this next unless the customer just answered it: {next_best_question}")
    if candidate_options:
        lines.append("Current focused options:")
        for option in candidate_options[:3]:
            title = str(option.get("title") or "").strip()
            summary = str(option.get("summary") or "").strip()
            position = str(option.get("position") or "").strip() or "option"
            if title:
                lines.append(f"- {title} ({position}): {summary}")
    return "\n".join(lines)


def merge_guidance_into_traversal_state(
    traversal_state: dict[str, Any],
    guidance: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not guidance:
        return traversal_state

    merged = dict(traversal_state)
    if guidance.get("next_best_question"):
        merged["next_best_question"] = guidance["next_best_question"]
    if guidance.get("missing_evidence"):
        merged["missing_evidence"] = guidance["missing_evidence"]
    if guidance.get("candidate_options"):
        merged["candidate_options"] = guidance["candidate_options"]
    if guidance.get("decision_focus"):
        merged["decision_focus"] = guidance["decision_focus"]
    if guidance.get("customer_confirmed_facts"):
        merged["customer_confirmed_facts"] = guidance["customer_confirmed_facts"]
    if guidance.get("structured_facts"):
        merged["structured_facts"] = guidance["structured_facts"]
    if guidance.get("engine_inferred_facts"):
        merged["engine_inferred_facts"] = guidance["engine_inferred_facts"]
    if guidance.get("closed_domains"):
        merged["closed_domains"] = guidance["closed_domains"]
    if guidance.get("active_slice"):
        merged["active_slice"] = guidance["active_slice"]
        merged["active_decision"] = guidance["active_slice"]
    if guidance.get("engine_hypotheses"):
        merged["engine_hypotheses"] = guidance["engine_hypotheses"]
    return merged


def _advisory_slice_nodes(kb: KnowledgeBase) -> list[tuple[KnowledgeNode, AdvisorySpec]]:
    nodes: list[tuple[KnowledgeNode, AdvisorySpec]] = []
    for node in kb._nodes.values():
        raw = node.metadata.get("advisory")
        if not isinstance(raw, Mapping):
            continue
        try:
            spec = AdvisorySpec.model_validate(raw)
        except ValidationError:
            continue
        if spec.slice:
            nodes.append((node, spec))
    return nodes


def _apply_fact_rules(
    node: KnowledgeNode,
    spec: AdvisorySpec,
    signal_text: str,
    fact_records: dict[str, dict[str, Any]],
) -> None:
    for rule in spec.fact_rules:
        value = _extract_fact_value(node, rule, signal_text)
        if value is None:
            continue
        existing = fact_records.get(rule.key)
        if existing and isinstance(existing.get("value"), list) and isinstance(value, list):
            value = _dedupe_list(existing["value"] + value)
        rendered_text = _render_fact_text(rule.fact_text, value)
        fact_records[rule.key] = {
            "key": rule.key,
            "value": value,
            "status": rule.status,
            "source": _normalize_fact_source(rule.source),
            "fact_text": rendered_text or existing.get("fact_text", "") if existing else rendered_text,
        }


def _extract_fact_value(node: KnowledgeNode, rule: FactRule, signal_text: str) -> Any | None:
    if rule.match_all and not all(_pattern_present(signal_text, pattern) for pattern in rule.match_all):
        return None
    if rule.match_any and not any(_pattern_present(signal_text, pattern) for pattern in rule.match_any):
        return None

    matched_labels: list[str] = []
    if rule.value_from == "matched_trigger_pool_labels":
        matched_labels = _matched_trigger_pool_labels(node, rule.label_map, signal_text)
        required = max(1, int(rule.min_trigger_pool_matches or 1))
        if len(matched_labels) < required:
            return None
        return matched_labels

    if rule.min_trigger_pool_matches > 0:
        matched_labels = _matched_trigger_pool_labels(node, rule.label_map, signal_text)
        if len(matched_labels) < int(rule.min_trigger_pool_matches):
            return None

    if not (rule.match_any or rule.match_all or rule.min_trigger_pool_matches):
        return None
    return rule.value


def _is_active(
    activation: ActivationRule,
    fact_records: Mapping[str, dict[str, Any]],
    signal_text: str,
) -> bool:
    if activation.requires_facts_all and not all(_fact_condition_met(fact_records, condition) for condition in activation.requires_facts_all):
        return False
    if activation.requires_facts_any and not any(_fact_condition_met(fact_records, condition) for condition in activation.requires_facts_any):
        return False
    if activation.match_all and not all(pattern in signal_text for pattern in activation.match_all):
        return False
    if activation.match_any and not any(pattern in signal_text for pattern in activation.match_any):
        return False
    return bool(activation.requires_facts_all or activation.requires_facts_any or activation.match_all or activation.match_any)


def _matched_resolutions(
    spec: AdvisorySpec,
    fact_records: Mapping[str, dict[str, Any]],
) -> list[ResolutionRule]:
    matched: list[ResolutionRule] = []
    for resolution in spec.resolutions:
        if all(_fact_condition_met(fact_records, condition) for condition in resolution.when_facts_all):
            matched.append(resolution)
    return matched


def _matched_trigger_pool_labels(node: KnowledgeNode, label_map: Mapping[str, str], signal_text: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for trigger in sorted(set(node.trigger_pool), key=len, reverse=True):
        if not trigger:
            continue
        if not _pattern_present(signal_text, trigger, use_word_boundaries=True):
            continue
        label = str(label_map.get(trigger, trigger)).strip()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels


def _seed_fact_records(workspace: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    structured = (
        traversal_state.get("customer_confirmed_facts")
        if isinstance(traversal_state.get("customer_confirmed_facts"), list)
        else []
    )
    if isinstance(structured, list):
        for item in structured:
            if not isinstance(item, Mapping):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            source = str(item.get("source") or "").strip().lower()
            if source not in _CONFIRMED_FACT_SOURCES:
                continue
            records[key] = {
                "key": key,
                "value": item.get("value"),
                "status": str(item.get("status") or "confirmed").strip() or "confirmed",
                "source": source or "customer",
                "fact_text": str(item.get("fact_text") or "").strip(),
            }
    operating_model = str(workspace.get("operating_model") or "").strip()
    if operating_model and operating_model != "undecided":
        records["operating_model"] = {
            "key": "operating_model",
            "value": operating_model,
            "status": "confirmed",
            "source": "operating_model",
            "fact_text": "",
        }
    return records


def _fact_condition_met(fact_records: Mapping[str, dict[str, Any]], condition: str) -> bool:
    if "=" in condition:
        key, expected = condition.split("=", 1)
        current = _fact_value(fact_records, key.strip())
        if isinstance(current, list):
            return expected.strip() in [str(item).strip() for item in current]
        return str(current).strip() == expected.strip()

    value = _fact_value(fact_records, condition.strip())
    if isinstance(value, list):
        return len(value) > 0
    return bool(value)


def _fact_value(fact_records: Mapping[str, dict[str, Any]], key: str) -> Any | None:
    record = fact_records.get(key)
    if not record:
        return None
    return record.get("value")


def _fact_records_for_sources(
    fact_records: Mapping[str, dict[str, Any]],
    allowed_sources: set[str],
) -> dict[str, dict[str, Any]]:
    return {
        key: dict(item)
        for key, item in fact_records.items()
        if str(item.get("source") or "").strip().lower() in allowed_sources
    }


def _serialize_fact_records(fact_records: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "value": item.get("value"),
            "status": item.get("status", "confirmed"),
            "source": item.get("source", "customer"),
            "fact_text": item.get("fact_text", ""),
        }
        for key, item in fact_records.items()
    ]


def _fact_texts(fact_records: Mapping[str, dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for item in fact_records.values():
        text = str(item.get("fact_text") or "").strip()
        if text:
            texts.append(text)
    return _dedupe_text_list(texts)


def _render_fact_text(template: str, value: Any) -> str:
    if not template:
        return ""
    rendered_value = ", ".join(str(item) for item in value) if isinstance(value, list) else str(value)
    return template.replace("{value}", rendered_value)


def _signal_text(user_message: str) -> str:
    return str(user_message or "").lower()


def _pattern_present(signal_text: str, pattern: str, *, use_word_boundaries: bool = False) -> bool:
    if not signal_text or not pattern:
        return False
    escaped = re.escape(pattern)
    regex = rf"\b{escaped}\b" if use_word_boundaries else escaped
    for match in re.finditer(regex, signal_text):
        prefix = signal_text[max(0, match.start() - 24):match.start()]
        if re.search(r"(?:^|[\s,(])(?:no|not|without)\s+[^.?!]{0,24}$", prefix):
            continue
        return True
    return False


def _normalize_fact_source(source: str) -> str:
    normalized = str(source or "").strip().lower()
    if normalized in _CONFIRMED_FACT_SOURCES | _INFERRED_FACT_SOURCES:
        return normalized
    return "customer"


def _detect_closed_domains(
    signal_text: str,
    fact_records: Mapping[str, dict[str, Any]],
) -> list[str]:
    closed: list[str] = []
    if _closes_compliance_domain(signal_text, fact_records):
        closed.append("compliance_overlay")
    return closed


def _closes_compliance_domain(
    signal_text: str,
    fact_records: Mapping[str, dict[str, Any]],
) -> bool:
    if any(bool(_fact_value(fact_records, key)) for key in ("export_control", "works_council_required")):
        return False
    if any(phrase in signal_text for phrase in _COMPLIANCE_CLOSE_PHRASES):
        return True
    negated_terms = [term for term in _COMPLIANCE_NEGATED_TERMS if f"no {term}" in signal_text or f"not {term}" in signal_text]
    return len(negated_terms) >= 2


def _build_active_slice(
    active_node: KnowledgeNode | None,
    active_spec: AdvisorySpec | None,
    decision_focus: str,
) -> dict[str, Any] | None:
    if active_node is None:
        return None
    question_id = ""
    if active_spec is not None and active_spec.output.question is not None:
        question_id = str(active_spec.output.question.id or "").strip()
    return {
        "path": active_node.path,
        "title": active_node.title,
        "decision_domain": decision_focus or active_node.decision_domain,
        "question_id": question_id,
        "source": "decision_spine",
    }


def _build_engine_hypotheses(
    *,
    recommendation: str,
    decision_focus: str,
    next_best_question: str,
    candidate_options: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hypotheses: list[dict[str, Any]] = []
    if recommendation:
        hypotheses.append(
            {
                "kind": "working_recommendation",
                "text": recommendation,
                "decision_domain": decision_focus,
            }
        )
    if next_best_question:
        hypotheses.append(
            {
                "kind": "next_best_question",
                "text": next_best_question,
                "decision_domain": decision_focus,
            }
        )
    for item in candidate_options[:3]:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        hypotheses.append(
            {
                "kind": "candidate_option",
                "text": title,
                "decision_domain": str(item.get("decision_domain") or decision_focus).strip(),
                "path": str(item.get("path") or "").strip(),
                "position": str(item.get("position") or "").strip(),
            }
        )
    return hypotheses


def _dedupe_text_list(items: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(text)
    return merged


def _dedupe_list(items: list[Any]) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for item in items:
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
