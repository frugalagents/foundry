from __future__ import annotations

from datetime import date
from pathlib import Path

from advisor_core.knowledge import (
    DecisionPattern,
    compile_decision_guidance,
    contextualize_decision_guidance,
    load_legacy_migration_bundle,
    load_okf_corpus,
    load_pinned_knowledge_release,
)
from advisor_core.v3.projection import build_frontend_projection
from advisor_core.v3.runtime import build_runtime_workspace


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "knowledge"
    / "migrations"
    / "coding-platform-v3.json"
)
RELEASE_ROOT = (
    REPOSITORY_ROOT
    / "knowledge"
    / "releases"
    / "coding-platform"
    / "1.5.0"
)


def test_reviewed_decision_pattern_pages_cover_every_bundle_template():
    corpus = load_okf_corpus(
        REPOSITORY_ROOT / "knowledge" / "decision-patterns"
    )

    patterns = tuple(
        entity
        for entity in corpus.entities
        if isinstance(entity, DecisionPattern)
    )
    assert len(patterns) == 5
    assert {
        tag
        for pattern in patterns
        for tag in pattern.tags
        if tag.startswith("bundle-template:")
    } == {
        "bundle-template:aws-governed",
        "bundle-template:byop-portable",
        "bundle-template:hybrid-governed",
        "bundle-template:oss-sovereign",
        "bundle-template:saas-composable",
    }
    assert all(pattern.recommended_when for pattern in patterns)
    assert all(pattern.avoid_when for pattern in patterns)
    assert all(pattern.tradeoffs for pattern in patterns)


def test_guidance_compiles_with_reviewed_evidence_and_stable_template_keys():
    migration, _, _ = load_legacy_migration_bundle(MIGRATION_PATH)

    guidance = compile_decision_guidance(
        entities=migration.entities,
        source_registry=migration.source_registry,
        snapshots=migration.snapshots,
        as_of=date(2026, 8, 12),
    )

    assert len(guidance.patterns) == 5
    assert all(pattern.evidence for pattern in guidance.patterns)
    assert len({pattern.template_id for pattern in guidance.patterns}) == 5


def test_runtime_contextualizes_guidance_for_each_deployable_candidate():
    release = load_pinned_knowledge_release(RELEASE_ROOT)
    _, workspace = build_runtime_workspace(
        date(2026, 8, 12),
        workspace_id="workspace:guidance-test",
        release=release,
    )
    projection = build_frontend_projection(
        workspace,
        release.logical_catalog,
        deployable_catalog=release.deployable_catalog,
    )

    contextual = contextualize_decision_guidance(
        projection,
        release.decision_guidance,
    )

    candidate_ids = {
        candidate["bundle_id"]
        for candidate in projection["deployable_solution"]["candidates"]
    }
    assert {item["candidate_id"] for item in contextual} == candidate_ids
    assert all(item["advisory"] is True for item in contextual)
    assert all(item["fit"]["summary"] for item in contextual)
    assert all(item["recommended_when"] for item in contextual)
    assert all(item["avoid_when"] for item in contextual)
