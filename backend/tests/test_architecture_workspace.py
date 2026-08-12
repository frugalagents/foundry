from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.auth import get_current_user
from api.engine import agents as engine_agents
from api.routers import architecture


USER = {
    "sub": "architecture-user",
    "custom:tenant_id": "tenant-one",
    "cognito:groups": ["user"],
}
OTHER_USER = {
    "sub": "other-user",
    "custom:tenant_id": "tenant-one",
    "cognito:groups": ["user"],
}
OTHER_TENANT = {
    "sub": "architecture-user",
    "custom:tenant_id": "tenant-two",
    "cognito:groups": ["user"],
}
ADMIN_USER = {
    "sub": "admin-user",
    "custom:tenant_id": "tenant-one",
    "cognito:groups": ["admin"],
}
CUSTOMER_ID = "cust-owned"
SESSION_ONE_ID = "sess-one"
SESSION_TWO_ID = "sess-two"
DEMO_CUSTOMER_ID = "cust-demo"
DEMO_SESSION_ID = "sess-demo"

_GET_PERSISTED_STATE = architecture.db.get_architecture_workspace_state
_INITIALIZE_PERSISTED_STATE = (
    architecture.db.initialize_architecture_workspace_state
)
_UPDATE_PERSISTED_STATE = architecture.db.update_architecture_workspace_state


class MemoryArchitectureStore:
    def __init__(self):
        self.items: dict[tuple[str, str, str], dict] = {}
        self.revisions: dict[tuple[str, str, str, int], dict] = {}

    @staticmethod
    def _key(
        tenant_id: str,
        owner_id: str,
        scope_id: str = "standalone",
    ) -> tuple[str, str, str]:
        return tenant_id, owner_id, scope_id

    def get(self, tenant_id: str, owner_id: str, scope_id: str = "standalone"):
        item = self.items.get(self._key(tenant_id, owner_id, scope_id))
        return deepcopy(item) if item else None

    def initialize(self, **values):
        key = self._key(
            values["tenant_id"],
            values["owner_id"],
            values.get("scope_id", "standalone"),
        )
        if key not in self.items:
            self.items[key] = {
                "workspace_id": values["workspace_id"],
                "tenant_id": values["tenant_id"],
                "created_by": values["owner_id"],
                "scope_id": values.get("scope_id", "standalone"),
                "answers": deepcopy(values["answers"]),
                "persistence_revision": 1,
                "state_hash": values["state_hash"],
                "as_of": values["as_of"],
                "created_at": "2026-07-30T00:00:00+00:00",
            }
            self.revisions[(*key, 1)] = {
                "item_type": "architecture_workspace_revision",
                **deepcopy(self.items[key]),
                "revision_number": 1,
                "parent_revision_number": None,
                "previous_state_hash": None,
                "operation": "initialize",
            }
        return deepcopy(self.items[key])

    def update(self, **values):
        key = self._key(
            values["tenant_id"],
            values["owner_id"],
            values.get("scope_id", "standalone"),
        )
        item = self.items[key]
        if (
            item["persistence_revision"] != values["expected_revision"]
            or item["state_hash"] != values["expected_state_hash"]
        ):
            raise architecture.db.ArchitectureWorkspaceConflict()
        revision_number = values["expected_revision"] + 1
        item.update({
            "answers": deepcopy(values["answers"]),
            "persistence_revision": revision_number,
            "state_hash": values["state_hash"],
        })
        self.revisions[(*key, revision_number)] = {
            "item_type": "architecture_workspace_revision",
            "workspace_id": item["workspace_id"],
            "tenant_id": item["tenant_id"],
            "created_by": item["created_by"],
            "scope_id": item["scope_id"],
            "answers": deepcopy(values["answers"]),
            "revision_number": revision_number,
            "parent_revision_number": revision_number - 1,
            "previous_state_hash": values["expected_state_hash"],
            "state_hash": values["state_hash"],
            "as_of": item["as_of"],
            "operation": values.get("operation", "evaluate"),
            "created_at": (
                f"2026-07-30T00:00:{revision_number:02d}+00:00"
            ),
        }
        return deepcopy(item)

    def get_revision(
        self,
        tenant_id,
        owner_id,
        revision_number,
        scope_id="standalone",
    ):
        item = self.revisions.get(
            (tenant_id, owner_id, scope_id, revision_number)
        )
        return deepcopy(item) if item else None

    def list_revisions(
        self,
        tenant_id,
        owner_id,
        scope_id="standalone",
        *,
        limit=100,
    ):
        key_prefix = tenant_id, owner_id, scope_id
        return [
            deepcopy(item)
            for key, item in sorted(self.revisions.items())
            if key[:3] == key_prefix
        ][:limit]


