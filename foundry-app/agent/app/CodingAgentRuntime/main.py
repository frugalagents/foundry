"""
Coding Agent Platform Advisor — Amazon Bedrock AgentCore Runtime.

Architecture:
  - BedrockAgentCoreApp entry point, one runtime per module
  - Strands Agent with coding-agent-advisor.md as system prompt
  - Knowledge base: OKF nodes loaded from knowledge/ folder
  - Tools: query_knowledge, update_architecture, save_session_note
  - AC Memory: STM for conversation continuity across invocations
  - SSE events: chat_stream (text), architecture_update (canvas), module_detected
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator, Mapping

import boto3
import jwt
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from jwt import PyJWKClient
from pydantic import BaseModel, Field
from strands import Agent, tool
from strands.models import BedrockModel

from architecture_case import build_architecture_case_payload
from architecture_spine import build_architecture_snapshot
from decision_spine import (
    build_turn_guidance,
    merge_guidance_into_traversal_state,
    render_turn_guidance_context,
)
from knowledge_loader import KnowledgeBase, load_knowledge_base
from okf_compiler import OKFCompileError, compile_okf_release
from store import (
    get_latest_architecture_case,
    get_latest_canvas_snapshot,
    get_recent_messages,
    get_workspace_snapshot,
    put_architecture_case_snapshot,
    put_canvas_snapshot,
    put_message,
    put_session_note,
    put_workspace_snapshot,
)
from traversal_engine import build_traversal_frontier, build_traversal_state, render_traversal_context
from workspace_state import build_workspace_state, reconcile_workspace_state

app = BedrockAgentCoreApp()
log = app.logger

# ── Config ────────────────────────────────────────────────────────────────────

_REGION    = os.environ.get("AWS_REGION", "us-east-1")
_MODEL_ID  = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
_TABLE     = os.environ.get("DYNAMODB_TABLE", "foundry-app-main")
_MEMORY_ID = os.environ.get("MEMORY_CODINGAGENTRUNTIMEMEMORY_ID", "")

# Midway / OIDC — identical env vars as the FastAPI backend
_MIDWAY_ISSUER   = os.environ.get("MIDWAY_ISSUER", "")
_OIDC_CLIENT_ID  = os.environ.get("OIDC_CLIENT_ID", "")
_TOKEN_HEADER    = "x-amzn-bedrock-agentcore-runtime-custom-cognito-id-token"

# Knowledge base is loaded once at cold-start
_KNOWLEDGE_DIR  = Path(__file__).parent / "knowledge"
_kb: KnowledgeBase | None = None
_okf_release_id = ""
_okf_contract_initialized = False


def _get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = load_knowledge_base(_KNOWLEDGE_DIR)
        log.info("Knowledge base loaded: %d nodes", len(_kb._nodes))
        _initialize_okf_contract(_kb)
    return _kb


def _okf_invalid_bypass_enabled() -> bool:
    value = str(os.environ.get("OKF_ALLOW_INVALID", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _initialize_okf_contract(kb: KnowledgeBase) -> None:
    global _okf_release_id, _okf_contract_initialized
    if _okf_contract_initialized:
        return
    _okf_contract_initialized = True

    release = None
    try:
        release = compile_okf_release(_KNOWLEDGE_DIR)
    except OKFCompileError as exc:
        if _okf_invalid_bypass_enabled():
            _okf_release_id = "invalid:bypass"
            log.warning(
                "OKF contract gate bypassed via OKF_ALLOW_INVALID with %d issue(s): %s",
                len(exc.issues),
                exc,
            )
            return
        _okf_contract_initialized = False
        raise RuntimeError(
            f"OKF contract initialization failed with {len(exc.issues)} issue(s): {exc}"
        ) from exc

    _okf_release_id = f"{release.manifest.schema_version}:{release.manifest.graph_sha256[:12]}"
    log.info(
        "OKF contract compiled: nodes=%d advisory_slices=%d typed_edges=%d release=%s",
        release.manifest.node_count,
        release.manifest.advisory_slice_count,
        release.manifest.typed_edge_count,
        _okf_release_id,
    )


# ── System prompt ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_system_prompt() -> str:
    # The skill file lives two levels up from the runtime package
    skill_path = Path(__file__).parent / "coding-agent-advisor.md"
    if skill_path.exists():
        raw = skill_path.read_text(encoding="utf-8")
        # Strip YAML front-matter (--- ... ---)
        if raw.startswith("---"):
            end = raw.index("---", 3)
            raw = raw[end + 3:].lstrip()
        return raw

    log.warning("coding-agent-advisor.md not found at %s", skill_path)
    return (
        "You are the Coding Agent Platform Advisor. "
        "Help enterprise leaders design and deploy a coding agent platform."
    )


def augment_system_prompt_with_conditional_knowledge(
    base_prompt: str, kb: KnowledgeBase, user_message: str
) -> str:
    """Auto-load OKF nodes whose signal keywords appear in the user's message.

    The skill file documents a three-tier traversal model (mandate/conditional/
    probe) where conditional nodes should load automatically when a matching
    signal appears in discovery — this is the wiring that makes that automatic,
    rather than relying on the model to guess the right query_knowledge keywords.
    """
    nodes = kb.conditional_nodes_for(user_message)
    if not nodes:
        return base_prompt
    log.info("Conditional knowledge triggered: %s", [n.path for n in nodes])
    block = "\n\n---\n\n".join(
        f"### {n.title} ({n.path})\n\n{_node_body(kb, n)}" for n in nodes
    )
    related = kb.related_nodes_for([n.path for n in nodes], max_results=6)
    related_block = ""
    if related:
        bullets = "\n".join(
            f"- `{n.path}` — {n.decision_question or n.title}"
            for n in related
        )
        related_block = (
            "\n\n## Graph Follow-On Nodes To Consider Next\n\n"
            f"{bullets}"
        )
    return (
        f"{base_prompt}\n\n"
        f"## Signals Detected This Turn — Relevant Knowledge Already Loaded\n\n{block}"
        f"{related_block}"
    )


def augment_system_prompt_with_traversal_context(
    base_prompt: str,
    kb: KnowledgeBase,
    user_message: str,
    workspace: Mapping[str, Any] | None,
) -> str:
    guidance = build_turn_guidance(kb, workspace, user_message)
    frontier = build_traversal_frontier(kb, workspace, user_message, guidance)
    if not frontier:
        fallback = augment_system_prompt_with_conditional_knowledge(base_prompt, kb, user_message)
        guidance_block = render_turn_guidance_context(guidance)
        return f"{fallback}\n\n{guidance_block}".strip() if guidance_block else fallback

    traversal_state = build_traversal_state(kb, workspace, user_message, guidance)
    traversal_state = merge_guidance_into_traversal_state(traversal_state, guidance)
    log.info(
        "Traversal frontier: active=%s loaded=%s",
        frontier.active_node_path,
        list(frontier.loaded_node_paths),
    )
    context_block = render_traversal_context(kb, frontier, traversal_state)
    guidance_block = render_turn_guidance_context(guidance)
    if not context_block:
        fallback = augment_system_prompt_with_conditional_knowledge(base_prompt, kb, user_message)
        return f"{fallback}\n\n{guidance_block}".strip() if guidance_block else fallback
    if guidance_block:
        return f"{base_prompt}\n\n{guidance_block}\n\n{context_block}"
    return f"{base_prompt}\n\n{context_block}"


def _node_body(kb: KnowledgeBase, node) -> str:
    content = getattr(node, "content", "")
    if content:
        return content
    if hasattr(kb, "get_content"):
        return kb.get_content(node)
    return content


# ── Auth ──────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient | None:
    if not _MIDWAY_ISSUER:
        return None
    return PyJWKClient(f"{_MIDWAY_ISSUER}/.well-known/jwks.json")


def _verify_token(context) -> str | None:
    """Verify the forwarded Midway token and return the actor_id (sub)."""
    headers = getattr(context, "request_headers", {}) or {}
    token = next(
        (v for k, v in headers.items() if k.lower() == _TOKEN_HEADER),
        None,
    )
    if not token:
        return None

    jwk = _jwk_client()
    if not jwk:
        # Dev mode — no Midway configured, accept any token
        try:
            import base64
            parts = token.split(".")
            padding = "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
            return claims.get("sub")
        except Exception:
            return None

    try:
        signing_key = jwk.get_signing_key_from_jwt(token)
        options: dict = {"require": ["exp", "iat", "sub"]}
        kwargs: dict = {"algorithms": ["RS256"], "issuer": _MIDWAY_ISSUER, "options": options}
        if _OIDC_CLIENT_ID:
            kwargs["audience"] = _OIDC_CLIENT_ID
        else:
            options["verify_aud"] = False
        claims = jwt.decode(token, signing_key.key, **kwargs)
        return claims.get("sub")
    except jwt.PyJWTError as exc:
        log.warning("Rejected token: %s", type(exc).__name__)
        return None


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _chat_stream(text: str) -> str:
    return f"data: {json.dumps({'type': 'chat_stream', 'data': {'text': text}})}\n\n"


def _architecture_event(
    nodes: list,
    edges: list,
    stage: str = "",
    baseline_node_ids: list[str] | None = None,
    architecture_artifact: dict | None = None,
) -> str:
    return f"data: {json.dumps({'type': 'architecture_update', 'data': {'stage': stage, 'nodes': nodes, 'edges': edges, 'baseline_node_ids': baseline_node_ids or [], 'architecture_artifact': architecture_artifact or None}})}\n\n"


def _module_detected_event(module: str) -> str:
    return f"data: {json.dumps({'type': 'module_detected', 'data': {'module': module}})}\n\n"


def _project_workspace_from_architecture_case(
    workspace: Mapping[str, Any] | None,
    architecture_case: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(workspace or {})
    case = architecture_case if isinstance(architecture_case, Mapping) else {}
    if not case:
        return payload

    artifacts = case.get("artifacts") if isinstance(case.get("artifacts"), Mapping) else {}
    facts = case.get("facts") if isinstance(case.get("facts"), list) else []
    questions = case.get("open_questions") if isinstance(case.get("open_questions"), list) else []
    decisions = case.get("decisions") if isinstance(case.get("decisions"), list) else []
    risks = case.get("risks") if isinstance(case.get("risks"), list) else []

    payload["stage"] = str(case.get("stage") or "").strip()
    payload["recommendation"] = str(case.get("current_recommendation") or "").strip()
    payload["blueprint_markdown"] = str(artifacts.get("blueprint_markdown") or "").strip()
    payload["operating_model"] = str(case.get("operating_model") or "").strip()

    projected_facts = [
        str(item.get("statement") or "").strip()
        for item in facts
        if isinstance(item, Mapping) and str(item.get("statement") or "").strip()
    ]
    payload["facts"] = projected_facts

    projected_questions = [
        {
            "id": str(item.get("id") or "").strip(),
            "text": str(item.get("text") or "").strip(),
            "why_it_matters": str(item.get("why_it_matters") or "").strip(),
            "blocking": bool(item.get("blocking", True)),
            "decision_domain": str(item.get("decision_domain") or "").strip(),
            "status": str(item.get("status") or "open").strip() or "open",
            "answer": str(item.get("answer") or "").strip(),
            "source": str(item.get("source") or "engine").strip() or "engine",
        }
        for item in questions
        if isinstance(item, Mapping) and str(item.get("text") or "").strip()
    ]
    payload["question_state"] = projected_questions
    payload["open_questions"] = [
        item["text"]
        for item in projected_questions
        if item["status"] == "open"
    ]

    projected_decisions = [
        str(item.get("statement") or "").strip()
        for item in decisions
        if isinstance(item, Mapping) and str(item.get("statement") or "").strip()
    ]
    payload["decisions"] = projected_decisions

    projected_risks = [
        str(item.get("risk") or "").strip()
        for item in risks
        if isinstance(item, Mapping) and str(item.get("risk") or "").strip()
    ]
    payload["risks"] = projected_risks

    return payload


def _workspace_event(workspace: dict, architecture_case: dict | None = None) -> str:
    payload = _project_workspace_from_architecture_case(workspace, architecture_case)
    if architecture_case:
        payload["architecture_case"] = architecture_case
    return f"data: {json.dumps({'type': 'workspace_update', 'data': payload})}\n\n"


def _complete_event(session_id: str) -> str:
    return f"data: {json.dumps({'type': 'complete', 'data': {'session_id': session_id}})}\n\ndata: [DONE]\n\n"


def _error_event(message: str) -> str:
    return f"data: {json.dumps({'type': 'error', 'data': {'message': message}})}\n\n"


# ── Stream merge ──────────────────────────────────────────────────────────────

def _text_from_strands_event(ev) -> str | None:
    if isinstance(ev, dict):
        text = ev.get("data", "")
        return text if isinstance(text, str) and text else None
    if isinstance(ev, str) and ev:
        return ev
    if hasattr(ev, "delta") and hasattr(ev.delta, "text") and ev.delta.text:
        return ev.delta.text
    return None


class RecoveredWorkspaceArtifacts(BaseModel):
    recommendation: str = ""
    blueprint_markdown: str = ""
    open_questions: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    implementation_plan: list[str] = Field(default_factory=list)


def _normalize_question_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lstrip("-*0123456789. ")).strip()


def _extract_open_questions_from_text(content: str) -> list[str]:
    questions: list[str] = []
    for raw_line in content.splitlines():
        line = _normalize_question_line(raw_line)
        if not line or "?" not in line:
            continue
        last_question_mark = line.rfind("?")
        question = line[: last_question_mark + 1].strip()
        if question and question not in questions:
            questions.append(question)
    return questions


def _has_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(_has_content(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_content(item) for item in value)
    return bool(value)


def _is_explicit_blueprint_request(user_message: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_message.lower()).strip()
    phrases = (
        "generate blueprint",
        "create blueprint",
        "produce blueprint",
        "build blueprint",
        "finalize blueprint",
        "show blueprint",
        "publish blueprint",
        "technical blueprint",
    )
    return any(phrase in normalized for phrase in phrases)


def _is_explicit_finalization_request(user_message: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_message.lower()).strip()
    phrases = (
        "finalize",
        "finalise",
        "complete brief",
        "complete blueprint",
        "lock the architecture",
        "no open questions",
        "ready to build",
        "end this session with",
    )
    return any(phrase in normalized for phrase in phrases)


def _should_recover_blueprint(user_message: str, workspace: Mapping[str, Any]) -> bool:
    if _has_content(workspace.get("blueprint_markdown")):
        return False
    if _is_explicit_blueprint_request(user_message):
        return True
    if _is_explicit_finalization_request(user_message):
        return True
    if workspace.get("open_questions"):
        return False
    return (
        _has_content(workspace.get("recommendation"))
        and (
            _has_content(workspace.get("implementation_plan"))
            or _has_content(workspace.get("decisions"))
        )
        and (
            _has_content(workspace.get("facts"))
            or _has_content(workspace.get("risks"))
            or _has_content(workspace.get("assumptions"))
        )
    )


def _format_json_block(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _normalized_architecture_case_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    normalized = json.loads(json.dumps(payload, sort_keys=True))
    if isinstance(normalized, dict):
        normalized.pop("revision", None)
    return normalized


def _build_architecture_case_candidate(
    *,
    customer_id: str,
    session_id: str,
    workspace: Mapping[str, Any] | None,
    canvas_snapshot: Mapping[str, Any] | None,
    revision: int | None = None,
) -> dict[str, Any]:
    latest_case = get_latest_architecture_case(customer_id, session_id) or {}
    latest_revision = int(latest_case.get("revision") or 0) if isinstance(latest_case, Mapping) else 0
    next_revision = revision if revision is not None else (latest_revision + 1 if latest_revision else 1)
    return build_architecture_case_payload(
        case_id=f"{customer_id}/{session_id}",
        revision=max(1, int(next_revision)),
        okf_release_id=_okf_release_id,
        workspace=workspace,
        canvas_snapshot=_normalize_canvas_snapshot(canvas_snapshot),
    )


def _persist_architecture_case_shadow(
    *,
    customer_id: str,
    session_id: str,
    workspace: Mapping[str, Any] | None,
    canvas_snapshot: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not customer_id or not session_id:
        return None
    if not _has_content(workspace) and not _has_content(canvas_snapshot):
        return None

    latest_case = get_latest_architecture_case(customer_id, session_id) or {}
    latest_revision = int(latest_case.get("revision") or 0) if isinstance(latest_case, Mapping) else 0
    base_revision = max(1, latest_revision or 1)
    candidate = _build_architecture_case_candidate(
        customer_id=customer_id,
        session_id=session_id,
        workspace=workspace,
        canvas_snapshot=canvas_snapshot,
        revision=base_revision,
    )

    if _normalized_architecture_case_payload(candidate) == _normalized_architecture_case_payload(latest_case):
        return dict(latest_case) if isinstance(latest_case, Mapping) else candidate

    next_revision = latest_revision + 1 if latest_revision else 1
    if next_revision != base_revision:
        candidate = _build_architecture_case_candidate(
            customer_id=customer_id,
            session_id=session_id,
            workspace=workspace,
            canvas_snapshot=canvas_snapshot,
            revision=next_revision,
        )

    put_architecture_case_snapshot(customer_id, session_id, candidate)
    return candidate


def _persist_workspace_and_case(
    *,
    customer_id: str,
    session_id: str,
    workspace: Mapping[str, Any],
    canvas_snapshot: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    architecture_case_payload = _persist_architecture_case_shadow(
        customer_id=customer_id,
        session_id=session_id,
        workspace=workspace,
        canvas_snapshot=canvas_snapshot,
    )
    projected = _project_workspace_from_architecture_case(workspace, architecture_case_payload)
    put_workspace_snapshot(
        customer_id,
        session_id,
        stage=str(projected.get("stage") or workspace.get("stage") or "").strip(),
        recommendation=str(projected.get("recommendation") or workspace.get("recommendation") or "").strip(),
        blueprint_markdown=str(projected.get("blueprint_markdown") or workspace.get("blueprint_markdown") or "").strip(),
        assumptions=workspace.get("assumptions"),
        facts=projected.get("facts") if isinstance(projected.get("facts"), list) else workspace.get("facts"),
        operating_model=str(projected.get("operating_model") or workspace.get("operating_model") or "").strip(),
        question_state=projected.get("question_state") if isinstance(projected.get("question_state"), list) else workspace.get("question_state"),
        open_questions=projected.get("open_questions") if isinstance(projected.get("open_questions"), list) else workspace.get("open_questions"),
        decisions=projected.get("decisions") if isinstance(projected.get("decisions"), list) else workspace.get("decisions"),
        risks=projected.get("risks") if isinstance(projected.get("risks"), list) else workspace.get("risks"),
        implementation_plan=workspace.get("implementation_plan"),
        advisory_case=workspace.get("advisory_case"),
        recommendation_state=workspace.get("recommendation_state"),
        artifact_status=workspace.get("artifact_status"),
        traversal_state=workspace.get("traversal_state"),
    )
    return architecture_case_payload


def _explicit_blueprint_request_instructions() -> str:
    return """
