"""AgentCore adapter for the persisted architecture-first v3 workspace."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError
from pydantic import BaseModel, ConfigDict, Field

from advisor_core.v3.models import content_hash
from advisor_core.v3.projection import build_frontend_projection
from advisor_core.v3.runtime import build_runtime_workspace


ACTION = "architecture.v3.workspace"
CONTRACT_VERSION = "3.0"
ENGINE_RELEASE = "advisor-core-v3-coding-platform"
_HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"
_SERIALIZER = TypeSerializer()


class ArchitectureV3Request(BaseModel):
    """Versioned AgentCore contract for v3 workspace operations."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["3.0"]
    operation: Literal["get", "evaluate", "reset"]
    answers: dict[str, Any] = Field(default_factory=dict)
    base_revision_number: int | None = Field(default=None, ge=1)
    base_state_hash: str | None = Field(default=None, pattern=_HASH_PATTERN)
    idempotency_key: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )


class ArchitectureV3Conflict(Exception):
    """The persisted workspace changed after the caller read it."""

    def __init__(self, state: dict[str, Any] | None = None):
        super().__init__("Architecture workspace changed; reload before retrying")
        self.state = state


class ArchitectureV3IdempotencyConflict(ValueError):
    """An idempotency key was reused for a different command."""


def _to_dynamodb(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_dynamodb(item) for item in value]
    return value


