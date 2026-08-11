"""Compiled in-memory graph projection for approved architecture knowledge."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from pydantic import Field, field_validator, model_validator

from .models import (
    Claim,
    DecisionPattern,
    EntityKind,
    FrozenModel,
    KnowledgeEntity,
    KnowledgeLifecycle,
    KnowledgeRelationship,
    RELATIONSHIP_SEMANTICS,
    RelationshipType,
    StableId,
    content_hash,
)
from .validation import ValidationSeverity, validate_knowledge_release


class RuntimeGraphCompilationError(ValueError):
    pass


class RuntimeGraphNode(FrozenModel):
    id: StableId
    kind: EntityKind
    title: str = Field(min_length=1)
    entity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class RuntimeGraphEdge(FrozenModel):
    id: StableId
    relationship_type: RelationshipType
    source_id: StableId
    target_id: StableId
    directed: bool
    supporting_claim_ids: tuple[StableId, ...]
    relationship_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class RuntimeGraphArc(FrozenModel):
    edge_id: StableId
    neighbor_id: StableId
    relationship_type: RelationshipType


class RuntimeGraphAdjacency(FrozenModel):
    node_id: StableId
    arcs: tuple[RuntimeGraphArc, ...]

    @field_validator("arcs")
    @classmethod
    def arcs_are_unique_and_sorted(
        cls,
        arcs: tuple[RuntimeGraphArc, ...],
    ) -> tuple[RuntimeGraphArc, ...]:
        identities = [
            (arc.edge_id, arc.neighbor_id, arc.relationship_type)
            for arc in arcs
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("runtime graph arcs must be unique")
        return tuple(
            sorted(
                arcs,
                key=lambda arc: (
                    arc.relationship_type.value,
                    arc.neighbor_id,
                    arc.edge_id,
                ),
            )
        )


class RuntimeRelationshipIndex(FrozenModel):
    relationship_type: RelationshipType
    outgoing: tuple[RuntimeGraphAdjacency, ...] = ()
    incoming: tuple[RuntimeGraphAdjacency, ...] = ()


class RuntimeEvidenceIndex(FrozenModel):
    subject_id: StableId
    claim_ids: tuple[StableId, ...] = Field(min_length=1)

    @field_validator("claim_ids")
    @classmethod
    def claims_are_unique_and_sorted(
        cls,
        claim_ids: tuple[StableId, ...],
    ) -> tuple[StableId, ...]:
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("evidence claim IDs must be unique")
        return tuple(sorted(claim_ids))


class RuntimeEdgeEvidence(FrozenModel):
    edge_id: StableId
    claim_ids: tuple[StableId, ...] = Field(min_length=1)

    _sort_claims = field_validator("claim_ids")(
        RuntimeEvidenceIndex.claims_are_unique_and_sorted.__func__
    )


class RuntimeKnowledgeGraph(FrozenModel):
    schema_version: str = "1.0"
    as_of: date
    nodes: tuple[RuntimeGraphNode, ...]
    edges: tuple[RuntimeGraphEdge, ...]
    outgoing: tuple[RuntimeGraphAdjacency, ...]
    incoming: tuple[RuntimeGraphAdjacency, ...]
    relationship_indexes: tuple[RuntimeRelationshipIndex, ...]
    evidence_by_subject: tuple[RuntimeEvidenceIndex, ...]
    evidence_by_edge: tuple[RuntimeEdgeEvidence, ...]
    graph_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def graph_hash_matches_content(self) -> "RuntimeKnowledgeGraph":
        payload = self.model_dump(mode="json", exclude={"graph_hash"})
        if self.graph_hash != content_hash(payload):
            raise ValueError("runtime graph hash does not match graph content")
        return self


def _adjacency_records(
    adjacency: dict[str, list[RuntimeGraphArc]],
) -> tuple[RuntimeGraphAdjacency, ...]:
    return tuple(
        RuntimeGraphAdjacency(node_id=node_id, arcs=tuple(arcs))
        for node_id, arcs in sorted(adjacency.items())
        if arcs
    )


def compile_runtime_graph(
    *,
    entities: tuple[KnowledgeEntity, ...],
    relationships: tuple[KnowledgeRelationship, ...],
    known_snapshot_ids: tuple[StableId, ...],
    as_of: date,
) -> RuntimeKnowledgeGraph:
    """Compile a validated active corpus into deterministic traversal indexes."""

    active_entities = tuple(
        entity
        for entity in entities
        if entity.lifecycle is KnowledgeLifecycle.ACTIVE
    )
    active_ids = {entity.id for entity in active_entities}
    active_relationships = tuple(
        relationship
        for relationship in relationships
        if relationship.lifecycle is KnowledgeLifecycle.ACTIVE
    )
    validation = validate_knowledge_release(
        entities=active_entities,
        relationships=active_relationships,
        known_snapshot_ids=known_snapshot_ids,
        as_of=as_of,
    )
    if not validation.is_valid:
        errors = "; ".join(
            f"{issue.code} at {issue.location}"
            for issue in validation.issues
            if issue.severity is ValidationSeverity.ERROR
        )
        raise RuntimeGraphCompilationError(
            f"knowledge cannot produce a runtime graph: {errors}"
        )

    nodes = tuple(
        RuntimeGraphNode(
            id=entity.id,
            kind=EntityKind(entity.kind),
            title=entity.title,
            entity_hash=content_hash(entity),
        )
        for entity in sorted(active_entities, key=lambda item: item.id)
    )
    outgoing: dict[str, list[RuntimeGraphArc]] = defaultdict(list)
    incoming: dict[str, list[RuntimeGraphArc]] = defaultdict(list)
    type_outgoing: dict[
        RelationshipType,
        dict[str, list[RuntimeGraphArc]],
    ] = defaultdict(lambda: defaultdict(list))
    type_incoming: dict[
        RelationshipType,
        dict[str, list[RuntimeGraphArc]],
    ] = defaultdict(lambda: defaultdict(list))
    edges: list[RuntimeGraphEdge] = []
    evidence_by_subject: dict[str, set[str]] = defaultdict(set)
    evidence_by_edge: dict[str, set[str]] = defaultdict(set)

    for entity in active_entities:
        if isinstance(entity, Claim):
            evidence_by_subject[entity.subject_id].add(entity.id)
        elif isinstance(entity, DecisionPattern):
            evidence_by_subject[entity.id].update(
                entity.supporting_claim_ids
            )

    for relationship in sorted(
        active_relationships,
        key=lambda item: item.id,
    ):
        semantics = RELATIONSHIP_SEMANTICS[
            relationship.relationship_type
        ]
        edge = RuntimeGraphEdge(
            id=relationship.id,
            relationship_type=relationship.relationship_type,
            source_id=relationship.source_id,
            target_id=relationship.target_id,
            directed=semantics.directed,
            supporting_claim_ids=relationship.supporting_claim_ids,
            relationship_hash=content_hash(relationship),
        )
        edges.append(edge)
        forward = RuntimeGraphArc(
            edge_id=edge.id,
            neighbor_id=edge.target_id,
            relationship_type=edge.relationship_type,
        )
        reverse = RuntimeGraphArc(
            edge_id=edge.id,
            neighbor_id=edge.source_id,
            relationship_type=edge.relationship_type,
        )
        outgoing[edge.source_id].append(forward)
        incoming[edge.target_id].append(reverse)
        type_outgoing[edge.relationship_type][edge.source_id].append(
            forward
        )
        type_incoming[edge.relationship_type][edge.target_id].append(
            reverse
        )
        if not edge.directed:
            outgoing[edge.target_id].append(reverse)
            incoming[edge.source_id].append(forward)
            type_outgoing[edge.relationship_type][edge.target_id].append(
                reverse
            )
            type_incoming[edge.relationship_type][edge.source_id].append(
                forward
            )
        evidence_by_edge[edge.id].update(edge.supporting_claim_ids)
        if relationship.relationship_type is RelationshipType.SUPPORTED_BY:
            evidence_by_subject[relationship.source_id].update(
                relationship.supporting_claim_ids
            )

    relationship_indexes = tuple(
        RuntimeRelationshipIndex(
            relationship_type=relationship_type,
            outgoing=_adjacency_records(
                type_outgoing.get(relationship_type, {})
            ),
            incoming=_adjacency_records(
                type_incoming.get(relationship_type, {})
            ),
        )
        for relationship_type in RelationshipType
    )
    payload = {
        "schema_version": "1.0",
        "as_of": as_of.isoformat(),
        "nodes": [
            node.model_dump(mode="json") for node in nodes
        ],
        "edges": [
            edge.model_dump(mode="json") for edge in edges
        ],
        "outgoing": [
            item.model_dump(mode="json")
            for item in _adjacency_records(outgoing)
        ],
        "incoming": [
            item.model_dump(mode="json")
            for item in _adjacency_records(incoming)
        ],
        "relationship_indexes": [
            item.model_dump(mode="json")
            for item in relationship_indexes
        ],
        "evidence_by_subject": [
            RuntimeEvidenceIndex(
                subject_id=subject_id,
                claim_ids=tuple(claim_ids),
            ).model_dump(mode="json")
            for subject_id, claim_ids in sorted(evidence_by_subject.items())
            if subject_id in active_ids and claim_ids
        ],
        "evidence_by_edge": [
            RuntimeEdgeEvidence(
                edge_id=edge_id,
                claim_ids=tuple(claim_ids),
            ).model_dump(mode="json")
            for edge_id, claim_ids in sorted(evidence_by_edge.items())
            if claim_ids
        ],
    }
    return RuntimeKnowledgeGraph(
        **payload,
        graph_hash=content_hash(payload),
    )
