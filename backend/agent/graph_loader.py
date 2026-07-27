"""Singleton loader for the knowledge graph."""
import json
from pathlib import Path
from .graph_engine import GraphEngine

_GRAPH_PATH = (
    Path(__file__).parent.parent.parent / "knowledge-base" / "graph.json"
)

_instance: GraphEngine | None = None


def get_graph() -> GraphEngine:
    global _instance
    if _instance is None:
        with open(_GRAPH_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _instance = GraphEngine(data)
    return _instance


def reload_graph() -> GraphEngine:
    global _instance
    _instance = None
    return get_graph()