@pytest.fixture(autouse=True)
def state_store(monkeypatch):
    store = MemoryArchitectureStore()
    monkeypatch.setattr(
        architecture.db,
        "get_architecture_workspace_state",
        store.get,
    )
    monkeypatch.setattr(
        architecture.db,
        "initialize_architecture_workspace_state",
        store.initialize,
    )
    monkeypatch.setattr(
        architecture.db,
        "update_architecture_workspace_state",
        store.update,
    )
    monkeypatch.setattr(
        architecture.db,
        "get_architecture_workspace_revision",
        store.get_revision,
    )
    monkeypatch.setattr(
        architecture.db,
        "list_architecture_workspace_revisions",
        store.list_revisions,
    )
    return store


@pytest.fixture
def scoped_resources(monkeypatch):
    customers = {
        CUSTOMER_ID: {
            "customer_id": CUSTOMER_ID,
            "created_by": USER["sub"],
        },
        "cust-other": {
            "customer_id": "cust-other",
            "created_by": OTHER_USER["sub"],
        },
        DEMO_CUSTOMER_ID: {
            "customer_id": DEMO_CUSTOMER_ID,
            "created_by": "demo-seed",
            "demo_data": True,
        },
    }
    sessions = {
        (CUSTOMER_ID, SESSION_ONE_ID): {
            "customer_id": CUSTOMER_ID,
            "session_id": SESSION_ONE_ID,
            "created_by": USER["sub"],
        },
        (CUSTOMER_ID, SESSION_TWO_ID): {
            "customer_id": CUSTOMER_ID,
            "session_id": SESSION_TWO_ID,
            "created_by": USER["sub"],
        },
        (CUSTOMER_ID, "sess-other"): {
            "customer_id": CUSTOMER_ID,
            "session_id": "sess-other",
            "created_by": OTHER_USER["sub"],
        },
        ("cust-other", "sess-other"): {
            "customer_id": "cust-other",
            "session_id": "sess-other",
            "created_by": OTHER_USER["sub"],
        },
        (DEMO_CUSTOMER_ID, DEMO_SESSION_ID): {
            "customer_id": DEMO_CUSTOMER_ID,
            "session_id": DEMO_SESSION_ID,
            "created_by": "demo-seed",
            "demo_data": True,
        },
    }
    monkeypatch.setattr(
        architecture.db,
        "get_customer",
        lambda customer_id: deepcopy(customers.get(customer_id)),
    )
    monkeypatch.setattr(
        architecture.db,
        "get_session",
        lambda customer_id, session_id: deepcopy(
            sessions.get((customer_id, session_id))
        ),
    )
    return customers, sessions


def _app(*, authenticated: bool, user: dict = USER) -> FastAPI:
    app = FastAPI()
    app.include_router(architecture.router, prefix="/api/v1")
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def _client(user: dict = USER) -> TestClient:
    return TestClient(_app(authenticated=True, user=user))


def _requirements_by_id(payload: dict) -> dict[str, dict]:
    return {
        requirement["requirement_id"]: requirement
        for requirement in payload["requirements"]
    }


def _component_ids(payload: dict) -> set[str]:
    return {
        component["component_id"]
        for plane in payload["architecture"]["planes"]
        for component in plane["components"]
    }


