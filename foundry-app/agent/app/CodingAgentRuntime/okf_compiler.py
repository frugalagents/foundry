from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from graph_healthcheck import run_graph_healthcheck
from knowledge_loader import KnowledgeNode, load_knowledge_base


TYPED_EDGE_FIELDS = (
    "alternatives",
    "implies",
    "conflicts_with",
    "requires",
    "exception_to",
)

ALLOWED_TRAVERSALS = {"mandate", "conditional", "probe"}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AdvisoryFactRule(_StrictModel):
    key: str
    value: Any = True
    status: str = "confirmed"
    match_any: list[str] = Field(default_factory=list)
    match_all: list[str] = Field(default_factory=list)
    min_trigger_pool_matches: int = 0
    value_from: str = ""
    label_map: dict[str, str] = Field(default_factory=dict)
    fact_text: str = ""

    @field_validator("key")
    @classmethod
    def _validate_key(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value


class AdvisoryActivationRule(_StrictModel):
    requires_facts_all: list[str] = Field(default_factory=list)
    requires_facts_any: list[str] = Field(default_factory=list)
    match_any: list[str] = Field(default_factory=list)
    match_all: list[str] = Field(default_factory=list)


class AdvisoryQuestionSpec(_StrictModel):
    id: str
    text: str
    why_it_matters: str = ""
    decision_domain: str = ""
    blocking: bool = True

    @field_validator("id", "text")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value


class AdvisoryOptionSpec(_StrictModel):
    path: str
    title: str
    summary: str = ""
    decision_domain: str = ""
    position: str = ""

    @field_validator("path", "title")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value


class AdvisoryOutputSpec(_StrictModel):
    decision_focus: str = ""
    question: AdvisoryQuestionSpec | None = None
    recommendation: str = ""
    risks: list[str] = Field(default_factory=list)
    options: list[AdvisoryOptionSpec] = Field(default_factory=list)


class AdvisoryResolutionRule(_StrictModel):
    when_facts_all: list[str] = Field(default_factory=list)
    decision: str = ""
    recommendation: str = ""


class AdvisorySpec(_StrictModel):
    slice: bool = False
    fact_rules: list[AdvisoryFactRule] = Field(default_factory=list)
    activate: AdvisoryActivationRule = Field(default_factory=AdvisoryActivationRule)
    output: AdvisoryOutputSpec = Field(default_factory=AdvisoryOutputSpec)
    resolutions: list[AdvisoryResolutionRule] = Field(default_factory=list)


class TypedEdges(_StrictModel):
    alternatives: tuple[str, ...] = ()
    implies: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    exception_to: tuple[str, ...] = ()

    @field_validator(*TYPED_EDGE_FIELDS, mode="before")
    @classmethod
    def _normalize_paths(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise ValueError("must be a list of node paths")
        normalized: list[str] = []
        for item in value:
            text = str(item).strip()
            if not text:
                raise ValueError("must not contain blank paths")
            if text.endswith(".md"):
                raise ValueError("must use node paths without .md suffix")
            normalized.append(text)
        return tuple(dict.fromkeys(normalized))


class CompiledOKFNode(_StrictModel):
    id: str
    path: str
    node_type: str = ""
    title: str
    group: str
    traversal: str
    decision_domain: str
    description: str = ""
    status: str = ""
    tags: tuple[str, ...] = ()
    decision_question: str = ""
    priority: int = 0
    blocking: bool = False
    linked_paths: tuple[str, ...] = ()
    typed_edges: TypedEdges = Field(default_factory=TypedEdges)
    advisory: AdvisorySpec | None = None
    source_file: str

    @field_validator("id", "path", "title", "group", "decision_domain", "source_file")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("traversal")
    @classmethod
    def _validate_traversal(cls, value: str) -> str:
        if value and value not in ALLOWED_TRAVERSALS:
            allowed = ", ".join(sorted(ALLOWED_TRAVERSALS))
            raise ValueError(f"must be one of: {allowed}")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> "CompiledOKFNode":
        if self.id != self.path:
            raise ValueError("id must match path for compiled OKF nodes")
        if self.traversal:
            return self

        if self.node_type == "platform-component-group":
            return self

        raise ValueError("traversal must not be empty")


class OKFValidationIssue(_StrictModel):
    type: str
    node: str
    message: str
    field: str = ""
    target: str = ""
    source_file: str = ""


class OKFReleaseManifest(_StrictModel):
    schema_version: str
    generated_at: str
    knowledge_dir: str
    node_count: int
    advisory_slice_count: int
    typed_edge_count: int
    graph_sha256: str


class CompiledOKFRelease(_StrictModel):
    manifest: OKFReleaseManifest
    nodes: list[CompiledOKFNode]


class OKFCompileError(Exception):
    def __init__(self, issues: list[OKFValidationIssue]):
        self.issues = issues
        super().__init__(self._render_message())

    def _render_message(self) -> str:
        preview = "; ".join(
            f"{issue.node or '<unknown>'}:{issue.field or issue.type}:{issue.message}"
            for issue in self.issues[:5]
        )
        extra = "" if len(self.issues) <= 5 else f" (+{len(self.issues) - 5} more)"
        return f"OKF compilation failed with {len(self.issues)} issue(s): {preview}{extra}"


def validate_okf_graph(knowledge_dir: Path) -> tuple[list[CompiledOKFNode], list[OKFValidationIssue]]:
    kb = load_knowledge_base(knowledge_dir)
    issues: list[OKFValidationIssue] = []
    compiled_nodes: list[CompiledOKFNode] = []

    for path, node in sorted(kb._nodes.items()):
        compiled = _compile_node(node=node, knowledge_dir=knowledge_dir, issues=issues)
        if compiled is not None:
            compiled_nodes.append(compiled)

    node_paths = {node.path for node in compiled_nodes}
    for node in compiled_nodes:
        for relation_name in TYPED_EDGE_FIELDS:
            for target in getattr(node.typed_edges, relation_name):
                if target not in node_paths:
                    issues.append(
                        OKFValidationIssue(
                            type="missing_edge_target",
                            node=node.path,
                            field=f"typed_edges.{relation_name}",
                            target=target,
                            message=f"typed edge target '{target}' does not exist",
                            source_file=node.source_file,
                        )
                    )

    issues.extend(_healthcheck_issues(kb, knowledge_dir))
    return compiled_nodes, issues


def compile_okf_release(knowledge_dir: Path, *, output_path: Path | None = None) -> CompiledOKFRelease:
    compiled_nodes, issues = validate_okf_graph(knowledge_dir)
    if issues:
        raise OKFCompileError(sorted(issues, key=lambda issue: (issue.node, issue.field, issue.target, issue.message)))

    release = _build_release(compiled_nodes, knowledge_dir)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_release_json(release), encoding="utf-8")
    return release


def _compile_node(
    *,
    node: KnowledgeNode,
    knowledge_dir: Path,
    issues: list[OKFValidationIssue],
) -> CompiledOKFNode | None:
    advisory = _validate_advisory(node=node, issues=issues)
    payload = {
        "id": node.path,
        "path": node.path,
        "node_type": str(node.metadata.get("type") or "").strip(),
        "title": node.title,
        "group": node.group,
        "traversal": node.traversal,
        "decision_domain": node.decision_domain,
        "description": node.description,
        "status": node.status,
        "tags": node.tags,
        "decision_question": node.decision_question,
        "priority": node.priority,
        "blocking": node.blocking,
        "linked_paths": node.linked_paths,
        "typed_edges": node.typed_edges(),
        "advisory": advisory.model_dump() if advisory is not None else None,
        "source_file": _relative_source_file(node.source_file, knowledge_dir),
    }
    try:
        return CompiledOKFNode.model_validate(payload)
    except ValidationError as exc:
        issues.extend(_validation_issues("invalid_node_schema", node.path, payload["source_file"], exc))
        return None


def _validate_advisory(
    *,
    node: KnowledgeNode,
    issues: list[OKFValidationIssue],
) -> AdvisorySpec | None:
    raw = node.metadata.get("advisory")
    if raw is None:
        return None
    try:
        return AdvisorySpec.model_validate(raw)
    except ValidationError as exc:
        issues.extend(_validation_issues("invalid_advisory_metadata", node.path, node.source_file, exc, prefix="advisory"))
        return None


def _validation_issues(
    issue_type: str,
    node_path: str,
    source_file: str,
    exc: ValidationError,
    *,
    prefix: str = "",
) -> list[OKFValidationIssue]:
    issues: list[OKFValidationIssue] = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", ()))
        field_name = ".".join(part for part in (prefix, loc) if part)
        issues.append(
            OKFValidationIssue(
                type=issue_type,
                node=node_path,
                field=field_name,
                message=error.get("msg", "validation error"),
                source_file=source_file,
            )
        )
    return issues


def _build_release(nodes: Iterable[CompiledOKFNode], knowledge_dir: Path) -> CompiledOKFRelease:
    ordered_nodes = sorted(nodes, key=lambda node: node.path)
    manifest_payload = {
        "schema_version": "okf.release.v1alpha1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "knowledge_dir": str(knowledge_dir),
        "node_count": len(ordered_nodes),
        "advisory_slice_count": sum(1 for node in ordered_nodes if node.advisory and node.advisory.slice),
        "typed_edge_count": sum(
            len(getattr(node.typed_edges, relation_name))
            for node in ordered_nodes
            for relation_name in TYPED_EDGE_FIELDS
        ),
        "graph_sha256": "",
    }
    graph_sha = _graph_sha256(ordered_nodes)
    manifest_payload["graph_sha256"] = graph_sha
    manifest = OKFReleaseManifest.model_validate(manifest_payload)
    return CompiledOKFRelease(manifest=manifest, nodes=ordered_nodes)


def _graph_sha256(nodes: Iterable[CompiledOKFNode]) -> str:
    payload = [
        node.model_dump(mode="json", exclude_none=True)
        for node in sorted(nodes, key=lambda item: item.path)
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _release_json(release: CompiledOKFRelease) -> str:
    return json.dumps(
        release.model_dump(mode="json", exclude_none=True),
        indent=2,
        sort_keys=True,
    ) + "\n"


def _relative_source_file(source_file: str, knowledge_dir: Path) -> str:
    try:
        return str(Path(source_file).resolve().relative_to(knowledge_dir.resolve()))
    except ValueError:
        return source_file


def _healthcheck_issues(kb, knowledge_dir: Path) -> list[OKFValidationIssue]:
    issues: list[OKFValidationIssue] = []
    for issue in run_graph_healthcheck(kb):
        issue_type = str(issue.get("type") or "").strip()
        if not issue_type or issue_type == "missing_edge_target":
            continue

        node_path = str(issue.get("node") or "").strip()
        node = kb.get(node_path)
        source_file = _relative_source_file(node.source_file, knowledge_dir) if node and node.source_file else ""
        target = str(issue.get("target") or "").strip()

        if issue_type == "asymmetric_conflict":
            field = "typed_edges.conflicts_with"
            message = f"conflict target '{target}' does not link back to '{node_path}'"
        elif issue_type == "asymmetric_alternative":
            field = "typed_edges.alternatives"
            message = f"alternative target '{target}' does not link back to '{node_path}'"
        elif issue_type == "cross_domain_alternative":
            field = "typed_edges.alternatives"
            message = (
                f"alternative target '{target}' crosses decision domains "
                f"('{issue.get('node_domain', '')}' vs '{issue.get('target_domain', '')}')"
            )
        elif issue_type == "self_conflict":
            field = "typed_edges.conflicts_with"
            message = "node cannot conflict with itself"
        else:
            field = ""
            message = "graph healthcheck failed"

        issues.append(
            OKFValidationIssue(
                type=issue_type,
                node=node_path,
                field=field,
                target=target,
                message=message,
                source_file=source_file,
            )
        )
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile the runtime OKF markdown graph into a validated JSON artifact.")
    parser.add_argument(
        "--knowledge-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "knowledge",
        help="Path to the markdown knowledge directory.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional output file for the compiled release JSON.",
    )
    args = parser.parse_args(argv)

    release = compile_okf_release(args.knowledge_dir, output_path=args.out)
    print(json.dumps(release.manifest.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
