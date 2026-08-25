from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph_healthcheck import run_graph_healthcheck
from knowledge_loader import load_knowledge_base

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def test_graph_healthcheck_has_no_missing_targets_in_pilot_graph():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    issues = run_graph_healthcheck(kb)
    assert [issue for issue in issues if issue["type"] == "missing_edge_target"] == []
    assert [issue for issue in issues if issue["type"] == "asymmetric_alternative"] == []
    assert [issue for issue in issues if issue["type"] == "asymmetric_conflict"] == []
    assert [issue for issue in issues if issue["type"] == "self_conflict"] == []