## Explicit Blueprint Request

The customer explicitly asked for the technical blueprint in this turn.
If the architecture is coherent enough to defend, you must publish the artifact
through `update_consulting_state` with a non-empty `blueprint_markdown`.
If one or two blockers remain, still publish the current best technical
blueprint with clear `[TBD]` markers for unresolved items and keep only those
blockers in `open_questions`.
Keep the chat reply to one short sentence after the workspace update.
"""


def _explicit_finalization_request_instructions() -> str:
    return """
## Explicit Finalization Request

The customer is asking you to finalize the session into a build-ready outcome.
Before you finish:
- close, explicitly defer, or convert any remaining blocker into a named conditional branch in `question_state`
- publish a non-empty `blueprint_markdown`
- refresh `recommendation`, `decisions`, `risks`, and `implementation_plan`
- ensure the final recommendation is customer-specific, not a generic principle
- move to `stage=blueprint` when the blueprint is non-empty and the remaining gap is captured as a bounded conditional branch or deferred dependency

If one risk or dependency still remains, keep it in `risks` or mark it `[TBD]`
in the blueprint instead of leaving the session half-finished.
"""


async def _recover_workspace_after_stream(
    *,
    user_message: str,
    reply_text: str,
    customer_id: str,
    session_id: str,
) -> dict[str, Any] | None:
    if not customer_id or not session_id:
        return None

    existing = get_workspace_snapshot(customer_id, session_id) or {}
    if not existing:
        return None

    updates: dict[str, Any] = {}
    if not existing.get("open_questions"):
        recovered_questions = _extract_open_questions_from_text(reply_text)
        if recovered_questions:
            updates["open_questions"] = recovered_questions

    if _should_recover_blueprint(user_message, existing):
        recent_messages = get_recent_messages(customer_id, session_id, limit=12)
        latest_canvas = get_latest_canvas_snapshot(customer_id, session_id)
        recovery_agent = Agent(
            model=BedrockModel(model_id=_MODEL_ID),
            system_prompt=(
                "You repair missing consulting workspace artifacts for a coding-agent "
                "platform advisory session. Use only the supplied workspace, architecture, "
                "and transcript context. Do not invent customer facts. If an item is still "
                "unresolved, keep it as [TBD] in the blueprint and preserve it in open_questions. "
                "If the session is otherwise coherent, publish a conditional blueprint instead of stalling. "
                "Return a detailed technical blueprint artifact, not an executive memo. "
                "The blueprint must use markdown with `##` section headers and include: "
                "Architecture, Architecture Decisions, Rollout Phases, Key Tradeoffs Accepted, "
                "Escalations Required Before Build, and Org Readiness - Non-Platform Actions."
            ),
        )
        recovery_prompt = f"""Customer turn:
{user_message}

