"""Compilation contracts for the imported coding-platform advisory corpus."""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path

from pydantic import Field, model_validator

from .models import FrozenModel, content_hash


class AdvisorySource(FrozenModel):
    title: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    checked_on: date | None = None


class AdvisoryRelationship(FrozenModel):
    label: str = Field(min_length=1)
    target_path: str = Field(min_length=1)


class AdvisoryDocument(FrozenModel):
    advisory_id: str = Field(pattern=r"^advisory:[a-z0-9_-]+$")
    source_path: str = Field(min_length=1)
    source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    document_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    group: str = Field(min_length=1)
    tags: tuple[str, ...] = ()
    timestamp: datetime
    status: str = Field(pattern=r"^(candidate|stable)$")
    body: str
    decisions: tuple[str, ...] = ()
    principles: tuple[str, ...] = ()
    stack_options: tuple[str, ...] = ()
    relationships: tuple[AdvisoryRelationship, ...] = ()
    sources: tuple[AdvisorySource, ...] = ()
    component_id: str | None = Field(
        default=None,
        pattern=r"^component:[a-z0-9_-]+$",
    )


class AdvisoryMigrationFile(FrozenModel):
    source_path: str
    imported_path: str
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: str = Field(pattern=r"^(candidate|stable)$")


class AdvisoryMigrationManifest(FrozenModel):
    schema_version: str = "1.0"
    source_root: str
    imported_root: str
    migrated_on: date
    files: tuple[AdvisoryMigrationFile, ...]
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def hash_matches_content(self) -> "AdvisoryMigrationManifest":
        payload = self.model_dump(mode="json", exclude={"manifest_hash"})
        if self.manifest_hash != content_hash(payload):
            raise ValueError("advisory migration manifest hash does not match content")
        return self


class AdvisoryCorpus(FrozenModel):
    schema_version: str = "1.0"
    authority: str = "advisory"
    compiled_on: date
    migration: AdvisoryMigrationManifest
    documents: tuple[AdvisoryDocument, ...]
    corpus_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def corpus_is_valid(self) -> "AdvisoryCorpus":
        if self.authority != "advisory":
            raise ValueError("imported corpus cannot be decision authority")
        ids = [document.advisory_id for document in self.documents]
        paths = [document.source_path for document in self.documents]
        if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
            raise ValueError("advisory document IDs and paths must be unique")
        payload = self.model_dump(mode="json", exclude={"corpus_hash"})
        if self.corpus_hash != content_hash(payload):
            raise ValueError("advisory corpus hash does not match content")
        return self


_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)(?:#[^)]+)?\)")
_SOURCE = re.compile(
    r"^- \[([^\]]+)\]\((https?://[^)]+)\)",
    re.IGNORECASE,
)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("advisory document is missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("advisory document frontmatter is unterminated")
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, text[end + 5 :].strip()


def _section(body: str, title: str) -> str:
    match = re.search(
        rf"^## {re.escape(title)}\s*$\n(.*?)(?=^## |\Z)",
        body,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _bullets(section: str) -> tuple[str, ...]:
    return tuple(
        line[2:].strip()
        for line in section.splitlines()
        if line.startswith("- ") and line[2:].strip()
    )


def _advisory_id(path: Path) -> str:
    return "advisory:" + "-".join(path.with_suffix("").parts)


def _tags(raw: str) -> tuple[str, ...]:
    if not raw.startswith("[") or not raw.endswith("]"):
        return ()
    return tuple(
        item.strip()
        for item in raw[1:-1].split(",")
        if item.strip()
    )


def compile_advisory_corpus(
    root: Path,
    *,
    source_root: str,
    component_mappings: dict[str, str],
    compiled_on: date,
) -> AdvisoryCorpus:
    """Compile Markdown into a deterministic, explicitly non-authoritative artifact."""

    documents: list[AdvisoryDocument] = []
    migration_files: list[AdvisoryMigrationFile] = []
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        raw = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(raw)
        status = metadata.get("status", "candidate")
        source_hash = f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"
        migration_files.append(AdvisoryMigrationFile(
            source_path=f"{source_root.rstrip('/')}/{relative.as_posix()}",
            imported_path=relative.as_posix(),
            content_hash=source_hash,
            status=status,
        ))
        connects = _section(body, "Connects to")
        sources = _section(body, "Sources")
        relationships = tuple(
            AdvisoryRelationship(
                label=label,
                target_path=(root / relative.parent / target).resolve().relative_to(
                    root.resolve()
                ).as_posix(),
            )
            for label, target in _LINK.findall(connects)
            if not target.startswith(("http://", "https://"))
            and (root / relative.parent / target).resolve().is_relative_to(
                root.resolve()
            )
        )
        source_rows = []
        for line in sources.splitlines():
            match = _SOURCE.match(line.strip())
            if match:
                checked_match = re.search(
                    r"checked\s+(\d{4}-\d{2}-\d{2})",
                    line,
                    flags=re.IGNORECASE,
                )
                source_rows.append(AdvisorySource(
                    title=match.group(1),
                    uri=match.group(2),
                    checked_on=(
                        date.fromisoformat(checked_match.group(1))
                        if checked_match
                        else None
                    ),
                ))
        documents.append(AdvisoryDocument(
            advisory_id=_advisory_id(relative),
            source_path=relative.as_posix(),
            source_hash=source_hash,
            document_type=metadata["type"],
            title=metadata["title"],
            description=metadata.get("description", ""),
            group=metadata["group"],
            tags=_tags(metadata.get("tags", "")),
            timestamp=datetime.fromisoformat(
                metadata["timestamp"].replace("Z", "+00:00")
            ),
            status=status,
            body=body,
            decisions=_bullets(_section(body, "Decisions")),
            principles=_bullets(_section(body, "Principles")),
            stack_options=_bullets(_section(body, "Stack Options")),
            relationships=relationships,
            sources=tuple(source_rows),
            component_id=component_mappings.get(relative.as_posix()),
        ))

    migration_payload = {
        "schema_version": "1.0",
        "source_root": source_root,
        "imported_root": "knowledge/advisory/coding-agent-platform",
        "migrated_on": compiled_on.isoformat(),
        "files": [item.model_dump(mode="json") for item in migration_files],
    }
    migration = AdvisoryMigrationManifest(
        **migration_payload,
        manifest_hash=content_hash(migration_payload),
    )
    corpus_payload = {
        "schema_version": "1.0",
        "authority": "advisory",
        "compiled_on": compiled_on.isoformat(),
        "migration": migration.model_dump(mode="json"),
        "documents": [item.model_dump(mode="json") for item in documents],
    }
    return AdvisoryCorpus(
        **corpus_payload,
        corpus_hash=content_hash(corpus_payload),
    )
