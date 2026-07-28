from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.engine_manifest import build_engine_manifest
from api.middleware.auth import require_admin
from api.routers import admin


def test_manifest_describes_all_workload_branches():
    manifest = build_engine_manifest()
    branches = manifest["questionnaire"]["branches"]

    assert manifest["engine"]["execution_model"] == "deterministic"
    assert manifest["engine"]["llm_decision_authority"] is False
    assert {branch["workload"] for branch in branches} == {
        "coding",
        "internal_copilot",
        "hosting",
        "customer_facing",
        "process_automation",
        "marketplace",
    }
    assert all(branch["question_count"] > 0 for branch in branches)


def test_manifest_component_catalog_is_complete():
    manifest = build_engine_manifest()
    components = manifest["catalog"]["components"]

    assert manifest["summary"]["components"] == len(components)
    assert all(component["activation"] for component in components)
    assert all(component["monthly_planning_base_usd"] > 0 for component in components)
    assert all(check["ok"] for check in manifest["checks"])


def test_coding_branch_does_not_ask_for_deployed_agents():
    manifest = build_engine_manifest()
    coding = next(
        branch
        for branch in manifest["questionnaire"]["branches"]
        if branch["workload"] == "coding"
    )
    paths = {question["path"] for question in coding["questions"]}

    assert "workload_profile.deployed_agents" not in paths
    assert "workload_profile.developers" in paths
    assert "workload_profile.concurrent_sessions" in paths


def test_admin_engine_endpoint_returns_manifest():
    app = FastAPI()
    app.include_router(admin.router)
    app.dependency_overrides[require_admin] = lambda: {
        "sub": "admin-user",
        "cognito:groups": ["admin"],
    }

    response = TestClient(app).get("/admin/engine")

    assert response.status_code == 200
    assert response.json()["engine"]["schema_version"] == "2.0"