Latest agent reply:
{reply_text}

Current workspace:
{_format_json_block(existing)}

Latest architecture snapshot:
{_format_json_block(latest_canvas or {})}

Recent transcript:
{_format_json_block(recent_messages)}

Return the refreshed recommendation, blueprint_markdown, open_questions, decisions, risks, and implementation_plan. Only include true blockers in open_questions. Keep recommendation to at most 3 sentences.
"""
        try:
            repaired = await recovery_agent.structured_output_async(RecoveredWorkspaceArtifacts, recovery_prompt)
        except Exception:
            log.exception("Failed to recover missing blueprint workspace artifact")
            repaired = None

        if repaired is not None:
            if repaired.recommendation.strip():
                updates["recommendation"] = repaired.recommendation.strip()
            if repaired.blueprint_markdown.strip():
                updates["blueprint_markdown"] = repaired.blueprint_markdown.strip()
            if repaired.decisions:
                updates["decisions"] = repaired.decisions
            if repaired.risks:
                updates["risks"] = repaired.risks
            if repaired.implementation_plan:
                updates["implementation_plan"] = repaired.implementation_plan
            if repaired.open_questions or _is_explicit_finalization_request(user_message):
                updates["open_questions"] = repaired.open_questions

    if "open_questions" in updates:
        for field in (
            "recommendation",
            "decisions",
            "risks",
            "implementation_plan",
            "blueprint_markdown",
            "advisory_case",
        ):
            if field not in updates and _has_content(existing.get(field)):
                updates[field] = existing[field]
    elif "recommendation" in updates:
        for field in ("blueprint_markdown", "advisory_case"):
            if field not in updates and _has_content(existing.get(field)):
                updates[field] = existing[field]

    if not updates:
        return None

    stage = existing.get("stage", "")
    if updates.get("blueprint_markdown"):
        stage = "blueprint"
    elif updates.get("open_questions") and stage == "":
        stage = "discovery"

    workspace, invalidated_fields, reasoning_changes = build_workspace_state(
        existing,
        recommendation=updates.get("recommendation"),
        blueprint_markdown=updates.get("blueprint_markdown"),
        open_questions=updates.get("open_questions"),
        decisions=updates.get("decisions"),
        risks=updates.get("risks"),
        implementation_plan=updates.get("implementation_plan"),
        advisory_case=updates.get("advisory_case"),
        stage=stage,
    )
    workspace = _apply_traversal_state(kb, workspace, user_message)
    workspace = _finalize_workspace_state(
        workspace,
        invalidated_fields=invalidated_fields,
        reasoning_changes=reasoning_changes,
    )
    latest_canvas = get_latest_canvas_snapshot(customer_id, session_id)
    _persist_workspace_and_case(
        customer_id=customer_id,
        session_id=session_id,
        workspace=workspace,
        canvas_snapshot=latest_canvas,
    )
    return workspace


def _apply_traversal_state(
    kb: KnowledgeBase,
    workspace: dict[str, Any],
    user_message: str,
    guidance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    traversal_state = build_traversal_state(kb, workspace, user_message, guidance)
    workspace["traversal_state"] = merge_guidance_into_traversal_state(traversal_state, guidance)
    return workspace


def _merge_text_lists(existing: list[str], derived: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in existing + derived:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(text)
    return merged


def _workspace_changed(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    tracked_fields = (
        "stage",
        "recommendation",
        "blueprint_markdown",
        "assumptions",
        "facts",
        "operating_model",
        "question_state",
        "open_questions",
        "decisions",
        "risks",
        "implementation_plan",
        "advisory_case",
        "recommendation_state",
        "artifact_status",
        "traversal_state",
    )
    return any(previous.get(field) != current.get(field) for field in tracked_fields)


def _normalize_canvas_snapshot(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    snapshot = snapshot or {}
    return {
        "stage": str(snapshot.get("stage") or ""),
        "nodes": snapshot.get("nodes") if isinstance(snapshot.get("nodes"), list) else [],
        "edges": snapshot.get("edges") if isinstance(snapshot.get("edges"), list) else [],
        "baseline_node_ids": snapshot.get("baseline_node_ids") if isinstance(snapshot.get("baseline_node_ids"), list) else [],
        "architecture_artifact": snapshot.get("architecture_artifact") if isinstance(snapshot.get("architecture_artifact"), Mapping) else None,
    }


def _architecture_snapshot_changed(previous: Mapping[str, Any] | None, current: Mapping[str, Any] | None) -> bool:
    return _normalize_canvas_snapshot(previous) != _normalize_canvas_snapshot(current)


def _canvas_concreteness_score(snapshot: Mapping[str, Any] | None) -> float:
    normalized = _normalize_canvas_snapshot(snapshot)
    nodes = normalized.get("nodes") if isinstance(normalized.get("nodes"), list) else []
    artifact = normalized.get("architecture_artifact") if isinstance(normalized.get("architecture_artifact"), Mapping) else {}
    score = 0.0

    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        label = str(node.get("label") or "").strip()
        sublabel = str(node.get("sublabel") or "").strip()
        kind = str(node.get("kind") or "").strip()
        path_role = str(node.get("path_role") or "").strip()
        combined = f"{label} {sublabel}".lower()

        if label:
            score += 1.0
        if "[tbd]" not in combined:
            score += 1.5
        if not any(
            marker in combined
            for marker in (
                "target-state harness policy",
                "default harness lane",
                "approved model route",
                "under review",
            )
        ):
            score += 1.0
        if kind in {"interactive_harness", "agent_runtime", "model_gateway", "model_provider", "tool_gateway"}:
            score += 1.0
        if path_role == "supporting":
            score += 0.5

    if isinstance(artifact.get("customizations"), list):
        score += len(artifact.get("customizations") or []) * 0.5
    if isinstance(artifact.get("supporting_lanes"), list):
        score += len(artifact.get("supporting_lanes") or []) * 0.5
    if isinstance(artifact.get("decisions"), list):
        score += len(artifact.get("decisions") or []) * 0.25

    return score


def _canvas_placeholder_count(snapshot: Mapping[str, Any] | None) -> int:
    normalized = _normalize_canvas_snapshot(snapshot)
    nodes = normalized.get("nodes") if isinstance(normalized.get("nodes"), list) else []
    placeholders = 0
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        label = str(node.get("label") or "").strip().lower()
        sublabel = str(node.get("sublabel") or "").strip().lower()
        if "[tbd]" in label or "[tbd]" in sublabel:
            placeholders += 1
    return placeholders


def _specific_harness_count(snapshot: Mapping[str, Any] | None) -> int:
    normalized = _normalize_canvas_snapshot(snapshot)
    nodes = normalized.get("nodes") if isinstance(normalized.get("nodes"), list) else []
    count = 0
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        label = str(node.get("label") or "").strip().lower()
        kind = str(node.get("kind") or "").strip()
        layer = str(node.get("layer") or "").strip()
        if layer != "harness" and kind != "interactive_harness":
            continue
        if "[tbd]" in label:
            continue
        if label in {"single standard harness", "governed harness portfolio"}:
            continue
        count += 1
    return count


def _prefer_existing_canvas(
    existing_canvas: Mapping[str, Any] | None,
    candidate_canvas: Mapping[str, Any] | None,
) -> bool:
    existing = _normalize_canvas_snapshot(existing_canvas)
    candidate = _normalize_canvas_snapshot(candidate_canvas)
    existing_nodes = existing.get("nodes") if isinstance(existing.get("nodes"), list) else []
    candidate_nodes = candidate.get("nodes") if isinstance(candidate.get("nodes"), list) else []

    if not existing_nodes or not candidate_nodes:
        return False

    existing_score = _canvas_concreteness_score(existing)
    candidate_score = _canvas_concreteness_score(candidate)
    existing_placeholders = _canvas_placeholder_count(existing)
    candidate_placeholders = _canvas_placeholder_count(candidate)
    existing_specific_harnesses = _specific_harness_count(existing)
    candidate_specific_harnesses = _specific_harness_count(candidate)
    if existing_specific_harnesses >= 2 and existing_specific_harnesses > candidate_specific_harnesses:
        return True
    if existing_specific_harnesses > candidate_specific_harnesses and existing_score >= candidate_score - 1.0:
        return True
    if candidate_placeholders > 0 and existing_specific_harnesses > candidate_specific_harnesses:
        return True
    if candidate_placeholders > existing_placeholders and existing_score >= candidate_score:
        return True
    return existing_score > candidate_score + 2.0 and len(existing_nodes) >= len(candidate_nodes)


def _merge_canvas_semantics(
    existing_canvas: Mapping[str, Any] | None,
    candidate_canvas: Mapping[str, Any] | None,
) -> dict[str, Any]:
    existing = _normalize_canvas_snapshot(existing_canvas)
    candidate = _normalize_canvas_snapshot(candidate_canvas)
    if not existing.get("nodes"):
        return candidate
    if not candidate.get("nodes"):
        return existing
    return {
        "stage": str(candidate.get("stage") or existing.get("stage") or ""),
        "nodes": existing.get("nodes", []),
        "edges": existing.get("edges", []),
        "baseline_node_ids": existing.get("baseline_node_ids", []),
        "architecture_artifact": candidate.get("architecture_artifact") or existing.get("architecture_artifact"),
    }


def _prepare_workspace_for_turn(
    kb: KnowledgeBase,
    existing_workspace: Mapping[str, Any] | None,
    user_message: str,
) -> tuple[dict[str, Any], bool]:
    existing_workspace = dict(existing_workspace or {})
    guidance = build_turn_guidance(kb, existing_workspace, user_message)
    if not any(
        (
            guidance.get("facts"),
            guidance.get("question_state"),
            guidance.get("risks"),
            guidance.get("recommendation"),
            guidance.get("decisions"),
        )
    ):
        workspace = dict(existing_workspace)
        if workspace:
            workspace = _apply_traversal_state(kb, workspace, user_message, guidance=guidance)
            workspace = _finalize_workspace_state(workspace)
        return workspace, False

    workspace, invalidated_fields, reasoning_changes = build_workspace_state(
        existing_workspace,
        recommendation=str(guidance.get("recommendation") or "").strip() or None,
        facts=guidance.get("facts"),
        operating_model=guidance.get("operating_model"),
        question_state=guidance.get("question_state"),
        decisions=guidance.get("decisions") or None,
        risks=guidance.get("risks") or None,
        stage=str(existing_workspace.get("stage") or ""),
    )
    workspace = _apply_traversal_state(kb, workspace, user_message, guidance=guidance)
    workspace = _finalize_workspace_state(
        workspace,
        invalidated_fields=invalidated_fields,
        reasoning_changes=reasoning_changes,
    )
    return workspace, _workspace_changed(existing_workspace, workspace)


def _maybe_emit_engine_architecture(
    *,
    workspace: Mapping[str, Any],
    panel_queue: asyncio.Queue[str],
    customer_id: str,
    session_id: str,
    existing_canvas: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    snapshot = build_architecture_snapshot(workspace)
    normalized_existing = _normalize_canvas_snapshot(existing_canvas)

    if snapshot is None:
        return normalized_existing if normalized_existing.get("nodes") else None
    if _prefer_existing_canvas(normalized_existing, snapshot):
        snapshot = _merge_canvas_semantics(normalized_existing, snapshot)
    if not _architecture_snapshot_changed(normalized_existing, snapshot):
        return normalized_existing

    panel_queue.put_nowait(
        _architecture_event(
            snapshot["nodes"],
            snapshot["edges"],
            snapshot["stage"],
            baseline_node_ids=snapshot.get("baseline_node_ids"),
            architecture_artifact=snapshot.get("architecture_artifact"),
        )
    )
    if customer_id and session_id:
        try:
            put_canvas_snapshot(
                customer_id,
                session_id,
                snapshot["nodes"],
                snapshot["edges"],
                snapshot["stage"],
                baseline_node_ids=snapshot.get("baseline_node_ids"),
                architecture_artifact=snapshot.get("architecture_artifact"),
            )
        except Exception:
            log.exception("Failed to persist deterministic architecture snapshot")
    return snapshot


def _finalize_workspace_state(
    workspace: dict[str, Any],
    *,
    invalidated_fields: list[str] | None = None,
    reasoning_changes: list[str] | None = None,
) -> dict[str, Any]:
    return reconcile_workspace_state(
        workspace,
        invalidated_fields=invalidated_fields,
        reasoning_changes=reasoning_changes,
    )


def _workspace_tool_instructions() -> str:
    return """
