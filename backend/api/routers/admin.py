"""Admin endpoints — metrics, graph config, user management."""
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import require_admin
from api.db import dynamodb as db
from api.db.models import AdminMetrics, GraphConfigUpdate
from agent.graph_loader import get_graph, reload_graph

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[dict, Depends(require_admin)]


@router.get("/metrics", response_model=AdminMetrics)
async def get_metrics(user: AdminUser):
    metrics = db.get_admin_metrics()
    return AdminMetrics(**metrics)


@router.get("/graph/nodes")
async def list_graph_nodes(user: AdminUser, node_type: str = ""):
    graph = get_graph()
    if node_type:
        nodes = graph.get_nodes_by_type(node_type)
    else:
        nodes = list(graph.nodes.values())
    return {"nodes": nodes, "count": len(nodes)}


@router.get("/graph/nodes/{node_id}")
async def get_graph_node(node_id: str, user: AdminUser):
    graph = get_graph()
    node = graph.nodes.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {
        "node": node,
        "out_edges": graph.get_out_edges(node_id),
        "in_edges": graph.get_in_edges(node_id),
    }


@router.post("/graph/reload")
async def reload_graph_endpoint(user: AdminUser):
    """Hot-reload the knowledge graph from disk."""
    graph = reload_graph()
    return {
        "ok": True,
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
    }


@router.get("/graph/stats")
async def graph_stats(user: AdminUser):
    graph = get_graph()
    type_counts: dict[str, int] = {}
    for node in graph.nodes.values():
        t = node.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    edge_type_counts: dict[str, int] = {}
    for edge in graph.edges:
        t = edge.get("type", "unknown")
        edge_type_counts[t] = edge_type_counts.get(t, 0) + 1
    return {
        "total_nodes": len(graph.nodes),
        "total_edges": len(graph.edges),
        "node_types": type_counts,
        "edge_types": edge_type_counts,
    }
