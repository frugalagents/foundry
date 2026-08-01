"""Architecture-first v3 workspace projection endpoints."""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from advisor_core.v3.demo import build_demo_workspace
from advisor_core.v3.models import content_hash
from advisor_core.v3.projection import build_frontend_projection
from api.db import dynamodb as db
from api.middleware.auth import get_current_user, get_user_id


router = APIRouter(prefix="/architecture", tags=["architecture"])
CurrentUser = Annotated[dict, Depends(get_current_user)]


class ArchitectureEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: dict[str, Any] = Field(default_factory=dict)
    base_revision_number: int | None = Field(default=None, ge=1)
    base_state_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )


class ArchitectureResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_revision_number: int | None = Field(default=None, ge=1)
    base_state_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )


class ArchitectureExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=400)
    top_k: int = Field(default=4, ge=1, le=8)


def _tenant_id(user: dict) -> str:
    for claim in (
        "custom:tenant_id",
        "tenant_id",
        "custom:organization_id",
        "organization_id",
    ):
        value = user.get(claim)
        if isinstance(value, str) and value.strip():
            return value.strip()
    # The current Cognito pool is user-owned. Falling back to the actor keeps
    # that isolation until an explicit tenant claim is configured.
    return get_user_id(user)


def _workspace_id(tenant_id: str, owner_id: str) -> str:
    scope = f"{tenant_id}\0{owner_id}\0coding-platform".encode()
    digest = hashlib.sha256(scope).hexdigest()[:24]
    return f"workspace:coding-platform-{digest}"


def _persistence_hash(answers: dict[str, Any], as_of: str) -> str:
    return content_hash({"answers": answers, "as_of": as_of})


def _rehash_projection(projection: dict[str, object]) -> None:
    projection.pop("projection_hash", None)
    projection["projection_hash"] = content_hash(projection)


def _projection(
    *,
    answers: dict[str, Any],
    as_of: date,
    workspace_id: str,
    persistence_revision: int,
    persistence_hash: str,
) -> dict[str, object]:
    try:
        catalog, workspace = build_demo_workspace(
            as_of,
            requirement_values=answers,
        )
        projection = build_frontend_projection(workspace, catalog)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    projection["workspace"]["workspace_id"] = workspace_id
    projection["workspace"]["persistence_revision"] = persistence_revision
    projection["workspace"]["persistence_hash"] = persistence_hash
    _rehash_projection(projection)
    return projection


def _load_or_initialize(user: dict) -> dict:
    owner_id = get_user_id(user)
    tenant_id = _tenant_id(user)
    state = db.get_architecture_workspace_state(tenant_id, owner_id)
    if state is not None:
        return state

    as_of = date.today().isoformat()
    answers: dict[str, Any] = {}
    return db.initialize_architecture_workspace_state(
        tenant_id=tenant_id,
        owner_id=owner_id,
        workspace_id=_workspace_id(tenant_id, owner_id),
        answers=answers,
        state_hash=_persistence_hash(answers, as_of),
        as_of=as_of,
    )


def _state_projection(state: dict) -> dict[str, object]:
    answers = state.get("answers")
    if not isinstance(answers, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted architecture workspace answers are invalid",
        )
    try:
        as_of = date.fromisoformat(state["as_of"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted architecture workspace date is invalid",
        ) from exc
    return _projection(
        answers=answers,
        as_of=as_of,
        workspace_id=state["workspace_id"],
        persistence_revision=int(state["persistence_revision"]),
        persistence_hash=state["state_hash"],
    )


def _reject_stale_base(
    state: dict,
    *,
    base_revision_number: int | None,
    base_state_hash: str | None,
) -> None:
    stale_revision = (
        base_revision_number is not None
        and base_revision_number != int(state["persistence_revision"])
    )
    stale_hash = (
        base_state_hash is not None
        and base_state_hash != state["state_hash"]
    )
    if stale_revision or stale_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Architecture workspace changed; reload before retrying",
                "current_revision_number": int(state["persistence_revision"]),
                "current_state_hash": state["state_hash"],
            },
        )


def _apply(
    user: dict,
    *,
    answers: dict[str, Any],
    reset: bool,
    base_revision_number: int | None,
    base_state_hash: str | None,
) -> dict[str, object]:
    state = _load_or_initialize(user)
    _reject_stale_base(
        state,
        base_revision_number=base_revision_number,
        base_state_hash=base_state_hash,
    )

    current_answers = state.get("answers")
    if not isinstance(current_answers, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted architecture workspace answers are invalid",
        )
    merged_answers = {} if reset else {**current_answers, **answers}
    new_hash = _persistence_hash(merged_answers, state["as_of"])

    # Validate the complete merged state before making it durable.
    candidate = _projection(
        answers=merged_answers,
        as_of=date.fromisoformat(state["as_of"]),
        workspace_id=state["workspace_id"],
        persistence_revision=int(state["persistence_revision"]) + 1,
        persistence_hash=new_hash,
    )
    if new_hash == state["state_hash"]:
        return _state_projection(state)

    try:
        saved = db.update_architecture_workspace_state(
            tenant_id=state["tenant_id"],
            owner_id=state["created_by"],
            expected_revision=int(state["persistence_revision"]),
            expected_state_hash=state["state_hash"],
            answers=merged_answers,
            state_hash=new_hash,
        )
    except db.ArchitectureWorkspaceConflict as exc:
        latest = db.get_architecture_workspace_state(
            state["tenant_id"],
            state["created_by"],
        )
        detail: dict[str, object] = {
            "message": "Architecture workspace changed; reload before retrying"
        }
        if latest is not None:
            detail.update({
                "current_revision_number": int(
                    latest["persistence_revision"]
                ),
                "current_state_hash": latest["state_hash"],
            })
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc

    # The conditional write only changes persistence metadata; the candidate
    # is therefore the exact projection of the state that was stored.
    candidate["workspace"]["persistence_revision"] = int(
        saved["persistence_revision"]
    )
    candidate["workspace"]["persistence_hash"] = saved["state_hash"]
    _rehash_projection(candidate)
    return candidate