## Workspace State Contract

Maintain a live consulting workspace alongside the chat. Use the
`update_consulting_state` tool throughout the session, not just at the end.

Update it whenever you:
- learn a concrete customer fact
- identify an unresolved question
- commit to an architecture decision
- surface a delivery/compliance risk
- can state the current recommended direction

Tool rules:
- Keep every list concise and specific. Prefer short bullets, not paragraphs.
- `facts`: only confirmed customer facts or explicit constraints.
- `operating_model`: target-state harness model when relevant.
  Use one of `undecided`, `single_standard`, `multi_harness_governed`, or
  `default_plus_exceptions`.
- `question_state`: authoritative question registry when you can provide structure.
  Each item should look like:
  `{"id","text","why_it_matters","blocking","decision_domain","status","answer"}`
  Use `status=open` for active blockers and `status=answered` once the customer resolves one.
- `open_questions`: shorthand unanswered blocker list. The runtime derives this from `question_state` when present.
- `decisions`: architecture choices already made, phrased as decisions.
- `risks`: unresolved risks, tradeoffs, or external dependencies.
- `implementation_plan`: near-term rollout steps in order.
- `recommendation`: 1-3 sentences describing the current direction.
- `blueprint_markdown`: the current technical blueprint artifact in markdown.
  Use this for the substantial blueprint/plan document instead of dumping it into chat.
