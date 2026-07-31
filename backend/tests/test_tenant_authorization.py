from __future__ import annotations

import asyncio
import base64
import json

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.middleware import auth
from api.middleware.auth import get_current_user
from api.routers import customers, sessions, stream


OWNER = {"sub": "owner-user", "cognito:groups": ["user"]}
OTHER = {"sub": "other-user", "cognito:groups": ["user"]}
ADMIN = {"sub": "admin-user", "cognito:groups": ["admin"]}


def _customer(owner: str = "owner-user") -> dict:
    return {
        "customer_id": "cust_1",
        "name": "Customer",
        "industry": "Technology",
        "created_by": owner,
        "created_at": "2026-07-30T10:00:00+00:00",
        "updated_at": "2026-07-30T10:00:00+00:00",
        "session_count": 1,
    }


def _session(owner: str = "owner-user") -> dict:
    return {
        "session_id": "sess_1",
        "customer_id": "cust_1",
        "title": "Blueprint",
        "description": "",
        "status": "active",
        "current_step": 0,
        "created_by": owner,
        "created_at": "2026-07-30T10:00:00+00:00",
        "updated_at": "2026-07-30T10:00:00+00:00",
    }


def _demo_customer() -> dict:
    item = _customer("demo-seed")
    item["demo_data"] = True
    return item


def _demo_session() -> dict:
    item = _session("demo-seed")
    item["demo_data"] = True
    return item


def _client(user: dict) -> TestClient:
    app = FastAPI()
    app.include_router(customers.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")
    app.include_router(stream.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _dev_token(payload: dict) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


def test_dev_mode_accepts_existing_eventsource_query_token(monkeypatch):
    monkeypatch.setattr(auth, "DEV_MODE", True)
    token = _dev_token(OWNER)
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/run",
        "headers": [],
        "query_string": f"token={token}".encode(),
    })

    user = asyncio.run(get_current_user(request, None))

    assert user["sub"] == "owner-user"


def test_authenticated_claims_without_actor_id_fail_closed(monkeypatch):
    monkeypatch.setattr(auth, "DEV_MODE", True)
    token = _dev_token({"cognito:groups": ["user"]})
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/customers",
        "headers": [],
        "query_string": f"token={token}".encode(),
    })

    try:
        asyncio.run(get_current_user(request, None))
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("Expected missing actor identifier to be rejected")


def test_standard_user_list_is_filtered_to_owned_customers(monkeypatch):
    seen = {}

    def list_customers(*, created_by=None, include_demo=False):
        seen["created_by"] = created_by
        seen["include_demo"] = include_demo
        return [_customer(), _customer("other-user"), _demo_customer()]

    monkeypatch.setattr(customers.db, "list_customers", list_customers)

    response = _client(OWNER).get("/api/v1/customers")

    assert response.status_code == 200
    assert seen["created_by"] == "owner-user"
    assert seen["include_demo"] is True
    assert [item["created_by"] for item in response.json()] == [
        "owner-user",
        "demo-seed",
    ]


def test_standard_user_cannot_read_another_users_customer(monkeypatch):
    monkeypatch.setattr(customers.db, "get_customer", lambda _customer_id: _customer())

    response = _client(OTHER).get("/api/v1/customers/cust_1")

    assert response.status_code == 404


def test_admin_can_read_but_cannot_update_another_users_customer(monkeypatch):
    monkeypatch.setattr(customers.db, "get_customer", lambda _customer_id: _customer())

    client = _client(ADMIN)
    read_response = client.get("/api/v1/customers/cust_1")
    update_response = client.patch(
        "/api/v1/customers/cust_1",
        json={"name": "Changed"},
    )

    assert read_response.status_code == 200
    assert update_response.status_code == 403


def test_standard_user_can_read_but_cannot_modify_shared_demo(monkeypatch):
    monkeypatch.setattr(
        customers.db,
        "get_customer",
        lambda _customer_id: _demo_customer(),
    )
    monkeypatch.setattr(
        sessions.db,
        "get_customer",
        lambda _customer_id: _demo_customer(),
    )
    monkeypatch.setattr(
        sessions.db,
        "get_session",
        lambda _customer_id, _session_id: _demo_session(),
    )
    monkeypatch.setattr(
        sessions.db,
        "get_panel_states",
        lambda _session_id, **kwargs: [{"step": 1, "panel_type": "intake"}],
    )

    client = _client(OTHER)

    assert client.get("/api/v1/customers/cust_1").status_code == 200
    assert client.get("/api/v1/customers/cust_1/sessions/sess_1").status_code == 200
    assert (
        client.get("/api/v1/customers/cust_1/sessions/sess_1/panels").status_code
        == 200
    )
    assert (
        client.patch(
            "/api/v1/customers/cust_1",
            json={"name": "Changed"},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            "/api/v1/customers/cust_1/sessions/sess_1",
            json={"title": "Changed"},
        ).status_code
        == 404
    )


def test_session_and_panel_routes_enforce_parent_and_session_ownership(monkeypatch):
    monkeypatch.setattr(sessions.db, "get_customer", lambda _customer_id: _customer())
    monkeypatch.setattr(
        sessions.db,
        "get_session",
        lambda _customer_id, _session_id: _session(),
    )

    client = _client(OTHER)

    assert client.get("/api/v1/customers/cust_1/sessions/sess_1").status_code == 404
    assert (
        client.get("/api/v1/customers/cust_1/sessions/sess_1/panels").status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/customers/cust_1/sessions/sess_1/inputs",
            json={"answers": {"region": "us-east-1"}},
        ).status_code
        == 404
    )


def test_admin_session_access_is_read_only_for_other_users(monkeypatch):
    monkeypatch.setattr(sessions.db, "get_customer", lambda _customer_id: _customer())
    monkeypatch.setattr(
        sessions.db,
        "get_session",
        lambda _customer_id, _session_id: _session(),
    )

    client = _client(ADMIN)
    read_response = client.get("/api/v1/customers/cust_1/sessions/sess_1")
    update_response = client.patch(
        "/api/v1/customers/cust_1/sessions/sess_1",
        json={"title": "Changed"},
    )

    assert read_response.status_code == 200
    assert update_response.status_code == 403


def test_stream_mutation_and_drilldown_read_follow_owner_contract(monkeypatch):
    customer = _customer()
    session = _session()
    session["pipeline_ctx"] = {
        "assessment_result": {
            "components": [{"id": "gateway", "name": "Gateway"}],
            "trace": [],
        },
    }
    monkeypatch.setattr(stream.db, "get_customer", lambda _customer_id: customer)
    monkeypatch.setattr(
        stream.db,
        "get_session",
        lambda _customer_id, _session_id: session,
    )

    other_client = _client(OTHER)
    admin_client = _client(ADMIN)

    assert (
        other_client.get(
            "/api/v1/sessions/cust_1/sess_1/run",
            params={"user_message": "continue"},
        ).status_code
        == 404
    )
    assert (
        admin_client.get(
            "/api/v1/sessions/cust_1/sess_1/run",
            params={"user_message": "continue"},
        ).status_code
        == 403
    )
    drilldown = admin_client.get(
        "/api/v1/sessions/cust_1/sess_1/drilldown",
        params={"component_id": "gateway"},
    )
    assert drilldown.status_code == 200
    assert drilldown.json()["component_id"] == "gateway"
