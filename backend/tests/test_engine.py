"""Engine tests — run offline (no Bedrock): the propose path falls back to the
deterministic constraint-compliant selection, so these assert the guard + record
behavior deterministically regardless of model availability."""
from __future__ import annotations

import os

os.environ.setdefault("AWS_REGION", "us-east-1")

from api.engine import generate_architecture  # noqa: E402
from api.engine import agents  # noqa: E402


def _force_offline(monkeypatch):
    # Make the LLM unreachable so we test the deterministic guarantees.
    monkeypatch.setattr(agents, "_propose_via_llm", lambda a, b: None)
    monkeypatch.setattr(agents, "converse", lambda *a, **k: None)
    monkeypatch.setattr(agents, "converse_json", lambda *a, **k: None)


def test_managed_only_never_selects_self_hosted(monkeypatch):
    _force_offline(monkeypatch)
    out = generate_architecture(
        workspace_id="ws",
        answers={"operational-posture": "managed-only"},
        boxes=["model-gateway", "harness"],
        created_at="2026-07-31T00:00:00Z",
    )
    assert out["guard"]["passed"] is True
    labels = {s["box_id"]: s["chosen"] for s in out["stack"]}
    # no self-hosted option should be chosen under a managed-only mandate
    assert "self-hosted" not in labels["model-gateway"].lower()
    assert "self-managed" not in labels["harness"].lower()


def test_decision_record_is_complete_and_stamped(monkeypatch):
    _force_offline(monkeypatch)
    out = generate_architecture(
        workspace_id="ws-2",
        answers={},
        boxes=["model-gateway"],
        created_at="2026-07-31T00:00:00Z",
    )
    rec = out["decision_record"]
    assert rec["workspace_id"] == "ws-2"
    assert rec["guard_version"]
    assert rec["proposal"]["components"]
    assert rec["model_stamp"]["model_id"]
    assert rec["reproducibility"].startswith("reproducible-with-trace")


def test_self_hosted_cascade_is_surfaced(monkeypatch):
    # Force the agent to pick a self-hosted gateway with no constraint blocking it.
    _force_offline(monkeypatch)
    monkeypatch.setattr(
        agents, "_propose_via_llm",
        lambda a, b: {"selections": [
            {"box_id": "model-gateway", "value": "litellm"},
            {"box_id": "harness", "value": "eks"},
        ]},
    )
    out = generate_architecture(
        workspace_id="ws-3",
        answers={},  # no managed-only constraint → self-hosted allowed
        boxes=["model-gateway", "harness"],
        created_at="2026-07-31T00:00:00Z",
    )
    assert out["guard"]["passed"] is True
    notes = " ".join(c["note"] for c in out["cascades"])
    assert "hosting" in notes.lower() or "EKS" in notes


def test_self_hosted_vetoed_and_corrected_under_managed_only(monkeypatch):
    _force_offline(monkeypatch)
    # agent tries a self-hosted pick, but customer is managed-only → guard forces correction
    monkeypatch.setattr(
        agents, "_propose_via_llm",
        lambda a, b: {"selections": [{"box_id": "model-gateway", "value": "litellm"}]},
    )
    out = generate_architecture(
        workspace_id="ws-4",
        answers={"operational-posture": "managed-only"},
        boxes=["model-gateway"],
        created_at="2026-07-31T00:00:00Z",
    )
    assert out["guard"]["passed"] is True
    assert out["source"] == "agent+guard-corrected"
    assert "self-hosted" not in out["stack"][0]["chosen"].lower()
