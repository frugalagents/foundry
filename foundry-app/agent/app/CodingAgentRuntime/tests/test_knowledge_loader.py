"""Tests for the OKF knowledge loader — mandate/conditional node selection and
keyword query ranking. These are the mechanisms that decide what domain
knowledge the advisor actually sees, so a regression here silently degrades
advice quality with no visible error.
"""
from __future__ import annotations
from pathlib import Path

import pytest

from knowledge_loader import (
    CONDITIONAL_NODES,
    MANDATE_NODES,
    KnowledgeBase,
    load_knowledge_base,
)

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    return load_knowledge_base(KNOWLEDGE_DIR)


def test_loads_all_markdown_files_under_knowledge_dir(kb: KnowledgeBase):
    on_disk = set(KNOWLEDGE_DIR.rglob("*.md"))
    assert len(kb._nodes) == len(on_disk)


def test_every_mandate_node_path_resolves_to_a_real_file(kb: KnowledgeBase):
    # If a mandate path is renamed/removed on disk without updating this set,
    # the advisor silently loses baseline context for every customer.
    missing = [p for p in MANDATE_NODES if kb.get(p) is None]
    assert missing == []


def test_every_conditional_node_path_resolves_to_a_real_file(kb: KnowledgeBase):
    missing = [path for _, path in CONDITIONAL_NODES if kb.get(path) is None]
    assert missing == []


def test_mandate_nodes_returns_exactly_the_mandate_set(kb: KnowledgeBase):
    paths = {n.path for n in kb.mandate_nodes()}
    assert paths == MANDATE_NODES


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
    assert all(n.path in MANDATE_NODES for n in results)


def test_query_returns_empty_for_nonsense_terms(kb: KnowledgeBase):
    results = kb.query("zzz_no_such_keyword_zzz")
    assert results == []
