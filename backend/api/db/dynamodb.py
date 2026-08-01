"""DynamoDB single-table operations for platform-advisor-main."""
from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import boto3
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "platform-advisor-main")
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT")  # for local dev

_dynamodb = None


def _get_table():
    global _dynamodb
    if _dynamodb is None:
        kwargs: dict = {"region_name": os.environ.get("AWS_REGION", "us-east-1")}
        if DYNAMODB_ENDPOINT:
            kwargs["endpoint_url"] = DYNAMODB_ENDPOINT
        resource = boto3.resource("dynamodb", **kwargs)
        _dynamodb = resource.Table(TABLE_NAME)
    return _dynamodb


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _owned_by(item: dict | None, owner_id: str | None) -> bool:
    return bool(item) and (owner_id is None or item.get("created_by") == owner_id)


def _is_conditional_failure(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def _is_transaction_conflict(exc: ClientError) -> bool:
    code = exc.response.get("Error", {}).get("Code")
    if code == "ConditionalCheckFailedException":
        return True
    if code != "TransactionCanceledException":
        return False
    reasons = exc.response.get("CancellationReasons", ())
    return not reasons or any(
        reason.get("Code") in {
            "ConditionalCheckFailed",
            "TransactionConflict",
        }
        for reason in reasons
    )


class ArchitectureWorkspaceConflict(Exception):
    """The architecture workspace changed after the caller read it."""


# ── Architecture workspace ───────────────────────────────────────────────────

_ARCHITECTURE_WORKSPACE_SK = "ARCHITECTURE#CODING-PLATFORM#HEAD"
_ARCHITECTURE_REVISION_WIDTH = 12


def _architecture_workspace_key(
    tenant_id: str,
    owner_id: str,
    scope_id: str = "standalone",
) -> dict[str, str]:
    # Both values come from authenticated claims, never request parameters.
    sort_key = (
        _ARCHITECTURE_WORKSPACE_SK
        if scope_id == "standalone"
        else f"ARCHITECTURE#CODING-PLATFORM#{scope_id}#HEAD"
    )
    return {
        "PK": f"TENANT#{tenant_id}#USER#{owner_id}",
        "SK": sort_key,
    }


def _architecture_revision_prefix(scope_id: str = "standalone") -> str:
    scope_prefix = (
        "ARCHITECTURE#CODING-PLATFORM"
        if scope_id == "standalone"
        else f"ARCHITECTURE#CODING-PLATFORM#{scope_id}"
    )
    return f"{scope_prefix}#REVISION#"


def _architecture_revision_key(
    tenant_id: str,
    owner_id: str,
    revision_number: int,
    scope_id: str = "standalone",
) -> dict[str, str]:
    return {
        "PK": f"TENANT#{tenant_id}#USER#{owner_id}",
        "SK": (
            f"{_architecture_revision_prefix(scope_id)}"
            f"{revision_number:0{_ARCHITECTURE_REVISION_WIDTH}d}"
        ),
    }


def _architecture_revision_item(
    *,
    tenant_id: str,
    owner_id: str,
    scope_id: str,
    workspace_id: str,
    revision_number: int,
    previous_state_hash: str | None,
    answers: dict[str, Any],
    state_hash: str,
    as_of: str,
    operation: str,
    created_at: str,
) -> dict:
    return {
        **_architecture_revision_key(
            tenant_id,
            owner_id,
            revision_number,
            scope_id,
        ),
        "item_type": "architecture_workspace_revision",
        "workspace_id": workspace_id,
        "tenant_id": tenant_id,
        "created_by": owner_id,
        "scope_id": scope_id,
        "revision_number": revision_number,
        "parent_revision_number": (
            revision_number - 1 if revision_number > 1 else None
        ),
        "previous_state_hash": previous_state_hash,
        "answers": dict(answers),
        "state_hash": state_hash,
        "as_of": as_of,
        "operation": operation,
        "created_at": created_at,
    }


def _serialize_dynamodb_map(value: dict[str, Any]) -> dict[str, Any]:
    serializer = TypeSerializer()
    return {key: serializer.serialize(item) for key, item in value.items()}


def get_architecture_workspace_state(
    tenant_id: str,
    owner_id: str,
    scope_id: str = "standalone",
) -> Optional[dict]:
    """Read one actor's workspace head within its authenticated tenant."""

    response = _get_table().get_item(
        Key=_architecture_workspace_key(tenant_id, owner_id, scope_id),
        ConsistentRead=True,
    )
    item = response.get("Item")
    if (
        not item
        or item.get("tenant_id") != tenant_id
        or item.get("created_by") != owner_id
        or (
            scope_id != "standalone"
            and item.get("scope_id") != scope_id
        )
    ):
        return None
    return item


def initialize_architecture_workspace_state(
    *,
    tenant_id: str,
    owner_id: str,
    workspace_id: str,
    answers: dict[str, Any],
    state_hash: str,
    as_of: str,
    scope_id: str = "standalone",
) -> dict:
    """Create a deterministic workspace head, returning a concurrent winner."""

    table = _get_table()
    now = _now()
    item = {
        **_architecture_workspace_key(tenant_id, owner_id, scope_id),
        "item_type": "architecture_workspace",
        "workspace_id": workspace_id,
        "tenant_id": tenant_id,
        "created_by": owner_id,
        "scope_id": scope_id,
        "answers": dict(answers),
        "persistence_revision": 1,
        "state_hash": state_hash,
        "as_of": as_of,
        "created_at": now,
        "updated_at": now,
    }
    try:
        table.put_item(
            Item=item,
            ConditionExpression=(
                "attribute_not_exists(PK) AND attribute_not_exists(SK)"
            ),
        )
    except ClientError as exc:
        if not _is_conditional_failure(exc):
            raise
        existing = get_architecture_workspace_state(
            tenant_id,
            owner_id,
            scope_id,
        )
        if existing is None:
            raise ArchitectureWorkspaceConflict(
                "workspace initialization raced but no workspace head is readable"
            )
        item = existing

    if int(item["persistence_revision"]) == 1:
        revision = _architecture_revision_item(
            tenant_id=tenant_id,
            owner_id=owner_id,
            scope_id=scope_id,
            workspace_id=item["workspace_id"],
            revision_number=1,
            previous_state_hash=None,
            answers=item["answers"],
            state_hash=item["state_hash"],
            as_of=item["as_of"],
            operation="initialize",
            created_at=item.get("created_at", now),
        )
        try:
            table.put_item(
                Item=revision,
                ConditionExpression=(
                    "attribute_not_exists(PK) AND attribute_not_exists(SK)"
                ),
            )
        except ClientError as exc:
            if not _is_conditional_failure(exc):
                raise
    return item


def get_architecture_workspace_revision(
    tenant_id: str,
    owner_id: str,
    revision_number: int,
    scope_id: str = "standalone",
) -> Optional[dict]:
    """Read one immutable revision within an authenticated workspace scope."""

    response = _get_table().get_item(
        Key=_architecture_revision_key(
            tenant_id,
            owner_id,
            revision_number,
            scope_id,
        ),
        ConsistentRead=True,
    )
    item = response.get("Item")
    if (
        not item
        or item.get("item_type") != "architecture_workspace_revision"
        or item.get("tenant_id") != tenant_id
        or item.get("created_by") != owner_id
        or item.get("scope_id") != scope_id
        or int(item.get("revision_number", 0)) != revision_number
    ):
        return None
    return item


def list_architecture_workspace_revisions(
    tenant_id: str,
    owner_id: str,
    scope_id: str = "standalone",
    *,
    limit: int = 100,
) -> list[dict]:
    """List immutable revisions in ascending revision order."""

    table = _get_table()
    items: list[dict] = []
    query_args: dict[str, Any] = {
        "KeyConditionExpression": (
            "#pk = :pk AND begins_with(#sk, :revision_prefix)"
        ),
        "ExpressionAttributeNames": {
            "#pk": "PK",
            "#sk": "SK",
        },
        "ExpressionAttributeValues": {
            ":pk": f"TENANT#{tenant_id}#USER#{owner_id}",
            ":revision_prefix": _architecture_revision_prefix(scope_id),
        },
        "ConsistentRead": True,
        "ScanIndexForward": True,
        "Limit": limit,
    }
    while len(items) < limit:
        response = table.query(**query_args)
        for item in response.get("Items", []):
            if (
                item.get("item_type") == "architecture_workspace_revision"
                and item.get("tenant_id") == tenant_id
                and item.get("created_by") == owner_id
                and item.get("scope_id") == scope_id
            ):
                items.append(item)
                if len(items) == limit:
                    break
        last_key = response.get("LastEvaluatedKey")
        if not last_key or len(items) == limit:
            break
        query_args["ExclusiveStartKey"] = last_key
    return items


def update_architecture_workspace_state(
    *,
    tenant_id: str,
    owner_id: str,
    expected_revision: int,
    expected_state_hash: str,
    answers: dict[str, Any],
    state_hash: str,
    scope_id: str = "standalone",
    operation: str = "evaluate",
) -> dict:
    """Atomically append a revision and conditionally advance workspace HEAD."""

    table = _get_table()
    current = table.get_item(
        Key=_architecture_workspace_key(tenant_id, owner_id, scope_id),
        ConsistentRead=True,
    ).get("Item")
    if (
        current is None
        or current.get("tenant_id") != tenant_id
        or current.get("created_by") != owner_id
        or (
            current.get("scope_id") != scope_id
            and not (
                scope_id == "standalone"
                and current.get("scope_id") is None
            )
        )
        or int(current["persistence_revision"]) != expected_revision
        or current["state_hash"] != expected_state_hash
    ):
        raise ArchitectureWorkspaceConflict(
            "architecture workspace revision is stale"
        )
    now = _now()
    revision = _architecture_revision_item(
        tenant_id=tenant_id,
        owner_id=owner_id,
        scope_id=scope_id,
        workspace_id=current["workspace_id"],
        revision_number=expected_revision + 1,
        previous_state_hash=expected_state_hash,
        answers=answers,
        state_hash=state_hash,
        as_of=current["as_of"],
        operation=operation,
        created_at=now,
    )
    try:
        table.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": table.name,
                        "Key": _serialize_dynamodb_map(
                            _architecture_workspace_key(
                                tenant_id,
                                owner_id,
                                scope_id,
                            )
                        ),
                        "UpdateExpression": (
                            "SET #answers = :answers, "
                            "#revision = :new_revision, "
                            "#state_hash = :new_state_hash, "
                            "#updated_at = :updated_at"
                        ),
                        "ExpressionAttributeNames": {
                            "#answers": "answers",
                            "#revision": "persistence_revision",
                            "#state_hash": "state_hash",
                            "#updated_at": "updated_at",
                            "#tenant_id": "tenant_id",
                            "#created_by": "created_by",
                            "#pk": "PK",
                        },
                        "ExpressionAttributeValues": _serialize_dynamodb_map({
                            ":answers": dict(answers),
                            ":expected_revision": expected_revision,
                            ":new_revision": expected_revision + 1,
                            ":expected_state_hash": expected_state_hash,
                            ":new_state_hash": state_hash,
                            ":updated_at": now,
                            ":tenant_id": tenant_id,
                            ":owner_id": owner_id,
                        }),
                        "ConditionExpression": (
                            "attribute_exists(#pk) "
                            "AND #tenant_id = :tenant_id "
                            "AND #created_by = :owner_id "
                            "AND #revision = :expected_revision "
                            "AND #state_hash = :expected_state_hash"
                        ),
                    }
                },
                {
                    "Put": {
                        "TableName": table.name,
                        "Item": _serialize_dynamodb_map(revision),
                        "ConditionExpression": (
                            "attribute_not_exists(PK) "
                            "AND attribute_not_exists(SK)"
                        ),
                    }
                },
            ]
        )
    except ClientError as exc:
        if _is_transaction_conflict(exc):
            raise ArchitectureWorkspaceConflict(
                "architecture workspace revision is stale"
            ) from exc
        raise
    saved = table.get_item(
        Key=_architecture_workspace_key(tenant_id, owner_id, scope_id),
        ConsistentRead=True,
    ).get("Item")
    if saved is None:
        raise RuntimeError("architecture workspace HEAD disappeared after commit")
    return saved


