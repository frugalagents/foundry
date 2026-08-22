"""Tests for the conditional-knowledge auto-loading wired into the system
prompt. This is the mechanism that makes the skill file's documented
three-tier traversal model (mandate/conditional/probe) actually automatic
instead of relying on the model to guess query_knowledge keywords.
"""
from __future__ import annotations
import os
import sys
import types

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

from main import augment_system_prompt_with_conditional_knowledge  # noqa: E402
from knowledge_loader import KnowledgeNode  # noqa: E402


class FakeKnowledgeBase:
    """Stand-in that records what conversation text it was queried with."""

    def __init__(self, nodes: list[KnowledgeNode]):
        self._nodes = nodes
        self.last_query: str | None = None
        self.related_nodes: list[KnowledgeNode] = []

    def conditional_nodes_for(self, conversation_text: str) -> list[KnowledgeNode]:
        self.last_query = conversation_text
        return self._nodes

    def related_nodes_for(self, node_paths: list[str], *, max_results: int = 6) -> list[KnowledgeNode]:
        _ = (node_paths, max_results)
        return self.related_nodes


def test_returns_base_prompt_unchanged_when_no_signal_triggers():
    kb = FakeKnowledgeBase([])
    result = augment_system_prompt_with_conditional_knowledge(
        "BASE PROMPT", kb, "hello, just getting started"
    )
    assert result == "BASE PROMPT"


def test_appends_triggered_node_content_to_the_prompt():
    node = KnowledgeNode(path="access/export-control", title="Export Control", content="ITAR/EAR rules.")
    kb = FakeKnowledgeBase([node])
    result = augment_system_prompt_with_conditional_knowledge(
        "BASE PROMPT", kb, "we have ITAR-controlled firmware"
    )
    assert "BASE PROMPT" in result
    assert "Export Control" in result
    assert "ITAR/EAR rules." in result
    assert "access/export-control" in result


def test_passes_user_message_through_to_knowledge_base():
    kb = FakeKnowledgeBase([])
    augment_system_prompt_with_conditional_knowledge("BASE", kb, "some message about HIPAA")
    assert kb.last_query == "some message about HIPAA"


def test_multiple_triggered_nodes_are_all_included():
    nodes = [
        KnowledgeNode(path="access/hipaa", title="HIPAA", content="PHI rules."),
        KnowledgeNode(path="gateway/vault-integration", title="Vault", content="Vault adapter."),
    ]
    kb = FakeKnowledgeBase(nodes)
    result = augment_system_prompt_with_conditional_knowledge("BASE", kb, "hipaa and vault")
    assert "PHI rules." in result
    assert "Vault adapter." in result


def test_related_graph_hints_are_appended_when_available():
    node = KnowledgeNode(path="harness-selection/multi-harness-governance", title="Portfolio", content="Portfolio rules.")
    related = KnowledgeNode(
        path="access/policy-tiers",
        title="Policy Tiers",
        content="Tier rules.",
        decision_question="Do populations need differentiated controls?",
    )
    kb = FakeKnowledgeBase([node])
    kb.related_nodes = [related]
    result = augment_system_prompt_with_conditional_knowledge("BASE", kb, "copilot cursor claude code")
    assert "Graph Follow-On Nodes To Consider Next" in result
    assert "access/policy-tiers" in result
    assert "Do populations need differentiated controls?" in result
