from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from advisor_core.knowledge import (
    LegacyMigrationIntegrityError,
    compile_knowledge_catalog,
    compile_knowledge_deployable_catalog,
    load_legacy_migration_bundle,
    migrate_legacy_catalogs,
)
from advisor_core.v3 import compile_catalog
from advisor_core.v3.deployable import compile_deployable_catalog


AS_OF = date(2026, 8, 11)
CATALOG_ROOT = (
    Path(__file__).resolve().parents[1]
    / "advisor_core"
    / "v3"
    / "catalogs"
)
BUNDLE_PATH = (
    Path(__file__).resolve().parents[4]
    / "knowledge"
    / "migrations"
    / "coding-platform-v3.json"
)


def records_by_id(records):
    return {record.id: record for record in records}


def test_current_catalogs_round_trip_through_semantic_migration():
    legacy_logical = compile_catalog(
        CATALOG_ROOT / "coding-platform",
        as_of=AS_OF,
    )
    legacy_deployable = compile_deployable_catalog(
        legacy_logical,
        CATALOG_ROOT / "coding-platform-r0.2",
        as_of=AS_OF,
    )
    migration = migrate_legacy_catalogs(
        legacy_logical,
        legacy_deployable,
    )

    compiled_logical = compile_knowledge_catalog(
        entities=migration.entities,
        relationships=migration.relationships,
        source_registry=migration.source_registry,
        snapshots=migration.snapshots,
        projection=migration.logical_projection,
        as_of=AS_OF,
    )
    compiled_deployable = compile_knowledge_deployable_catalog(
        logical_catalog=compiled_logical,
        entities=migration.entities,
        relationships=migration.relationships,
        projection=migration.deployable_projection,
        as_of=AS_OF,
    )

    assert records_by_id(compiled_logical.requirements) == records_by_id(
        legacy_logical.requirements
    )
    assert records_by_id(compiled_logical.components) == records_by_id(
        legacy_logical.components
    )
    assert records_by_id(compiled_logical.patterns) == records_by_id(
        legacy_logical.patterns
    )
    assert records_by_id(compiled_logical.rules) == records_by_id(
        legacy_logical.rules
    )
    assert {
        claim.id for claim in compiled_logical.evidence_claims
    } == {
        claim.id for claim in legacy_logical.evidence_claims
    }
    assert records_by_id(compiled_deployable.interfaces) == records_by_id(
        legacy_deployable.interfaces
    )
    assert records_by_id(
        compiled_deployable.service_variants
    ) == records_by_id(legacy_deployable.service_variants)
    assert records_by_id(
        compiled_deployable.bundle_templates
    ) == records_by_id(legacy_deployable.bundle_templates)
    assert records_by_id(
        compiled_deployable.capability_rules
    ) == records_by_id(legacy_deployable.capability_rules)


def test_checked_in_migration_bundle_matches_current_catalog_sources():
    legacy_logical = compile_catalog(
        CATALOG_ROOT / "coding-platform",
        as_of=AS_OF,
    )
    legacy_deployable = compile_deployable_catalog(
        legacy_logical,
        CATALOG_ROOT / "coding-platform-r0.2",
        as_of=AS_OF,
    )

    migration, logical_hash, deployable_hash = load_legacy_migration_bundle(
        BUNDLE_PATH
    )

    assert logical_hash == legacy_logical.content_hash
    assert deployable_hash == legacy_deployable.content_hash
    assert len(migration.logical_projection.requirements) == 25
    assert len(
        [
            entity
            for entity in migration.entities
            if entity.kind == "Component"
        ]
    ) == 44
    assert len(migration.deployable_projection.variant_bindings) == 176


def test_migration_bundle_rejects_tampering(tmp_path: Path):
    tampered = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    tampered["logical_projection"]["manifest"]["title"] = "Tampered Platform"
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")

    try:
        load_legacy_migration_bundle(path)
    except LegacyMigrationIntegrityError as error:
        assert "hash does not match" in str(error)
    else:
        raise AssertionError("tampered migration bundle was accepted")