def _scope_query(customer_id: str, session_id: str) -> str:
    return f"?customer_id={customer_id}&session_id={session_id}"


def test_workspace_routes_require_authentication():
    client = TestClient(_app(authenticated=False))

    assert client.get("/api/v1/architecture/workspace").status_code == 401
    assert client.get(
        "/api/v1/architecture/workspace/revisions"
    ).status_code == 401
    assert client.get(
        "/api/v1/architecture/workspace/revisions/1"
    ).status_code == 401
    assert client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {}},
    ).status_code == 401
    assert client.post(
        "/api/v1/architecture/workspace/exports",
        json={},
    ).status_code == 401
    assert client.post(
        "/api/v1/architecture/workspace/reopen",
        json={"package": {}},
    ).status_code == 401


def test_authenticated_get_returns_real_v3_projection():
    response = _client().get("/api/v1/architecture/workspace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "3.0"
    assert payload["workspace"]["workspace_id"].startswith(
        "workspace:coding-platform-"
    )
    assert payload["workspace"]["workspace_id"] != (
        "workspace:coding-platform-demo"
    )
    assert payload["workspace"]["persistence_revision"] == 1
    assert payload["workspace"]["persistence_hash"].startswith("sha256:")
    assert payload["architecture"]["pattern"]["pattern_id"] == (
        "pattern:logical-reference"
    )
    assert payload["revision"]["revision_number"] == 2
    assert payload["projection_hash"]


def test_authenticated_post_applies_answer_and_changes_projection():
    client = _client()
    baseline = client.get("/api/v1/architecture/workspace").json()

    response = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:long-running-workspaces": True}},
    )

    assert response.status_code == 200
    refined = response.json()
    requirement = _requirements_by_id(refined)[
        "requirement:long-running-workspaces"
    ]
    assert requirement["status"] == "answered"
    assert requirement["value"] is True
    assert "component:persistent-workspace" in _component_ids(refined)
    assert refined["revision"]["state_hash"] != baseline["revision"]["state_hash"]
    assert refined["projection_hash"] != baseline["projection_hash"]
    assert (
        refined["architecture"]["summary"]["current_component_count"]
        == baseline["architecture"]["summary"]["current_component_count"] + 1
    )
    assert refined["workspace"]["persistence_revision"] == 2


def test_get_reloads_saved_answers_and_post_merges_incrementally():
    client = _client()
    first = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:long-running-workspaces": True}},
    )
    second = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:model-fallback": True}},
    )
    reloaded = client.get("/api/v1/architecture/workspace")

    assert first.status_code == 200
    assert second.status_code == 200
    assert reloaded.status_code == 200
    requirements = _requirements_by_id(reloaded.json())
    assert requirements["requirement:long-running-workspaces"]["value"] is True
    assert requirements["requirement:model-fallback"]["value"] is True
    assert reloaded.json()["workspace"]["persistence_revision"] == 3
    assert reloaded.json()["projection_hash"] == second.json()["projection_hash"]


def test_workspace_state_is_isolated_by_tenant_and_actor():
    owner_client = _client(USER)
    owner_client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:long-running-workspaces": True}},
    )

    owner = owner_client.get("/api/v1/architecture/workspace").json()
    other_user = _client(OTHER_USER).get(
        "/api/v1/architecture/workspace"
    ).json()
    other_tenant = _client(OTHER_TENANT).get(
        "/api/v1/architecture/workspace"
    ).json()

    assert owner["workspace"]["workspace_id"] != (
        other_user["workspace"]["workspace_id"]
    )
    assert owner["workspace"]["workspace_id"] != (
        other_tenant["workspace"]["workspace_id"]
    )
    assert _requirements_by_id(owner)[
        "requirement:long-running-workspaces"
    ]["value"] is True
    assert _requirements_by_id(other_user)[
        "requirement:long-running-workspaces"
    ]["status"] == "unanswered"
    assert _requirements_by_id(other_tenant)[
        "requirement:long-running-workspaces"
    ]["status"] == "unanswered"