@router.get("/workspace")
async def get_architecture_workspace(
    current_user: CurrentUser,
) -> dict[str, object]:
    return _state_projection(_load_or_initialize(current_user))


@router.post("/workspace/evaluate")
async def evaluate_architecture_workspace(
    payload: ArchitectureEvaluationRequest,
    current_user: CurrentUser,
) -> dict[str, object]:
    return _apply(
        current_user,
        answers=payload.answers,
        reset=False,
        base_revision_number=payload.base_revision_number,
        base_state_hash=payload.base_state_hash,
    )


@router.post("/workspace/reset")
async def reset_architecture_workspace(
    payload: ArchitectureResetRequest,
    current_user: CurrentUser,
) -> dict[str, object]:
    return _apply(
        current_user,
        answers={},
        reset=True,
        base_revision_number=payload.base_revision_number,
        base_state_hash=payload.base_state_hash,
    )


@router.post("/explain")
async def explain_architecture_decision(
    payload: ArchitectureExplainRequest,
    current_user: CurrentUser,
) -> dict[str, object]:
    """Retrieve supporting passages for a decision from the knowledge base.

    This is an EXPLANATION affordance only. It never selects an architecture,
    changes a decision, or weakens a constraint — those come exclusively from
    the deterministic engine and its curated, approved evidence claims. Here we
    only surface reference material (AgentCore, Well-Architected, tokenomics,
    best-practice docs) so a user can read more about a decision the engine
    already made. Retrieved passages are clearly labeled as reference, not
    authority, and the endpoint degrades to an empty list when no KB is wired.
    """
    # Imported lazily so the API starts even when the agent package or KB is
    # unavailable (e.g. local dev without KNOWLEDGE_BASE_ID configured).
    try:
        from pipeline_skills import kb_utils
    except ImportError:
        return {"query": payload.query, "configured": False, "passages": []}

    passages = kb_utils.retrieve(payload.query, top_k=payload.top_k)
    return {
        "query": payload.query,
        "configured": kb_utils.is_configured(),
        "kind": "reference",
        "passages": passages,
    }


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)


@router.post("/chat")
async def chat_architecture(
    payload: ChatRequest,
    current_user: CurrentUser,
) -> dict[str, object]:
    """Interpret a free-text message into typed engine answers and merge them.

    The conversational path into the SAME engine the canvas clicks feed: the
    LLM extracts answers (box choices + constraints), we merge them into the
    stored answer set (chat and clicks accumulate together), and return a short
    reply plus the merged answers so the UI can reflect them. Extraction only —
    the engine still decides.
    """
    state = _load_or_initialize(current_user)
    answers = state.get("answers")
    if not isinstance(answers, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted architecture workspace answers are invalid",
        )
    try:
        from api.engine import agents as engine_agents
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Architecture engine is unavailable",
        ) from exc

    result = engine_agents.interpret(payload.message, answers)
    merged = {**answers, **result["answers"]}
    if result["answers"]:
        try:
            db.save_architecture_engine_answers(
                tenant_id=state["tenant_id"],
                owner_id=state["created_by"],
                answers=merged,
            )
        except Exception:  # noqa: BLE001
            pass
    return {
        "reply": result["reply"],
        "applied_answers": result["answers"],
        "answers": merged,
        "source": result["source"],
    }


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # boxes to decide now; defaults to the domains authored in the engine
    boxes: list[str] = Field(default_factory=lambda: ["model-gateway", "harness"])


@router.post("/generate")
async def generate_architecture_endpoint(
    payload: GenerateRequest,
    current_user: CurrentUser,
) -> dict[str, object]:
    """Run the agentic engine (propose → guard → generate → critic) over the
    stored answers and return the purpose-built architecture: solution stack,
    grounded rationale, cascades, guard verdict, and a persisted Decision Record.

    Available at any point — gaps fall back to constraint-compliant defaults, so
    the output is always defensible even from partial input.
    """
    from datetime import datetime, timezone

    state = _load_or_initialize(current_user)
    answers = state.get("answers")
    if not isinstance(answers, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted architecture workspace answers are invalid",
        )

    try:
        from api.engine import generate_architecture
    except ImportError as exc:  # engine package missing → cannot generate
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Architecture engine is unavailable",
        ) from exc

    result = generate_architecture(
        workspace_id=state["workspace_id"],
        answers=answers,
        boxes=payload.boxes,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    # Persist the Decision Record (best-effort; generation still returns on
    # a persistence hiccup so the user isn't blocked).
    try:
        db.save_architecture_decision_record(
            tenant_id=state["tenant_id"],
            owner_id=state["created_by"],
            record=result["decision_record"],
        )
    except Exception:  # noqa: BLE001
        result["persisted"] = False
    else:
        result["persisted"] = True

    return result
