"""Regression tests for the deterministic scoring engine.

Guards the two bugs fixed in graph_engine.py:
  1. Law nodes with no `trigger_condition` must NOT fire (previously `all()` over an
     empty condition was vacuously True, disqualifying Mesh/Economy on every input).
  2. Answer→constraint matching must be scoped to the answer's own signal group, so a
     value never collides with a same-substring answer_value under another question
     (e.g. data-location "single_region" must not match "1-3 teams (single org)").
"""
from __future__ import annotations

import pytest

from agent_core_engine.graph_loader import get_graph
from agent_core_engine.graph_engine import GraphEngine

BLOCKED = -100  # select_pattern treats total <= -100 as disqualified


@pytest.fixture(scope="module")
def g() -> GraphEngine:
    return get_graph()


def _score(g: GraphEngine, answers: dict) -> dict:
    scores = g.compute_pattern_scores(answers)
    return g.apply_laws(scores, answers)


# ── Bug 1: laws must not fire without a matching trigger ────────────────────────

def test_empty_answers_block_no_pattern(g):
    """With no answers, no law should fire — every pattern stays reachable at 0."""
    scores = _score(g, {})
    for pid, s in scores.items():
        assert s["total"] > BLOCKED, f"{pid} was disqualified on empty input"
        assert s["total"] == pytest.approx(0.0), f"{pid} scored non-zero on empty input"


def test_all_patterns_reachable(g):
    """All four operating models must be reachable (not hard-blocked) on empty input."""
    scores = _score(g, {})
    assert set(scores) >= {
        "pattern:centralized",
        "pattern:federated",
        "pattern:mesh",
        "pattern:economy",
    }
    assert all(s["total"] > BLOCKED for s in scores.values())


def test_law_fires_when_trigger_matches():
    """A law WITH a matching trigger_condition must disqualify its BLOCKS target."""
    graph = {
        "nodes": [
            {"id": "pattern:centralized", "type": "Pattern", "props": {"name": "C"}},
            {"id": "pattern:mesh", "type": "Pattern", "props": {"name": "M"}},
            {
                "id": "law:x",
                "type": "Law",
                "props": {"trigger_condition": {"autonomy_model": "supervised"}},
            },
        ],
        "edges": [{"from": "law:x", "to": "pattern:mesh", "type": "BLOCKS"}],
    }
    eng = GraphEngine(graph)
    scores = {p: {"total": 1.0, "axes": [0] * 5} for p in ("pattern:centralized", "pattern:mesh")}

    # Trigger matches → mesh blocked.
    fired = eng.apply_laws({k: dict(v) for k, v in scores.items()}, {"autonomy_model": "supervised"})
    assert fired["pattern:mesh"]["total"] == -999.0
    assert fired["pattern:centralized"]["total"] == 1.0

    # Trigger does not match → nothing blocked.
    not_fired = eng.apply_laws({k: dict(v) for k, v in scores.items()}, {"autonomy_model": "full"})
    assert not_fired["pattern:mesh"]["total"] == 1.0


# ── Bug 2: answer matching is scoped to the signal group ────────────────────────

def test_no_cross_question_collision(g):
    """A data-location answer must not apply team-count (Q3) pressure.

    Previously `single_region` matched "1-3 teams (single org)" via substring `single`.
    Scoring `single_region` alone must therefore differ from scoring `lob_count=1-3`.
    """
    single_region = g.compute_pattern_scores({"data_gravity": "single_region"})
    small_teams = g.compute_pattern_scores({"lob_count": "1-3"})
    # If the collision still existed these would be identical; they must not be.
    assert single_region["pattern:centralized"]["total"] != small_teams["pattern:centralized"]["total"]


def test_match_constraint_scoped_to_signal(g):
    """_match_constraint must resolve an answer to a node under its own signal_id."""
    node = g._match_constraint("data_gravity", "single_region")
    assert node is not None
    assert g.get_props(node["id"])["signal_id"] == "Q6"

    node2 = g._match_constraint("lob_count", "1-3")
    assert node2 is not None
    assert g.get_props(node2["id"])["signal_id"] == "Q3"


def test_unmapped_key_contributes_nothing(g):
    """An intake key with no signal mapping must match no constraint (zero pressure)."""
    assert g._match_constraint("governance_model", "federated") is None
    scores = g.compute_pattern_scores({"governance_model": "federated"})
    assert all(s["total"] == pytest.approx(0.0) for s in scores.values())


# ── Sanity: sensible recommendations still come out ─────────────────────────────

def test_centralized_profile_wins_centralized(g):
    answers = {
        "autonomy_model": "supervised",
        "lob_count": "1-3",
        "cost_sensitivity": "primary",
        "cloud_posture": "single_aws",
    }
    pid, conf = g.select_pattern(_score(g, answers))
    assert pid == "pattern:centralized"
    assert conf > 0.0


def test_federated_profile_wins_federated(g):
    answers = {
        "autonomy_model": "full",
        "lob_count": "10+",
        "cloud_posture": "multi_cloud",
        "data_gravity": "multi_region",
    }
    pid, _ = g.select_pattern(_score(g, answers))
    assert pid == "pattern:federated"


def test_mesh_profile_wins_mesh(g):
    answers = {
        "autonomy_model": "full",
        "lob_count": "10+",
        "cloud_posture": "multi_cloud",
        "team_expertise": "high",
        "data_gravity": "edge",
    }
    pid, _ = g.select_pattern(_score(g, answers))
    assert pid == "pattern:mesh"


# ── Topology derivation (axis C — rule-based, discovery-methodology §3.6) ───────

def test_topology_single_account_for_one_team_centralized(g):
    t = g.derive_topology("pattern:centralized", {"lob_count": "1-3"})
    assert t["base"] == "single-account"


def test_topology_hub_and_spoke_for_federated(g):
    t = g.derive_topology("pattern:federated", {"lob_count": "10+"})
    assert t["base"] == "hub-and-spoke"


def test_topology_peer_to_peer_for_mesh_never_called_mesh(g):
    t = g.derive_topology("pattern:mesh", {"lob_count": "10+"})
    assert t["base"] == "peer-to-peer"
    # Guard the naming-collision fix: topology is never labelled "mesh".
    assert "mesh" not in t["label"].lower()


def test_topology_multicloud_modifier(g):
    t = g.derive_topology("pattern:federated", {"lob_count": "10+", "cloud_posture": "multi_cloud"})
    assert "multi-cloud/hybrid" in t["modifiers"]


def test_topology_gateway_modifier_from_pain(g):
    t = g.derive_topology("pattern:federated", {"lob_count": "10+"}, pain_points=["Auth mess"])
    assert "gateway-fronted" in t["modifiers"]