def test_customer_sessions_have_independent_workspaces(scoped_resources):
    client = _client()
    first_scope = _scope_query(CUSTOMER_ID, SESSION_ONE_ID)
    second_scope = _scope_query(CUSTOMER_ID, SESSION_TWO_ID)

    first_initial = client.get(
        f"/api/v1/architecture/workspace{first_scope}"
    ).json()
    second_initial = client.get(
        f"/api/v1/architecture/workspace{second_scope}"
    ).json()
    first_updated = client.post(
        f"/api/v1/architecture/workspace/evaluate{first_scope}",
        json={"answers": {"requirement:long-running-workspaces": True}},
    )
    second_updated = client.post(
        f"/api/v1/architecture/workspace/evaluate{second_scope}",
        json={"answers": {"requirement:model-fallback": True}},
    )

    assert first_updated.status_code == 200
    assert second_updated.status_code == 200
    assert first_initial["workspace"]["workspace_id"] != (
        second_initial["workspace"]["workspace_id"]
    )

    first = client.get(
        f"/api/v1/architecture/workspace{first_scope}"
    ).json()
    second = client.get(
        f"/api/v1/architecture/workspace{second_scope}"
    ).json()
    first_requirements = _requirements_by_id(first)
    second_requirements = _requirements_by_id(second)
    assert first_requirements[
        "requirement:long-running-workspaces"
    ]["value"] is True
    assert first_requirements[
        "requirement:model-fallback"
    ]["status"] == "unanswered"
    assert second_requirements[
        "requirement:long-running-workspaces"
    ]["status"] == "unanswered"
    assert second_requirements[
        "requirement:model-fallback"
    ]["value"] is True
    assert first["workspace"]["persistence_revision"] == 2
    assert second["workspace"]["persistence_revision"] == 2


@pytest.mark.parametrize(
    "query",
    [
        f"?customer_id={CUSTOMER_ID}",
        f"?session_id={SESSION_ONE_ID}",
    ],
)
def test_customer_and_session_scope_must_be_supplied_together(
    query,
    scoped_resources,
):
    response = _client().get(f"/api/v1/architecture/workspace{query}")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "customer_id and session_id must be supplied together"
    )


@pytest.mark.parametrize(
    ("customer_id", "session_id"),
    [
        ("cust-other", "sess-other"),
        (CUSTOMER_ID, "sess-other"),
        ("cust-missing", "sess-missing"),
        (CUSTOMER_ID, "sess-missing"),
    ],
)
def test_cross_owner_and_nonexistent_scopes_are_denied(
    customer_id,
    session_id,
    scoped_resources,
):
    response = _client().get(
        "/api/v1/architecture/workspace"
        + _scope_query(customer_id, session_id)
    )

    assert response.status_code == 404


def test_demo_session_opens_an_independent_workspace_per_user(
    scoped_resources,
):
    query = _scope_query(DEMO_CUSTOMER_ID, DEMO_SESSION_ID)

    first = _client(USER).get(
        f"/api/v1/architecture/workspace{query}"
    )
    second = _client(OTHER_USER).get(
        f"/api/v1/architecture/workspace{query}"
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["workspace"]["workspace_id"] != (
        second.json()["workspace"]["workspace_id"]
    )


def test_admin_cannot_open_cross_owner_non_demo_scope(scoped_resources):
    response = _client(ADMIN_USER).get(
        "/api/v1/architecture/workspace"
        + _scope_query("cust-other", "sess-other")
    )

    assert response.status_code == 403


def test_post_rejects_stale_revision_and_hash():
    client = _client()
    baseline = client.get("/api/v1/architecture/workspace").json()
    base = baseline["workspace"]
    accepted = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={
            "answers": {"requirement:long-running-workspaces": True},
            "base_revision_number": base["persistence_revision"],
            "base_state_hash": base["persistence_hash"],
        },
    )
    stale = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={
            "answers": {"requirement:model-fallback": True},
            "base_revision_number": base["persistence_revision"],
            "base_state_hash": base["persistence_hash"],
        },
    )

    assert accepted.status_code == 200
    assert stale.status_code == 409
    assert stale.json()["detail"]["current_revision_number"] == 2
    reloaded = client.get("/api/v1/architecture/workspace").json()
    assert _requirements_by_id(reloaded)[
        "requirement:model-fallback"
    ]["status"] == "unanswered"


