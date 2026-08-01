from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

import architecture_v3_runtime
from advisor_core.v3.demo import build_demo_workspace
from advisor_core.v3.models import content_hash
from advisor_core.v3.projection import build_frontend_projection
from architecture_v3_runtime import (
    ACTION,
    ArchitectureV3Conflict,
    ArchitectureV3IdempotencyConflict,
    ArchitectureV3RuntimeAdapter,
)


AS_OF = date(2026, 7, 30)


def _transaction_failure() -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "TransactionCanceledException",
                "Message": "transaction condition failed",
            },
            "CancellationReasons": [{"Code": "ConditionalCheckFailed"}],
        },
        "TransactWriteItems",
    )


def _conditional_failure(operation: str) -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "conditional failure",
            }
        },
        operation,
    )


class MemoryClient:
    def __init__(self, table: "MemoryTable"):
        self._table = table

    def transact_write_items(self, *, TransactItems):
        return self._table.transact_write_items(TransactItems=TransactItems)


class MemoryMeta:
    def __init__(self, table: "MemoryTable"):
        self.client = MemoryClient(table)


class MemoryTable:
    def __init__(self):
        self.name = "platform-advisor-test"
        self.meta = MemoryMeta(self)
        self.items: dict[tuple[str, str], dict] = {}
        self.transaction_calls: list[list[dict]] = []
        self.fail_next_transaction = False
        self.deserializer = TypeDeserializer()

    @staticmethod
    def _key(key: dict[str, str]) -> tuple[str, str]:
        return key["PK"], key["SK"]

    def _deserialize(self, values: dict) -> dict:
        return {
            key: self.deserializer.deserialize(value)
            for key, value in values.items()
        }

    def get_item(self, *, Key, ConsistentRead=False):
        item = self.items.get(self._key(Key))
        return {"Item": deepcopy(item)} if item else {}

    def put_item(self, *, Item, ConditionExpression):
        key = self._key(Item)
        if key in self.items:
            raise _conditional_failure("PutItem")
        self.items[key] = deepcopy(Item)
        return {}

    def transact_write_items(self, *, TransactItems):
        self.transaction_calls.append(deepcopy(TransactItems))
        if self.fail_next_transaction:
            self.fail_next_transaction = False
            raise _transaction_failure()

        pending_puts: list[tuple[tuple[str, str], dict]] = []
        pending_update: tuple[tuple[str, str], dict] | None = None
        for operation in TransactItems:
            if "Put" in operation:
                item = self._deserialize(operation["Put"]["Item"])
                key = self._key(item)
                if key in self.items or any(
                    existing_key == key for existing_key, _ in pending_puts
                ):
                    raise _transaction_failure()
                pending_puts.append((key, item))
                continue

            update = operation["Update"]
            key_data = self._deserialize(update["Key"])
            key = self._key(key_data)
            values = self._deserialize(
                update["ExpressionAttributeValues"]
            )
            item = self.items.get(key)
            if (
                item is None
                or item["tenant_id"] != values[":tenant_id"]
                or item["created_by"] != values[":owner_id"]
                or item["scope_id"] != values[":scope_id"]
                or item["persistence_revision"]
                != values[":expected_revision"]
                or item["state_hash"] != values[":expected_state_hash"]
            ):
                raise _transaction_failure()
            pending_update = (key, {
                "answers": deepcopy(values[":answers"]),
                "persistence_revision": values[":new_revision"],
                "state_hash": values[":new_state_hash"],
                "current_revision_sk": values[":current_revision_sk"],
                "updated_at": values[":updated_at"],
            })

        if pending_update is not None:
            key, values = pending_update
            self.items[key].update(values)
        for key, item in pending_puts:
            self.items[key] = deepcopy(item)
        return {}


def _adapter(
    table: MemoryTable,
    *,
    session_id: str = "sess-one",
) -> ArchitectureV3RuntimeAdapter:
    return ArchitectureV3RuntimeAdapter(
        table,
        tenant_id="tenant-one",
        owner_id="actor-one",
        customer_id="cust-one",
        session_id=session_id,
        today=AS_OF,
    )


def _request(operation: str, **values):
    return {
        "schema_version": "3.0",
        "operation": operation,
        **values,
    }


def _mutation(
    operation: str,
    projection: dict,
    *,
    idempotency_key: str,
    **values,
) -> dict:
    return _request(
        operation,
        base_revision_number=projection["workspace"][
            "persistence_revision"
        ],
        base_state_hash=projection["workspace"]["persistence_hash"],
        idempotency_key=idempotency_key,
        **values,
    )


def _requirements(projection: dict) -> dict[str, dict]:
    return {
        item["requirement_id"]: item
        for item in projection["requirements"]
    }


