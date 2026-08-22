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
from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator

import boto3
import jwt
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from jwt import PyJWKClient
from strands import Agent, tool
from strands.models import BedrockModel

from knowledge_loader import KnowledgeBase, load_knowledge_base
from store import put_canvas_snapshot, put_message, put_session_note, put_workspace_snapshot

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


def _get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = load_knowledge_base(_KNOWLEDGE_DIR)
        log.info("Knowledge base loaded: %d nodes", len(_kb._nodes))
    return _kb


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
    block = "\n\n---\n\n".join(f"### {n.title} ({n.path})\n\n{n.content}" for n in nodes)
    return (
        f"{base_prompt}\n\n"
        f"## Signals Detected This Turn — Relevant Knowledge Already Loaded\n\n{block}"
    )


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


def _workspace_event(workspace: dict) -> str:
    return f"data: {json.dumps({'type': 'workspace_update', 'data': workspace})}\n\n"


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
- `open_questions`: unanswered questions blocking or materially shaping the recommendation.
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
- When `stage=blueprint`, keep the chat reply short and point the customer to the blueprint panel.
  Put the actual blueprint artifact in `blueprint_markdown`.
- Put only true blockers in `open_questions`.
- Put non-blocking defaults in `assumptions` with plain-English rationale and
  1-2 override options the customer can choose from later.
- If you ask the customer for input, call `update_consulting_state` in the same turn and put those prompts in `open_questions`.
- If the customer answers a previous question, remove or replace it in `open_questions` on your next call.
- If you make a concrete architecture choice, add it to `decisions` in the same turn; do not leave decisions only in prose.
- If you surface a blocker, ambiguity, or control concern, add it to `risks` in the same turn.
- If the architecture changes, update both `update_architecture` and `update_consulting_state` in that same turn.
- Every meaningful recommendation turn should call `update_consulting_state` before you finish your response so the workspace stays current.
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

    # ── Build tools ───────────────────────────────────────────────────────────

    kb = _get_kb()

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
            parts.append(f"### {n.title} ({n.path})\n\n{n.content}")
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
        parts = [f"### {n.title} ({n.path})\n\n{n.content}" for n in nodes]
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

        Each node must have:
          id, type ("arch"), label, sublabel, icon, color, x=0, y=0
        Optional but strongly recommended:
          layer   — zone band for the node (see below)
          cost    — monthly cost string e.g. "$180/mo"
          size    — sizing string e.g. "2 vCPU · 4 GB · ALB"

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

        Target-state architecture rule:
          - Emit exactly one primary harness path in the architecture for the
            recommended target state.
          - Put rejected or deferred harnesses in rationale/alternatives, not as
            parallel harness nodes in the same target-state architecture.
          - Only show multiple harness paths in the architecture when the
            customer explicitly asks for scenario comparison.

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
              ]
            }

        Treat this architecture artifact as mandatory once you have moved past
        vague discovery. The VP should be able to answer:
          - what is the standard baseline?
          - what changed for this org?
          - why did it change?

        Call at these stages:
          - After scale + cloud provider: skeleton (harness + execution zones)
          - After compliance + access: overlay (add policy + identity nodes)
          - After harness selection: full (complete platform stack)

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
        recommendation: str = "",
        blueprint_markdown: str = "",
        assumptions: list[dict] | None = None,
        facts: list[str] | None = None,
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
        """
        workspace = {
            "stage": stage,
            "recommendation": recommendation,
            "blueprint_markdown": blueprint_markdown,
            "assumptions": assumptions or [],
            "facts": facts or [],
            "open_questions": open_questions or [],
            "decisions": decisions or [],
            "risks": risks or [],
            "implementation_plan": implementation_plan or [],
            "advisory_case": advisory_case or None,
        }
        panel_queue.put_nowait(_workspace_event(workspace))
        if customer_id and session_id:
            try:
                put_workspace_snapshot(
                    customer_id,
                    session_id,
                    stage=stage,
                    recommendation=recommendation,
                    blueprint_markdown=blueprint_markdown,
                    assumptions=assumptions or [],
                    facts=facts or [],
                    open_questions=open_questions or [],
                    decisions=decisions or [],
                    risks=risks or [],
                    implementation_plan=implementation_plan or [],
                    advisory_case=advisory_case or None,
                )
            except Exception:
                log.exception("Failed to persist workspace snapshot")
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
    system_prompt = augment_system_prompt_with_conditional_knowledge(
        _load_system_prompt(), kb, user_message
    )
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

    yield _complete_event(session_id)


if __name__ == "__main__":
    app.run()