def test_reset_is_deterministic_and_preserves_workspace_identity():
    client = _client()
    baseline = client.get("/api/v1/architecture/workspace").json()
    changed = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:long-running-workspaces": True}},
    ).json()
    changed_head = changed["workspace"]

    reset = client.post(
        "/api/v1/architecture/workspace/reset",
        json={
            "base_revision_number": changed_head["persistence_revision"],
            "base_state_hash": changed_head["persistence_hash"],
        },
    )
    reloaded = client.get("/api/v1/architecture/workspace")

    assert reset.status_code == 200
    assert reloaded.status_code == 200
    reset_payload = reset.json()
    assert reset_payload["workspace"]["workspace_id"] == (
        baseline["workspace"]["workspace_id"]
    )
    assert reset_payload["workspace"]["persistence_revision"] == 3
    assert reset_payload["revision"]["state_hash"] == (
        baseline["revision"]["state_hash"]
    )
    assert _requirements_by_id(reset_payload)[
        "requirement:long-running-workspaces"
    ]["status"] == "unanswered"
    assert reloaded.json()["projection_hash"] == reset_payload["projection_hash"]


def test_dynamodb_helpers_use_scoped_key_and_conditional_head_update(
    monkeypatch,
):
    class RecordingTable:
        def __init__(self):
            self.name = "platform-advisor-main"
            self.meta = SimpleNamespace(client=self)
            self.items = {}
            self.get_calls = []
            self.put_calls = []
            self.transact_calls = []
            self.deserializer = TypeDeserializer()

        @staticmethod
        def _conditional_failure(operation: str):
            return ClientError(
                {
                    "Error": {
                        "Code": "ConditionalCheckFailedException",
                        "Message": "stale",
                    }
                },
                operation,
            )

        def get_item(self, **kwargs):
            self.get_calls.append(kwargs)
            key = (kwargs["Key"]["PK"], kwargs["Key"]["SK"])
            item = self.items.get(key)
            return {"Item": deepcopy(item)} if item else {}

        def put_item(self, **kwargs):
            self.put_calls.append(kwargs)
            item = kwargs["Item"]
            key = (item["PK"], item["SK"])
            if key in self.items:
                raise self._conditional_failure("PutItem")
            self.items[key] = deepcopy(item)
            return {}

        def _deserialize_map(self, values):
            return {
                key: self.deserializer.deserialize(value)
                for key, value in values.items()
            }

        def transact_write_items(self, **kwargs):
            self.transact_calls.append(kwargs)
            update = kwargs["TransactItems"][0]["Update"]
            put = kwargs["TransactItems"][1]["Put"]
            key_data = self._deserialize_map(update["Key"])
            key = (key_data["PK"], key_data["SK"])
            values = self._deserialize_map(
                update["ExpressionAttributeValues"]
            )
            item = self.items.get(key)
            if (
                item is None
                or item["persistence_revision"]
                != values[":expected_revision"]
                or item["state_hash"] != values[":expected_state_hash"]
            ):
                raise ClientError(
                    {
                        "Error": {
                            "Code": "TransactionCanceledException",
                            "Message": "stale",
                        },
                        "CancellationReasons": [
                            {"Code": "ConditionalCheckFailed"},
                            {"Code": "None"},
                        ],
                    },
                    "TransactWriteItems",
                )
            revision = self._deserialize_map(put["Item"])
            revision_key = (revision["PK"], revision["SK"])
            if revision_key in self.items:
                raise self._conditional_failure("TransactWriteItems")
            item.update({
                "answers": deepcopy(values[":answers"]),
                "persistence_revision": values[":new_revision"],
                "state_hash": values[":new_state_hash"],
                "updated_at": values[":updated_at"],
            })
            self.items[revision_key] = revision
            return {}

    table = RecordingTable()
    monkeypatch.setattr(architecture.db, "_get_table", lambda: table)
    initial = _INITIALIZE_PERSISTED_STATE(
        tenant_id="tenant-one",
        owner_id="architecture-user",
        workspace_id="workspace:scoped",
        answers={},
        state_hash="sha256:" + ("1" * 64),
        as_of="2026-07-30",
        scope_id="customer-session-test",
    )
    loaded = _GET_PERSISTED_STATE(
        "tenant-one",
        "architecture-user",
        "customer-session-test",
    )
    updated = _UPDATE_PERSISTED_STATE(
        tenant_id="tenant-one",
        owner_id="architecture-user",
        expected_revision=1,
        expected_state_hash=initial["state_hash"],
        answers={"requirement:model-fallback": True},
        state_hash="sha256:" + ("2" * 64),
        scope_id="customer-session-test",
    )

    assert initial["PK"] == "TENANT#tenant-one#USER#architecture-user"
    assert initial["SK"] == (
        "ARCHITECTURE#CODING-PLATFORM#customer-session-test#HEAD"
    )
    assert initial["scope_id"] == "customer-session-test"
    assert table.put_calls[0]["ConditionExpression"] == (
        "attribute_not_exists(PK) AND attribute_not_exists(SK)"
    )
    assert table.get_calls[0]["ConsistentRead"] is True
    assert loaded["workspace_id"] == "workspace:scoped"
    assert updated["persistence_revision"] == 2
    transaction = table.transact_calls[0]["TransactItems"]
    condition = transaction[0]["Update"]["ConditionExpression"]
    assert "#tenant_id = :tenant_id" in condition
    assert "#created_by = :owner_id" in condition
    assert "#revision = :expected_revision" in condition
    assert "#state_hash = :expected_state_hash" in condition
    assert transaction[1]["Put"]["ConditionExpression"] == (
        "attribute_not_exists(PK) AND attribute_not_exists(SK)"
    )

    with pytest.raises(architecture.db.ArchitectureWorkspaceConflict):
        _UPDATE_PERSISTED_STATE(
            tenant_id="tenant-one",
            owner_id="architecture-user",
            expected_revision=1,
            expected_state_hash=initial["state_hash"],
            answers={"requirement:model-fallback": False},
            state_hash="sha256:" + ("3" * 64),
            scope_id="customer-session-test",
        )

    assert architecture.db._architecture_workspace_key(
        "tenant-one",
        "architecture-user",
    )["SK"] == "ARCHITECTURE#CODING-PLATFORM#HEAD"


