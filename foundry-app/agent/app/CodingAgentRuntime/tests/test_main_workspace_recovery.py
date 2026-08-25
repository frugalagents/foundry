from __future__ import annotations

import asyncio
import os
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "bedrock_agentcore.runtime" not in sys.modules:
    runtime_module = types.ModuleType("bedrock_agentcore.runtime")

    class FakeBedrockAgentCoreApp:
        def __init__(self):
            import logging
            self.logger = logging.getLogger("test-agentcore")

        def entrypoint(self, fn):
            return fn

        def run(self):
            return None

    runtime_module.BedrockAgentCoreApp = FakeBedrockAgentCoreApp
    bedrock_agentcore_module = types.ModuleType("bedrock_agentcore")
    bedrock_agentcore_module.runtime = runtime_module
    sys.modules["bedrock_agentcore"] = bedrock_agentcore_module
    sys.modules["bedrock_agentcore.runtime"] = runtime_module

if "strands" not in sys.modules:
    strands_module = types.ModuleType("strands")
    strands_models_module = types.ModuleType("strands.models")

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)

    def fake_tool(fn):
        return fn

    class FakeBedrockModel:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)

    strands_module.Agent = FakeAgent
    strands_module.tool = fake_tool
    strands_models_module.BedrockModel = FakeBedrockModel
    sys.modules["strands"] = strands_module
    sys.modules["strands.models"] = strands_models_module

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import main as main_module  # noqa: E402
from architecture_case import build_architecture_case_payload  # noqa: E402
from okf_compiler import OKFCompileError, OKFValidationIssue  # noqa: E402
from main import (  # noqa: E402
    _extract_open_questions_from_text,
    _initialize_okf_contract,
    _is_explicit_blueprint_request,
    _maybe_emit_engine_architecture,
    _persist_architecture_case_shadow,
    _prepare_workspace_for_turn,
    _project_workspace_from_architecture_case,
    _should_recover_blueprint,
)
from knowledge_loader import load_knowledge_base  # noqa: E402


KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def test_extract_open_questions_from_mixed_reply():
    reply = """Blueprint is in the panel.
One question still worth a fast answer before you build - do any compliance frameworks (HIPAA, ITAR, PCI, SOX) apply?
Everything else can stay as-is.
"""
    assert _extract_open_questions_from_text(reply) == [
        "One question still worth a fast answer before you build - do any compliance frameworks (HIPAA, ITAR, PCI, SOX) apply?"
    ]


def test_is_explicit_blueprint_request_matches_direct_user_ask():
    assert _is_explicit_blueprint_request("please generate blueprint now") is True
    assert _is_explicit_blueprint_request("can you create the technical blueprint?") is True
    assert _is_explicit_blueprint_request("what compliance frameworks apply?") is False


def test_should_recover_blueprint_on_explicit_request_even_with_open_questions():
    workspace = {
        "blueprint_markdown": "",
        "open_questions": ["Which compliance regime applies?"],
        "recommendation": "Use a governed multi-harness portfolio.",
        "decisions": ["Use a shared model gateway."],
        "facts": ["AWS is the primary cloud."],
    }
    assert _should_recover_blueprint("generate blueprint", workspace) is True


def test_should_recover_blueprint_when_workspace_is_coherent_and_no_questions_remain():
    workspace = {
        "blueprint_markdown": "",
        "open_questions": [],
        "recommendation": "Use a governed multi-harness portfolio.",
        "implementation_plan": ["Pilot", "Expand"],
        "decisions": ["Use a shared model gateway."],
        "facts": ["AWS is the primary cloud."],
    }
    assert _should_recover_blueprint("continue", workspace) is True


def test_prepare_workspace_for_turn_seeds_guided_question_state_and_recommendation():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    workspace, changed = _prepare_workspace_for_turn(
        kb,
        {"stage": "discovery", "facts": [], "decisions": [], "risks": []},
        "We already use Copilot and Cursor, some repos are ITAR-controlled, and one BU wants local execution.",
    )

    assert changed is True
    assert workspace["facts"]
    assert workspace["recommendation"]
    assert workspace["question_state"][0]["decision_domain"] == "execution_boundary"
    assert workspace["recommendation_state"]["next_best_question"].startswith(
        "Are the export-controlled repositories isolated"
    )