- `assumptions`: non-blocking working defaults the architecture currently relies on.
  Use this for choices the customer can override later instead of turning every
  architecture variable into a question.
  Each item should look like:
  `{"id","title","assumed","why","impact","confidence","options":[{"id","label","prompt"}]}`
- `advisory_case`: the authoritative executive artifact for the app. Use structured JSON instead of prose-heavy chat.
  It should contain:
  `recommendation`, `alternatives`, `decisions`, `risks`, `maturity`,
  `readout`, `next_best_question`, `output_pack`, and optional `delta`.
  The recommendation should include `summary`, `why_this`, `why_not`,
  `confidence`, `confidence_reason`, and `change_triggers`.
  The output pack should include `executive_summary`, `recommendation_memo`,
  `architecture_narrative`, `key_decisions`, `risks_and_mitigations`,
  `open_questions`, `rollout_30_90_180`, `operating_principles`,
  and `control_checklist`.
- `stage`: one of discovery, solutioning, blueprint.

Execution rules:
- Always set `stage` explicitly on every workspace update.
- `discovery`: use while gathering constraints, context, and unresolved questions.
- `solutioning`: use once you are actively recommending a direction or locking in architecture decisions.
- `blueprint`: use only when the recommendation is materially coherent, major decisions are captured, and rollout steps are present.
- Discovery-first ordering is strict:
  1. publish `facts`, `assumptions`, `open_questions`, and the current short recommendation via `update_consulting_state`
  2. then, only if the architecture is mature enough or the customer explicitly asked for a strawman, publish `update_architecture`
  3. publish `blueprint_markdown` only when you have genuinely moved into `stage=blueprint`
