"""Architecture-first v3 workspace projection endpoints."""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field

from advisor_core.knowledge.runtime_release import (
    KnowledgeReleaseLoadError,
    get_configured_knowledge_release,
)
from advisor_core.knowledge.decision_guidance import (
    contextualize_decision_guidance,
)
from advisor_core.v3.models import content_hash
from advisor_core.v3.projection import build_frontend_projection
from advisor_core.v3.runtime import build_runtime_workspace
from api.db import dynamodb as db
from api.middleware.auth import authorize_owned_resource, get_current_user, get_user_id


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


class ArchitectureExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_number: int | None = Field(default=None, ge=1)


class ArchitectureReopenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package: dict[str, Any]


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


def _workspace_id(tenant_id: str, owner_id: str, scope_id: str) -> str:
    scope = f"{tenant_id}\0{owner_id}\0{scope_id}\0coding-platform".encode()
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
        release, workspace = build_runtime_workspace(
            as_of,
            workspace_id=workspace_id,
            requirement_values=answers,
        )
        projection = build_frontend_projection(
            workspace,
            release.logical_catalog,
            deployable_catalog=release.deployable_catalog,
        )
        projection["decision_guidance"] = contextualize_decision_guidance(
            projection,
            release.decision_guidance,
        )
    except KnowledgeReleaseLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The pinned architecture knowledge release is unavailable",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    projection["knowledge_release"] = {
        "release_id": release.manifest.release_id,
        "version": release.manifest.release_version,
        "manifest_hash": release.manifest.manifest_hash,
        "deployable_catalog_id": release.deployable_catalog.id,
        "deployable_catalog_version": release.deployable_catalog.version,
        "deployable_catalog_hash": release.deployable_catalog.content_hash,
    }
    projection["workspace"]["workspace_id"] = workspace_id
    projection["workspace"]["persistence_revision"] = persistence_revision
    projection["workspace"]["persistence_hash"] = persistence_hash
    _rehash_projection(projection)
    return projection