def _items_of_type(table: MemoryTable, item_type: str) -> list[dict]:
    return [
        item
        for item in table.items.values()
        if item["item_type"] == item_type
    ]


def test_get_matches_shared_projection_and_atomically_pins_initial_revision():
    table = MemoryTable()
    result = _adapter(table).execute(_request("get"))
    projection = result["projection"]

    catalog, workspace = build_demo_workspace(AS_OF, requirement_values={})
    expected = build_frontend_projection(workspace, catalog)
    expected["workspace"]["workspace_id"] = projection["workspace"][
        "workspace_id"
    ]
    expected["workspace"]["persistence_revision"] = 1
    expected["workspace"]["persistence_hash"] = projection["workspace"][
        "persistence_hash"
    ]
    expected.pop("projection_hash")
    expected["projection_hash"] = content_hash(expected)

    assert result["action"] == ACTION
    assert result["contract_version"] == "3.0"
    assert projection == expected
    assert len(table.transaction_calls[0]) == 2
    revision = _items_of_type(
        table,
        "architecture_workspace_revision",
    )[0]
    assert architecture_v3_runtime._from_dynamodb(
        revision["projection_packet"]
    ) == projection
    for field in (
        "catalog_hash",
        "ruleset_hash",
        "engine_hash",
        "projection_hash",
    ):
        assert revision[field].startswith("sha256:")


@pytest.mark.parametrize(
    "values, message",
    [
        ({}, "require base_revision_number"),
        (
            {"base_revision_number": 1},
            "require base_revision_number",
        ),
        (
            {"base_state_hash": "sha256:" + ("0" * 64)},
            "require base_revision_number",
        ),
        (
            {
                "base_revision_number": 1,
                "base_state_hash": "sha256:" + ("0" * 64),
            },
            "require an idempotency_key",
        ),
    ],
)
def test_mutations_reject_missing_or_partial_controls(values, message):
    with pytest.raises(ValueError, match=message):
        _adapter(MemoryTable()).execute(_request("evaluate", **values))


def test_evaluate_appends_revisions_and_reloads_stored_packet():
    table = MemoryTable()
    adapter = _adapter(table)
    baseline = adapter.execute(_request("get"))["projection"]

    first = adapter.execute(_mutation(
        "evaluate",
        baseline,
        idempotency_key="eval-first",
        answers={"requirement:long-running-workspaces": True},
    ))["projection"]
    second = adapter.execute(_mutation(
        "evaluate",
        first,
        idempotency_key="eval-second",
        answers={"requirement:model-fallback": True},
    ))["projection"]
    reloaded = adapter.execute(_request("get"))["projection"]

    requirements = _requirements(reloaded)
    assert requirements["requirement:long-running-workspaces"]["value"] is True
    assert requirements["requirement:model-fallback"]["value"] is True
    assert reloaded == second
    assert reloaded["workspace"]["persistence_revision"] == 3
    revisions = _items_of_type(
        table,
        "architecture_workspace_revision",
    )
    assert [item["revision_number"] for item in revisions] == [1, 2, 3]
    assert architecture_v3_runtime._from_dynamodb(
        revisions[0]["projection_packet"]
    ) == baseline
    assert len(_items_of_type(
        table,
        "architecture_workspace_idempotency",
    )) == 2


def test_get_replays_stored_packet_without_current_catalogs(monkeypatch):
    table = MemoryTable()
    adapter = _adapter(table)
    baseline = adapter.execute(_request("get"))["projection"]
    saved = adapter.execute(_mutation(
        "evaluate",
        baseline,
        idempotency_key="replay-one",
        answers={"requirement:model-fallback": True},
    ))["projection"]

    def unavailable(*_args, **_kwargs):
        raise AssertionError("live catalog path must not run during replay")

    monkeypatch.setattr(
        architecture_v3_runtime,
        "build_demo_workspace",
        unavailable,
    )

    assert adapter.execute(_request("get"))["projection"] == saved


def test_duplicate_idempotency_key_returns_exact_result_without_new_write():
    table = MemoryTable()
    adapter = _adapter(table)
    baseline = adapter.execute(_request("get"))["projection"]
    request = _mutation(
        "evaluate",
        baseline,
        idempotency_key="duplicate-one",
        answers={"requirement:model-fallback": True},
    )

    first = adapter.execute(request)
    transaction_count = len(table.transaction_calls)
    second = adapter.execute(request)

    assert second == first
    assert len(table.transaction_calls) == transaction_count
    assert len(_items_of_type(
        table,
        "architecture_workspace_revision",
    )) == 2