- On the first substantive turn of a new session, prioritize questions and assumptions over architecture and blueprint generation.
- Do not populate `blueprint_markdown` or a full `advisory_case.output_pack` during early discovery just to fill panels.
- Keep the blueprint panel effectively empty until the direction is coherent enough to defend.
- If you do have enough context for a working baseline architecture, update the questions/assumptions panels first in that same turn so the customer sees what is still open before the architecture appears.
- Only call `update_architecture` when the answer changes the platform shape:
  topology, trust boundary, identity boundary, harness model, execution model,
  model-routing design, control placement, or customer-specific additions.
- If an answer only changes confidence, recommendation wording, risks,
  implementation sequencing, or open questions, refresh
  `update_consulting_state` without republishing the architecture.
- Never narrate your own workflow in chat. Do not say things like:
  "I have enough to build...", "let me produce...", "now I will update...",
  or "here's everything at once."
- Treat chat as a thin status layer over the panels. When you update the
  workspace or architecture panels, keep the chat reply to at most 2 short
  sentences.
- Do not restate the full architecture, assumption list, or blueprint in chat
  if those artifacts were published to panels.
- If the customer asks for a one-page or executive summary, write it into
  `advisory_case.output_pack.executive_summary` and related executive fields
  instead of printing the body in chat.
- After publishing an executive-summary artifact, the chat reply should be one
  short sentence such as "Executive summary added to the brief."
- If there are open questions, name only the single highest-leverage one in
  chat and leave the rest in the questions panel.
- When `stage=blueprint`, keep the chat reply short and point the customer to the blueprint panel.
  Put the actual blueprint artifact in `blueprint_markdown`.
- Put only true blockers in `open_questions`.
- If the customer names multiple current tools, resolve `operating_model`
  before continuing with generic harness-selection questions.
- Put non-blocking defaults in `assumptions` with plain-English rationale and
  1-2 override options the customer can choose from later.
- If you ask the customer for input, call `update_consulting_state` in the same turn and put those prompts in `question_state` and `open_questions`.
- If the customer answers a previous question, mark it answered in `question_state` and remove or replace it in `open_questions` on your next call.
- If you make a concrete architecture choice, add it to `decisions` in the same turn; do not leave decisions only in prose.
- If you surface a blocker, ambiguity, or control concern, add it to `risks` in the same turn.
- If the architecture changes, update both `update_architecture` and `update_consulting_state` in that same turn.
- Every meaningful recommendation turn should call `update_consulting_state` before you finish your response so the workspace stays current.
- If a customer answer changes facts, assumptions, operating model, blockers, risks, or decisions, regenerate all dependent reasoning artifacts in that same turn:
  `recommendation`, `open_questions`, `decisions`, `risks`, `implementation_plan`,
  and any affected `blueprint_markdown` / `advisory_case`.
- Do not rely on previously saved blueprint, executive brief, or risk/question
  lists remaining valid after a blocker is resolved or the target pattern shifts.
- The runtime clears omitted dependent artifacts after a material reasoning change.
  If you want an artifact to remain visible after such a change, explicitly send
  the refreshed field again in the same `update_consulting_state` call.
- When refreshing the workspace, omit fields that are unchanged. Do not send an
  empty `blueprint_markdown` or empty executive artifact just because your
  current turn is focused on a different panel.
