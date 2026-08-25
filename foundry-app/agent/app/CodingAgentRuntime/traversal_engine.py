from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping

from knowledge_loader import KnowledgeBase, KnowledgeNode

_CONFIRMED_FACT_SOURCES = {"customer", "customer_confirmed", "explicit_constraint", "operating_model"}

_DISCOVERY_ANCHORS = (
    "harness-selection/index",
    "harness-selection/lifecycle-implications",
    "access/identity",
    "access/quota",
    "exec/local",
)

_STAGE_DOMAIN_WEIGHTS: dict[str, dict[str, int]] = {
    "discovery": {
        "operating_model": 16,
        "harness_cascade": 11,
        "harness_family": 13,
        "execution_boundary": 10,
        "identity_boundary": 9,
        "tool_governance": 8,
        "model_routing": 7,
        "population_policy": 6,
        "surface_strategy": 9,
        "approval_posture": 8,
        "security_posture": 8,
        "audit_ops": 7,
        "cost_control": 7,
        "resilience_ops": 5,
        "multi_cloud": 6,
        "multi_instance": 6,
        "model_provider": 7,
        "harness_runtime": 9,
        "agent_loop": 6,
        "context_strategy": 5,
        "memory_strategy": 5,
        "change_safety": 4,
        "registry_governance": 6,
        "knowledge_layer": 6,
        "quality_gate": 6,
        "gateway_strategy": 5,
        "secrets_integration": 5,
        "external_integration": 6,
        "governance_group": 3,
        "compliance_overlay": 8,
    },
    "solutioning": {
        "operating_model": 10,
        "harness_cascade": 10,
        "harness_family": 10,
        "execution_boundary": 11,
        "identity_boundary": 9,
        "tool_governance": 10,
        "model_routing": 10,
        "population_policy": 8,
        "surface_strategy": 7,
        "approval_posture": 9,
        "security_posture": 8,
        "audit_ops": 9,
        "cost_control": 8,
        "resilience_ops": 8,
        "multi_cloud": 8,
        "multi_instance": 8,
        "model_provider": 9,
        "harness_runtime": 8,
        "agent_loop": 6,
        "context_strategy": 5,
        "memory_strategy": 5,
        "change_safety": 5,
        "registry_governance": 7,
        "knowledge_layer": 7,
        "quality_gate": 8,
        "gateway_strategy": 6,
        "secrets_integration": 6,
        "external_integration": 7,
        "governance_group": 3,
        "compliance_overlay": 11,
    },
    "blueprint": {
        "operating_model": 7,
        "harness_cascade": 8,
        "harness_family": 7,
        "execution_boundary": 9,
        "identity_boundary": 9,
        "tool_governance": 8,
        "model_routing": 8,
        "population_policy": 8,
        "surface_strategy": 5,
        "approval_posture": 8,
        "security_posture": 8,
        "audit_ops": 10,
        "cost_control": 7,
        "resilience_ops": 8,
        "multi_cloud": 9,
        "multi_instance": 9,
        "model_provider": 8,
        "harness_runtime": 6,
        "agent_loop": 4,
        "context_strategy": 4,
        "memory_strategy": 4,
        "change_safety": 5,
        "registry_governance": 6,
        "knowledge_layer": 6,
        "quality_gate": 9,
        "gateway_strategy": 5,
        "secrets_integration": 5,
        "external_integration": 6,
        "governance_group": 2,
        "compliance_overlay": 12,
    },
}