def test_post_rejects_unknown_requirement_cleanly():
    response = _client().post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:not-in-catalog": True}},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "unknown requirement in patch: requirement:not-in-catalog"
    )


def test_post_rejects_invalid_allowed_value_cleanly():
    response = _client().post(
        "/api/v1/architecture/workspace/evaluate",
        json={
            "answers": {
                "requirement:execution-placement": "unsupported-placement",
            }
        },
    )

    assert response.status_code == 422
    assert "requirement:execution-placement must be one of" in (
        response.json()["detail"]
    )


def test_post_rejects_invalid_value_type_and_extra_fields():
    client = _client()

    invalid_type = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:developer-count": "many"}},
    )
    extra_field = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {}, "workspace_id": "workspace:other"},
    )

    assert invalid_type.status_code == 422
    assert "requirement:developer-count expects integer" in (
        invalid_type.json()["detail"]
    )
    assert extra_field.status_code == 422


def test_chat_proposes_requirements_without_mutating_workspace(
    monkeypatch,
    state_store,
):
    client = _client()
    baseline = client.get("/api/v1/architecture/workspace").json()
    monkeypatch.setattr(
        engine_agents,
        "interpret_requirements",
        lambda _message, _requirements: {
            "answers": {"requirement:private-connectivity": True},
            "reply": "Private connectivity is proposed.",
            "source": "agent",
        },
    )

    proposal = client.post(
        "/api/v1/architecture/chat",
        json={"message": "All model access must stay on private connectivity."},
    )

    assert proposal.status_code == 200
    assert proposal.json()["proposed_answers"] == {
        "requirement:private-connectivity": True
    }
    stored = state_store.get("tenant-one", "architecture-user")
    assert stored["answers"] == {}
    assert stored["persistence_revision"] == 1

    accepted = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={
            "answers": proposal.json()["proposed_answers"],
            "base_revision_number": baseline["workspace"][
                "persistence_revision"
            ],
            "base_state_hash": baseline["workspace"]["persistence_hash"],
        },
    )

    assert accepted.status_code == 200
    requirements = _requirements_by_id(accepted.json())
    assert requirements["requirement:private-connectivity"]["value"] is True
    assert accepted.json()["workspace"]["persistence_revision"] == 2