def save_architecture_decision_record(
    *,
    tenant_id: str,
    owner_id: str,
    record: dict[str, Any],
    scope_id: str = "standalone",
) -> dict:
    """Persist the latest Decision Record on the owned workspace head.

    The full provenance record (answers, proposal, guard verdict, citations,
    version stamps) is the audit substrate for the honest-risk mitigation.
    Stored as latest-wins; history could later move to child items.
    """
    response = _get_table().update_item(
        Key=_architecture_workspace_key(tenant_id, owner_id, scope_id),
        UpdateExpression="SET #rec = :rec, #updated_at = :updated_at",
        ExpressionAttributeNames={
            "#rec": "decision_record",
            "#updated_at": "updated_at",
            "#tenant_id": "tenant_id",
            "#created_by": "created_by",
            "#pk": "PK",
        },
        ExpressionAttributeValues={
            ":rec": record,
            ":updated_at": _now(),
            ":tenant_id": tenant_id,
            ":owner_id": owner_id,
        },
        ConditionExpression=(
            "attribute_exists(#pk) AND #tenant_id = :tenant_id "
            "AND #created_by = :owner_id"
        ),
        ReturnValues="ALL_NEW",
    )
    return response["Attributes"]


def save_architecture_engine_answers(
    *,
    tenant_id: str,
    owner_id: str,
    answers: dict[str, Any],
    scope_id: str = "standalone",
) -> dict:
    """Replace engine answers on an owned workspace head.

    Kept for callers that explicitly commit validated engine answers. Chat only
    proposes answers and does not call this persistence helper.
    """
    response = _get_table().update_item(
        Key=_architecture_workspace_key(tenant_id, owner_id, scope_id),
        UpdateExpression="SET #answers = :answers, #updated_at = :updated_at",
        ExpressionAttributeNames={
            "#answers": "answers",
            "#updated_at": "updated_at",
            "#tenant_id": "tenant_id",
            "#created_by": "created_by",
            "#pk": "PK",
        },
        ExpressionAttributeValues={
            ":answers": dict(answers),
            ":updated_at": _now(),
            ":tenant_id": tenant_id,
            ":owner_id": owner_id,
        },
        ConditionExpression=(
            "attribute_exists(#pk) AND #tenant_id = :tenant_id "
            "AND #created_by = :owner_id"
        ),
        ReturnValues="ALL_NEW",
    )
    return response["Attributes"]