def test_prepare_workspace_for_turn_clears_stale_single_standard_reasoning_on_brownfield_signal():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    workspace, changed = _prepare_workspace_for_turn(
        kb,
        {
            "stage": "solutioning",
            "recommendation": "Use Claude Code Enterprise as the single standard harness.",
            "facts": ["One default tool is assumed."],
            "operating_model": "single_standard",
            "decisions": ["The target operating model is one standard harness for the default developer population."],
            "risks": ["Migration sequencing is still open."],
            "question_state": [],
            "traversal_state": {
                "customer_confirmed_facts": [
                    {
                        "key": "operating_model",
                        "value": "single_standard",
                        "status": "confirmed",
                        "source": "operating_model",
                        "fact_text": "",
                    }
                ]
            },
        },
        "We already use GitHub Copilot and Cursor across engineering teams.",
    )

    assert changed is True
    assert workspace["recommendation"] != "Use Claude Code Enterprise as the single standard harness."
    assert any("Current tools in scope: GitHub Copilot, Cursor." == item for item in workspace["facts"])
    assert all("single standard harness for the default developer population" not in item.lower() for item in workspace["decisions"])


def test_project_workspace_from_architecture_case_prefers_canonical_case_view():
    projected = _project_workspace_from_architecture_case(
        {
            "stage": "solutioning",
            "recommendation": "Old recommendation",
            "blueprint_markdown": "",
            "facts": ["Legacy fact"],
            "question_state": [],
            "open_questions": [],
            "decisions": ["Legacy decision"],
            "risks": ["Legacy risk"],
            "operating_model": "single_standard",
        },
        {
            "stage": "blueprint",
            "current_recommendation": "Use one default harness with formal exception paths.",
            "operating_model": "default_plus_exceptions",
            "facts": [{"id": "f1", "statement": "Current tools in scope: GitHub Copilot, Cursor."}],
            "open_questions": [
                {
                    "id": "q1",
                    "text": "Which teams need exception lanes?",
                    "why_it_matters": "This decides the governance carve-out.",
                    "blocking": True,
                    "decision_domain": "operating_model",
                    "status": "open",
                    "answer": "",
                    "source": "engine",
                }
            ],
            "decisions": [{"id": "d1", "statement": "Adopt one default harness with formal exception paths."}],
            "risks": [{"id": "r1", "risk": "Exception approvals could become a bottleneck."}],
            "artifacts": {"blueprint_markdown": "## Architecture\nTarget state"},
        },
    )

    assert projected["stage"] == "blueprint"
    assert projected["recommendation"] == "Use one default harness with formal exception paths."
    assert projected["blueprint_markdown"] == "## Architecture\nTarget state"
    assert projected["operating_model"] == "default_plus_exceptions"
    assert projected["facts"] == ["Current tools in scope: GitHub Copilot, Cursor."]
    assert projected["open_questions"] == ["Which teams need exception lanes?"]
    assert projected["question_state"][0]["why_it_matters"] == "This decides the governance carve-out."
    assert projected["decisions"] == ["Adopt one default harness with formal exception paths."]
    assert projected["risks"] == ["Exception approvals could become a bottleneck."]


def test_project_workspace_from_architecture_case_clears_stale_workspace_lists_when_case_is_authoritative():
    projected = _project_workspace_from_architecture_case(
        {
            "stage": "solutioning",
            "recommendation": "Old recommendation",
            "facts": ["Old fact"],
            "question_state": [{"id": "q1", "text": "Old question", "status": "open"}],
            "open_questions": ["Old question"],
            "decisions": ["Old decision"],
            "risks": ["Old risk"],
            "operating_model": "single_standard",
        },
        {
            "stage": "solutioning",
            "current_recommendation": "New recommendation",
            "operating_model": "multi_harness_governed",
            "facts": [],
            "open_questions": [],
            "decisions": [],
            "risks": [],
            "artifacts": {"blueprint_markdown": ""},
        },
    )

    assert projected["facts"] == []
    assert projected["question_state"] == []
    assert projected["open_questions"] == []
    assert projected["decisions"] == []
    assert projected["risks"] == []