def _authorized_scope(
    user: dict,
    customer_id: str | None,
    session_id: str | None,
) -> str:
    if customer_id is None and session_id is None:
        return "standalone"
    if not customer_id or not session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="customer_id and session_id must be supplied together",
        )

    customer = db.get_customer(customer_id)
    if not customer or customer.get("demo_data") is not True:
        customer = authorize_owned_resource(
            user,
            customer,
            resource_name="Customer",
            write=True,
        )

    session = db.get_session(customer_id, session_id)
    if not session or session.get("demo_data") is not True:
        session = authorize_owned_resource(
            user,
            session,
            resource_name="Session",
            write=True,
        )
    if session.get("customer_id") != customer.get("customer_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    digest = hashlib.sha256(f"{customer_id}\0{session_id}".encode()).hexdigest()[:24]
    return f"customer-session-{digest}"


def _load_or_initialize(user: dict, scope_id: str = "standalone") -> dict:
    owner_id = get_user_id(user)
    tenant_id = _tenant_id(user)
    state = db.get_architecture_workspace_state(tenant_id, owner_id, scope_id)
    if state is not None:
        return state

    as_of = date.today().isoformat()
    answers: dict[str, Any] = {}
    return db.initialize_architecture_workspace_state(
        tenant_id=tenant_id,
        owner_id=owner_id,
        workspace_id=_workspace_id(tenant_id, owner_id, scope_id),
        answers=answers,
        state_hash=_persistence_hash(answers, as_of),
        as_of=as_of,
        scope_id=scope_id,
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


def _public_revision(revision: dict) -> dict[str, object]:
    return {
        "workspace_id": revision["workspace_id"],
        "revision_number": int(revision["revision_number"]),
        "parent_revision_number": (
            int(revision["parent_revision_number"])
            if revision.get("parent_revision_number") is not None
            else None
        ),
        "previous_state_hash": revision.get("previous_state_hash"),
        "state_hash": revision["state_hash"],
        "answers": jsonable_encoder(revision["answers"]),
        "as_of": revision["as_of"],
        "operation": revision["operation"],
        "created_at": revision["created_at"],
    }


def _get_scoped_revision(
    user: dict,
    scope_id: str,
    revision_number: int,
) -> dict:
    tenant_id = _tenant_id(user)
    owner_id = get_user_id(user)
    revision = db.get_architecture_workspace_revision(
        tenant_id,
        owner_id,
        revision_number,
        scope_id,
    )
    if revision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Architecture workspace revision not found",
        )
    return revision


def _customer_package(
    revision: dict,
    *,
    customer_id: str | None,
    session_id: str | None,
) -> dict[str, object]:
    answers = jsonable_encoder(revision["answers"])
    as_of = revision["as_of"]
    if _persistence_hash(answers, as_of) != revision["state_hash"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted architecture revision failed integrity verification",
        )
    projection = _projection(
        answers=answers,
        as_of=date.fromisoformat(as_of),
        workspace_id=revision["workspace_id"],
        persistence_revision=int(revision["revision_number"]),
        persistence_hash=revision["state_hash"],
    )
    package: dict[str, object] = {
        "schema_version": "1.0.0",
        "package_type": "platform-advisor.customer-architecture",
        "workspace": {
            "workspace_id": revision["workspace_id"],
            "scope": {
                "type": (
                    "customer_session"
                    if customer_id is not None
                    else "standalone"
                ),
                "customer_id": customer_id,
                "session_id": session_id,
            },
        },
        "revision": _public_revision(revision),
        "pinned_versions": {
            "package_contract_version": "1.0.0",
            "projection_schema_version": projection["schema_version"],
            "catalog_release_id": projection["catalog"]["catalog_release_id"],
            "catalog_release_version": projection["catalog"]["version"],
            "catalog_content_hash": projection["catalog"]["content_hash"],
            "catalog_validated_as_of": projection["catalog"][
                "validated_as_of"
            ],
            "knowledge_release_id": projection["knowledge_release"][
                "release_id"
            ],
            "knowledge_release_version": projection["knowledge_release"][
                "version"
            ],
            "knowledge_release_manifest_hash": projection[
                "knowledge_release"
            ]["manifest_hash"],
            "deployable_catalog_id": projection["knowledge_release"][
                "deployable_catalog_id"
            ],
            "deployable_catalog_version": projection[
                "knowledge_release"
            ]["deployable_catalog_version"],
            "deployable_catalog_hash": projection["knowledge_release"][
                "deployable_catalog_hash"
            ],
            "engine_revision_id": projection["revision"]["revision_id"],
            "engine_revision_number": projection["revision"][
                "revision_number"
            ],
            "engine_state_hash": projection["revision"]["state_hash"],
            "projection_hash": projection["projection_hash"],
        },
        "inputs": {
            "answers": answers,
            "as_of": as_of,
        },
        "solution": projection,
    }
    package["package_hash"] = content_hash(package)
    return package


def _invalid_package(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail,
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
    scope_id: str = "standalone",
) -> dict[str, object]:
    state = _load_or_initialize(user, scope_id)
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
            scope_id=scope_id,
            operation="reset" if reset else "evaluate",
        )
    except db.ArchitectureWorkspaceConflict as exc:
        latest = db.get_architecture_workspace_state(
            state["tenant_id"],
            state["created_by"],
            scope_id,
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
    customer_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, object]:
    scope_id = _authorized_scope(current_user, customer_id, session_id)
    return _state_projection(_load_or_initialize(current_user, scope_id))


@router.post("/workspace/evaluate")
async def evaluate_architecture_workspace(
    payload: ArchitectureEvaluationRequest,
    current_user: CurrentUser,
    customer_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, object]:
    scope_id = _authorized_scope(current_user, customer_id, session_id)
    return _apply(
        current_user,
        answers=payload.answers,
        reset=False,
        base_revision_number=payload.base_revision_number,
        base_state_hash=payload.base_state_hash,
        scope_id=scope_id,
    )


@router.post("/workspace/reset")
async def reset_architecture_workspace(
    payload: ArchitectureResetRequest,
    current_user: CurrentUser,
    customer_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, object]:
    scope_id = _authorized_scope(current_user, customer_id, session_id)
    return _apply(
        current_user,
        answers={},
        reset=True,
        base_revision_number=payload.base_revision_number,
        base_state_hash=payload.base_state_hash,
        scope_id=scope_id,
    )


@router.get("/workspace/revisions")
async def list_architecture_workspace_revisions(
    current_user: CurrentUser,
    customer_id: str | None = None,
    session_id: str | None = None,
    limit: int = 100,
) -> dict[str, object]:
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="limit must be between 1 and 100",
        )
    scope_id = _authorized_scope(current_user, customer_id, session_id)
    head = _load_or_initialize(current_user, scope_id)
    revisions = db.list_architecture_workspace_revisions(
        _tenant_id(current_user),
        get_user_id(current_user),
        scope_id,
        limit=limit,
    )
    return {
        "workspace_id": head["workspace_id"],
        "current_revision_number": int(head["persistence_revision"]),
        "revisions": [_public_revision(revision) for revision in revisions],
    }