# ── Customers ─────────────────────────────────────────────────────────────────

def create_customer(name: str, industry: str, contact_email: str,
                    created_by: str, notes: str = "") -> dict:
    table = _get_table()
    customer_id = _new_id("cust")
    now = _now()
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": "METADATA",
        "customer_id": customer_id,
        "name": name,
        "industry": industry,
        "contact_email": contact_email,
        "notes": notes,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "session_count": 0,
        "GSI1PK": "CUSTOMERS",
        "GSI1SK": now,
    }
    table.put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(PK)",
    )
    return item


def get_customer(customer_id: str, owner_id: str | None = None) -> Optional[dict]:
    table = _get_table()
    resp = table.get_item(Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"})
    item = resp.get("Item")
    return item if _owned_by(item, owner_id) else None


def list_customers(
    limit: int = 50,
    created_by: str | None = None,
    *,
    include_demo: bool = False,
) -> list[dict]:
    table = _get_table()
    items: list[dict] = []
    query_args: dict[str, Any] = {
        "IndexName": "GSI1",
        "KeyConditionExpression": "GSI1PK = :pk",
        "ExpressionAttributeValues": {":pk": "CUSTOMERS"},
        "Limit": limit,
        "ScanIndexForward": False,
    }
    while len(items) < limit:
        resp = table.query(**query_args)
        for item in resp.get("Items", []):
            if (
                created_by is None
                or item.get("created_by") == created_by
                or (include_demo and item.get("demo_data") is True)
            ):
                items.append(item)
                if len(items) == limit:
                    break
        last_key = resp.get("LastEvaluatedKey")
        if not last_key or (created_by is None and not include_demo):
            break
        query_args["ExclusiveStartKey"] = last_key
    return items


def update_customer(
    customer_id: str,
    updates: dict,
    owner_id: str | None = None,
) -> Optional[dict]:
    table = _get_table()
    updates = dict(updates)
    updates["updated_at"] = _now()
    expr_parts = [f"#{k} = :{k}" for k in updates]
    update_expr = "SET " + ", ".join(expr_parts)
    names = {f"#{k}": k for k in updates}
    values = {f":{k}": v for k, v in updates.items()}
    names["#pk"] = "PK"
    conditions = ["attribute_exists(#pk)"]
    if owner_id is not None:
        names["#created_by"] = "created_by"
        values[":owner_id"] = owner_id
        conditions.append("#created_by = :owner_id")
    try:
        resp = table.update_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ConditionExpression=" AND ".join(conditions),
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")
    except ClientError as exc:
        if _is_conditional_failure(exc):
            return None
        logger.error("update_customer error: %s", exc)
        return None


def delete_customer(customer_id: str, owner_id: str | None = None) -> bool:
    table = _get_table()
    try:
        customer_pk = f"CUSTOMER#{customer_id}"
        customer = table.get_item(
            Key={"PK": customer_pk, "SK": "METADATA"},
            ConsistentRead=True,
        ).get("Item")
        if not _owned_by(customer, owner_id):
            return False

        customer_items = _query_partition(table, customer_pk)
        session_ids = [
            item["session_id"]
            for item in customer_items
            if item.get("SK", "").startswith("SESSION#") and item.get("session_id")
        ]
        with table.batch_writer() as batch:
            for session_id in session_ids:
                for panel in _query_partition(table, f"SESSION#{session_id}"):
                    batch.delete_item(Key={"PK": panel["PK"], "SK": panel["SK"]})
            for item in customer_items:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        return True
    except ClientError as exc:
        logger.error("delete_customer error: %s", exc)
        return False


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(customer_id: str, created_by: str,
                   title: str = "", description: str = "") -> dict:
    table = _get_table()
    session_id = _new_id("sess")
    now = _now()
    if not title:
        title = f"Session {now[:10]}"
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"SESSION#{session_id}",
        "session_id": session_id,
        "customer_id": customer_id,
        "title": title,
        "description": description,
        "status": "active",
        "current_step": 0,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "GSI1PK": "SESSIONS",
        "GSI1SK": now,
    }
    table.put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
    )
    # Increment customer session count
    try:
        table.update_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"},
            UpdateExpression="ADD session_count :one",
            ExpressionAttributeNames={"#pk": "PK", "#created_by": "created_by"},
            ExpressionAttributeValues={":one": 1, ":created_by": created_by},
            ConditionExpression=(
                "attribute_exists(#pk) AND #created_by = :created_by"
            ),
        )
    except ClientError as exc:
        logger.warning("Failed to increment customer session count: %s", exc)
    return item


