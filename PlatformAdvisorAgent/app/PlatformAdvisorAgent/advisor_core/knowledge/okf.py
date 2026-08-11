"""Strict loading for OKF-compatible Markdown knowledge documents."""
from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import yaml
from pydantic import Field, TypeAdapter, field_validator

from .models import (
    FrozenModel,
    KnowledgeEntity,
    KnowledgeRelationship,
    StableId,
    content_hash,
)


KnowledgeRecord: TypeAlias = KnowledgeEntity | KnowledgeRelationship
_ENTITY_ADAPTER = TypeAdapter(KnowledgeEntity)


class OkfDocument(FrozenModel):
    relative_path: str = Field(min_length=1)
    body: str = Field(min_length=1)
    record: KnowledgeRecord
    document_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class OkfCorpus(FrozenModel):
    documents: tuple[OkfDocument, ...] = Field(min_length=1)

    @field_validator("documents")
    @classmethod
    def unique_records(
        cls,
        documents: tuple[OkfDocument, ...],
    ) -> tuple[OkfDocument, ...]:
        identifiers = [document.record.id for document in documents]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("OKF corpus record IDs must be unique")
        paths = [document.relative_path for document in documents]
        if len(paths) != len(set(paths)):
            raise ValueError("OKF corpus paths must be unique")
        return tuple(
            sorted(documents, key=lambda document: document.relative_path)
        )

    @property
    def entities(self) -> tuple[KnowledgeEntity, ...]:
        return tuple(
            document.record
            for document in self.documents
            if not isinstance(document.record, KnowledgeRelationship)
        )

    @property
    def relationships(self) -> tuple[KnowledgeRelationship, ...]:
        return tuple(
            document.record
            for document in self.documents
            if isinstance(document.record, KnowledgeRelationship)
        )


class OkfLoadError(ValueError):
    pass


def _split_document(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise OkfLoadError(f"{path} must begin with YAML front matter")
    closing = text.find("\n---\n", 4)
    if closing < 0:
        raise OkfLoadError(f"{path} has no closing front-matter delimiter")
    front_matter = text[4:closing]
    body = text[closing + 5 :].strip()
    if not body:
        raise OkfLoadError(f"{path} must include a Markdown body")
    parsed = yaml.safe_load(front_matter)
    if not isinstance(parsed, dict):
        raise OkfLoadError(f"{path} front matter must be an object")
    return parsed, body


def load_okf_document(path: Path, *, root: Path | None = None) -> OkfDocument:
    metadata, body = _split_document(path)
    kind = metadata.get("kind")
    try:
        record: KnowledgeRecord
        if kind == "Relationship":
            record = KnowledgeRelationship.model_validate(metadata)
        else:
            record = _ENTITY_ADAPTER.validate_python(metadata)
    except ValueError as error:
        raise OkfLoadError(f"invalid knowledge contract in {path}: {error}") from error

    relative_path = str(path.relative_to(root)) if root is not None else path.name
    hash_payload = {
        "relative_path": relative_path,
        "metadata": record.model_dump(mode="json", exclude_none=True),
        "body": body,
    }
    return OkfDocument(
        relative_path=relative_path,
        body=body,
        record=record,
        document_hash=content_hash(hash_payload),
    )


def load_okf_corpus(root: Path) -> OkfCorpus:
    if not root.exists():
        raise OkfLoadError(f"knowledge path does not exist: {root}")
    paths = sorted(root.rglob("*.md")) if root.is_dir() else [root]
    if not paths:
        raise OkfLoadError(f"knowledge path contains no Markdown files: {root}")
    corpus_root = root if root.is_dir() else root.parent
    return OkfCorpus(
        documents=tuple(
            load_okf_document(path, root=corpus_root) for path in paths
        )
    )
