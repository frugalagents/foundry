from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_loader import KnowledgeNode, load_knowledge_base
from traversal_engine import (
    _build_packet_paths,
    _normalize_operating_model,
    _resolved_domains,
    _score_node,
    build_traversal_frontier,
    build_traversal_state,
    render_traversal_context,
)

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def test_multi_tool_context_prioritizes_multi_harness_frontier():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    workspace = {
        "stage": "discovery",
        "facts": ["Current tools: Claude Code, Cursor, Copilot, Codex CLI"],
        "operating_model": "undecided",
        "open_questions": [],
        "decisions": [],
        "risks": [],
    }

    frontier = build_traversal_frontier(kb, workspace, "We need a recommendation for 5000 engineers on AWS.")

    assert frontier is not None
    assert frontier.active_node_path == "harness-selection/multi-harness-governance"
    assert "access/policy-tiers" in frontier.loaded_node_paths
    assert "gateway/modelgw" in frontier.loaded_node_paths
    assert len(frontier.loaded_node_paths) <= 6


def test_hipaa_signal_prioritizes_compliance_frontier():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    workspace = {
        "stage": "solutioning",
        "facts": ["PHI may appear in test fixtures and support workflows."],
        "open_questions": ["Are we a HIPAA covered entity or business associate?"],
        "decisions": ["Use a governed multi-harness portfolio."],
        "operating_model": "multi_harness_governed",
    }

    frontier = build_traversal_frontier(kb, workspace, "Healthcare environment with PHI and Bedrock usage.")

    assert frontier is not None
    assert frontier.active_node_path == "access/hipaa"
    assert "access/identity" in frontier.loaded_node_paths


def test_rendered_context_is_packetized_not_full_graph_dump():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    frontier = build_traversal_frontier(
        kb,
        {"stage": "discovery", "facts": ["Current tools: Claude Code, Cursor, Copilot"], "operating_model": "undecided"},
        "Need target-state advice.",
    )
    assert frontier is not None

    rendered = render_traversal_context(kb, frontier)
    assert "## Decision Frontier" in rendered
    assert "Active node: Multi-Harness Governance" in rendered
    assert "### Alternatives" not in rendered or "SaaS Coding Agent Products" in rendered
    assert "Only broaden beyond it when the current answer creates a new conflict" in rendered


def test_traversal_state_exposes_inferred_decisions_for_multi_harness():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    state = build_traversal_state(
        kb,
        {
            "stage": "discovery",
            "facts": ["Current tools: Claude Code, Cursor, Copilot, Codex CLI"],
            "operating_model": "undecided",
        },
        "Need target-state guidance for an enterprise rollout.",
    )

    assert state["active_decision"]["path"] == "harness-selection/multi-harness-governance"
    assert any(item["path"] == "access/policy-tiers" for item in state["inferred_decisions"])
    assert any(item["path"] == "gateway/modelgw" for item in state["inferred_decisions"])


def test_traversal_state_detects_single_standard_harness_conflict():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    state = build_traversal_state(
        kb,
        {
            "stage": "solutioning",
            "operating_model": "single_standard",
            "recommendation": "Use one standard harness, but also keep a custom harness on managed runtime for central workflows.",
            "decisions": [
                "Primary harness family is SaaS products.",
                "Add managed runtime as a second primary harness family.",
            ],
        },
        "Finalize the target state.",
    )

    assert any(item["type"] == "operating_model_conflict" for item in state["conflicts_detected"])


def test_prior_traversal_state_reduces_heuristic_dependence_for_requires():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    state = build_traversal_state(
        kb,
        {
            "stage": "solutioning",
            "facts": ["PHI may appear in test fixtures and support workflows."],
            "open_questions": ["Are we a HIPAA covered entity or business associate?"],
            "traversal_state": {
                "resolved_domains": ["identity_boundary"],
                "selected_node_paths": ["access/identity"],
            },
        },
        "Healthcare environment with PHI and Bedrock usage.",
    )

    assert any(
        item["path"] == "access/identity" and item["status"] == "already_selected"
        for item in state["inferred_decisions"]
    )


def test_harness_cascade_domain_receives_stage_weight():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    node = kb.get("harness-selection/lifecycle-implications")

    assert node is not None

    score, reasons = _score_node(
        node,
        signal_text="multi-harness downstream implications",
        open_question_text="",
        stage="solutioning",
        resolved_domains=set(),
        triggered_path_set=set(),
        query_rank={},
        open_question_rank={},
    )

    assert score > node.priority
    assert "harness_cascade matters in solutioning" in reasons


def test_operating_model_aliases_are_normalized_for_selection_logic():
    kb = load_knowledge_base(KNOWLEDGE_DIR)

    assert _normalize_operating_model("multi-harness-portfolio") == "multi_harness_governed"
    assert _normalize_operating_model("Default with formal exception paths") == "default_plus_exceptions"

    state = build_traversal_state(
        kb,
        {
            "stage": "discovery",
            "operating_model": "multi-harness-portfolio",
            "recommendation": "Keep several approved harnesses under one governed control plane.",
        },
        "Need target-state guidance.",
    )

    assert "harness-selection/multi-harness-governance" in state["selected_node_paths"]