def get_session(
    customer_id: str,
    session_id: str,
    owner_id: str | None = None,
) -> Optional[dict]:
    table = _get_table()
    resp = table.get_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"}
    )
    item = resp.get("Item")
    return item if _owned_by(item, owner_id) else None


def list_sessions(customer_id: str, created_by: str | None = None) -> list[dict]:
    table = _get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": f"CUSTOMER#{customer_id}",
            ":sk_prefix": "SESSION#",
        },
        ScanIndexForward=False,
    )
    items = resp.get("Items", [])
    if created_by is not None:
        items = [item for item in items if item.get("created_by") == created_by]
    return items


def update_session(
    customer_id: str,
    session_id: str,
    updates: dict,
    owner_id: str | None = None,
) -> Optional[dict]:
    table = _get_table()
    updates = dict(updates)
    updates["updated_at"] = _now()
    expr_parts = [f"#{k} = :{k}" for k in updates]
    update_expr = "SET " + ", ".join(expr_parts)
    names = {f"#{k}": k for k in updates}
    values = {f":{k}": v for k, v in updates.items()}
    names["#pk"] = "PK"
    conditions = ["attribute_exists(#pk)"]
    if owner_id is not None:
        names["#created_by"] = "created_by"
        values[":owner_id"] = owner_id
        conditions.append("#created_by = :owner_id")
    try:
        resp = table.update_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ConditionExpression=" AND ".join(conditions),
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")
    except ClientError as exc:
        if _is_conditional_failure(exc):
            return None
        logger.error("update_session error: %s", exc)
        return None