def _from_dynamodb(value: Any) -> Any:
    if isinstance(value, Decimal):
        return (
            int(value)
            if value.as_tuple().exponent >= 0
            else float(value)
        )
    if isinstance(value, dict):
        return {key: _from_dynamodb(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_from_dynamodb(item) for item in value]
    return value


def _serialize_map(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _to_dynamodb(value)
    return {
        key: _SERIALIZER.serialize(item)
        for key, item in normalized.items()
    }


def _is_conditional_failure(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") in {
        "ConditionalCheckFailedException",
        "TransactionCanceledException",
    }


def _scope_id(customer_id: str, session_id: str) -> str:
    digest = hashlib.sha256(
        f"{customer_id}\0{session_id}".encode()
    ).hexdigest()[:24]
    return f"customer-session-{digest}"


def _workspace_id(tenant_id: str, owner_id: str, scope_id: str) -> str:
    scope = f"{tenant_id}\0{owner_id}\0{scope_id}\0coding-platform".encode()
    digest = hashlib.sha256(scope).hexdigest()[:24]
    return f"workspace:coding-platform-{digest}"


def _persistence_hash(answers: dict[str, Any], as_of: str) -> str:
    return content_hash({"answers": answers, "as_of": as_of})


@lru_cache(maxsize=1)
def _engine_hash() -> str:
    """Digest the packaged v3 engine sources used to build projections."""

    root = Path(__file__).parent / "advisor_core" / "v3"
    digest = hashlib.sha256()
    source_paths = sorted(root.rglob("*.py"))
    if not source_paths:
        return content_hash({"engine_release": ENGINE_RELEASE})
    for path in source_paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _request_hash(request: ArchitectureV3Request) -> str:
    return content_hash({
        "schema_version": request.schema_version,
        "operation": request.operation,
        "answers": request.answers,
        "base_revision_number": request.base_revision_number,
        "base_state_hash": request.base_state_hash,
    })


def _rehash_projection(projection: dict[str, Any]) -> None:
    projection.pop("projection_hash", None)
    projection["projection_hash"] = content_hash(projection)


def _verify_projection_hash(projection: dict[str, Any]) -> str:
    saved_hash = projection.get("projection_hash")
    if not isinstance(saved_hash, str):
        raise ValueError("Persisted architecture projection hash is missing")
    unhashed = dict(projection)
    unhashed.pop("projection_hash")
    if content_hash(unhashed) != saved_hash:
        raise ValueError("Persisted architecture projection failed integrity check")
    return saved_hash


class ArchitectureV3RuntimeAdapter:
    """Execute backend-compatible v3 operations against one owned scope."""

    def __init__(
        self,
        table: Any,
        *,
        tenant_id: str,
        owner_id: str,
        customer_id: str,
        session_id: str,
        today: date | None = None,
    ):
        self._table = table
        self._tenant_id = tenant_id
        self._owner_id = owner_id
        self._scope_id = _scope_id(customer_id, session_id)
        self._today = today or date.today()

    @property
    def _head_key(self) -> dict[str, str]:
        return {
            "PK": f"TENANT#{self._tenant_id}#USER#{self._owner_id}",
            "SK": f"{self._record_prefix}HEAD",
        }

    @property
    def _record_prefix(self) -> str:
        return (
            "ARCHITECTURE#CODING-PLATFORM#"
            f"{self._scope_id}#"
        )

    def _revision_key(self, revision_number: int) -> dict[str, str]:
        return {
            "PK": self._head_key["PK"],
            "SK": f"{self._record_prefix}REVISION#{revision_number:020d}",
        }

    def _idempotency_key(self, idempotency_key: str) -> dict[str, str]:
        digest = hashlib.sha256(idempotency_key.encode()).hexdigest()
        return {
            "PK": self._head_key["PK"],
            "SK": f"{self._record_prefix}IDEMPOTENCY#{digest}",
        }

    @property
    def _client(self) -> Any:
        return self._table.meta.client

    @property
    def _table_name(self) -> str:
        return self._table.name

    def execute(self, raw_request: dict[str, Any]) -> dict[str, Any]:
        request = ArchitectureV3Request.model_validate(raw_request)
        self._validate_operation_fields(request)
        state = self._load_or_initialize()

        if request.operation == "get":
            projection = self._state_projection(state)
        else:
            projection = self._apply(state, request)

        return {
            "contract_version": CONTRACT_VERSION,
            "action": ACTION,
            "operation": request.operation,
            "projection": projection,
        }

    @staticmethod
    def _validate_operation_fields(request: ArchitectureV3Request) -> None:
        base_fields = (
            request.base_revision_number,
            request.base_state_hash,
        )
        has_any_base = any(value is not None for value in base_fields)
        has_all_base = all(value is not None for value in base_fields)
        if request.operation == "get":
            if request.answers or has_any_base or request.idempotency_key:
                raise ValueError(
                    "get does not accept answers, base revision fields, "
                    "or an idempotency key"
                )
            return
        if not has_all_base:
            raise ValueError(
                "evaluate and reset require base_revision_number and "
                "base_state_hash"
            )
        if request.idempotency_key is None:
            raise ValueError("evaluate and reset require an idempotency_key")
        if request.operation == "reset" and request.answers:
            raise ValueError("reset does not accept answers")

    def _get_item(self, key: dict[str, str]) -> dict[str, Any] | None:
        response = self._table.get_item(Key=key, ConsistentRead=True)
        raw_item = response.get("Item")
        return _from_dynamodb(raw_item) if raw_item else None

    def _owned_item(
        self,
        key: dict[str, str],
        *,
        item_type: str,
    ) -> dict[str, Any] | None:
        item = self._get_item(key)
        if (
            item is None
            or item.get("item_type") != item_type
            or item.get("tenant_id") != self._tenant_id
            or item.get("created_by") != self._owner_id
            or item.get("scope_id") != self._scope_id
        ):
            return None
        return item

    def _get_state(self) -> dict[str, Any] | None:
        return self._owned_item(
            self._head_key,
            item_type="architecture_workspace",
        )

    def _get_revision(self, revision_number: int) -> dict[str, Any] | None:
        item = self._owned_item(
            self._revision_key(revision_number),
            item_type="architecture_workspace_revision",
        )
        if (
            item is None
            or int(item.get("revision_number", 0)) != revision_number
        ):
            return None
        return item

    def _get_idempotency(self, key: str) -> dict[str, Any] | None:
        return self._owned_item(
            self._idempotency_key(key),
            item_type="architecture_workspace_idempotency",
        )

    def _load_or_initialize(self) -> dict[str, Any]:
        state = self._get_state()
        if state is not None:
            return state

        as_of = self._today.isoformat()
        answers: dict[str, Any] = {}
        now = datetime.now(timezone.utc).isoformat()
        workspace_id = _workspace_id(
            self._tenant_id,
            self._owner_id,
            self._scope_id,
        )
        state_hash = _persistence_hash(answers, as_of)
        projection, pins = self._projection(
            answers=answers,
            as_of=self._today,
            workspace_id=workspace_id,
            persistence_revision=1,
            persistence_hash=state_hash,
        )
        revision = self._revision_item(
            workspace_id=workspace_id,
            revision_number=1,
            previous_state_hash=None,
            answers=answers,
            state_hash=state_hash,
            as_of=as_of,
            operation="initialize",
            projection=projection,
            pins=pins,
            created_at=now,
        )
        item = {
            **self._head_key,
            "item_type": "architecture_workspace",
            "workspace_id": workspace_id,
            "tenant_id": self._tenant_id,
            "created_by": self._owner_id,
            "scope_id": self._scope_id,
            "answers": answers,
            "persistence_revision": 1,
            "state_hash": state_hash,
            "as_of": as_of,
            "current_revision_sk": revision["SK"],
            "created_at": now,
            "updated_at": now,
        }
        try:
            self._client.transact_write_items(TransactItems=[
                self._put_transaction(item),
                self._put_transaction(revision),
            ])
            return item
        except ClientError as exc:
            if not _is_conditional_failure(exc):
                raise

        winner = self._get_state()
        if winner is None:
            raise ArchitectureV3Conflict()
        return winner

    @staticmethod
    def _projection(
        *,
        answers: dict[str, Any],
        as_of: date,
        workspace_id: str,
        persistence_revision: int,
        persistence_hash: str,
    ) -> tuple[dict[str, Any], dict[str, str]]:
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
        pins = {
            "catalog_hash": release.logical_catalog.content_hash,
            "deployable_catalog_hash": release.deployable_catalog.content_hash,
            "knowledge_release_manifest_hash": release.manifest.manifest_hash,
            "ruleset_hash": content_hash({
                "rules": [
                    rule.model_dump(mode="json")
                    for rule in release.logical_catalog.rules
                ],
            }),
            "engine_hash": _engine_hash(),
            "projection_hash": projection["projection_hash"],
        }
        return projection, pins

    def _revision_item(
        self,
        *,
        workspace_id: str,
        revision_number: int,
        previous_state_hash: str | None,
        answers: dict[str, Any],
        state_hash: str,
        as_of: str,
        operation: str,
        projection: dict[str, Any],
        pins: dict[str, str],
        created_at: str,
    ) -> dict[str, Any]:
        return {
            **self._revision_key(revision_number),
            "item_type": "architecture_workspace_revision",
            "workspace_id": workspace_id,
            "tenant_id": self._tenant_id,
            "created_by": self._owner_id,
            "scope_id": self._scope_id,
            "revision_number": revision_number,
            "previous_state_hash": previous_state_hash,
            "answers": answers,
            "state_hash": state_hash,
            "as_of": as_of,
            "operation": operation,
            **pins,
            "projection_packet": projection,
            "created_at": created_at,
        }

    def _read_revision_projection(
        self,
        revision: dict[str, Any],
    ) -> dict[str, Any]:
        projection = revision.get("projection_packet")
        if not isinstance(projection, dict):
            raise ValueError("Persisted architecture revision packet is invalid")
        projection_hash = _verify_projection_hash(projection)
        if projection_hash != revision.get("projection_hash"):
            raise ValueError(
                "Persisted architecture revision projection hash is invalid"
            )
        answers = revision.get("answers")
        as_of = revision.get("as_of")
        if (
            not isinstance(answers, dict)
            or not isinstance(as_of, str)
            or _persistence_hash(answers, as_of) != revision.get("state_hash")
        ):
            raise ValueError(
                "Persisted architecture revision state hash is invalid"
            )
        for field in (
            "catalog_hash",
            "ruleset_hash",
            "engine_hash",
            "projection_hash",
        ):
            value = revision.get(field)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise ValueError(
                    f"Persisted architecture revision {field} is invalid"
                )
        workspace = projection.get("workspace")
        if not isinstance(workspace, dict):
            raise ValueError("Persisted architecture revision workspace is invalid")
        if (
            int(workspace.get("persistence_revision", 0))
            != int(revision["revision_number"])
            or workspace.get("persistence_hash") != revision["state_hash"]
        ):
            raise ValueError(
                "Persisted architecture revision metadata is inconsistent"
            )
        catalog = projection.get("catalog")
        if (
            not isinstance(catalog, dict)
            or catalog.get("content_hash") != revision["catalog_hash"]
        ):
            raise ValueError(
                "Persisted architecture revision catalog hash is inconsistent"
            )
        knowledge_release = projection.get("knowledge_release")
        if knowledge_release is not None:
            if (
                not isinstance(knowledge_release, dict)
                or knowledge_release.get("manifest_hash")
                != revision.get("knowledge_release_manifest_hash")
                or knowledge_release.get("deployable_catalog_hash")
                != revision.get("deployable_catalog_hash")
            ):
                raise ValueError(
                    "Persisted architecture knowledge release is inconsistent"
                )
            for field in (
                "knowledge_release_manifest_hash",
                "deployable_catalog_hash",
            ):
                value = revision.get(field)
                if (
                    not isinstance(value, str)
                    or not value.startswith("sha256:")
                    or len(value) != 71
                ):
                    raise ValueError(
                        f"Persisted architecture revision {field} is invalid"
                    )
        return projection

    def _state_projection(self, state: dict[str, Any]) -> dict[str, Any]:
        revision_number = int(state["persistence_revision"])
        revision = self._get_revision(revision_number)
        if revision is None:
            revision = self._migrate_legacy_revision(state)
        if revision["state_hash"] != state["state_hash"]:
            raise ValueError("Architecture HEAD does not match its revision")
        return self._read_revision_projection(revision)

    def _migrate_legacy_revision(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        answers = state.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("Persisted architecture workspace answers are invalid")
        revision_number = int(state["persistence_revision"])
        try:
            as_of = date.fromisoformat(state["as_of"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Persisted architecture workspace date is invalid"
            ) from exc
        projection, pins = self._projection(
            answers=answers,
            as_of=as_of,
            workspace_id=state["workspace_id"],
            persistence_revision=revision_number,
            persistence_hash=state["state_hash"],
        )
        revision = self._revision_item(
            workspace_id=state["workspace_id"],
            revision_number=revision_number,
            previous_state_hash=None,
            answers=answers,
            state_hash=state["state_hash"],
            as_of=state["as_of"],
            operation="legacy-import",
            projection=projection,
            pins=pins,
            created_at=state.get(
                "updated_at",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        try:
            self._table.put_item(
                Item=_to_dynamodb(revision),
                ConditionExpression=(
                    "attribute_not_exists(PK) AND attribute_not_exists(SK)"
                ),
            )
            return revision
        except ClientError as exc:
            if not _is_conditional_failure(exc):
                raise
        winner = self._get_revision(revision_number)
        if winner is None:
            raise ArchitectureV3Conflict(self._get_state())
        return winner

    @staticmethod
    def _reject_stale_base(
        state: dict[str, Any],
        *,
        base_revision_number: int,
        base_state_hash: str,
    ) -> None:
        if (
            base_revision_number != int(state["persistence_revision"])
            or base_state_hash != state["state_hash"]
        ):
            raise ArchitectureV3Conflict(state)

    def _resolve_idempotency(
        self,
        record: dict[str, Any],
        *,
        request_hash: str,
    ) -> dict[str, Any]:
        if record.get("request_hash") != request_hash:
            raise ArchitectureV3IdempotencyConflict(
                "idempotency_key was already used for a different request"
            )
        revision = self._get_revision(int(record["revision_number"]))
        if (
            revision is None
            or revision.get("state_hash") != record.get("state_hash")
        ):
            raise ValueError(
                "Persisted idempotency result does not resolve to its revision"
            )
        return self._read_revision_projection(revision)

    def _apply(
        self,
        state: dict[str, Any],
        request: ArchitectureV3Request,
    ) -> dict[str, Any]:
        assert request.base_revision_number is not None
        assert request.base_state_hash is not None
        assert request.idempotency_key is not None
        request_hash = _request_hash(request)
        prior = self._get_idempotency(request.idempotency_key)
        if prior is not None:
            return self._resolve_idempotency(
                prior,
                request_hash=request_hash,
            )

        self._reject_stale_base(
            state,
            base_revision_number=request.base_revision_number,
            base_state_hash=request.base_state_hash,
        )
        current_answers = state.get("answers")
        if not isinstance(current_answers, dict):
            raise ValueError("Persisted architecture workspace answers are invalid")
        merged_answers = (
            {}
            if request.operation == "reset"
            else {**current_answers, **request.answers}
        )
        new_hash = _persistence_hash(merged_answers, state["as_of"])
        new_revision = int(state["persistence_revision"]) + 1
        projection, pins = self._projection(
            answers=merged_answers,
            as_of=date.fromisoformat(state["as_of"]),
            workspace_id=state["workspace_id"],
            persistence_revision=new_revision,
            persistence_hash=new_hash,
        )
        now = datetime.now(timezone.utc).isoformat()
        revision = self._revision_item(
            workspace_id=state["workspace_id"],
            revision_number=new_revision,
            previous_state_hash=state["state_hash"],
            answers=merged_answers,
            state_hash=new_hash,
            as_of=state["as_of"],
            operation=request.operation,
            projection=projection,
            pins=pins,
            created_at=now,
        )
        idempotency = {
            **self._idempotency_key(request.idempotency_key),
            "item_type": "architecture_workspace_idempotency",
            "workspace_id": state["workspace_id"],
            "tenant_id": self._tenant_id,
            "created_by": self._owner_id,
            "scope_id": self._scope_id,
            "idempotency_key": request.idempotency_key,
            "request_hash": request_hash,
            "revision_number": new_revision,
            "state_hash": new_hash,
            "created_at": now,
        }
        try:
            self._client.transact_write_items(TransactItems=[
                self._head_update_transaction(
                    state=state,
                    answers=merged_answers,
                    new_revision=new_revision,
                    new_state_hash=new_hash,
                    revision_sk=revision["SK"],
                    updated_at=now,
                ),
                self._put_transaction(revision),
                self._put_transaction(idempotency),
            ])
        except ClientError as exc:
            if not _is_conditional_failure(exc):
                raise
            winner = self._get_idempotency(request.idempotency_key)
            if winner is not None:
                return self._resolve_idempotency(
                    winner,
                    request_hash=request_hash,
                )
            raise ArchitectureV3Conflict(self._get_state()) from exc
        return projection

    def _put_transaction(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "Put": {
                "TableName": self._table_name,
                "Item": _serialize_map(item),
                "ConditionExpression": (
                    "attribute_not_exists(PK) AND attribute_not_exists(SK)"
                ),
            }
        }

    def _head_update_transaction(
        self,
        *,
        state: dict[str, Any],
        answers: dict[str, Any],
        new_revision: int,
        new_state_hash: str,
        revision_sk: str,
        updated_at: str,
    ) -> dict[str, Any]:
        return {
            "Update": {
                "TableName": self._table_name,
                "Key": _serialize_map(self._head_key),
                "UpdateExpression": (
                    "SET #answers = :answers, #revision = :new_revision, "
                    "#state_hash = :new_state_hash, "
                    "#current_revision_sk = :current_revision_sk, "
                    "#updated_at = :updated_at"
                ),
                "ExpressionAttributeNames": {
                    "#answers": "answers",
                    "#revision": "persistence_revision",
                    "#state_hash": "state_hash",
                    "#current_revision_sk": "current_revision_sk",
                    "#updated_at": "updated_at",
                    "#tenant_id": "tenant_id",
                    "#created_by": "created_by",
                    "#scope_id": "scope_id",
                    "#pk": "PK",
                },
                "ExpressionAttributeValues": _serialize_map({
                    ":answers": answers,
                    ":expected_revision": int(state["persistence_revision"]),
                    ":new_revision": new_revision,
                    ":expected_state_hash": state["state_hash"],
                    ":new_state_hash": new_state_hash,
                    ":current_revision_sk": revision_sk,
                    ":updated_at": updated_at,
                    ":tenant_id": self._tenant_id,
                    ":owner_id": self._owner_id,
                    ":scope_id": self._scope_id,
                }),
                "ConditionExpression": (
                    "attribute_exists(#pk) "
                    "AND #tenant_id = :tenant_id "
                    "AND #created_by = :owner_id "
                    "AND #scope_id = :scope_id "
                    "AND #revision = :expected_revision "
                    "AND #state_hash = :expected_state_hash"
                ),
            }
        }


def conflict_payload(exc: ArchitectureV3Conflict) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "action": ACTION,
        "code": "revision_conflict",
        "message": str(exc),
    }
    if exc.state is not None:
        payload.update({
            "current_revision_number": int(
                exc.state["persistence_revision"]
            ),
            "current_state_hash": exc.state["state_hash"],
        })
    return payload