_DOMAIN_HINTS: dict[str, tuple[str, ...]] = {
    "operating_model": (
        "operating model",
        "multi-harness",
        "single standard",
        "default harness",
        "exception path",
        "approved portfolio",
    ),
    "harness_family": (
        "saas",
        "custom harness",
        "framework",
        "managed runtime",
        "oss harness",
        "codex cli",
        "cursor",
        "copilot",
        "claude code",
    ),
    "execution_boundary": (
        "local",
        "container",
        "microvm",
        "remote execution",
        "on-prem",
        "air-gapped",
        "sandbox",
    ),
    "tool_governance": (
        "mcp",
        "tool gateway",
        "tool routing",
        "credential injection",
        "approved tools",
    ),
    "model_routing": (
        "model gateway",
        "bedrock",
        "openai",
        "anthropic",
        "model routing",
        "model tiering",
        "provider fallback",
    ),
    "identity_boundary": (
        "identity",
        "sso",
        "idp",
        "okta",
        "entra",
        "cognito",
        "iam",
    ),
    "population_policy": (
        "policy tier",
        "innovation lab",
        "contractor",
        "restricted",
        "population mapping",
        "exception registry",
    ),
    "surface_strategy": (
        "ide",
        "cli",
        "chat",
        "pr bot",
        "ci/cd",
        "jupyterlab",
        "notebook",
    ),
    "approval_posture": (
        "approval",
        "human review",
        "autonomous write",
        "dlp",
        "guardrail",
    ),
    "security_posture": (
        "threat model",
        "prompt injection",
        "attack surface",
        "mcp security",
    ),
    "audit_ops": (
        "audit",
        "observability",
        "siem",
        "trace",
        "tamper-evident",
    ),
    "cost_control": (
        "cost",
        "chargeback",
        "quota",
        "spend cap",
        "budget",
    ),
    "resilience_ops": (
        "outage",
        "fallback",
        "resilience",
        "circuit-breaker",
        "multi-region",
    ),
    "multi_cloud": (
        "multi-cloud",
        "azure",
        "gcp",
        "acquisition",
        "vertex ai",
    ),
    "multi_instance": (
        "multi-instance",
        "federated platform",
        "regional instances",
        "bu autonomy",
    ),
    "model_provider": (
        "provider",
        "bedrock",
        "openai",
        "anthropic",
        "self-hosted",
    ),
    "harness_runtime": (
        "runtime",
        "managed runtime",
        "saas product",
        "framework",
        "tool runtime",
    ),
    "agent_loop": (
        "agent loop",
        "multi-step",
        "termination",
        "checkpoint",
    ),
    "context_strategy": (
        "context",
        "compaction",
        "working set",
        "context window",
    ),
    "memory_strategy": (
        "memory",
        "cross-session",
        "preferences",
        "personalization",
    ),
    "change_safety": (
        "rollback",
        "revert",
        "diff",
        "change safety",
    ),
    "registry_governance": (
        "registry",
        "catalog",
        "mcp server",
        "skill library",
        "provenance",
    ),
    "knowledge_layer": (
        "knowledge layer",
        "rag",
        "code intelligence",
        "standards injection",
        "org knowledge",
    ),
    "quality_gate": (
        "eval",
        "quality gate",
        "capability evaluation",
        "safety-critical",
    ),
    "gateway_strategy": (
        "gateway",
        "broker",
        "chokepoint",
    ),
    "secrets_integration": (
        "vault",
        "cyberark",
        "pam",
        "credential injection",
    ),
    "external_integration": (
        "enterprise systems",
        "web browsing",
        "external search",
        "integrations",
    ),
    "governance_group": (
        "governance",
        "control plane",
        "shared controls",
    ),
    "compliance_overlay": (
        "hipaa",
        "phi",
        "itar",
        "ear",
        "cmmc",
        "sox",
        "gdpr",
        "works council",
        "govcloud",
    ),
}


@dataclass(frozen=True)
class TraversalFrontier:
    stage: str
    active_node_path: str
    candidate_paths: tuple[str, ...]
    loaded_node_paths: tuple[str, ...]
    relation_paths: dict[str, tuple[str, ...]] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()
    next_best_question: str = ""


def build_traversal_frontier(
    kb: KnowledgeBase,
    workspace: Mapping[str, object] | None,
    user_message: str,
    deterministic_guidance: Mapping[str, Any] | None = None,
) -> TraversalFrontier | None:
    workspace = workspace or {}
    prior_state = _prior_traversal_state(workspace)
    authoritative_guidance = deterministic_guidance if isinstance(deterministic_guidance, Mapping) else {}
    stage = _normalize_stage(str(workspace.get("stage") or prior_state.get("stage") or ""))
    signal_text = _workspace_signal_text(workspace, user_message)
    triggered_nodes = kb.conditional_nodes_for(signal_text)
    query_candidates = kb.query(signal_text, max_results=6)
    open_question_entries = _open_question_entries(workspace)
    open_question_text = " ".join(item["text"] for item in open_question_entries)
    open_question_candidates = kb.query(open_question_text, max_results=4) if open_question_text else []

    candidate_paths: list[str] = list(_DISCOVERY_ANCHORS)
    candidate_paths.extend(_state_paths(prior_state.get("selected_node_paths")))
    candidate_paths.extend(_state_paths(prior_state.get("candidate_paths")))
    candidate_paths.extend(_state_paths(prior_state.get("loaded_node_paths")))
    active_prior = prior_state.get("active_decision") if isinstance(prior_state.get("active_decision"), Mapping) else None
    if active_prior and isinstance(active_prior.get("path"), str):
        candidate_paths.append(active_prior["path"])
    preferred_active_path = _deterministic_active_path(workspace, authoritative_guidance)
    if preferred_active_path:
        candidate_paths.insert(0, preferred_active_path)
    candidate_paths.extend(_state_object_paths(prior_state.get("candidate_alternatives")))
    candidate_paths.extend(node.path for node in triggered_nodes)
    candidate_paths.extend(node.path for node in query_candidates)
    candidate_paths.extend(node.path for node in open_question_candidates)
    candidate_paths = list(dict.fromkeys(path for path in candidate_paths if kb.get(path)))

    if not candidate_paths:
        return None

    closed_domains = _closed_domains(workspace, prior_state, authoritative_guidance)
    resolved_domains = _resolved_domains(kb, workspace, prior_state, authoritative_guidance)
    triggered_path_set = {node.path for node in triggered_nodes}
    query_rank = {node.path: index for index, node in enumerate(query_candidates)}
    open_question_rank = {node.path: index for index, node in enumerate(open_question_candidates)}

    scored: list[tuple[float, KnowledgeNode, list[str]]] = []
    for path in candidate_paths:
        node = kb.get(path)
        if not node:
            continue
        if node.decision_domain and node.decision_domain in closed_domains:
            continue
        score, reasons = _score_node(
            node,
            signal_text=signal_text,
            open_question_text=open_question_text,
            stage=stage,
            resolved_domains=resolved_domains,
            triggered_path_set=triggered_path_set,
            query_rank=query_rank,
            open_question_rank=open_question_rank,
        )
        scored.append((score, node, reasons))

    if not scored:
        return None

    scored.sort(key=lambda item: (-item[0], item[1].path))
    if preferred_active_path:
        preferred = next((item for item in scored if item[1].path == preferred_active_path), None)
        if preferred is not None:
            scored = [preferred] + [item for item in scored if item[1].path != preferred_active_path]
    active_score, active_node, active_reasons = scored[0]
    _ = active_score
    packet_paths, relation_paths = _build_packet_paths(kb, active_node)
    active_reasons = list(active_reasons)
    if preferred_active_path and active_node.path == preferred_active_path:
        active_reasons.insert(0, "deterministic advisory slice is the current authority")
    next_best_question = _authoritative_next_best_question(workspace, active_node, authoritative_guidance)

    return TraversalFrontier(
        stage=stage,
        active_node_path=active_node.path,
        candidate_paths=tuple(node.path for _, node, _ in scored[:5]),
        loaded_node_paths=tuple(packet_paths),
        relation_paths={key: tuple(value) for key, value in relation_paths.items() if value},
        reasons=tuple(active_reasons[:5]),
        next_best_question=next_best_question,
    )