@router.get("/workspace/revisions/{revision_number}")
async def get_architecture_workspace_revision(
    revision_number: int,
    current_user: CurrentUser,
    customer_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, object]:
    if revision_number < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="revision_number must be at least 1",
        )
    scope_id = _authorized_scope(current_user, customer_id, session_id)
    _load_or_initialize(current_user, scope_id)
    return _public_revision(
        _get_scoped_revision(current_user, scope_id, revision_number)
    )


@router.post("/workspace/exports")
async def export_architecture_customer_package(
    payload: ArchitectureExportRequest,
    current_user: CurrentUser,
    customer_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, object]:
    scope_id = _authorized_scope(current_user, customer_id, session_id)
    head = _load_or_initialize(current_user, scope_id)
    revision_number = (
        payload.revision_number
        if payload.revision_number is not None
        else int(head["persistence_revision"])
    )
    revision = _get_scoped_revision(
        current_user,
        scope_id,
        revision_number,
    )
    return _customer_package(
        revision,
        customer_id=customer_id,
        session_id=session_id,
    )


@router.post("/workspace/reopen")
async def reopen_architecture_customer_package(
    payload: ArchitectureReopenRequest,
    current_user: CurrentUser,
    customer_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, object]:
    scope_id = _authorized_scope(current_user, customer_id, session_id)
    package = payload.package
    supplied_hash = package.get("package_hash")
    if not isinstance(supplied_hash, str):
        raise _invalid_package("Customer package hash is missing")
    hash_input = dict(package)
    hash_input.pop("package_hash", None)
    try:
        calculated_hash = content_hash(hash_input)
    except (TypeError, ValueError):
        raise _invalid_package("Customer package is not canonical JSON") from None
    if calculated_hash != supplied_hash:
        raise _invalid_package("Customer package hash verification failed")
    if (
        package.get("schema_version") != "1.0.0"
        or package.get("package_type")
        != "platform-advisor.customer-architecture"
    ):
        raise _invalid_package("Customer package contract is unsupported")

    workspace = package.get("workspace")
    revision_data = package.get("revision")
    if not isinstance(workspace, dict) or not isinstance(revision_data, dict):
        raise _invalid_package("Customer package identity is invalid")
    expected_workspace_id = _workspace_id(
        _tenant_id(current_user),
        get_user_id(current_user),
        scope_id,
    )
    if workspace.get("workspace_id") != expected_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer package not found",
        )
    try:
        revision_number = int(revision_data["revision_number"])
    except (KeyError, TypeError, ValueError):
        raise _invalid_package("Customer package revision is invalid") from None
    if revision_number < 1:
        raise _invalid_package("Customer package revision is invalid")

    revision = _get_scoped_revision(
        current_user,
        scope_id,
        revision_number,
    )
    expected_package = _customer_package(
        revision,
        customer_id=customer_id,
        session_id=session_id,
    )
    if package != expected_package:
        raise _invalid_package(
            "Customer package does not match its immutable revision"
        )
    return {
        "verified": True,
        "replay_verified": True,
        "workspace_id": expected_workspace_id,
        "revision_number": revision_number,
        "package_hash": supplied_hash,
        "projection": expected_package["solution"],
    }


@router.post("/explain")
async def explain_architecture_decision(
    payload: ArchitectureExplainRequest,
    current_user: CurrentUser,
    customer_id: str | None = None,
    session_id: str | None = None,
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
    _authorized_scope(current_user, customer_id, session_id)
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
    customer_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, object]:
    """Interpret free text into a typed requirement proposal for user review.

    The model can extract candidate requirements, but this endpoint never
    mutates the workspace. The UI must submit an accepted proposal through the
    deterministic evaluate endpoint, which validates and commits the revision.
    """
    scope_id = _authorized_scope(current_user, customer_id, session_id)
    state = _load_or_initialize(current_user, scope_id)
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

    try:
        catalog = get_configured_knowledge_release().logical_catalog
    except KnowledgeReleaseLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The pinned architecture knowledge release is unavailable",
        ) from exc
    result = engine_agents.interpret_requirements(
        payload.message,
        catalog.requirements,
    )
    return {
        "reply": result["reply"],
        "proposed_answers": result["answers"],
        "source": result["source"],
    }