def test_engine_architecture_preserves_richer_existing_layout_but_refreshes_semantics():
    panel_queue: asyncio.Queue[str] = asyncio.Queue()
    existing_canvas = {
        "stage": "full",
        "nodes": [
            {"id": "surface-entry", "type": "arch", "label": "IDE surfaces", "sublabel": "Entry points currently in scope: GitHub Copilot, Cursor", "icon": "monitor", "color": "#5161ff", "layer": "surface", "kind": "developer_surface"},
            {"id": "harness-cursor", "type": "arch", "label": "Cursor", "sublabel": "Approved exception harness for high-velocity teams", "icon": "mouse-pointer-2", "color": "#7c4dff", "layer": "harness", "kind": "interactive_harness"},
            {"id": "harness-copilot", "type": "arch", "label": "GitHub Copilot", "sublabel": "Default harness for the general developer population", "icon": "sparkles", "color": "#7c4dff", "layer": "harness", "kind": "interactive_harness"},
            {"id": "gateway-model", "type": "arch", "label": "Model gateway", "sublabel": "Shared provider and routing boundary", "icon": "split", "color": "#0ea5e9", "layer": "gateway", "kind": "model_gateway"},
        ],
        "edges": [],
        "baseline_node_ids": ["surface-entry", "harness-copilot", "gateway-model"],
        "architecture_artifact": {
            "executive_summary": "Concrete architecture with explicit harness cards.",
            "customizations": [{"id": "cursor-lane", "title": "Cursor lane", "layer": "harness", "added_component_ids": ["harness-cursor"], "reason": "Cursor remains an approved exception lane.", "tradeoff": "", "triggered_by": ["brownfield estate"]}],
            "supporting_lanes": [{"id": "current-estate", "title": "Estate harnesses", "narrative": "Concrete harness cards remain visible.", "component_ids": ["harness-cursor", "harness-copilot"]}],
            "decisions": [],
            "risks": [],
            "rollout": [],
            "baseline": {"name": "Concrete baseline", "layers": []},
            "primary_flow": [],
            "cross_cutting_controls": [],
        },
    }

    retained = _maybe_emit_engine_architecture(
        workspace={
            "stage": "solutioning",
            "recommendation": "Use one default harness with formal exception governance.",
            "facts": ["Brownfield rollout.", "General engineering baseline.", "Execution boundary still under review."],
            "operating_model": "default_plus_exceptions",
            "question_state": [{"id": "q1", "text": "Which teams need exception lanes?", "status": "open", "blocking": True}],
            "decisions": ["Default harness still needs confirmation."],
        },
        panel_queue=panel_queue,
        customer_id="",
        session_id="",
        existing_canvas=existing_canvas,
    )

    assert retained is not None
    assert retained["nodes"] == existing_canvas["nodes"]
    assert retained["edges"] == existing_canvas["edges"]
    assert retained["baseline_node_ids"] == existing_canvas["baseline_node_ids"]
    assert retained["stage"] == "baseline"
    assert retained["architecture_artifact"]["executive_summary"] != existing_canvas["architecture_artifact"]["executive_summary"]
    assert retained["architecture_artifact"]["decisions"]
    assert not panel_queue.empty()


