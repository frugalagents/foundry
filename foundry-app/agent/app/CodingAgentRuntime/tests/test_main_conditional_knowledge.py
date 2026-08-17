"""Tests for the conditional-knowledge auto-loading wired into the system
prompt. This is the mechanism that makes the skill file's documented
three-tier traversal model (mandate/conditional/probe) actually automatic
instead of relying on the model to guess query_knowledge keywords.
"""
from __future__ import annotations
import os

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

from main import augment_system_prompt_with_conditional_knowledge  # noqa: E402
from knowledge_loader import KnowledgeNode  # noqa: E402


class FakeKnowledgeBase:
    """Stand-in that records what conversation text it was queried with."""

    def __init__(self, nodes: list[KnowledgeNode]):
        self._nodes = nodes
        self.last_query: str | None = None

    def conditional_nodes_for(self, conversation_text: str) -> list[KnowledgeNode]:
        self.last_query = conversation_text
        return self._nodes


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