def test_scoped_chat_does_not_mutate_workspace(
    monkeypatch,
    state_store,
    scoped_resources,
):
    client = _client()
    query = _scope_query(CUSTOMER_ID, SESSION_ONE_ID)
    initial = client.get(f"/api/v1/architecture/workspace{query}")
    assert initial.status_code == 200
    scope_id = architecture._authorized_scope(
        USER,
        CUSTOMER_ID,
        SESSION_ONE_ID,
    )
    before = state_store.get("tenant-one", USER["sub"], scope_id)

    monkeypatch.setattr(
        engine_agents,
        "interpret_requirements",
        lambda _message, _requirements: {
            "answers": {"requirement:private-connectivity": True},
            "reply": "Private connectivity is proposed.",
            "source": "agent",
        },
    )
    proposal = client.post(
        f"/api/v1/architecture/chat{query}",
        json={"message": "Require private connectivity."},
    )

    assert proposal.status_code == 200
    assert proposal.json()["proposed_answers"] == {
        "requirement:private-connectivity": True
    }
    after = state_store.get("tenant-one", USER["sub"], scope_id)
    assert after == before


def test_workspace_revisions_are_append_only_and_retrievable():
    client = _client()
    initial = client.get("/api/v1/architecture/workspace").json()
    first = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:long-running-workspaces": True}},
    )
    second = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:model-fallback": True}},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    history = client.get(
        "/api/v1/architecture/workspace/revisions"
    )
    assert history.status_code == 200
    revisions = history.json()["revisions"]
    assert [item["revision_number"] for item in revisions] == [1, 2, 3]
    assert revisions[0]["parent_revision_number"] is None
    assert revisions[1]["parent_revision_number"] == 1
    assert revisions[2]["parent_revision_number"] == 2
    assert revisions[1]["previous_state_hash"] == revisions[0]["state_hash"]
    assert revisions[2]["previous_state_hash"] == revisions[1]["state_hash"]
    assert revisions[0]["state_hash"] == initial["workspace"][
        "persistence_hash"
    ]
    assert revisions[0]["answers"] == {}
    assert revisions[1]["answers"] == {
        "requirement:long-running-workspaces": True
    }
    assert revisions[2]["answers"] == {
        "requirement:long-running-workspaces": True,
        "requirement:model-fallback": True,
    }

    old_revision = client.get(
        "/api/v1/architecture/workspace/revisions/2"
    )
    assert old_revision.status_code == 200
    assert old_revision.json() == revisions[1]
    assert history.json()["current_revision_number"] == 3


def test_workspace_noop_and_stale_write_do_not_append_revisions():
    client = _client()
    baseline = client.get("/api/v1/architecture/workspace").json()
    base = baseline["workspace"]
    accepted = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={
            "answers": {"requirement:model-fallback": True},
            "base_revision_number": base["persistence_revision"],
            "base_state_hash": base["persistence_hash"],
        },
    )
    repeated = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:model-fallback": True}},
    )
    stale = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={
            "answers": {"requirement:long-running-workspaces": True},
            "base_revision_number": base["persistence_revision"],
            "base_state_hash": base["persistence_hash"],
        },
    )

    assert accepted.status_code == 200
    assert repeated.status_code == 200
    assert stale.status_code == 409
    history = client.get(
        "/api/v1/architecture/workspace/revisions"
    ).json()
    assert [item["revision_number"] for item in history["revisions"]] == [1, 2]
    assert history["current_revision_number"] == 2