def delete_session(
    customer_id: str,
    session_id: str,
    owner_id: str | None = None,
) -> bool:
    table = _get_table()
    try:
        session_key = {
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"SESSION#{session_id}",
        }
        session = table.get_item(Key=session_key, ConsistentRead=True).get("Item")
        if not _owned_by(session, owner_id):
            return False

        panels = _query_partition(table, f"SESSION#{session_id}")
        with table.batch_writer() as batch:
            for panel in panels:
                batch.delete_item(Key={"PK": panel["PK"], "SK": panel["SK"]})
            batch.delete_item(Key=session_key)
        # Decrement customer session count
        try:
            table.update_item(
                Key={"PK": f"CUSTOMER#{customer_id}", "SK": "METADATA"},
                UpdateExpression="ADD session_count :neg",
                ExpressionAttributeValues={":neg": -1},
            )
        except ClientError:
            pass
        return True
    except ClientError as exc:
        logger.error("delete_session error: %s", exc)
        return False


# ── Panel States ──────────────────────────────────────────────────────────────

def save_panel_state(
    session_id: str,
    step: int,
    panel_type: str,
    data: dict,
    *,
    customer_id: str | None = None,
    owner_id: str | None = None,
) -> bool:
    if customer_id is not None and not get_session(customer_id, session_id, owner_id):
        return False
    table = _get_table()
    now = _now()
    item = {
        "PK": f"SESSION#{session_id}",
        "SK": f"PANEL#{step:02d}",
        "session_id": session_id,
        "step": step,
        "panel_type": panel_type,
        "data": data,
        "updated_at": now,
    }
    if customer_id is not None:
        item["customer_id"] = customer_id
    if owner_id is not None:
        item["created_by"] = owner_id
    table.put_item(Item=item)
    return True


