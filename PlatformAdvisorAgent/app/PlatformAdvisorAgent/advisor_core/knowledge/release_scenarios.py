"""Declarative safety scenarios for knowledge release validation."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from .legacy_migration import LegacyKnowledgeMigration
from .models import (
    FrozenModel,
    KnowledgeEntity,
    KnowledgeRelationship,
    StableId,
    StrEnum,
)
from .validation import validate_knowledge_release


class ReleaseScenarioKind(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"
    STALE = "stale"
    CONTRADICTION = "contradiction"
    ONE_VARIABLE_FLIP = "one_variable_flip"


class ReleaseMutationType(StrEnum):
    NONE = "none"
    REMOVE_ENTITY = "remove_entity"
    REMOVE_SNAPSHOT = "remove_snapshot"
    SET_STALE_AFTER = "set_stale_after"
    ADD_RELATIONSHIP_CONFLICT = "add_relationship_conflict"


class ReleaseScenarioMutation(FrozenModel):
    mutation_type: ReleaseMutationType
    target_id: StableId | None = None
    value: date | None = None
    source_id: StableId | None = None
    relationship_target_id: StableId | None = None
    supporting_claim_id: StableId | None = None

    @model_validator(mode="after")
    def fields_match_mutation(self) -> "ReleaseScenarioMutation":
        if self.mutation_type in {
            ReleaseMutationType.REMOVE_ENTITY,
            ReleaseMutationType.REMOVE_SNAPSHOT,
            ReleaseMutationType.SET_STALE_AFTER,
        } and self.target_id is None:
            raise ValueError(f"{self.mutation_type.value} requires target_id")
        if (
            self.mutation_type is ReleaseMutationType.SET_STALE_AFTER
            and self.value is None
        ):
            raise ValueError("set_stale_after requires value")
        if self.mutation_type is ReleaseMutationType.ADD_RELATIONSHIP_CONFLICT:
            if not (
                self.source_id
                and self.relationship_target_id
                and self.supporting_claim_id
            ):
                raise ValueError(
                    "relationship conflict requires source, target, and claim"
                )
        return self


class ReleaseScenario(FrozenModel):
    id: StableId
    kind: ReleaseScenarioKind
    mutation: ReleaseScenarioMutation
    expected_valid: bool
    expected_issue_codes: tuple[str, ...] = ()
    expected_before_valid: bool | None = None


class ReleaseScenarioSuite(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    id: StableId
    version: str = Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
    )
    as_of: date
    scenarios: tuple[ReleaseScenario, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def covers_required_safety_kinds(self) -> "ReleaseScenarioSuite":
        kinds = [scenario.kind for scenario in self.scenarios]
        if len(kinds) != len(set(kinds)):
            raise ValueError("release scenario kinds must be unique")
        if set(kinds) != set(ReleaseScenarioKind):
            raise ValueError("release scenarios must cover every safety kind")
        return self


class ReleaseScenarioResult(FrozenModel):
    scenario_id: StableId
    kind: ReleaseScenarioKind
    before_valid: bool
    after_valid: bool
    issue_codes: tuple[str, ...]
    before_report_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    after_report_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def load_release_scenario_suite(path: Path) -> ReleaseScenarioSuite:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("release scenario suite must be an object")
    return ReleaseScenarioSuite.model_validate(document)


def _replace_entity(
    entities: tuple[KnowledgeEntity, ...],
    target_id: str,
    field: str,
    value: object,
) -> tuple[KnowledgeEntity, ...]:
    replaced: list[KnowledgeEntity] = []
    found = False
    for entity in entities:
        if entity.id != target_id:
            replaced.append(entity)
            continue
        found = True
        payload = entity.model_dump(mode="python")
        payload[field] = value
        replaced.append(entity.__class__.model_validate(payload))
    if not found:
        raise ValueError(f"scenario target entity does not exist: {target_id}")
    return tuple(replaced)


def _apply_mutation(
    migration: LegacyKnowledgeMigration,
    mutation: ReleaseScenarioMutation,
) -> tuple[
    tuple[KnowledgeEntity, ...],
    tuple[KnowledgeRelationship, ...],
    tuple[str, ...],
]:
    entities = migration.entities
    relationships = migration.relationships
    snapshot_ids = tuple(
        snapshot.snapshot_id for snapshot in migration.snapshots
    )
    if mutation.mutation_type is ReleaseMutationType.NONE:
        return entities, relationships, snapshot_ids
    if mutation.mutation_type is ReleaseMutationType.REMOVE_ENTITY:
        entities = tuple(
            entity for entity in entities if entity.id != mutation.target_id
        )
    elif mutation.mutation_type is ReleaseMutationType.REMOVE_SNAPSHOT:
        snapshot_ids = tuple(
            snapshot_id
            for snapshot_id in snapshot_ids
            if snapshot_id != mutation.target_id
        )
    elif mutation.mutation_type is ReleaseMutationType.SET_STALE_AFTER:
        entities = _replace_entity(
            entities,
            str(mutation.target_id),
            "stale_after",
            mutation.value,
        )
    elif (
        mutation.mutation_type
        is ReleaseMutationType.ADD_RELATIONSHIP_CONFLICT
    ):
        source = next(
            entity
            for entity in entities
            if entity.id == mutation.source_id
        )
        template = relationships[0]
        conflict_relationships = tuple(
            KnowledgeRelationship(
                id=f"relationship:scenario-{relationship_type.lower()}",
                title=f"Scenario {relationship_type.lower()} edge",
                summary=(
                    f"Release scenario edge between {mutation.source_id} and "
                    f"{mutation.relationship_target_id}."
                ),
                lifecycle="active",
                owner_id=source.owner_id,
                effective_from=source.effective_from,
                stale_after=source.stale_after,
                review=source.review,
                relationship_type=relationship_type,
                source_id=mutation.source_id,
                source_kind="Component",
                target_id=mutation.relationship_target_id,
                target_kind="Component",
                cardinality="many_to_many",
                scope=template.scope,
                supporting_claim_ids=(str(mutation.supporting_claim_id),),
            )
            for relationship_type in (
                "COMPATIBLE_WITH",
                "INCOMPATIBLE_WITH",
            )
        )
        relationships = (*relationships, *conflict_relationships)
    return entities, relationships, snapshot_ids


def run_release_scenarios(
    suite: ReleaseScenarioSuite,
    migration: LegacyKnowledgeMigration,
) -> tuple[ReleaseScenarioResult, ...]:
    baseline = validate_knowledge_release(
        entities=migration.entities,
        relationships=migration.relationships,
        known_snapshot_ids=tuple(
            snapshot.snapshot_id for snapshot in migration.snapshots
        ),
        as_of=suite.as_of,
    )
    results = []
    for scenario in suite.scenarios:
        entities, relationships, snapshot_ids = _apply_mutation(
            migration,
            scenario.mutation,
        )
        after = validate_knowledge_release(
            entities=entities,
            relationships=relationships,
            known_snapshot_ids=snapshot_ids,
            as_of=suite.as_of,
        )
        results.append(
            ReleaseScenarioResult(
                scenario_id=scenario.id,
                kind=scenario.kind,
                before_valid=baseline.is_valid,
                after_valid=after.is_valid,
                issue_codes=tuple(
                    sorted({issue.code for issue in after.issues})
                ),
                before_report_hash=baseline.report_hash,
                after_report_hash=after.report_hash,
            )
        )
    return tuple(results)