"""


async def _merge_streams(
    agent_gen: AsyncIterator,
    panel_queue: asyncio.Queue,
    on_text: "callable[[str], None] | None" = None,
) -> AsyncIterator[str]:
    out: asyncio.Queue[str] = asyncio.Queue()
    done = asyncio.Event()

    async def _agent_pump():
        sent_any_text = False
        try:
            async for ev in agent_gen:
                text = _text_from_strands_event(ev)
                if text:
                    if on_text:
                        on_text(text)
                    await out.put(_chat_stream(text))
                    sent_any_text = True
        except Exception as exc:
            log.exception("Agent stream error")
            if sent_any_text:
                await out.put(_chat_stream("\n\n⚠️ *Response interrupted — the above may be incomplete.*"))
            await out.put(_error_event(str(exc)))
        finally:
            done.set()

    async def _panel_pump():
        while not done.is_set() or not panel_queue.empty():
            try:
                item = panel_queue.get_nowait()
                await out.put(item)
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.005)

    agent_task = asyncio.create_task(_agent_pump())
    panel_task = asyncio.create_task(_panel_pump())

    try:
        while True:
            if done.is_set() and panel_queue.empty() and out.empty():
                break
            try:
                item = await asyncio.wait_for(out.get(), timeout=0.1)
                yield item
            except asyncio.TimeoutError:
                if done.is_set() and panel_queue.empty():
                    break
    finally:
        panel_task.cancel()
        try:
            await panel_task
        except asyncio.CancelledError:
            pass
        await agent_task


# ── AgentCore entrypoint ──────────────────────────────────────────────────────

@app.entrypoint
async def invoke(payload: dict, context):
    """
    Single entrypoint for all user messages.

    payload keys:
      user_message : str    — the user's message
      session_id   : str    — DynamoDB session id
      customer_id  : str    — DynamoDB customer id
      module_id    : str    — which module (coding-agent)
    """
    # Handle CLI wrapper: agentcore run wraps payload as {"prompt": "<json>"}
    if "prompt" in payload and isinstance(payload.get("prompt"), str):
        try:
            payload = json.loads(payload["prompt"])
        except (json.JSONDecodeError, TypeError):
            pass

    session_id   = payload.get("session_id", "")
    customer_id  = payload.get("customer_id", "")
    user_message = payload.get("user_message") or "Hello, I'd like to design a coding agent platform."

    actor_id = _verify_token(context)
    if not actor_id:
        # Dev mode without Midway configured — use a sentinel
        actor_id = payload.get("actor_id") or "dev-user"
        log.info("Dev mode: actor_id=%s", actor_id)

    log.info("invoke: session=%s customer=%s msg=%.120s", session_id, customer_id, user_message)

    if customer_id and session_id:
        try:
            put_message(customer_id, session_id, "user", user_message)
        except Exception:
            log.exception("Failed to persist user message")

    # Emit module_detected so the frontend sidebar can label this session
    yield _module_detected_event("coding-agent")

    # Panel side-channel — tools write SSE strings here
    panel_queue: asyncio.Queue[str] = asyncio.Queue()

    existing_workspace: dict[str, Any] = {}
    existing_canvas: dict[str, Any] | None = None
    if customer_id and session_id:
        try:
            existing_workspace = get_workspace_snapshot(customer_id, session_id) or {}
            existing_workspace = _finalize_workspace_state(existing_workspace)
            existing_canvas = get_latest_canvas_snapshot(customer_id, session_id)
        except Exception:
            log.exception("Failed to load existing workspace before prompt assembly")

    # ── Build tools ───────────────────────────────────────────────────────────

    kb = _get_kb()
    existing_workspace, workspace_seeded = _prepare_workspace_for_turn(kb, existing_workspace, user_message)
    if workspace_seeded:
        architecture_case_payload = None
        if customer_id and session_id:
            try:
                architecture_case_payload = _persist_workspace_and_case(
                    customer_id=customer_id,
                    session_id=session_id,
                    workspace=existing_workspace,
                    canvas_snapshot=existing_canvas,
                )
            except Exception:
                log.exception("Failed to persist deterministic pre-turn workspace snapshot")
        panel_queue.put_nowait(_workspace_event(existing_workspace, architecture_case_payload))
    existing_canvas = _maybe_emit_engine_architecture(
        workspace=existing_workspace,
        panel_queue=panel_queue,
        customer_id=customer_id,
        session_id=session_id,
        existing_canvas=existing_canvas,
    )
    if customer_id and session_id:
        try:
            _persist_workspace_and_case(
                customer_id=customer_id,
                session_id=session_id,
                workspace=existing_workspace,
                canvas_snapshot=existing_canvas,
            )
        except Exception:
            log.exception("Failed to persist shadow architecture case before streaming")

    @tool
    def query_knowledge(topic: str) -> str:
        """
        Query the Coding Agent Platform knowledge base for a given topic.
        Use this whenever you need to answer a question about platform
        architecture, harness selection, execution environments, access
        controls, gateways, quality, or cost.

        Args:
            topic: Keywords describing the topic to look up
                   (e.g. "model gateway tiering", "hipaa compliance", "container execution")
        """
        nodes = kb.query(topic, max_results=4)
        if not nodes:
            return "No relevant knowledge found for: " + topic
        parts = []
        for n in nodes:
            parts.append(f"### {n.title} ({n.path})\n\n{_node_body(kb, n)}")
        return "\n\n---\n\n".join(parts)

    @tool
    def load_mandate_knowledge() -> str:
        """
        Load the core knowledge nodes that are always relevant for every
        coding agent platform conversation. Call this at the start of a
        new session or when you need baseline context.
        """
        nodes = kb.mandate_nodes()
        if not nodes:
            return "No mandate knowledge nodes found."
        parts = [f"### {n.title} ({n.path})\n\n{_node_body(kb, n)}" for n in nodes]
        return "\n\n---\n\n".join(parts)

    @tool
    def update_architecture(
        nodes: list,
        edges: list,
        stage: str = "",
        baseline_node_ids: list[str] | None = None,
        architecture_artifact: dict | None = None,
    ) -> str:
        """
        Emit a live architecture canvas update to the frontend.
        Call this after gathering enough information about the customer's
        platform to meaningfully visualize the architecture.
        In discovery, publish questions and assumptions via
        `update_consulting_state` before calling this tool unless the customer
        explicitly asked for a strawman architecture.
        Do not call this tool for non-structural changes such as fuller rollout
        detail, refined risk wording, or confidence updates when the platform
        shape has not changed.

        Each node must have:
          id, type ("arch"), label, sublabel, icon, color, x=0, y=0
        Optional but strongly recommended:
          layer      — zone band for the node (see below)
          kind       — semantic category used by the UI to separate harnesses,
                       frameworks, runtimes, gateways, connectors, models, and controls
          path_role  — one of `primary`, `overlay`, or `supporting`
          cost       — monthly cost string e.g. "$180/mo"
          size       — sizing string e.g. "2 vCPU · 4 GB · ALB"

        ALWAYS set `layer` on every node so it lands in the correct zone band —
        these match the platform stack used throughout this conversation:
          "surface"   → Surface:   IDE, CLI, chat/PR bot, CI integration
          "harness"   → Harness:   SaaS product, managed runtime, pre-built OSS coding harness, framework SDK
          "execution" → Execution: local, container, microVM, remote runner
          "gateway"   → Gateway:   MCP tool gateway, model gateway, credential injection, tiering
          "model"     → Model:     LLM provider + tier (Haiku/Sonnet/Opus)
          "ops"       → Ops:       observability, cost tracking, resilience
          "access"    → Access:    identity, guardrails, quota, compliance controls

        Harness taxonomy is strict:
          - Strands, LangChain/LangGraph, PydanticAI, AutoGen, CrewAI = framework SDKs
          - OpenCode, Pi, Cline, Codex CLI, Goose, Aider, OpenHands, Mastra, SWE-agent = pre-built OSS coding harnesses
        Never call Strands or LangChain an "OSS harness" unless you explicitly
        mean a custom harness the customer is building on top of that framework.
        Never place a framework SDK in the same peer list as approved interactive
        harnesses unless the recommendation is explicitly a custom harness built on
        that framework. Background-agent lanes, runtimes, adapters, and connectors
        are not peer harnesses.

        Target-state architecture rule:
          - Represent the actual target-state operating model. If the customer is
            standardizing on one harness, emit one primary harness path.
          - If the target state is governed multi-harness coexistence, show the
            approved harness portfolio in the architecture and make the control
            model explicit: shared guardrails, identity boundary, routing rules,
            approved personas, and exception handling.
          - Use rationale/alternatives for rejected or deferred harnesses. Do not
            mix target-state approved harnesses with options that are merely being
            evaluated.
          - Only use scenario-comparison framing when the session is genuinely
            comparing future-state options rather than defining one operating model.

        Set x=0, y=0 on all nodes — the frontend positions them inside the correct zone band automatically.

        Each edge: {id, source, target, animated?, color?, dashed?}

        Baseline/customization contract:
          - `baseline_node_ids`: IDs of the standard reference architecture nodes.
            Any node not in this list is treated as a customization for this customer.
          - `architecture_artifact`: executive-facing architecture package with:
            {
              "executive_summary": string,
              "baseline": {
                "name": string,
                "layers": [
                  {
                    "id": string,
                    "label": string,
                    "purpose": string,
                    "component_ids": [string],
                    "component_labels": [string]
                  }
                ]
              },
              "customizations": [
                {
                  "id": string,
                  "title": string,
                  "layer": string,
                  "added_component_ids": [string],
                  "reason": string,
                  "tradeoff": string,
                  "triggered_by": [string]
                }
              ],
              "decisions": [
                {
                  "decision": string,
                  "why": string,
                  "alternatives_rejected": [string]
                }
              ],
              "risks": [
                {
                  "risk": string,
                  "mitigation": string
                }
              ],
	              "rollout": [
	                {
	                  "phase": string,
	                  "outcome": string
	                }
              ],
              "primary_flow": [
                {
                  "id": string,
                  "title": string,
                  "narrative": string,
                  "component_ids": [string]
                }
              ],
              "cross_cutting_controls": [
                {
                  "id": string,
                  "title": string,
                  "narrative": string,
                  "component_ids": [string]
                }
              ],
              "supporting_lanes": [
                {
                  "id": string,
                  "title": string,
                  "narrative": string,
                  "component_ids": [string]
                }
              ]
            }

        Treat this architecture artifact as mandatory once you have moved past
        vague discovery. The VP should be able to answer:
          - what is the standard baseline?
          - what changed for this org?
          - why did it change?
          - what is the end-to-end request path?
          - which controls apply across that path?
          - which lanes are sidecars or exceptions instead of the main flow?

        Consistency rules are strict:
          - Do not list the same concept as both baseline and customization.
          - Do not say all major decisions are resolved if open questions,
            prerequisites, or blockers still remain.
          - Deduplicate near-identical risks and open questions.
          - If multiple interactive tools are approved, show them as the approved
            harness portfolio and move frameworks/runtimes/connectors into
            supporting lanes or overlays rather than the peer harness row.

	        Call at these stages:
	          - After scale + cloud provider: skeleton (harness + execution zones)
	          - After compliance + access: overlay (add policy + identity nodes)
	          - After harness selection: full (complete platform stack)
	        Treat `architecture_artifact.rollout` as architecture
	        implementation implications or prerequisites, not the full program
	        rollout plan. The full phased rollout belongs in
	        `advisory_case.output_pack`.
	        Do not use this tool just to fill the panel while discovery is still
	        waiting on its first decision-driving questions.

        Args:
            nodes: List of architecture node objects
            edges: List of edge objects connecting nodes
            stage: Stage label ("skeleton" | "compliance" | "full")
            baseline_node_ids: IDs of nodes that belong to the reference baseline
            architecture_artifact: Executive summary + rationale package
        """
        event = _architecture_event(
            nodes,
            edges,
            stage,
            baseline_node_ids=baseline_node_ids,
            architecture_artifact=architecture_artifact,
        )
        panel_queue.put_nowait(event)
        nonlocal existing_canvas
        existing_canvas = _normalize_canvas_snapshot(
            {
                "stage": stage,
                "nodes": nodes,
                "edges": edges,
                "baseline_node_ids": baseline_node_ids,
                "architecture_artifact": architecture_artifact,
            }
        )
        log.info("Architecture update emitted: stage=%s nodes=%d edges=%d",
                 stage, len(nodes), len(edges))
        if customer_id and session_id:
            try:
                put_canvas_snapshot(
                    customer_id,
                    session_id,
                    nodes,
                    edges,
                    stage,
                    baseline_node_ids=baseline_node_ids,
                    architecture_artifact=architecture_artifact,
                )
                architecture_case_payload = _persist_workspace_and_case(
                    customer_id=customer_id,
                    session_id=session_id,
                    workspace=existing_workspace,
                    canvas_snapshot=existing_canvas,
                )
                panel_queue.put_nowait(_workspace_event(existing_workspace, architecture_case_payload))
            except Exception:
                log.exception("Failed to persist canvas snapshot")
        return f"Architecture canvas updated ({stage or 'update'}: {len(nodes)} nodes, {len(edges)} edges)."

    @tool
    def save_session_note(note: str) -> str:
        """
        Save a structured note about this session — key decisions, constraints,
        or open questions discovered during the conversation.
        Use this to capture important architectural decisions or customer
        requirements that should be remembered alongside the conversation.

        Args:
            note: The note text to save (e.g. "Customer is HIPAA-regulated;
                  chosen harness: managed-runtime; exec: container")
        """
        if customer_id and session_id:
            try:
                put_session_note(customer_id, session_id, note)
                return "Note saved."
            except Exception:
                log.exception("Failed to save session note")
                return "Note could not be saved."
        return "No session context — note not persisted."

    @tool
    def update_consulting_state(
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
    ) -> str:
        """
        Persist and publish the current consulting workspace state.

        Keep each list short and specific. This tool updates the workspace
        panels in the UI so the customer can track facts, questions, decisions,
        risks, assumptions, and next steps outside the chat transcript.
        Omit fields that are unchanged. Passing an empty string or empty list
        clears that field explicitly.
        """
        existing = {}
        if customer_id and session_id:
            try:
                existing = get_workspace_snapshot(customer_id, session_id) or {}
            except Exception:
                log.exception("Failed to load existing workspace snapshot")

        workspace, invalidated_fields, reasoning_changes = build_workspace_state(
            existing,
            recommendation=recommendation,
            blueprint_markdown=blueprint_markdown,
            assumptions=assumptions,
            facts=facts,
            operating_model=operating_model,
            question_state=question_state,
            open_questions=open_questions,
            decisions=decisions,
            risks=risks,
            implementation_plan=implementation_plan,
            advisory_case=advisory_case,
            stage=stage,
        )
        if invalidated_fields:
            log.info(
                "Workspace invalidated stale dependent fields: %s (reasoning changes: %s)",
                invalidated_fields,
                reasoning_changes or ["n/a"],
            )
        workspace = _apply_traversal_state(kb, workspace, user_message)
        workspace = _finalize_workspace_state(
            workspace,
            invalidated_fields=invalidated_fields,
            reasoning_changes=reasoning_changes,
        )
        nonlocal existing_canvas
        nonlocal existing_workspace
        existing_workspace = workspace
        existing_canvas = _maybe_emit_engine_architecture(
            workspace=workspace,
            panel_queue=panel_queue,
            customer_id=customer_id,
            session_id=session_id,
            existing_canvas=existing_canvas,
        )
        architecture_case_payload = None
        if customer_id and session_id:
            try:
                architecture_case_payload = _persist_workspace_and_case(
                    customer_id=customer_id,
                    session_id=session_id,
                    workspace=workspace,
                    canvas_snapshot=existing_canvas,
                )
            except Exception:
                log.exception("Failed to persist workspace snapshot")
        panel_queue.put_nowait(_workspace_event(workspace, architecture_case_payload))
        return "Consulting workspace updated."

    tools = [
        query_knowledge,
        load_mandate_knowledge,
        update_architecture,
        save_session_note,
        update_consulting_state,
    ]

    # ── AC Memory session manager ─────────────────────────────────────────────
    session_manager = None
    if _MEMORY_ID:
        try:
            from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
            from bedrock_agentcore.memory.integrations.strands.session_manager import (
                AgentCoreMemorySessionManager,
            )
            agentcore_session_id = getattr(context, "session_id", None) or session_id
            session_manager = AgentCoreMemorySessionManager(
                AgentCoreMemoryConfig(
                    memory_id=_MEMORY_ID,
                    session_id=agentcore_session_id,
                    actor_id=actor_id,
                ),
                region_name=_REGION,
            )
        except Exception:
            log.exception("Failed to initialize AgentCore memory session manager")
            session_manager = None

    # ── Build Strands Agent ───────────────────────────────────────────────────
    system_prompt = augment_system_prompt_with_traversal_context(
        _load_system_prompt(), kb, user_message, existing_workspace
    )
    if _is_explicit_blueprint_request(user_message):
        system_prompt = f"{system_prompt}\n\n{_explicit_blueprint_request_instructions()}"
    if _is_explicit_finalization_request(user_message):
        system_prompt = f"{system_prompt}\n\n{_explicit_finalization_request_instructions()}"
    system_prompt = f"{system_prompt}\n\n{_workspace_tool_instructions()}"
    model = BedrockModel(model_id=_MODEL_ID, streaming=True)
    agent_kwargs: dict = dict(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )
    if session_manager:
        agent_kwargs["session_manager"] = session_manager

    agent = Agent(**agent_kwargs)

    # ── Stream merged output ──────────────────────────────────────────────────
    reply_parts: list[str] = []
    try:
        async for sse_event in _merge_streams(
            agent.stream_async(user_message), panel_queue, on_text=reply_parts.append
        ):
            yield sse_event
    finally:
        log.info("Stream complete: session=%s", session_id)
        if customer_id and session_id and reply_parts:
            try:
                put_message(customer_id, session_id, "agent", "".join(reply_parts))
            except Exception:
                log.exception("Failed to persist agent message")

    reply_text = "".join(reply_parts)
    if reply_text and customer_id and session_id:
        try:
            recovered_workspace = await _recover_workspace_after_stream(
                user_message=user_message,
                reply_text=reply_text,
                customer_id=customer_id,
                session_id=session_id,
            )
        except Exception:
            log.exception("Failed to repair workspace after stream")
            recovered_workspace = None
        if recovered_workspace is not None:
            existing_workspace = recovered_workspace
            existing_canvas = get_latest_canvas_snapshot(customer_id, session_id)
            latest_case = get_latest_architecture_case(customer_id, session_id)
            yield _workspace_event(recovered_workspace, latest_case if isinstance(latest_case, dict) else None)

    if customer_id and session_id:
        try:
            latest_workspace = get_workspace_snapshot(customer_id, session_id) or existing_workspace
            latest_canvas = get_latest_canvas_snapshot(customer_id, session_id)
            post_turn_queue: asyncio.Queue[str] = asyncio.Queue()
            existing_canvas = _maybe_emit_engine_architecture(
                workspace=latest_workspace,
                panel_queue=post_turn_queue,
                customer_id=customer_id,
                session_id=session_id,
                existing_canvas=latest_canvas,
            )
            while not post_turn_queue.empty():
                yield post_turn_queue.get_nowait()
        except Exception:
            log.exception("Failed to reassert deterministic architecture after stream")

    yield _complete_event(session_id)


if __name__ == "__main__":
    app.run()
