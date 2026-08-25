from __future__ import annotations

from typing import Any

from knowledge_loader import KnowledgeBase


def run_graph_healthcheck(kb: KnowledgeBase) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for node in kb._nodes.values():
        for relation_name, paths in node.typed_edges().items():
            for path in paths:
                if kb.get(path) is None:
                    issues.append({
                        "type": "missing_edge_target",
                        "node": node.path,
                        "relation": relation_name,
                        "target": path,
                    })
        for conflict_path in node.conflicts_with:
            other = kb.get(conflict_path)
            if other is None:
                continue
            if node.path not in other.conflicts_with:
                issues.append({
                    "type": "asymmetric_conflict",
                    "node": node.path,
                    "target": conflict_path,
                })
        for alt_path in node.alternatives:
            other = kb.get(alt_path)
            if other is None:
                continue
            if node.decision_domain and other.decision_domain and node.decision_domain != other.decision_domain:
                issues.append({
                    "type": "cross_domain_alternative",
                    "node": node.path,
                    "target": alt_path,
                    "node_domain": node.decision_domain,
                    "target_domain": other.decision_domain,
                })
            if node.path not in other.alternatives:
                issues.append({
                    "type": "asymmetric_alternative",
                    "node": node.path,
                    "target": alt_path,
                })
        if node.path in node.conflicts_with:
            issues.append({
                "type": "self_conflict",
                "node": node.path,
            })
    return issues