def build_traversal_state(
    kb: KnowledgeBase,
    workspace: Mapping[str, object] | None,
    user_message: str,
    deterministic_guidance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    workspace = workspace or {}
    prior_state = _prior_traversal_state(workspace)
    authoritative_guidance = deterministic_guidance if isinstance(deterministic_guidance, Mapping) else {}
    frontier = build_traversal_frontier(kb, workspace, user_message, authoritative_guidance)
    closed_domains = sorted(_closed_domains(workspace, prior_state, authoritative_guidance))
    resolved_domains = sorted(_resolved_domains(kb, workspace, prior_state, authoritative_guidance))
    if not frontier:
        return {
            "stage": _normalize_stage(str(workspace.get("stage") or "")),
            "closed_domains": closed_domains,
            "resolved_domains": resolved_domains,
            "active_decision": _authoritative_active_decision(workspace, authoritative_guidance),
            "loaded_node_paths": [],
            "candidate_paths": [],
            "candidate_alternatives": [],
            "inferred_decisions": [],
            "conflicts_detected": [],
            "next_best_question": _authoritative_next_best_question(workspace, None, authoritative_guidance),
            "candidate_options": [],
            "missing_evidence": _authoritative_missing_evidence(workspace, None, resolved_domains, authoritative_guidance),
        }

    active_node = kb.get(frontier.active_node_path)
    authoritative_active = _authoritative_active_decision(workspace, authoritative_guidance) or _node_summary(kb, active_node)
    selected_paths = _selected_node_paths(kb, workspace, active_node, prior_state, authoritative_guidance)
    selected_nodes = [kb.get(path) for path in selected_paths]
    selected_nodes = [node for node in selected_nodes if node is not None]

    alternatives = [_node_summary(kb, kb.get(path)) for path in frontier.relation_paths.get("alternatives", ()) if kb.get(path)]
    candidate_options = _authoritative_candidate_options(kb, frontier, active_node, authoritative_guidance)
    inferred = _build_inferred_decisions(kb, active_node, selected_paths, resolved_domains) if active_node else []
    conflicts = _detect_conflicts(kb, workspace, active_node, selected_nodes)
    missing_evidence = _authoritative_missing_evidence(workspace, active_node, resolved_domains, authoritative_guidance)

    return {
        "stage": frontier.stage,
        "closed_domains": closed_domains,
        "resolved_domains": resolved_domains,
        "active_decision": authoritative_active,
        "loaded_node_paths": list(frontier.loaded_node_paths),
        "candidate_paths": list(frontier.candidate_paths),
        "candidate_alternatives": alternatives,
        "candidate_options": candidate_options,
        "inferred_decisions": inferred,
        "conflicts_detected": conflicts,
        "missing_evidence": missing_evidence,
        "next_best_question": _authoritative_next_best_question(workspace, active_node, authoritative_guidance) or frontier.next_best_question,
        "reasons": list(frontier.reasons),
        "selected_node_paths": selected_paths,
    }


def render_traversal_context(
    kb: KnowledgeBase,
    frontier: TraversalFrontier,
    traversal_state: Mapping[str, Any] | None = None,
) -> str:
    active = kb.get(frontier.active_node_path)
    if not active:
        return ""

    lines: list[str] = [
        "## Decision Frontier",
        f"Stage: {frontier.stage}",
        f"Active node: {active.title} ({active.path})",
    ]
    if active.decision_domain:
        lines.append(f"Decision domain: {active.decision_domain}")
    if frontier.reasons:
        lines.append("Why this node is active now:")
        lines.extend(f"- {reason}" for reason in frontier.reasons)
    if frontier.next_best_question:
        lines.append(f"Next best question: {frontier.next_best_question}")
    if frontier.candidate_paths:
        lines.append("Candidate order:")
        for path in frontier.candidate_paths:
            node = kb.get(path)
            if not node:
                continue
            lines.append(f"- {node.title} ({path})")

    if traversal_state:
        inferred = traversal_state.get("inferred_decisions") or []
        conflicts = traversal_state.get("conflicts_detected") or []
        if inferred:
            lines.append("Implications already visible from this choice:")
            lines.extend(f"- {item['summary']}" for item in inferred[:4] if item.get("summary"))
        if conflicts:
            lines.append("Conflicts to challenge now:")
            lines.extend(f"- {item['summary']}" for item in conflicts[:3] if item.get("summary"))

    lines.extend(
        [
            "",
            "Use this packet as the primary decision context for the current turn.",
            "Only broaden beyond it when the current answer creates a new conflict, implication, or blocker.",
            "",
            "### Active Node Detail",
            _render_node_block(kb, active, heading_level=4, max_chars=2600),
        ]
    )

    for relation_name in ("requires", "implies", "alternatives", "conflicts_with", "exception_to"):
        relation_nodes = [kb.get(path) for path in frontier.relation_paths.get(relation_name, ())]
        relation_nodes = [node for node in relation_nodes if node is not None]
        if not relation_nodes:
            continue
        pretty_name = relation_name.replace("_", " ").title()
        lines.append(f"### {pretty_name}")
        for node in relation_nodes:
            lines.append(_render_node_block(kb, node, heading_level=4, max_chars=1200))

    supporting_paths = [
        path
        for path in frontier.loaded_node_paths
        if path != frontier.active_node_path
        and all(path not in paths for paths in frontier.relation_paths.values())
    ]
    if supporting_paths:
        lines.append("### Supporting Context")
        for path in supporting_paths:
            node = kb.get(path)
            if node:
                lines.append(_render_node_block(kb, node, heading_level=4, max_chars=800))

    return "\n".join(line for line in lines if line is not None).strip()


def _normalize_stage(stage: str) -> str:
    normalized = stage.strip().lower()
    if normalized in {"discovery", "solutioning", "blueprint"}:
        return normalized
    return "discovery"


def _normalize_operating_model(value: object) -> str:
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

    tokens = {token for token in normalized.split("_") if token}
    if {"single", "standard"} <= tokens or {"one", "standard"} <= tokens:
        return "single_standard"
    if "default" in tokens and ("exception" in tokens or "exceptions" in tokens):
        return "default_plus_exceptions"
    if (
        "multi" in tokens
        and "harness" in tokens
        and ("governed" in tokens or "portfolio" in tokens or "approved" in tokens)
    ):
        return "multi_harness_governed"

    return normalized


def _workspace_signal_text(workspace: Mapping[str, object], user_message: str) -> str:
    parts = [user_message]
    parts.extend(_confirmed_fact_texts(workspace))
    parts.extend(_open_question_texts(workspace))
    operating_model = str(workspace.get("operating_model") or "").strip()
    if operating_model:
        parts.append(operating_model)
    return "\n".join(parts).lower()


def _confirmed_target_state_signal_text(workspace: Mapping[str, object], active_node: KnowledgeNode | None = None) -> str:
    parts: list[str] = []
    parts.extend(_confirmed_fact_texts(workspace))
    recommendation = str(workspace.get("recommendation") or "").strip()
    if recommendation:
        parts.append(recommendation)
    parts.extend(_string_list(workspace.get("decisions")))
    operating_model = str(workspace.get("operating_model") or "").strip()
    if operating_model:
        parts.append(operating_model)
    if active_node:
        parts.append(active_node.title)
        parts.append(active_node.path)
    return "\n".join(parts).lower()


def _confirmed_fact_texts(workspace: Mapping[str, object]) -> list[str]:
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    structured = (
        traversal_state.get("customer_confirmed_facts")
        if isinstance(traversal_state.get("customer_confirmed_facts"), list)
        else traversal_state.get("structured_facts")
        if isinstance(traversal_state.get("structured_facts"), list)
        else []
    )
    texts: list[str] = []
    seen: set[str] = set()
    for item in structured:
        if not isinstance(item, Mapping):
            continue
        source = str(item.get("source") or "").strip().lower()
        if source and source not in _CONFIRMED_FACT_SOURCES:
            continue
        text = str(item.get("fact_text") or "").strip()
        if not text:
            key = str(item.get("key") or "").strip()
            value = item.get("value")
            if key and value not in (None, "", []):
                text = f"{key}: {value}"
        normalized = text.lower()
        if not text or normalized in seen:
            continue
        seen.add(normalized)
        texts.append(text)
    if texts:
        return texts
    return _string_list(workspace.get("facts"))


def _closed_domains(
    workspace: Mapping[str, object],
    prior_state: Mapping[str, object] | None = None,
    deterministic_guidance: Mapping[str, Any] | None = None,
) -> set[str]:
    closed: set[str] = set()
    guidance = deterministic_guidance if isinstance(deterministic_guidance, Mapping) else {}
    if prior_state:
        closed.update(str(item).strip() for item in _string_list(prior_state.get("closed_domains")) if str(item).strip())
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    closed.update(str(item).strip() for item in _string_list(traversal_state.get("closed_domains")) if str(item).strip())
    closed.update(str(item).strip() for item in _string_list(guidance.get("closed_domains")) if str(item).strip())
    return closed


def _deterministic_active_path(
    workspace: Mapping[str, object],
    deterministic_guidance: Mapping[str, Any] | None = None,
) -> str:
    guidance = deterministic_guidance if isinstance(deterministic_guidance, Mapping) else {}
    active_slice = guidance.get("active_slice") if isinstance(guidance.get("active_slice"), Mapping) else {}
    path = str(active_slice.get("path") or "").strip()
    if path:
        return path
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    prior_active = traversal_state.get("active_slice") if isinstance(traversal_state.get("active_slice"), Mapping) else {}
    return str(prior_active.get("path") or "").strip()


def _authoritative_active_decision(
    workspace: Mapping[str, object],
    deterministic_guidance: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    guidance = deterministic_guidance if isinstance(deterministic_guidance, Mapping) else {}
    active_slice = guidance.get("active_slice") if isinstance(guidance.get("active_slice"), Mapping) else None
    if active_slice:
        return dict(active_slice)
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    prior_active = traversal_state.get("active_slice") if isinstance(traversal_state.get("active_slice"), Mapping) else None
    if prior_active:
        return dict(prior_active)
    active_decision = traversal_state.get("active_decision") if isinstance(traversal_state.get("active_decision"), Mapping) else None
    if active_decision:
        return dict(active_decision)
    return None


def _resolved_domains(
    kb: KnowledgeBase,
    workspace: Mapping[str, object],
    prior_state: Mapping[str, object] | None = None,
    deterministic_guidance: Mapping[str, Any] | None = None,
) -> set[str]:
    resolved: set[str] = set()
    closed_domains = _closed_domains(workspace, prior_state, deterministic_guidance)
    resolved.update(closed_domains)
    if prior_state:
        resolved.update(str(item).strip() for item in _string_list(prior_state.get("resolved_domains")) if str(item).strip())
        for path in _state_paths(prior_state.get("selected_node_paths")):
            node = kb.get(path)
            if node and node.decision_domain:
                resolved.add(node.decision_domain)
    operating_model = _normalize_operating_model(workspace.get("operating_model"))
    if operating_model != "undecided":
        resolved.add("operating_model")

    decision_text = _confirmed_target_state_signal_text(workspace)
    normalized_decision_text = _normalize_matchable_text(decision_text)
    for domain, hints in _DOMAIN_HINTS.items():
        if domain in closed_domains:
            continue
        if any(_hint_matches_text(hint, normalized_decision_text) for hint in hints):
            resolved.add(domain)
    return resolved


def _score_node(
    node: KnowledgeNode,
    *,
    signal_text: str,
    open_question_text: str,
    stage: str,
    resolved_domains: set[str],
    triggered_path_set: set[str],
    query_rank: Mapping[str, int],
    open_question_rank: Mapping[str, int],
) -> tuple[float, list[str]]:
    score = float(node.priority)
    reasons: list[str] = []

    stage_weights = _STAGE_DOMAIN_WEIGHTS.get(stage, _STAGE_DOMAIN_WEIGHTS["discovery"])
    domain_weight = stage_weights.get(node.decision_domain, 0)
    if domain_weight:
        score += domain_weight
        reasons.append(f"{node.decision_domain} matters in {stage}")

    if node.blocking:
        score += 7
        reasons.append("marked as blocking")

    if node.path in triggered_path_set:
        score += 8
        reasons.append("explicitly triggered by current session signals")

    if node.path in query_rank:
        bonus = max(1, 5 - query_rank[node.path])
        score += bonus
        reasons.append("high-ranking text match for current context")

    if node.path in open_question_rank:
        bonus = max(2, 6 - open_question_rank[node.path])
        score += bonus
        reasons.append("aligned with an unresolved open question")

    if node.decision_domain and node.decision_domain not in resolved_domains:
        score += 4
        reasons.append("decision domain is still unresolved")
    elif node.decision_domain:
        score -= 3

    relation_count = len(node.edge_paths)
    if relation_count:
        score += min(relation_count, 6)
        reasons.append("high downstream fan-out")

    trigger_hits = _count_trigger_hits(node, signal_text)
    if trigger_hits:
        score += min(trigger_hits, 4)
        reasons.append("multiple signal matches point here")

    question_hits = _count_text_hits(node, open_question_text)
    if question_hits:
        score += min(question_hits, 3)

    if node.path in _DISCOVERY_ANCHORS:
        score += 1.5

    if node.decision_domain == "compliance_overlay" and _contains_compliance_signal(signal_text):
        score += 10
        reasons.append("explicit compliance signal is present")

    return score, reasons


def _count_trigger_hits(node: KnowledgeNode, signal_text: str) -> int:
    total = sum(1 for trigger in node.triggers if trigger and trigger in signal_text)
    total += sum(1 for trigger in node.trigger_pool if trigger and trigger in signal_text)
    total += sum(1 for signal in node.fit_signals if signal and signal in signal_text)
    return total


def _count_text_hits(node: KnowledgeNode, text: str) -> int:
    if not text:
        return 0
    combined_terms = [node.title.lower(), node.path.lower(), node.description.lower(), node.decision_question.lower()]
    return sum(1 for term in combined_terms if term and any(chunk in term or term in chunk for chunk in _text_chunks(text)))


def _text_chunks(text: str) -> list[str]:
    return [chunk for chunk in re.split(r"[\n,.!?;:]+", text.lower()) if chunk.strip()]


def _question_state_entries(workspace: Mapping[str, object]) -> list[dict[str, Any]]:
    value = workspace.get("question_state")
    entries: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            text = str(item.get("text") or item.get("question") or "").strip()
            if not text:
                continue
            entries.append(
                {
                    "id": str(item.get("id") or "").strip(),
                    "text": text,
                    "why_it_matters": str(item.get("why_it_matters") or "").strip(),
                    "decision_domain": str(item.get("decision_domain") or "").strip(),
                    "status": str(item.get("status") or "open").strip().lower() or "open",
                    "blocking": bool(item.get("blocking", True)),
                    "answer": str(item.get("answer") or "").strip(),
                }
            )
    if entries:
        return entries
    return [
        {
            "id": "",
            "text": text,
            "why_it_matters": "",
            "decision_domain": "",
            "status": "open",
            "blocking": True,
            "answer": "",
        }
        for text in _string_list(workspace.get("open_questions"))
    ]


def _open_question_entries(workspace: Mapping[str, object]) -> list[dict[str, Any]]:
    return [item for item in _question_state_entries(workspace) if item.get("status") == "open"]


def _open_question_texts(workspace: Mapping[str, object]) -> list[str]:
    return [item["text"] for item in _open_question_entries(workspace)]


def _build_candidate_options(
    kb: KnowledgeBase,
    frontier: TraversalFrontier,
    active_node: KnowledgeNode | None,
) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_option(path: str, position: str) -> None:
        if path in seen:
            return
        node = kb.get(path)
        summary = _node_summary(kb, node)
        if not summary:
            return
        options.append({**summary, "position": position})
        seen.add(path)

    if active_node is not None:
        add_option(active_node.path, "recommended")
    for path in frontier.candidate_paths:
        add_option(path, "viable")
    for path in frontier.relation_paths.get("alternatives", ()):
        add_option(path, "viable")
    return options


def _authoritative_candidate_options(
    kb: KnowledgeBase,
    frontier: TraversalFrontier,
    active_node: KnowledgeNode | None,
    deterministic_guidance: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    guidance = deterministic_guidance if isinstance(deterministic_guidance, Mapping) else {}
    candidate_options = guidance.get("candidate_options")
    if isinstance(candidate_options, list) and candidate_options:
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, item in enumerate(candidate_options):
            if not isinstance(item, Mapping):
                continue
            path = str(item.get("path") or "").strip()
            title = str(item.get("title") or "").strip()
            if not path or not title or path in seen:
                continue
            normalized.append(
                {
                    "path": path,
                    "title": title,
                    "summary": str(item.get("summary") or "").strip(),
                    "decision_domain": str(item.get("decision_domain") or "").strip(),
                    "position": str(item.get("position") or ("recommended" if index == 0 else "viable")).strip(),
                }
            )
            seen.add(path)
        if normalized:
            return normalized
    return _build_candidate_options(kb, frontier, active_node)


def _build_missing_evidence(
    workspace: Mapping[str, object],
    active_node: KnowledgeNode | None,
    resolved_domains: list[str],
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    open_entries = _prioritized_open_question_entries(workspace, active_node)
    relevant_domains = _related_question_domains(active_node)
    for item in open_entries:
        missing.append(
            {
                "question": item.get("text", ""),
                "decision_domain": item.get("decision_domain", ""),
                "why_it_matters": item.get("why_it_matters", ""),
                "blocking": bool(item.get("blocking", True)),
            }
        )
    if (
        active_node
        and active_node.decision_question
        and active_node.decision_domain not in resolved_domains
        and not any(str(item.get("decision_domain") or "").strip() in relevant_domains for item in open_entries)
    ):
        missing.insert(
            0,
            {
                "question": active_node.decision_question,
                "decision_domain": active_node.decision_domain,
                "why_it_matters": "This unresolved decision domain still materially changes the recommendation.",
                "blocking": True,
            }
        )
    return missing[:5]


def _authoritative_missing_evidence(
    workspace: Mapping[str, object],
    active_node: KnowledgeNode | None,
    resolved_domains: list[str],
    deterministic_guidance: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    guidance = deterministic_guidance if isinstance(deterministic_guidance, Mapping) else {}
    missing = guidance.get("missing_evidence")
    if isinstance(missing, list) and missing:
        normalized: list[dict[str, Any]] = []
        for item in missing:
            if not isinstance(item, Mapping):
                continue
            question = str(item.get("question") or item.get("text") or "").strip()
            if not question:
                continue
            normalized.append(
                {
                    "question": question,
                    "decision_domain": str(item.get("decision_domain") or "").strip(),
                    "why_it_matters": str(item.get("why_it_matters") or "").strip(),
                    "blocking": bool(item.get("blocking", True)),
                }
            )
        if normalized:
            return normalized[:5]
    return _build_missing_evidence(workspace, active_node, resolved_domains)


def _normalize_matchable_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _contains_compliance_signal(text: str) -> bool:
    normalized = _normalize_matchable_text(text)
    return any(_hint_matches_text(hint, normalized) for hint in _DOMAIN_HINTS["compliance_overlay"])


def _hint_matches_text(hint: str, normalized_text: str) -> bool:
    if not hint or not normalized_text:
        return False
    normalized_hint = _normalize_matchable_text(hint)
    if not normalized_hint:
        return False
    text_tokens = set(normalized_text.split())
    hint_tokens = normalized_hint.split()
    if len(hint_tokens) == 1:
        return hint_tokens[0] in text_tokens
    return normalized_hint in normalized_text


def _build_packet_paths(kb: KnowledgeBase, active_node: KnowledgeNode) -> tuple[list[str], dict[str, list[str]]]:
    max_packet_size = 6
    packet_paths: list[str] = [active_node.path]
    relation_paths: dict[str, list[str]] = {key: [] for key in ("requires", "implies", "alternatives", "conflicts_with", "exception_to")}

    def try_add(path: str, relation_name: str | None = None) -> bool:
        if len(packet_paths) >= max_packet_size:
            return False
        if not kb.get(path) or path in packet_paths:
            return True
        packet_paths.append(path)
        if relation_name:
            relation_paths[relation_name].append(path)
        return len(packet_paths) < max_packet_size

    for relation_name in ("requires", "implies", "alternatives", "conflicts_with", "exception_to"):
        relation_values = list(getattr(active_node, relation_name))
        if relation_values and not try_add(relation_values[0], relation_name):
            return packet_paths, relation_paths

    for relation_name in ("requires", "implies", "alternatives", "conflicts_with", "exception_to"):
        relation_values = list(getattr(active_node, relation_name))
        for path in relation_values[1:]:
            if not try_add(path, relation_name):
                return packet_paths, relation_paths

    for path in active_node.linked_paths:
        if not try_add(path):
            break
    return packet_paths, relation_paths


def _next_best_question(active_node: KnowledgeNode, workspace: Mapping[str, object]) -> str:
    prioritized = _prioritized_open_question_entries(workspace, active_node)
    relevant_domains = _related_question_domains(active_node)
    if active_node.decision_question:
        if prioritized and str(prioritized[0].get("decision_domain") or "").strip() in relevant_domains:
            return prioritized[0]["text"]
        if active_node.decision_domain and not any(
            str(item.get("decision_domain") or "").strip() in relevant_domains for item in prioritized
        ):
            return active_node.decision_question
        if prioritized:
            return prioritized[0]["text"]
        return active_node.decision_question
    if prioritized:
        return prioritized[0]["text"]
    return ""


def _authoritative_next_best_question(
    workspace: Mapping[str, object],
    active_node: KnowledgeNode | None,
    deterministic_guidance: Mapping[str, Any] | None,
) -> str:
    guidance = deterministic_guidance if isinstance(deterministic_guidance, Mapping) else {}
    question = str(guidance.get("next_best_question") or "").strip()
    if question:
        return question
    if active_node is not None:
        return _next_best_question(active_node, workspace)
    prioritized = _open_question_texts(workspace)
    return prioritized[0] if prioritized else ""


def _selected_node_paths(
    kb: KnowledgeBase,
    workspace: Mapping[str, object],
    active_node: KnowledgeNode | None,
    prior_state: Mapping[str, object] | None = None,
    deterministic_guidance: Mapping[str, Any] | None = None,
) -> list[str]:
    target_text = _confirmed_target_state_signal_text(workspace, active_node)
    selected = _state_paths((prior_state or {}).get("selected_node_paths"))
    preferred_active_path = _deterministic_active_path(workspace, deterministic_guidance)
    if preferred_active_path:
        selected.insert(0, preferred_active_path)
    if target_text.strip():
        selected.extend(node.path for node in kb.query(target_text, max_results=10))
    operating_model = _normalize_operating_model(workspace.get("operating_model"))
    if operating_model == "multi_harness_governed":
        selected.insert(0, "harness-selection/multi-harness-governance")
    elif operating_model == "single_standard":
        selected.insert(0, "harness-selection/saas-products")
    elif operating_model == "default_plus_exceptions":
        selected.insert(0, "harness-selection/multi-harness-governance")
    if active_node:
        selected.insert(0, active_node.path)
    return list(dict.fromkeys(path for path in selected if kb.get(path)))


def _build_inferred_decisions(
    kb: KnowledgeBase,
    active_node: KnowledgeNode | None,
    selected_paths: list[str],
    resolved_domains: list[str],
) -> list[dict[str, Any]]:
    if active_node is None:
        return []

    items: list[dict[str, Any]] = []
    for relation_name in ("requires", "implies"):
        for path in getattr(active_node, relation_name):
            node = kb.get(path)
            if node is None:
                continue
            status = "already_selected" if path in selected_paths or node.decision_domain in resolved_domains else "pending"
            action = "must also be resolved" if relation_name == "requires" else "now becomes decision-relevant"
            items.append(
                {
                    "path": node.path,
                    "title": node.title,
                    "relation": relation_name,
                    "status": status,
                    "summary": f"{active_node.title} {action}: {node.title}.",
                }
            )
    return items


def _detect_conflicts(
    kb: KnowledgeBase,
    workspace: Mapping[str, object],
    active_node: KnowledgeNode | None,
    selected_nodes: list[KnowledgeNode],
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    selected_by_path = {node.path: node for node in selected_nodes}

    for node in selected_nodes:
        for conflict_path in node.conflicts_with:
            other = selected_by_path.get(conflict_path)
            if other is None:
                continue
            pair_key = tuple(sorted((node.path, other.path)))
            if any(item.get("pair_key") == list(pair_key) for item in conflicts):
                continue
            conflicts.append(
                {
                    "pair_key": list(pair_key),
                    "paths": [node.path, other.path],
                    "summary": f"{node.title} conflicts with {other.title}; challenge whether both belong in the same target-state design.",
                    "type": "edge_conflict",
                }
            )

    operating_model = _normalize_operating_model(workspace.get("operating_model"))
    harness_family_nodes = [node for node in selected_nodes if node.decision_domain == "harness_family"]
    if operating_model == "single_standard" and len(harness_family_nodes) > 1:
        conflicts.append(
            {
                "paths": [node.path for node in harness_family_nodes],
                "summary": "The target state is marked single_standard, but multiple harness families are still selected in the recommendation context.",
                "type": "operating_model_conflict",
            }
        )

    if active_node and active_node.decision_domain == "compliance_overlay":
        for node in selected_nodes:
            if node.path == active_node.path:
                continue
            if node.decision_domain == "harness_family" and "saas" in node.path and operating_model == "single_standard":
                conflicts.append(
                    {
                        "paths": [active_node.path, node.path],
                        "summary": f"{active_node.title} may invalidate a default SaaS-only target state; confirm the compliance boundary before finalizing the harness recommendation.",
                        "type": "compliance_pressure",
                    }
                )
                break

    return conflicts



def _prior_traversal_state(workspace: Mapping[str, object]) -> Mapping[str, object]:
    value = workspace.get("traversal_state")
    return value if isinstance(value, Mapping) else {}


def _state_paths(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def _state_object_paths(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    paths: list[str] = []
    for item in value:
        if isinstance(item, Mapping) and isinstance(item.get("path"), str) and item.get("path").strip():
            paths.append(item["path"].strip())
    return paths

def _node_summary(kb: KnowledgeBase, node: KnowledgeNode | None) -> dict[str, Any] | None:
    if node is None:
        return None
    return {
        "path": node.path,
        "title": node.title,
        "decision_domain": node.decision_domain,
        "decision_question": node.decision_question,
        "description": node.description,
        "body_excerpt": _excerpt(kb.get_content(node), max_chars=420),
    }


def _render_node_block(kb: KnowledgeBase, node: KnowledgeNode, *, heading_level: int, max_chars: int) -> str:
    heading = "#" * max(heading_level, 1)
    lines = [f"{heading} {node.title} ({node.path})"]
    if node.description:
        lines.append(f"Summary: {node.description}")
    if node.decision_question:
        lines.append(f"Decision question: {node.decision_question}")
    excerpt = _excerpt(kb.get_content(node), max_chars=max_chars)
    if excerpt:
        lines.append(excerpt)
    return "\n".join(lines)


def _excerpt(content: str, *, max_chars: int) -> str:
    trimmed = content.strip()
    if not trimmed:
        return ""
    sources_index = trimmed.find("\n## Sources")
    if sources_index >= 0:
        trimmed = trimmed[:sources_index].rstrip()
    if len(trimmed) <= max_chars:
        return trimmed
    cut = trimmed[:max_chars].rsplit("\n", 1)[0].rstrip()
    return f"{cut}\n\n[Excerpt truncated for active packet focus]"


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _prioritized_open_question_entries(
    workspace: Mapping[str, object],
    active_node: KnowledgeNode | None,
) -> list[dict[str, Any]]:
    entries = _open_question_entries(workspace)
    if not active_node or not active_node.decision_domain:
        return entries

    relevant_domains = _related_question_domains(active_node)
    matching_domain = [
        item
        for item in entries
        if str(item.get("decision_domain") or "").strip() in relevant_domains
    ]
    blocking = [
        item
        for item in entries
        if str(item.get("decision_domain") or "").strip() not in relevant_domains and bool(item.get("blocking", True))
    ]
    remainder = [
        item
        for item in entries
        if str(item.get("decision_domain") or "").strip() not in relevant_domains and not bool(item.get("blocking", True))
    ]
    return matching_domain + blocking + remainder


def _related_question_domains(active_node: KnowledgeNode | None) -> set[str]:
    if not active_node or not active_node.decision_domain:
        return set()

    related = {active_node.decision_domain}
    if active_node.decision_domain == "operating_model":
        related.add("population_policy")
    if active_node.decision_domain == "compliance_overlay":
        related.update({"compliance_boundary", "execution_boundary"})
    if active_node.decision_domain == "execution_boundary":
        related.update({"compliance_boundary", "compliance_overlay"})
    return related