def test_reused_idempotency_key_with_different_payload_fails_closed():
    table = MemoryTable()
    adapter = _adapter(table)
    baseline = adapter.execute(_request("get"))["projection"]
    adapter.execute(_mutation(
        "evaluate",
        baseline,
        idempotency_key="reused-key",
        answers={"requirement:model-fallback": True},
    ))
    stored_before = deepcopy(table.items)

    with pytest.raises(
        ArchitectureV3IdempotencyConflict,
        match="different request",
    ):
        adapter.execute(_mutation(
            "evaluate",
            baseline,
            idempotency_key="reused-key",
            answers={"requirement:model-fallback": False},
        ))

    assert table.items == stored_before


def test_stale_patch_fails_closed_without_overwriting_state():
    table = MemoryTable()
    adapter = _adapter(table)
    baseline = adapter.execute(_request("get"))["projection"]
    adapter.execute(_mutation(
        "evaluate",
        baseline,
        idempotency_key="winning-change",
        answers={"requirement:model-fallback": True},
    ))
    stored_before = deepcopy(table.items)

    with pytest.raises(ArchitectureV3Conflict) as caught:
        adapter.execute(_mutation(
            "evaluate",
            baseline,
            idempotency_key="stale-change",
            answers={"requirement:model-fallback": False},
        ))

    assert caught.value.state["persistence_revision"] == 2
    assert table.items == stored_before


def test_transaction_race_leaves_no_partial_revision_or_idempotency_record():
    table = MemoryTable()
    adapter = _adapter(table)
    baseline = adapter.execute(_request("get"))["projection"]
    table.fail_next_transaction = True

    with pytest.raises(ArchitectureV3Conflict):
        adapter.execute(_mutation(
            "evaluate",
            baseline,
            idempotency_key="racing-change",
            answers={"requirement:model-fallback": True},
        ))

    assert len(_items_of_type(
        table,
        "architecture_workspace_revision",
    )) == 1
    assert not _items_of_type(
        table,
        "architecture_workspace_idempotency",
    )
    head = _items_of_type(table, "architecture_workspace")[0]
    assert head["persistence_revision"] == 1


def test_invalid_requirement_fails_before_mutation_transaction():
    table = MemoryTable()
    adapter = _adapter(table)
    baseline = adapter.execute(_request("get"))["projection"]
    transaction_count = len(table.transaction_calls)

    with pytest.raises(ValueError, match="unknown requirement"):
        adapter.execute(_mutation(
            "evaluate",
            baseline,
            idempotency_key="invalid-req",
            answers={"requirement:not-in-catalog": True},
        ))

    assert len(table.transaction_calls) == transaction_count
    assert _items_of_type(table, "architecture_workspace")[0]["answers"] == {}


def test_customer_sessions_have_independent_workspace_heads():
    table = MemoryTable()
    first = _adapter(table, session_id="sess-one")
    second = _adapter(table, session_id="sess-two")
    first_baseline = first.execute(_request("get"))["projection"]

    first.execute(_mutation(
        "evaluate",
        first_baseline,
        idempotency_key="session-one",
        answers={"requirement:model-fallback": True},
    ))
    second_projection = second.execute(_request("get"))["projection"]

    assert len(_items_of_type(table, "architecture_workspace")) == 2
    assert _requirements(second_projection)[
        "requirement:model-fallback"
    ]["status"] == "unanswered"


def test_reset_is_audited_and_get_rejects_mutation_fields():
    table = MemoryTable()
    adapter = _adapter(table)
    baseline = adapter.execute(_request("get"))["projection"]
    changed = adapter.execute(_mutation(
        "evaluate",
        baseline,
        idempotency_key="change-before-reset",
        answers={"requirement:model-fallback": True},
    ))["projection"]

    reset = adapter.execute(_mutation(
        "reset",
        changed,
        idempotency_key="reset-workspace",
    ))["projection"]

    assert _requirements(reset)["requirement:model-fallback"][
        "status"
    ] == "unanswered"
    assert reset["workspace"]["persistence_revision"] == 3
    with pytest.raises(ValueError, match="get does not accept"):
        adapter.execute(_request(
            "get",
            answers={"requirement:model-fallback": True},
        ))
    with pytest.raises(ValueError, match="reset does not accept"):
        adapter.execute(_mutation(
            "reset",
            reset,
            idempotency_key="bad-reset",
            answers={"requirement:model-fallback": True},
        ))


def test_tampered_revision_packet_is_rejected():
    table = MemoryTable()
    adapter = _adapter(table)
    adapter.execute(_request("get"))
    revision = _items_of_type(
        table,
        "architecture_workspace_revision",
    )[0]
    revision["projection_packet"]["workspace"]["workspace_id"] = "tampered"

    with pytest.raises(ValueError, match="integrity check"):
        adapter.execute(_request("get"))
