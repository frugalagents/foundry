from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from advisor_core.knowledge.runtime_release import (
    DEFAULT_RELEASE_MANIFEST_HASH,
    KnowledgeReleaseLoadError,
    get_configured_knowledge_release,
    load_pinned_knowledge_release,
    resolve_configured_release_directory,
)
from advisor_core.v3.projection import build_frontend_projection
from advisor_core.v3.runtime import build_runtime_workspace


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
RELEASE_ROOT = (
    REPOSITORY_ROOT
    / "knowledge"
    / "releases"
    / "coding-platform"
    / "1.3.0"
)
AS_OF = date(2026, 8, 11)


def test_checked_in_release_loads_with_every_runtime_pin_verified():
    release = load_pinned_knowledge_release(RELEASE_ROOT)

    assert release.manifest.manifest_hash == DEFAULT_RELEASE_MANIFEST_HASH
    assert release.logical_catalog.content_hash == (
        release.manifest.logical_catalog_hash
    )
    assert release.deployable_catalog.content_hash == (
        release.manifest.deployable_catalog_hash
    )
    assert release.deployable_catalog.logical_catalog_id == (
        release.logical_catalog.id
    )


def test_runtime_release_rejects_tampering_and_unlisted_files(tmp_path: Path):
    target = tmp_path / "release"
    shutil.copytree(RELEASE_ROOT, target)
    logical_path = target / "logical-catalog.json"
    logical_path.write_text(
        logical_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        KnowledgeReleaseLoadError,
        match="failed integrity verification",
    ):
        load_pinned_knowledge_release(target)

    shutil.rmtree(target)
    shutil.copytree(RELEASE_ROOT, target)
    (target / "unlisted.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(
        KnowledgeReleaseLoadError,
        match="file inventory differs",
    ):
        load_pinned_knowledge_release(target)


def test_runtime_release_rejects_the_wrong_manifest_pin():
    with pytest.raises(
        KnowledgeReleaseLoadError,
        match="manifest hash does not match",
    ):
        load_pinned_knowledge_release(
            RELEASE_ROOT,
            expected_manifest_hash=f"sha256:{'0' * 64}",
        )


def test_configured_release_resolution_supports_packaged_root(
    monkeypatch,
    tmp_path: Path,
):
    packaged = tmp_path / "coding-platform" / "1.3.0"
    shutil.copytree(RELEASE_ROOT, packaged)
    monkeypatch.setenv(
        "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_ROOT",
        str(tmp_path),
    )
    get_configured_knowledge_release.cache_clear()

    assert resolve_configured_release_directory() == packaged
    assert get_configured_knowledge_release().root == packaged

    get_configured_knowledge_release.cache_clear()


def test_runtime_projection_never_recompiles_source_catalogs(monkeypatch):
    release = load_pinned_knowledge_release(RELEASE_ROOT)
    pinned, workspace = build_runtime_workspace(
        AS_OF,
        workspace_id="workspace:runtime-release-test",
        requirement_values={"requirement:model-fallback": True},
        release=release,
    )

    def unavailable(*_args, **_kwargs):
        raise AssertionError("source catalog compiler must not run")

    monkeypatch.setattr(
        "advisor_core.v3.projection.compile_deployable_catalog",
        unavailable,
    )
    monkeypatch.setattr(
        "advisor_core.v3.deployable.builder.compile_deployable_catalog",
        unavailable,
    )
    projection = build_frontend_projection(
        workspace,
        pinned.logical_catalog,
        deployable_catalog=pinned.deployable_catalog,
    )

    assert projection["catalog"]["content_hash"] == (
        pinned.manifest.logical_catalog_hash
    )
    assert projection["deployable_solution"]["deployable_catalog_hash"] == (
        pinned.manifest.deployable_catalog_hash
    )
