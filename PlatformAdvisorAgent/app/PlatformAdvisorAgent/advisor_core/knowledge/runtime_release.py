"""Fail-closed loading for promoted runtime knowledge releases."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from advisor_core.v3.deployable.models import DeployableCatalogRelease
from advisor_core.v3.models import CatalogRelease

from .release_artifacts import (
    KnowledgeReleaseArtifacts,
    KnowledgeReleaseManifest,
    ReleaseArtifactFile,
)
from .decision_guidance import DecisionGuidanceProjection
from .advisory import AdvisoryCorpus


DEFAULT_RELEASE_ID = "release:coding-platform-knowledge"
DEFAULT_RELEASE_PLATFORM = "coding-platform"
DEFAULT_RELEASE_VERSION = "1.5.0"
DEFAULT_RELEASE_MANIFEST_HASH = (
    "sha256:0fbe1f63d216fd46ab80beed9e9f0a51d724f283974563430f98753366afef60"
)
RELEASE_ROOT_ENV = "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_ROOT"
RELEASE_PLATFORM_ENV = "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_PLATFORM"
RELEASE_VERSION_ENV = "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_VERSION"
RELEASE_MANIFEST_HASH_ENV = (
    "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_MANIFEST_HASH"
)


class KnowledgeReleaseLoadError(ValueError):
    """Raised when a promoted release cannot be trusted at runtime."""


@dataclass(frozen=True, slots=True)
class LoadedKnowledgeRelease:
    root: Path
    manifest: KnowledgeReleaseManifest
    logical_catalog: CatalogRelease
    deployable_catalog: DeployableCatalogRelease
    decision_guidance: DecisionGuidanceProjection
    advisory_corpus: AdvisoryCorpus | None


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise KnowledgeReleaseLoadError(
            f"knowledge release artifact is missing: {path}"
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KnowledgeReleaseLoadError(
            f"knowledge release artifact is not valid UTF-8 JSON: {path}"
        ) from exc


def _validate_internal_hash(
    payloads: dict[str, object],
    *,
    path: str,
    field: str,
    expected: str,
) -> None:
    payload = payloads.get(path)
    if not isinstance(payload, dict) or payload.get(field) != expected:
        raise KnowledgeReleaseLoadError(
            f"{path} does not match manifest field {field}"
        )


def load_pinned_knowledge_release(
    release_directory: str | Path,
    *,
    expected_release_id: str = DEFAULT_RELEASE_ID,
    expected_version: str = DEFAULT_RELEASE_VERSION,
    expected_manifest_hash: str = DEFAULT_RELEASE_MANIFEST_HASH,
) -> LoadedKnowledgeRelease:
    """Load and verify every artifact in one immutable release directory."""

    root = Path(release_directory).expanduser().resolve()
    manifest_path = root / "manifest.json"
    try:
        manifest = KnowledgeReleaseManifest.model_validate(
            _load_json(manifest_path)
        )
    except ValidationError as exc:
        raise KnowledgeReleaseLoadError(
            f"knowledge release manifest is invalid: {exc}"
        ) from exc

    if manifest.release_id != expected_release_id:
        raise KnowledgeReleaseLoadError(
            f"knowledge release id {manifest.release_id!r} does not match "
            f"configured id {expected_release_id!r}"
        )
    if manifest.release_version != expected_version:
        raise KnowledgeReleaseLoadError(
            f"knowledge release version {manifest.release_version!r} does not "
            f"match configured version {expected_version!r}"
        )
    if manifest.manifest_hash != expected_manifest_hash:
        raise KnowledgeReleaseLoadError(
            "knowledge release manifest hash does not match the configured pin"
        )
    if manifest.scenario_pass_count != manifest.scenario_count:
        raise KnowledgeReleaseLoadError(
            "knowledge release benchmark did not pass every scenario"
        )

    listed_paths = {record.path for record in manifest.files}
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual_paths != listed_paths:
        missing = sorted(listed_paths - actual_paths)
        unexpected = sorted(actual_paths - listed_paths)
        raise KnowledgeReleaseLoadError(
            "knowledge release file inventory differs from its manifest: "
            f"missing={missing}, unexpected={unexpected}"
        )

    artifacts: list[ReleaseArtifactFile] = []
    payloads: dict[str, object] = {}
    for record in manifest.files:
        path = (root / record.path).resolve()
        if not path.is_relative_to(root):
            raise KnowledgeReleaseLoadError(
                f"knowledge release path escapes its root: {record.path}"
            )
        raw = path.read_bytes()
        if len(raw) != record.size_bytes or _sha256(raw) != record.content_hash:
            raise KnowledgeReleaseLoadError(
                f"knowledge release artifact failed integrity verification: "
                f"{record.path}"
            )
        try:
            content = raw.decode("utf-8")
            payloads[record.path] = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KnowledgeReleaseLoadError(
                f"knowledge release artifact is not valid UTF-8 JSON: "
                f"{record.path}"
            ) from exc
        artifacts.append(
            ReleaseArtifactFile(
                path=record.path,
                media_type=record.media_type,
                content=content,
                content_hash=record.content_hash,
                size_bytes=record.size_bytes,
            )
        )

    try:
        KnowledgeReleaseArtifacts(
            manifest=manifest,
            files=tuple(artifacts),
        )
        logical = CatalogRelease.model_validate(
            payloads["logical-catalog.json"]
        )
        deployable = DeployableCatalogRelease.model_validate(
            payloads["deployable-catalog.json"]
        )
        decision_guidance = DecisionGuidanceProjection.model_validate(
            payloads["decision-guidance.json"]
        )
        advisory_corpus = (
            AdvisoryCorpus.model_validate(payloads["advisory-corpus.json"])
            if "advisory-corpus.json" in payloads
            else None
        )
    except (KeyError, ValidationError, ValueError) as exc:
        raise KnowledgeReleaseLoadError(
            f"knowledge release runtime catalogs are invalid: {exc}"
        ) from exc

    if (
        logical.id != manifest.logical_catalog_id
        or logical.version != manifest.logical_catalog_version
        or logical.content_hash != manifest.logical_catalog_hash
    ):
        raise KnowledgeReleaseLoadError(
            "logical catalog metadata does not match the release manifest"
        )
    if (
        deployable.id != manifest.deployable_catalog_id
        or deployable.version != manifest.deployable_catalog_version
        or deployable.content_hash != manifest.deployable_catalog_hash
        or deployable.logical_catalog_id != logical.id
    ):
        raise KnowledgeReleaseLoadError(
            "deployable catalog metadata does not match the release manifest"
        )

    _validate_internal_hash(
        payloads,
        path="semantic-validation.json",
        field="report_hash",
        expected=manifest.semantic_validation_hash,
    )
    _validate_internal_hash(
        payloads,
        path="runtime-graph.json",
        field="graph_hash",
        expected=manifest.runtime_graph_hash,
    )
    _validate_internal_hash(
        payloads,
        path="search-projection.json",
        field="projection_hash",
        expected=manifest.search_projection_hash,
    )
    _validate_internal_hash(
        payloads,
        path="vector-projection.json",
        field="projection_hash",
        expected=manifest.vector_projection_hash,
    )
    _validate_internal_hash(
        payloads,
        path="decision-guidance.json",
        field="projection_hash",
        expected=manifest.decision_guidance_hash,
    )
    if manifest.advisory_corpus_hash is not None:
        _validate_internal_hash(
            payloads,
            path="advisory-corpus.json",
            field="corpus_hash",
            expected=manifest.advisory_corpus_hash,
        )
    elif advisory_corpus is not None:
        raise KnowledgeReleaseLoadError(
            "advisory corpus is present without a manifest hash"
        )
    benchmark = payloads.get("benchmark-report.json")
    benchmark_results = (
        benchmark.get("results", [])
        if isinstance(benchmark, dict)
        else []
    )
    if (
        not isinstance(benchmark, dict)
        or benchmark.get("scenario_count") != manifest.scenario_count
        or benchmark.get("pass_count") != manifest.scenario_pass_count
        or len(benchmark_results) != manifest.scenario_count
        or any(
            not isinstance(row, dict) or row.get("passed") is not True
            for row in benchmark_results
        )
    ):
        raise KnowledgeReleaseLoadError(
            "benchmark report does not match the release manifest"
        )
    validation = payloads.get("semantic-validation.json")
    if not isinstance(validation, dict) or validation.get("issues") != []:
        raise KnowledgeReleaseLoadError(
            "semantic validation report contains release-blocking issues"
        )

    return LoadedKnowledgeRelease(
        root=root,
        manifest=manifest,
        logical_catalog=logical,
        deployable_catalog=deployable,
        decision_guidance=decision_guidance,
        advisory_corpus=advisory_corpus,
    )


def _candidate_release_directories(
    platform: str,
    version: str,
) -> tuple[Path, ...]:
    bases: list[Path] = [
        Path.cwd() / "runtime_releases",
        Path.cwd() / "knowledge" / "releases",
    ]
    for ancestor in Path(__file__).resolve().parents:
        bases.extend((
            ancestor / "runtime_releases",
            ancestor / "knowledge" / "releases",
        ))
    candidates: list[Path] = []
    for base in bases:
        candidate = base / platform / version
        if candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)


def resolve_configured_release_directory() -> Path:
    platform = os.environ.get(
        RELEASE_PLATFORM_ENV,
        DEFAULT_RELEASE_PLATFORM,
    ).strip()
    version = os.environ.get(
        RELEASE_VERSION_ENV,
        DEFAULT_RELEASE_VERSION,
    ).strip()
    configured_root = os.environ.get(RELEASE_ROOT_ENV, "").strip()
    if not platform or not version:
        raise KnowledgeReleaseLoadError(
            "knowledge release platform and version must be configured"
        )
    if configured_root:
        root = Path(configured_root).expanduser()
        candidate = root if (root / "manifest.json").is_file() else (
            root / platform / version
        )
        if not (candidate / "manifest.json").is_file():
            raise KnowledgeReleaseLoadError(
                f"configured knowledge release does not exist: {candidate}"
            )
        return candidate

    for candidate in _candidate_release_directories(platform, version):
        if (candidate / "manifest.json").is_file():
            return candidate
    raise KnowledgeReleaseLoadError(
        f"knowledge release {platform}/{version} was not found"
    )


@lru_cache(maxsize=1)
def get_configured_knowledge_release() -> LoadedKnowledgeRelease:
    version = os.environ.get(
        RELEASE_VERSION_ENV,
        DEFAULT_RELEASE_VERSION,
    ).strip()
    configured_hash = os.environ.get(RELEASE_MANIFEST_HASH_ENV, "").strip()
    if not configured_hash:
        if version != DEFAULT_RELEASE_VERSION:
            raise KnowledgeReleaseLoadError(
                "a non-default knowledge release version requires an explicit "
                "manifest hash pin"
            )
        configured_hash = DEFAULT_RELEASE_MANIFEST_HASH
    return load_pinned_knowledge_release(
        resolve_configured_release_directory(),
        expected_version=version,
        expected_manifest_hash=configured_hash,
    )