def test_resolved_domains_use_token_matching_not_broad_substrings():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    resolved = _resolved_domains(
        kb,
        {
            "stage": "discovery",
            "recommendation": "Developers need repo access for advisory-only pilots.",
            "decisions": ["Start with read-only repository access."],
        },
        None,
    )

    assert "governance_group" not in resolved


def test_packet_builder_preserves_relation_coverage_under_cap():
    class DummyKb:
        def __init__(self, nodes: list[KnowledgeNode]):
            self.nodes = {node.path: node for node in nodes}

        def get(self, path: str):
            return self.nodes.get(path)

    related_paths = [
        "req-1",
        "req-2",
        "imp-1",
        "imp-2",
        "alt-1",
        "alt-2",
        "conf-1",
        "exc-1",
        "link-1",
    ]
    active = KnowledgeNode(
        path="active",
        title="Active",
        requires=("req-1", "req-2"),
        implies=("imp-1", "imp-2"),
        alternatives=("alt-1", "alt-2"),
        conflicts_with=("conf-1",),
        exception_to=("exc-1",),
        linked_paths=("link-1",),
    )
    nodes = [active] + [KnowledgeNode(path=path, title=path) for path in related_paths]
    kb = DummyKb(nodes)

    packet_paths, relation_paths = _build_packet_paths(kb, active)

    assert packet_paths == ["active", "req-1", "imp-1", "alt-1", "conf-1", "exc-1"]
    assert relation_paths["alternatives"] == ["alt-1"]
    assert relation_paths["conflicts_with"] == ["conf-1"]
    assert relation_paths["exception_to"] == ["exc-1"]


def test_question_state_drives_next_best_question_and_missing_evidence():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    state = build_traversal_state(
        kb,
        {
            "stage": "solutioning",
            "question_state": [
                {
                    "id": "q1",
                    "text": "Which teams need formal exception paths?",
                    "status": "open",
                    "blocking": True,
                    "decision_domain": "population_policy",
                    "why_it_matters": "This determines whether the target state is default-plus-exceptions or governed multi-harness.",
                }
            ],
            "recommendation": "Default to one standard harness with formal exception lanes.",
        },
        "Need to finalize the target operating model.",
    )

    assert state["next_best_question"] == "Which teams need formal exception paths?"
    assert state["missing_evidence"][0]["question"] == "Which teams need formal exception paths?"


def test_active_decision_question_beats_unrelated_older_open_question():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    state = build_traversal_state(
        kb,
        {
            "stage": "solutioning",
            "question_state": [
                {
                    "id": "q1",
                    "text": "Which teams need formal exception paths?",
                    "status": "open",
                    "blocking": True,
                    "decision_domain": "population_policy",
                }
            ],
        },
        "We have ITAR-controlled firmware repos and need guidance.",
    )

    assert state["active_decision"]["path"] == "access/export-control"
    assert state["next_best_question"].startswith("Do any repos contain ITAR or EAR controlled content")
    assert state["missing_evidence"][0]["decision_domain"] == "compliance_overlay"


def test_traversal_state_emits_candidate_options_for_recommendation_engine():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    state = build_traversal_state(
        kb,
        {
            "stage": "discovery",
            "facts": ["Current tools: Claude Code, Cursor, Copilot, Codex CLI"],
            "operating_model": "undecided",
        },
        "Need target-state guidance for an enterprise rollout.",
    )

    assert state["candidate_options"]
    assert state["candidate_options"][0]["position"] == "recommended"
    assert any(item["position"] == "viable" for item in state["candidate_options"][1:])


def test_closed_compliance_domain_blocks_compliance_frontier_revival():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    state = build_traversal_state(
        kb,
        {
            "stage": "discovery",
            "traversal_state": {
                "closed_domains": ["compliance_overlay"],
            },
        },
        "Continue the enterprise rollout with no special regulatory constraints.",
    )

    assert state["active_decision"]["path"] != "access/export-control"
    assert "compliance_overlay" in state["closed_domains"]


def test_deterministic_active_slice_overrides_heuristic_traversal_choice():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    state = build_traversal_state(
        kb,
        {
            "stage": "solutioning",
            "question_state": [
                {
                    "id": "q1",
                    "text": "Which teams need formal exception paths?",
                    "status": "open",
                    "blocking": True,
                    "decision_domain": "population_policy",
                }
            ],
        },
        "We already use GitHub Copilot and Cursor.",
        {
            "active_slice": {
                "path": "decision/exception-governance/named-population-lanes",
                "title": "Named population exception lanes",
                "decision_domain": "exception_governance",
            },
            "next_best_question": "Which teams need formal exception paths?",
            "candidate_options": [
                {
                    "path": "decision/exception-governance/named-population-lanes",
                    "title": "Named population exception lanes",
                    "position": "recommended",
                }
            ],
        },
    )

    assert state["active_decision"]["path"] == "decision/exception-governance/named-population-lanes"
    assert state["next_best_question"] == "Which teams need formal exception paths?"
    assert state["candidate_options"][0]["path"] == "decision/exception-governance/named-population-lanes"
