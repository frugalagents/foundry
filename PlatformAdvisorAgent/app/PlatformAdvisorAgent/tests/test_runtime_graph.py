from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from advisor_core.knowledge import (
    RuntimeGraphCompilationError,
    RuntimeKnowledgeGraph,
    compile_runtime_graph,
    load_legacy_migration_bundle,
)


AS_OF = date(2026, 8, 11)
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "knowledge"
    / "migrations"
    / "coding-platform-v3.json"
)


def migration():
    return load_legacy_migration_bundle(MIGRATION_PATH)[0]


def adjacency_by_node(records):
    return {record.node_id: record for record in records}


def test_runtime_graph_compiles_typed_indexes_and_evidence():
    knowledge = migration()
    graph = compile_runtime_graph(
        entities=knowledge.entities,
        relationships=knowledge.relationships,
        known_snapshot_ids=tuple(
            snapshot.snapshot_id for snapshot in knowledge.snapshots
        ),
        as_of=AS_OF,
    )

    assert len(graph.nodes) == len(knowledge.entities)
    assert len(graph.edges) == len(knowledge.relationships)
    assert len(graph.relationship_indexes) == 10

    requires = next(
        index
        for index in graph.relationship_indexes
        if index.relationship_type.value == "REQUIRES"
    )
    outgoing = adjacency_by_node(requires.outgoing)
    incoming = adjacency_by_node(requires.incoming)
    assert {
        arc.neighbor_id
        for arc in outgoing["component:workload-identity"].arcs
    } == {"component:workforce-identity"}
    assert "component:workload-identity" in {
        arc.neighbor_id
        for arc in incoming["component:workforce-identity"].arcs
    }

    evidence = {
        item.subject_id: set(item.claim_ids)
        for item in graph.evidence_by_subject
    }
    assert "claim:architecture-first-authority" in evidence[
        "component:architecture-knowledge"
    ]


def test_runtime_graph_is_deterministic_across_input_order():
    knowledge = migration()
    arguments = {
        "known_snapshot_ids": tuple(
            snapshot.snapshot_id for snapshot in knowledge.snapshots
        ),
        "as_of": AS_OF,
    }
    first = compile_runtime_graph(
        entities=knowledge.entities,
        relationships=knowledge.relationships,
        **arguments,
    )
    second = compile_runtime_graph(
        entities=tuple(reversed(knowledge.entities)),
        relationships=tuple(reversed(knowledge.relationships)),
        **arguments,
    )

    assert first == second
    assert first.graph_hash == second.graph_hash


def test_runtime_graph_fails_closed_without_evidence_snapshot():
    knowledge = migration()

    with pytest.raises(
        RuntimeGraphCompilationError,
        match="missing_evidence_snapshot",
    ):
        compile_runtime_graph(
            entities=knowledge.entities,
            relationships=knowledge.relationships,
            known_snapshot_ids=(),
            as_of=AS_OF,
        )


def test_runtime_graph_rejects_forged_hash():
    knowledge = migration()
    graph = compile_runtime_graph(
        entities=knowledge.entities,
        relationships=knowledge.relationships,
        known_snapshot_ids=tuple(
            snapshot.snapshot_id for snapshot in knowledge.snapshots
        ),
        as_of=AS_OF,
    )
    payload = graph.model_dump(mode="json")
    payload["graph_hash"] = f"sha256:{'f' * 64}"

    with pytest.raises(
        ValidationError,
        match="runtime graph hash does not match",
    ):
        RuntimeKnowledgeGraph.model_validate(payload)
