"""Tests for the OKF knowledge loader — mandate/conditional node selection and
keyword query ranking. These are the mechanisms that decide what domain
knowledge the advisor actually sees, so a regression here silently degrades
advice quality with no visible error.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from knowledge_loader import KnowledgeBase, load_knowledge_base

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    return load_knowledge_base(KNOWLEDGE_DIR)


def test_loads_all_markdown_files_under_knowledge_dir(kb: KnowledgeBase):
    on_disk = set(KNOWLEDGE_DIR.rglob("*.md"))
    assert len(kb._nodes) == len(on_disk)


def test_mandate_nodes_are_derived_from_frontmatter(kb: KnowledgeBase):
    expected = {
        node.path
        for node in kb._nodes.values()
        if node.traversal == "mandate"
    }
    paths = {n.path for n in kb.mandate_nodes()}
    assert paths == expected


def test_metadata_is_loaded_from_frontmatter_and_links(kb: KnowledgeBase):
    node = kb.get("harness-selection/multi-harness-governance")
    assert node is not None
    assert node.traversal == "conditional"
    assert node.decision_question.startswith("Is the target state")
    assert "copilot" in node.trigger_pool
    assert node.trigger_pool_min_matches == 2
    assert "access/policy-tiers" in node.linked_paths
    assert "gateway/mcpgw" in node.linked_paths


def test_conditional_nodes_for_triggers_on_matching_signal(kb: KnowledgeBase):
    nodes = kb.conditional_nodes_for("We have some ITAR-controlled firmware repos.")
    paths = {n.path for n in nodes}
    assert "access/export-control" in paths


def test_conditional_nodes_for_triggers_multiple_independent_signals(kb: KnowledgeBase):
    text = "We're on HashiCorp Vault for secrets and also need HIPAA compliance for PHI."
    nodes = kb.conditional_nodes_for(text)
    paths = {n.path for n in nodes}
    assert "access/hipaa" in paths
    assert "gateway/vault-integration" in paths


def test_conditional_nodes_for_can_trigger_multi_harness_from_multiple_tool_mentions(kb: KnowledgeBase):
    text = "We currently allow Copilot, Cursor, and Claude Code across different teams."
    nodes = kb.conditional_nodes_for(text)
    paths = {n.path for n in nodes}
    assert "harness-selection/multi-harness-governance" in paths


def test_conditional_nodes_for_returns_empty_when_no_signal_present(kb: KnowledgeBase):
    nodes = kb.conditional_nodes_for("Hello, we'd like to design a platform.")
    assert nodes == []


def test_conditional_nodes_for_is_case_insensitive(kb: KnowledgeBase):
    nodes = kb.conditional_nodes_for("Any HIPAA or PHI concerns here?")
    paths = {n.path for n in nodes}
    assert "access/hipaa" in paths


def test_query_boosts_exact_path_matches_above_content_only_matches(kb: KnowledgeBase):
    results = kb.query("identity", max_results=1)
    assert results
    assert results[0].path == "access/identity"


def test_query_with_no_terms_falls_back_to_mandate_nodes(kb: KnowledgeBase):
    results = kb.query("   ", max_results=3)
    assert len(results) == 3
    mandate_paths = {n.path for n in kb.mandate_nodes()}
    assert all(n.path in mandate_paths for n in results)


def test_query_returns_empty_for_nonsense_terms(kb: KnowledgeBase):
    results = kb.query("zzz_no_such_keyword_zzz")
    assert results == []


def test_related_nodes_for_returns_graph_link_targets(kb: KnowledgeBase):
    related = kb.related_nodes_for(["harness-selection/multi-harness-governance"])
    paths = {node.path for node in related}
    assert "access/policy-tiers" in paths
    assert "gateway/mcpgw" in paths
