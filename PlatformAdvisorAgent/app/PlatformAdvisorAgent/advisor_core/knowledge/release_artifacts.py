"""Deterministic, content-addressed knowledge release artifacts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from advisor_core.v3.deployable.models import DeployableCatalogRelease
from advisor_core.v3.models import CatalogRelease, SemanticVersion

from .legacy_migration import LegacyKnowledgeMigration
from .advisory import AdvisoryCorpus
from .decision_guidance import (
    DecisionGuidanceProjection,
    compile_decision_guidance,
)
from .models import FrozenModel, StableId, content_hash
from .release_scenarios import (
    ReleaseScenarioResult,
    ReleaseScenarioSuite,
)
from .runtime_graph import RuntimeKnowledgeGraph
from .search_projection import KnowledgeSearchProjection
from .vector_projection import KnowledgeVectorProjection
from .validation import KnowledgeValidationReport


class KnowledgeReleaseBuildError(ValueError):
    pass


class ReleaseArtifactConflictError(RuntimeError):
    pass


class ReleaseArtifactFile(FrozenModel):
    path: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._/-]*$")
    media_type: str = Field(min_length=1)
    content: str
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def path_is_relative_and_safe(cls, path: str) -> str:
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("artifact path must be safe and relative")
        return path

    @model_validator(mode="after")
    def content_matches_integrity_fields(self) -> "ReleaseArtifactFile":
        encoded = self.content.encode("utf-8")
        actual_hash = (
            f"sha256:{hashlib.sha256(encoded).hexdigest()}"
        )
        if self.content_hash != actual_hash:
            raise ValueError("artifact content hash does not match content")
        if self.size_bytes != len(encoded):
            raise ValueError("artifact size does not match content")
        return self


class ReleaseFileRecord(FrozenModel):
    path: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class KnowledgeReleaseManifestPayload(FrozenModel):
    schema_version: str = "1.0"
    release_id: StableId
    release_version: SemanticVersion
    built_at: datetime
    compiler_version: SemanticVersion
    migration_bundle_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    logical_catalog_id: StableId
    logical_catalog_version: SemanticVersion
    logical_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    deployable_catalog_id: StableId
    deployable_catalog_version: SemanticVersion
    deployable_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_graph_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    search_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    vector_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    decision_guidance_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    advisory_corpus_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    scenario_suite_id: StableId
    scenario_suite_version: SemanticVersion
    scenario_count: int = Field(ge=1)
    scenario_pass_count: int = Field(ge=0)
    files: tuple[ReleaseFileRecord, ...] = Field(min_length=1)


class KnowledgeReleaseManifest(KnowledgeReleaseManifestPayload):
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def manifest_hash_matches_content(self) -> "KnowledgeReleaseManifest":
        payload = self.model_dump(
            mode="json",
            exclude={"manifest_hash"},
            exclude_none=True,
        )
        if self.manifest_hash != content_hash(payload):
            raise ValueError("release manifest hash does not match content")
        if self.scenario_pass_count > self.scenario_count:
            raise ValueError("scenario pass count cannot exceed total")
        return self


class KnowledgeReleaseArtifacts(FrozenModel):
    manifest: KnowledgeReleaseManifest
    files: tuple[ReleaseArtifactFile, ...]

    @model_validator(mode="after")
    def files_match_manifest(self) -> "KnowledgeReleaseArtifacts":
        records = tuple(
            ReleaseFileRecord(
                path=file.path,
                media_type=file.media_type,
                content_hash=file.content_hash,
                size_bytes=file.size_bytes,
            )
            for file in self.files
        )
        if records != self.manifest.files:
            raise ValueError("release files do not match manifest records")
        return self


def _json_artifact(path: str, payload: object) -> ReleaseArtifactFile:
    content = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
    encoded = content.encode("utf-8")
    return ReleaseArtifactFile(
        path=path,
        media_type="application/json",
        content=content,
        content_hash=f"sha256:{hashlib.sha256(encoded).hexdigest()}",
        size_bytes=len(encoded),
    )


def build_knowledge_release_artifacts(
    *,
    release_id: StableId,
    release_version: SemanticVersion,
    built_at: datetime,
    compiler_version: SemanticVersion,
    migration_bundle_hash: str,
    migration: LegacyKnowledgeMigration,
    logical_catalog: CatalogRelease,
    deployable_catalog: DeployableCatalogRelease,
    validation: KnowledgeValidationReport,
    runtime_graph: RuntimeKnowledgeGraph,
    search_projection: KnowledgeSearchProjection,
    vector_projection: KnowledgeVectorProjection,
    scenario_suite: ReleaseScenarioSuite,
    scenario_results: tuple[ReleaseScenarioResult, ...],
    advisory_corpus: AdvisoryCorpus | None = None,
) -> KnowledgeReleaseArtifacts:
    if deployable_catalog.logical_catalog_id != logical_catalog.id:
        raise KnowledgeReleaseBuildError(
            "deployable catalog does not target the logical catalog"
        )
    if not validation.is_valid:
        raise KnowledgeReleaseBuildError(
            "semantic validation must pass before release generation"
        )
    if runtime_graph.as_of != validation.as_of:
        raise KnowledgeReleaseBuildError(
            "runtime graph and semantic validation dates do not match"
        )
    if search_projection.as_of != validation.as_of:
        raise KnowledgeReleaseBuildError(
            "search projection and semantic validation dates do not match"
        )
    if vector_projection.as_of != validation.as_of:
        raise KnowledgeReleaseBuildError(
            "vector projection and semantic validation dates do not match"
        )
    if (
        vector_projection.source_search_projection_hash
        != search_projection.projection_hash
    ):
        raise KnowledgeReleaseBuildError(
            "vector projection does not target the supplied search projection"
        )

    decision_guidance = compile_decision_guidance(
        entities=migration.entities,
        source_registry=migration.source_registry,
        snapshots=migration.snapshots,
        as_of=validation.as_of,
    )
    result_by_id = {
        result.scenario_id: result for result in scenario_results
    }
    benchmark_rows = []
    for scenario in scenario_suite.scenarios:
        result = result_by_id.get(scenario.id)
        if result is None:
            raise KnowledgeReleaseBuildError(
                f"missing scenario result for {scenario.id}"
            )
        passed = (
            result.after_valid is scenario.expected_valid
            and set(scenario.expected_issue_codes) <= set(result.issue_codes)
            and (
                scenario.expected_before_valid is None
                or result.before_valid is scenario.expected_before_valid
            )
        )
        benchmark_rows.append({
            "scenario_id": scenario.id,
            "kind": scenario.kind.value,
            "passed": passed,
            "before_valid": result.before_valid,
            "after_valid": result.after_valid,
            "issue_codes": list(result.issue_codes),
            "before_report_hash": result.before_report_hash,
            "after_report_hash": result.after_report_hash,
        })
    pass_count = sum(bool(row["passed"]) for row in benchmark_rows)
    if pass_count != len(benchmark_rows):
        raise KnowledgeReleaseBuildError(
            "one or more release benchmark scenarios failed"
        )

    snapshots_by_source: dict[str, list[object]] = {}
    for snapshot in migration.snapshots:
        snapshots_by_source.setdefault(snapshot.source_id, []).append(snapshot)
    source_inventory = {
        "schema_version": "1.0",
        "sources": [
            {
                "source_id": source.id,
                "name": source.name,
                "publisher": source.publisher,
                "authority_tier": source.authority_tier.value,
                "snapshots": [
                    {
                        "snapshot_id": snapshot.snapshot_id,
                        "retrieved_at": snapshot.retrieved_at,
                        "final_uri": snapshot.final_uri,
                        "raw_content_hash": snapshot.raw_content_hash,
                        "normalized_content_hash": (
                            snapshot.normalized_content_hash
                        ),
                    }
                    for snapshot in sorted(
                        snapshots_by_source.get(source.id, []),
                        key=lambda item: item.snapshot_id,
                    )
                ],
            }
            for source in migration.source_registry.sources
        ],
    }
    benchmark = {
        "schema_version": "1.0",
        "scenario_suite_id": scenario_suite.id,
        "scenario_suite_version": scenario_suite.version,
        "scenario_count": len(benchmark_rows),
        "pass_count": pass_count,
        "results": benchmark_rows,
    }
    artifact_files = [
        _json_artifact(
            "logical-catalog.json",
            logical_catalog.model_dump(mode="json"),
        ),
        _json_artifact(
            "deployable-catalog.json",
            deployable_catalog.model_dump(mode="json"),
        ),
        _json_artifact(
            "semantic-validation.json",
            validation.model_dump(mode="json"),
        ),
        _json_artifact(
            "runtime-graph.json",
            runtime_graph.model_dump(mode="json"),
        ),
        _json_artifact(
            "search-projection.json",
            search_projection.model_dump(mode="json"),
        ),
        _json_artifact(
            "vector-projection.json",
            vector_projection.model_dump(mode="json"),
        ),
        _json_artifact(
            "decision-guidance.json",
            decision_guidance.model_dump(mode="json"),
        ),
        _json_artifact("source-inventory.json", source_inventory),
        _json_artifact("benchmark-report.json", benchmark),
    ]
    if advisory_corpus is not None:
        artifact_files.append(_json_artifact(
            "advisory-corpus.json",
            advisory_corpus.model_dump(mode="json"),
        ))
    files = tuple(
        sorted(
            artifact_files,
            key=lambda file: file.path,
        )
    )
    records = tuple(
        ReleaseFileRecord(
            path=file.path,
            media_type=file.media_type,
            content_hash=file.content_hash,
            size_bytes=file.size_bytes,
        )
        for file in files
    )
    manifest_payload = KnowledgeReleaseManifestPayload(
        release_id=release_id,
        release_version=release_version,
        built_at=built_at,
        compiler_version=compiler_version,
        migration_bundle_hash=migration_bundle_hash,
        logical_catalog_id=logical_catalog.id,
        logical_catalog_version=logical_catalog.version,
        logical_catalog_hash=logical_catalog.content_hash,
        deployable_catalog_id=deployable_catalog.id,
        deployable_catalog_version=deployable_catalog.version,
        deployable_catalog_hash=deployable_catalog.content_hash,
        semantic_validation_hash=validation.report_hash,
        runtime_graph_hash=runtime_graph.graph_hash,
        search_projection_hash=search_projection.projection_hash,
        vector_projection_hash=vector_projection.projection_hash,
        decision_guidance_hash=decision_guidance.projection_hash,
        advisory_corpus_hash=(
            advisory_corpus.corpus_hash
            if advisory_corpus is not None
            else None
        ),
        scenario_suite_id=scenario_suite.id,
        scenario_suite_version=scenario_suite.version,
        scenario_count=len(benchmark_rows),
        scenario_pass_count=pass_count,
        files=records,
    )
    normalized_manifest_payload = manifest_payload.model_dump(
        mode="json",
        exclude_none=True,
    )
    manifest = KnowledgeReleaseManifest(
        **normalized_manifest_payload,
        manifest_hash=content_hash(normalized_manifest_payload),
    )
    return KnowledgeReleaseArtifacts(manifest=manifest, files=files)


def write_knowledge_release_artifacts(
    root: Path,
    artifacts: KnowledgeReleaseArtifacts,
) -> None:
    root.mkdir(parents=True, exist_ok=True)

    def write_immutable(path: Path, content: str) -> None:
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(content)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != content:
                raise ReleaseArtifactConflictError(
                    f"release artifact already exists with different content: {path}"
                ) from None

    for file in artifacts.files:
        destination = root / file.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_immutable(destination, file.content)
    manifest_content = json.dumps(
        artifacts.manifest.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
    write_immutable(root / "manifest.json", manifest_content)