def get_panel_states(
    session_id: str,
    *,
    customer_id: str | None = None,
    owner_id: str | None = None,
) -> list[dict]:
    if customer_id is not None and not get_session(customer_id, session_id, owner_id):
        return []
    table = _get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": f"SESSION#{session_id}",
            ":sk_prefix": "PANEL#",
        },
    )
    return resp.get("Items", [])


def _query_partition(table: Any, partition_key: str) -> list[dict]:
    """Read an entire partition, following DynamoDB pagination."""
    items: list[dict] = []
    query_args: dict[str, Any] = {
        "KeyConditionExpression": "PK = :pk",
        "ExpressionAttributeValues": {":pk": partition_key},
    }
    while True:
        response = table.query(**query_args)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        query_args["ExclusiveStartKey"] = last_key


# ── Admin metrics ─────────────────────────────────────────────────────────────

def get_admin_metrics() -> dict:
    """Scan-based metrics — acceptable for admin dashboard (low frequency)."""
    table = _get_table()
    try:
        customers = table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": "CUSTOMERS"},
            Select="COUNT",
        )
        sessions_all = table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": "SESSIONS"},
        )
        all_sessions = sessions_all.get("Items", [])
        today = _now()[:10]
        active = sum(1 for s in all_sessions if s.get("status") == "active")
        today_count = sum(1 for s in all_sessions if s.get("created_at", "")[:10] == today)

        return {
            "total_customers": customers.get("Count", 0),
            "total_sessions": len(all_sessions),
            "active_sessions": active,
            "sessions_today": today_count,
            "top_patterns": [],
            "top_industries": [],
        }
    except ClientError as exc:
        logger.error("get_admin_metrics error: %s", exc)
        return {
            "total_customers": 0, "total_sessions": 0,
            "active_sessions": 0, "sessions_today": 0,
            "top_patterns": [], "top_industries": [],
        }