def test_initialize_okf_contract_raises_when_compile_fails_and_bypass_is_disabled(monkeypatch):
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    monkeypatch.setattr(main_module, "_okf_contract_initialized", False)
    monkeypatch.setattr(main_module, "_okf_release_id", "")
    monkeypatch.delenv("OKF_ALLOW_INVALID", raising=False)

    def _raise_compile(_knowledge_dir):
        raise OKFCompileError(
            [
                OKFValidationIssue(
                    type="asymmetric_alternative",
                    node="option-a",
                    field="typed_edges.alternatives",
                    target="option-b",
                    message="alternative target 'option-b' does not link back to 'option-a'",
                    source_file="option-a.md",
                )
            ]
        )

    monkeypatch.setattr(main_module, "compile_okf_release", _raise_compile)

    with pytest.raises(RuntimeError, match="OKF contract initialization failed"):
        _initialize_okf_contract(kb)

    assert main_module._okf_contract_initialized is False
    assert main_module._okf_release_id == ""


def test_initialize_okf_contract_allows_explicit_bypass_for_invalid_graph(monkeypatch):
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    monkeypatch.setattr(main_module, "_okf_contract_initialized", False)
    monkeypatch.setattr(main_module, "_okf_release_id", "")
    monkeypatch.setenv("OKF_ALLOW_INVALID", "1")

    def _raise_compile(_knowledge_dir):
        raise OKFCompileError(
            [
                OKFValidationIssue(
                    type="asymmetric_alternative",
                    node="option-a",
                    field="typed_edges.alternatives",
                    target="option-b",
                    message="alternative target 'option-b' does not link back to 'option-a'",
                    source_file="option-a.md",
                )
            ]
        )

    monkeypatch.setattr(main_module, "compile_okf_release", _raise_compile)

    _initialize_okf_contract(kb)

    assert main_module._okf_contract_initialized is True
    assert main_module._okf_release_id == "invalid:bypass"


def test_persist_architecture_case_shadow_skips_duplicate_payload(monkeypatch):
    latest_case = build_architecture_case_payload(
        case_id="cust1/sess1",
        revision=2,
        okf_release_id="okf.release.v1alpha1:abc123",
        workspace={"stage": "discovery", "recommendation": "Resolve identity boundary first."},
        canvas_snapshot=None,
    )
    writes: list[dict] = []

    monkeypatch.setattr(main_module, "_okf_release_id", "okf.release.v1alpha1:abc123")
    monkeypatch.setattr(main_module, "get_latest_architecture_case", lambda customer_id, session_id: latest_case)
    monkeypatch.setattr(
        main_module,
        "put_architecture_case_snapshot",
        lambda customer_id, session_id, architecture_case: writes.append(architecture_case),
    )

    result = _persist_architecture_case_shadow(
        customer_id="cust1",
        session_id="sess1",
        workspace={"stage": "discovery", "recommendation": "Resolve identity boundary first."},
        canvas_snapshot=None,
    )

    assert result == latest_case
    assert writes == []


def test_persist_architecture_case_shadow_increments_revision_on_change(monkeypatch):
    latest_case = build_architecture_case_payload(
        case_id="cust1/sess1",
        revision=2,
        okf_release_id="okf.release.v1alpha1:abc123",
        workspace={"stage": "discovery", "recommendation": "Resolve identity boundary first."},
        canvas_snapshot=None,
    )
    writes: list[dict] = []

    monkeypatch.setattr(main_module, "_okf_release_id", "okf.release.v1alpha1:def456")
    monkeypatch.setattr(main_module, "get_latest_architecture_case", lambda customer_id, session_id: latest_case)
    monkeypatch.setattr(
        main_module,
        "put_architecture_case_snapshot",
        lambda customer_id, session_id, architecture_case: writes.append(architecture_case),
    )

    result = _persist_architecture_case_shadow(
        customer_id="cust1",
        session_id="sess1",
        workspace={"stage": "solutioning", "recommendation": "Adopt one default harness with formal exception paths."},
        canvas_snapshot={
            "nodes": [{"id": "harness-default", "label": "Default harness", "layer": "harness"}],
            "edges": [],
            "stage": "skeleton",
        },
    )

    assert result is not None
    assert result["revision"] == 3
    assert result["okf_release_id"] == "okf.release.v1alpha1:def456"
    assert writes and writes[0]["revision"] == 3