def test_workspace_export_is_complete_deterministic_and_revision_pinned():
    client = _client()
    client.get("/api/v1/architecture/workspace")
    updated = client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {"requirement:private-connectivity": True}},
    )
    assert updated.status_code == 200

    first = client.post(
        "/api/v1/architecture/workspace/exports",
        json={"revision_number": 2},
    )
    second = client.post(
        "/api/v1/architecture/workspace/exports",
        json={"revision_number": 2},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    package = first.json()
    assert package == second.json()
    hash_input = deepcopy(package)
    supplied_hash = hash_input.pop("package_hash")
    assert supplied_hash == architecture.content_hash(hash_input)
    assert package["revision"]["revision_number"] == 2
    assert package["revision"]["state_hash"] == package["solution"][
        "workspace"
    ]["persistence_hash"]
    assert package["inputs"]["answers"] == {
        "requirement:private-connectivity": True
    }
    assert package["pinned_versions"]["catalog_content_hash"].startswith(
        "sha256:"
    )
    assert package["pinned_versions"]["knowledge_release_version"] == "1.4.0"
    assert package["pinned_versions"][
        "knowledge_release_manifest_hash"
    ].startswith("sha256:")
    assert package["pinned_versions"]["deployable_catalog_hash"].startswith(
        "sha256:"
    )
    assert package["pinned_versions"]["projection_hash"] == package[
        "solution"
    ]["projection_hash"]
    assert package["solution"]["deployable_solution"]
    assert package["solution"]["assurance"]


def test_workspace_export_reopens_and_replays_exact_scoped_revision(
    scoped_resources,
):
    client = _client()
    query = _scope_query(CUSTOMER_ID, SESSION_ONE_ID)
    evaluated = client.post(
        f"/api/v1/architecture/workspace/evaluate{query}",
        json={"answers": {"requirement:model-fallback": True}},
    )
    assert evaluated.status_code == 200
    exported = client.post(
        f"/api/v1/architecture/workspace/exports{query}",
        json={},
    )
    assert exported.status_code == 200
    package = exported.json()
    assert package["workspace"]["scope"] == {
        "type": "customer_session",
        "customer_id": CUSTOMER_ID,
        "session_id": SESSION_ONE_ID,
    }

    reopened = client.post(
        f"/api/v1/architecture/workspace/reopen{query}",
        json={"package": package},
    )

    assert reopened.status_code == 200
    verification = reopened.json()
    assert verification["verified"] is True
    assert verification["replay_verified"] is True
    assert verification["package_hash"] == package["package_hash"]
    assert verification["revision_number"] == 2
    assert verification["projection"] == package["solution"]


def test_workspace_reopen_denies_cross_tenant_and_tampered_packages():
    owner_client = _client(USER)
    owner_client.get("/api/v1/architecture/workspace")
    exported = owner_client.post(
        "/api/v1/architecture/workspace/exports",
        json={},
    ).json()

    cross_tenant = _client(OTHER_TENANT).post(
        "/api/v1/architecture/workspace/reopen",
        json={"package": exported},
    )
    assert cross_tenant.status_code == 404

    tampered = deepcopy(exported)
    tampered["inputs"]["answers"] = {
        "requirement:private-connectivity": True
    }
    hash_input = deepcopy(tampered)
    hash_input.pop("package_hash")
    tampered["package_hash"] = architecture.content_hash(hash_input)
    rejected = owner_client.post(
        "/api/v1/architecture/workspace/reopen",
        json={"package": tampered},
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"] == (
        "Customer package does not match its immutable revision"
    )
