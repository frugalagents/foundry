from __future__ import annotations

from copy import deepcopy

import pytest
from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.auth import get_current_user
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

_GET_PERSISTED_STATE = architecture.db.get_architecture_workspace_state
_INITIALIZE_PERSISTED_STATE = (
    architecture.db.initialize_architecture_workspace_state
)
_UPDATE_PERSISTED_STATE = architecture.db.update_architecture_workspace_state


class MemoryArchitectureStore:
    def __init__(self):
        self.items: dict[tuple[str, str], dict] = {}

    @staticmethod
    def _key(tenant_id: str, owner_id: str) -> tuple[str, str]:
        return tenant_id, owner_id

    def get(self, tenant_id: str, owner_id: str):
        item = self.items.get(self._key(tenant_id, owner_id))
        return deepcopy(item) if item else None

    def initialize(self, **values):
        key = self._key(values["tenant_id"], values["owner_id"])
        if key not in self.items:
            self.items[key] = {
                "workspace_id": values["workspace_id"],
                "tenant_id": values["tenant_id"],
                "created_by": values["owner_id"],
                "answers": deepcopy(values["answers"]),
                "persistence_revision": 1,
                "state_hash": values["state_hash"],
                "as_of": values["as_of"],
            }
        return deepcopy(self.items[key])

    def update(self, **values):
        key = self._key(values["tenant_id"], values["owner_id"])
        item = self.items[key]
        if (
            item["persistence_revision"] != values["expected_revision"]
            or item["state_hash"] != values["expected_state_hash"]
        ):
            raise architecture.db.ArchitectureWorkspaceConflict()
        item.update({
            "answers": deepcopy(values["answers"]),
            "persistence_revision": values["expected_revision"] + 1,
            "state_hash": values["state_hash"],
        })
        return deepcopy(item)


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
    return store


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


def test_workspace_routes_require_authentication():
    client = TestClient(_app(authenticated=False))

    assert client.get("/api/v1/architecture/workspace").status_code == 401
    assert client.post(
        "/api/v1/architecture/workspace/evaluate",
        json={"answers": {}},
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
            self.item = None
            self.get_calls = []
            self.put_calls = []
            self.update_calls = []

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
            return {"Item": deepcopy(self.item)} if self.item else {}

        def put_item(self, **kwargs):
            self.put_calls.append(kwargs)
            if self.item is not None:
                raise self._conditional_failure("PutItem")
            self.item = deepcopy(kwargs["Item"])
            return {}

        def update_item(self, **kwargs):
            self.update_calls.append(kwargs)
            values = kwargs["ExpressionAttributeValues"]
            if (
                self.item is None
                or self.item["persistence_revision"]
                != values[":expected_revision"]
                or self.item["state_hash"] != values[":expected_state_hash"]
            ):
                raise self._conditional_failure("UpdateItem")
            self.item.update({
                "answers": deepcopy(values[":answers"]),
                "persistence_revision": values[":new_revision"],
                "state_hash": values[":new_state_hash"],
                "updated_at": values[":updated_at"],
            })
            return {"Attributes": deepcopy(self.item)}

    table = RecordingTable()
    monkeypatch.setattr(architecture.db, "_get_table", lambda: table)
    initial = _INITIALIZE_PERSISTED_STATE(
        tenant_id="tenant-one",
        owner_id="architecture-user",
        workspace_id="workspace:scoped",
        answers={},
        state_hash="sha256:" + ("1" * 64),
        as_of="2026-07-30",
    )
    loaded = _GET_PERSISTED_STATE("tenant-one", "architecture-user")
    updated = _UPDATE_PERSISTED_STATE(
        tenant_id="tenant-one",
        owner_id="architecture-user",
        expected_revision=1,
        expected_state_hash=initial["state_hash"],
        answers={"requirement:model-fallback": True},
        state_hash="sha256:" + ("2" * 64),
    )

    assert initial["PK"] == "TENANT#tenant-one#USER#architecture-user"
    assert initial["SK"] == "ARCHITECTURE#CODING-PLATFORM#HEAD"
    assert table.put_calls[0]["ConditionExpression"] == (
        "attribute_not_exists(PK) AND attribute_not_exists(SK)"
    )
    assert table.get_calls[0]["ConsistentRead"] is True
    assert loaded["workspace_id"] == "workspace:scoped"
    assert updated["persistence_revision"] == 2
    condition = table.update_calls[0]["ConditionExpression"]
    assert "#tenant_id = :tenant_id" in condition
    assert "#created_by = :owner_id" in condition
    assert "#revision = :expected_revision" in condition
    assert "#state_hash = :expected_state_hash" in condition

    with pytest.raises(architecture.db.ArchitectureWorkspaceConflict):
        _UPDATE_PERSISTED_STATE(
            tenant_id="tenant-one",
            owner_id="architecture-user",
            expected_revision=1,
            expected_state_hash=initial["state_hash"],
            answers={"requirement:model-fallback": False},
            state_hash="sha256:" + ("3" * 64),
        )


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
