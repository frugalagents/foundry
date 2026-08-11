"""Cross-document semantic validation for publishable knowledge releases."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable

from pydantic import Field

from .models import (
    Claim,
    DecisionPattern,
    EntityKind,
    FrozenModel,
    IdentifierTransition,
    KnowledgeEntity,
    KnowledgeLifecycle,
    KnowledgeRelationship,
    OutcomeObservation,
    RelationshipType,
    StableId,
    StrEnum,
    content_hash,
)


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(FrozenModel):
    severity: ValidationSeverity
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    location: str = Field(min_length=1)
    entity_id: StableId | None = None
    message: str = Field(min_length=1)


class KnowledgeValidationReport(FrozenModel):
    as_of: date
    entity_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    transition_count: int = Field(ge=0)
    snapshot_count: int = Field(ge=0)
    issues: tuple[ValidationIssue, ...] = ()
    report_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @property
    def is_valid(self) -> bool:
        return not any(
            issue.severity is ValidationSeverity.ERROR for issue in self.issues
        )


def _entity_kind(entity: KnowledgeEntity) -> EntityKind:
    return EntityKind(entity.kind)


def _canonical_cycle(nodes: list[str]) -> tuple[str, ...]:
    """Return a stable representation for one directed cycle."""

    cycle = nodes[:-1]
    rotations = [
        tuple(cycle[index:] + cycle[:index])
        for index in range(len(cycle))
    ]
    canonical = min(rotations)
    return (*canonical, canonical[0])


def _find_cycles(
    relationships: Iterable[KnowledgeRelationship],
    relationship_type: RelationshipType,
) -> tuple[tuple[str, ...], ...]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()
    for relationship in relationships:
        if (
            relationship.relationship_type is relationship_type
            and relationship.lifecycle is KnowledgeLifecycle.ACTIVE
        ):
            adjacency[relationship.source_id].add(relationship.target_id)
            nodes.update((relationship.source_id, relationship.target_id))

    state: dict[str, int] = {}
    stack: list[str] = []
    positions: dict[str, int] = {}
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        state[node] = 1
        positions[node] = len(stack)
        stack.append(node)
        for target in sorted(adjacency[node]):
            if state.get(target, 0) == 0:
                visit(target)
            elif state.get(target) == 1:
                cycles.add(
                    _canonical_cycle(stack[positions[target] :] + [target])
                )
        stack.pop()
        positions.pop(node)
        state[node] = 2

    for node in sorted(nodes):
        if state.get(node, 0) == 0:
            visit(node)
    return tuple(sorted(cycles))


def validate_knowledge_release(
    *,
    entities: tuple[KnowledgeEntity, ...],
    relationships: tuple[KnowledgeRelationship, ...] = (),
    transitions: tuple[IdentifierTransition, ...] = (),
    known_snapshot_ids: tuple[StableId, ...] = (),
    as_of: date,
) -> KnowledgeValidationReport:
    """Validate cross-document release invariants and return stable diagnostics."""

    issues: list[ValidationIssue] = []

    def add(
        severity: ValidationSeverity,
        code: str,
        location: str,
        message: str,
        entity_id: str | None = None,
    ) -> None:
        issues.append(
            ValidationIssue(
                severity=severity,
                code=code,
                location=location,
                entity_id=entity_id,
                message=message,
            )
        )

    all_ids: dict[str, list[str]] = defaultdict(list)
    for entity in entities:
        all_ids[entity.id].append(f"entity:{entity.kind}")
    for relationship in relationships:
        all_ids[relationship.id].append("relationship")
    for transition in transitions:
        all_ids[transition.id].append("transition")
    for identifier, locations in sorted(all_ids.items()):
        if len(locations) > 1:
            add(
                ValidationSeverity.ERROR,
                "duplicate_identifier",
                identifier,
                f"identifier is reused by: {', '.join(sorted(locations))}",
                identifier,
            )

    entity_by_id = {entity.id: entity for entity in entities}
    claim_by_id = {
        entity.id: entity for entity in entities if isinstance(entity, Claim)
    }
    aliases: dict[str, list[str]] = defaultdict(list)
    for entity in entities:
        for alias in entity.aliases:
            aliases[alias].append(entity.id)
    for alias, owners in sorted(aliases.items()):
        if alias in all_ids:
            add(
                ValidationSeverity.ERROR,
                "alias_conflicts_with_identifier",
                f"{owners[0]}.aliases",
                f"alias {alias} is also a canonical identifier",
                owners[0],
            )
        if len(owners) > 1:
            add(
                ValidationSeverity.ERROR,
                "duplicate_alias",
                alias,
                f"alias is assigned to multiple entities: {', '.join(owners)}",
            )

    def check_lifecycle(item: KnowledgeEntity | KnowledgeRelationship) -> None:
        if item.lifecycle is KnowledgeLifecycle.ACTIVE:
            if as_of < item.effective_from or (
                item.effective_until is not None
                and as_of > item.effective_until
            ):
                add(
                    ValidationSeverity.ERROR,
                    "active_outside_effective_window",
                    f"{item.id}.lifecycle",
                    "active knowledge is outside its effective date window",
                    item.id,
                )
            if as_of > item.stale_after:
                add(
                    ValidationSeverity.ERROR,
                    "stale_active_knowledge",
                    f"{item.id}.stale_after",
                    f"active knowledge became stale on {item.stale_after}",
                    item.id,
                )
        elif item.lifecycle is KnowledgeLifecycle.DEPRECATED:
            add(
                ValidationSeverity.WARNING,
                "deprecated_knowledge",
                f"{item.id}.lifecycle",
                "deprecated knowledge remains in the release",
                item.id,
            )

    for item in (*entities, *relationships):
        check_lifecycle(item)

    def check_entity_reference(
        *,
        owner_id: str,
        field: str,
        target_id: str,
        expected_kind: EntityKind | None = None,
        owner_active: bool = True,
    ) -> KnowledgeEntity | None:
        target = entity_by_id.get(target_id)
        if target is None:
            add(
                ValidationSeverity.ERROR,
                "missing_entity_reference",
                f"{owner_id}.{field}",
                f"referenced entity {target_id} does not exist",
                owner_id,
            )
            return None
        actual_kind = _entity_kind(target)
        if expected_kind is not None and actual_kind is not expected_kind:
            add(
                ValidationSeverity.ERROR,
                "entity_kind_mismatch",
                f"{owner_id}.{field}",
                (
                    f"{target_id} is {actual_kind.value}, expected "
                    f"{expected_kind.value}"
                ),
                owner_id,
            )
        if owner_active and target.lifecycle is KnowledgeLifecycle.RETIRED:
            add(
                ValidationSeverity.ERROR,
                "active_reference_to_retired_entity",
                f"{owner_id}.{field}",
                f"active knowledge references retired entity {target_id}",
                owner_id,
            )
        return target

    snapshot_ids = set(known_snapshot_ids)

    def check_snapshot_reference(
        owner_id: str,
        field: str,
        snapshot_id: str,
    ) -> None:
        if snapshot_id not in snapshot_ids:
            add(
                ValidationSeverity.ERROR,
                "missing_evidence_snapshot",
                f"{owner_id}.{field}",
                f"source snapshot {snapshot_id} is not in the release inventory",
                owner_id,
            )

    for entity in entities:
        owner_active = entity.lifecycle is KnowledgeLifecycle.ACTIVE
        if isinstance(entity, Claim):
            check_entity_reference(
                owner_id=entity.id,
                field="subject_id",
                target_id=entity.subject_id,
                owner_active=owner_active,
            )
            if entity.object_id is not None:
                check_entity_reference(
                    owner_id=entity.id,
                    field="object_id",
                    target_id=entity.object_id,
                    owner_active=owner_active,
                )
            for index, evidence in enumerate(entity.evidence):
                check_snapshot_reference(
                    entity.id,
                    f"evidence[{index}].source_snapshot_id",
                    evidence.source_snapshot_id,
                )
        elif isinstance(entity, DecisionPattern):
            for claim_id in entity.supporting_claim_ids:
                target = check_entity_reference(
                    owner_id=entity.id,
                    field="supporting_claim_ids",
                    target_id=claim_id,
                    expected_kind=EntityKind.CLAIM,
                    owner_active=owner_active,
                )
                if target is not None and claim_id not in claim_by_id:
                    add(
                        ValidationSeverity.ERROR,
                        "invalid_supporting_claim",
                        f"{entity.id}.supporting_claim_ids",
                        f"{claim_id} is not a claim",
                        entity.id,
                    )
        elif isinstance(entity, OutcomeObservation):
            for pattern_id in entity.decision_pattern_ids:
                check_entity_reference(
                    owner_id=entity.id,
                    field="decision_pattern_ids",
                    target_id=pattern_id,
                    expected_kind=EntityKind.DECISION_PATTERN,
                    owner_active=owner_active,
                )
            for snapshot_id in entity.source_snapshot_ids:
                check_snapshot_reference(
                    entity.id,
                    "source_snapshot_ids",
                    snapshot_id,
                )

    edge_keys: dict[tuple[object, ...], str] = {}
    active_relationship_pairs: dict[
        tuple[str, str],
        set[RelationshipType],
    ] = defaultdict(set)
    for relationship in relationships:
        owner_active = relationship.lifecycle is KnowledgeLifecycle.ACTIVE
        check_entity_reference(
            owner_id=relationship.id,
            field="source_id",
            target_id=relationship.source_id,
            expected_kind=relationship.source_kind,
            owner_active=owner_active,
        )
        check_entity_reference(
            owner_id=relationship.id,
            field="target_id",
            target_id=relationship.target_id,
            expected_kind=relationship.target_kind,
            owner_active=owner_active,
        )
        for claim_id in relationship.supporting_claim_ids:
            check_entity_reference(
                owner_id=relationship.id,
                field="supporting_claim_ids",
                target_id=claim_id,
                expected_kind=EntityKind.CLAIM,
                owner_active=owner_active,
            )

        edge_key = (
            relationship.relationship_type,
            relationship.source_id,
            relationship.target_id,
            relationship.scope,
        )
        prior_id = edge_keys.get(edge_key)
        if prior_id is not None:
            add(
                ValidationSeverity.ERROR,
                "duplicate_relationship",
                relationship.id,
                f"duplicates semantic edge declared by {prior_id}",
                relationship.id,
            )
        else:
            edge_keys[edge_key] = relationship.id

        if relationship.lifecycle is KnowledgeLifecycle.ACTIVE:
            pair = tuple(
                sorted((relationship.source_id, relationship.target_id))
            )
            active_relationship_pairs[pair].add(
                relationship.relationship_type
            )

    for pair, relationship_types in sorted(active_relationship_pairs.items()):
        if {
            RelationshipType.COMPATIBLE_WITH,
            RelationshipType.INCOMPATIBLE_WITH,
        }.issubset(relationship_types):
            add(
                ValidationSeverity.ERROR,
                "conflicting_relationships",
                f"{pair[0]}->{pair[1]}",
                "entities are both compatible and incompatible in active knowledge",
            )

    known_ids = set(entity_by_id) | set(aliases)
    for transition in transitions:
        for prior_id in transition.prior_ids:
            if prior_id not in known_ids:
                add(
                    ValidationSeverity.ERROR,
                    "unknown_transition_prior",
                    f"{transition.id}.prior_ids",
                    f"prior identifier {prior_id} is not known",
                    transition.id,
                )
        for successor_id in transition.successor_ids:
            if successor_id not in entity_by_id:
                add(
                    ValidationSeverity.ERROR,
                    "unknown_transition_successor",
                    f"{transition.id}.successor_ids",
                    f"successor identifier {successor_id} does not exist",
                    transition.id,
                )

    for relationship_type in (
        RelationshipType.REQUIRES,
        RelationshipType.SUPERSEDES,
    ):
        for cycle in _find_cycles(relationships, relationship_type):
            add(
                ValidationSeverity.ERROR,
                f"{relationship_type.value.lower()}_cycle",
                " -> ".join(cycle),
                (
                    f"{relationship_type.value} graph contains a cycle: "
                    + " -> ".join(cycle)
                ),
            )

    severity_order = {
        ValidationSeverity.ERROR: 0,
        ValidationSeverity.WARNING: 1,
    }
    ordered_issues = tuple(
        sorted(
            issues,
            key=lambda issue: (
                severity_order[issue.severity],
                issue.code,
                issue.location,
                issue.message,
            ),
        )
    )
    payload = {
        "as_of": as_of.isoformat(),
        "entity_count": len(entities),
        "relationship_count": len(relationships),
        "transition_count": len(transitions),
        "snapshot_count": len(snapshot_ids),
        "issues": [
            issue.model_dump(mode="json", exclude_none=True)
            for issue in ordered_issues
        ],
    }
    return KnowledgeValidationReport(
        as_of=as_of,
        entity_count=len(entities),
        relationship_count=len(relationships),
        transition_count=len(transitions),
        snapshot_count=len(snapshot_ids),
        issues=ordered_issues,
        report_hash=content_hash(payload),
    )
