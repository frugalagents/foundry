"""Rebuildable vector-ingestion inputs derived from approved search documents."""
from __future__ import annotations

from datetime import date

from pydantic import Field, model_validator

from .models import FrozenModel, StableId, content_hash
from .search_projection import KnowledgeSearchProjection


class VectorProjectionCompilationError(ValueError):
    pass


class VectorChunkingProfile(FrozenModel):
    id: StableId
    version: str = Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
    )
    max_words: int = Field(ge=32, le=1000)
    overlap_words: int = Field(ge=0, le=250)

    @model_validator(mode="after")
    def overlap_is_smaller_than_chunk(self) -> "VectorChunkingProfile":
        if self.overlap_words >= self.max_words:
            raise ValueError("chunk overlap must be smaller than max words")
        return self


class VectorEmbeddingProfile(FrozenModel):
    """Identity for separately managed embedding materialization."""

    id: StableId
    version: str = Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
    )
    provider: str = Field(min_length=1)
    model_id: str | None = Field(default=None, min_length=1)
    dimensions: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def model_and_dimensions_are_pinned_together(
        self,
    ) -> "VectorEmbeddingProfile":
        if (self.model_id is None) != (self.dimensions is None):
            raise ValueError(
                "embedding model ID and dimensions must be pinned together"
            )
        return self


class VectorChunk(FrozenModel):
    id: StableId
    search_document_id: StableId
    entity_id: StableId
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1)
    word_count: int = Field(ge=1)
    evidence_snapshot_ids: tuple[StableId, ...] = ()
    input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class KnowledgeVectorProjection(FrozenModel):
    schema_version: str = "1.0"
    as_of: date
    source_search_projection_hash: str = Field(
        pattern=r"^sha256:[0-9a-f]{64}$"
    )
    chunking_profile: VectorChunkingProfile
    embedding_profile: VectorEmbeddingProfile
    materialization_state: str = "inputs_only"
    chunks: tuple[VectorChunk, ...]
    projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def projection_hash_matches_content(self) -> "KnowledgeVectorProjection":
        payload = self.model_dump(mode="json", exclude={"projection_hash"})
        if self.projection_hash != content_hash(payload):
            raise ValueError(
                "vector projection hash does not match projection content"
            )
        return self


def _chunk_words(
    text: str,
    profile: VectorChunkingProfile,
) -> tuple[str, ...]:
    words = text.split()
    if not words:
        return ()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + profile.max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - profile.overlap_words
    return tuple(chunks)


def compile_vector_projection(
    *,
    search_projection: KnowledgeSearchProjection,
    chunking_profile: VectorChunkingProfile,
    embedding_profile: VectorEmbeddingProfile,
) -> KnowledgeVectorProjection:
    """Compile vector inputs without treating embeddings as release authority."""

    chunks: list[VectorChunk] = []
    for document in search_projection.documents:
        document_chunks = _chunk_words(document.text, chunking_profile)
        if not document_chunks:
            raise VectorProjectionCompilationError(
                f"search document has no vectorizable text: {document.id}"
            )
        entity_slug = document.entity_id.replace(":", "-")
        for ordinal, text in enumerate(document_chunks):
            chunk_payload = {
                "id": f"vector-chunk:{entity_slug}-{ordinal:04d}",
                "search_document_id": document.id,
                "entity_id": document.entity_id,
                "ordinal": ordinal,
                "text": text,
                "word_count": len(text.split()),
                "evidence_snapshot_ids": list(
                    document.evidence_snapshot_ids
                ),
            }
            chunks.append(
                VectorChunk(
                    **chunk_payload,
                    input_hash=content_hash(chunk_payload),
                )
            )

    payload = {
        "schema_version": "1.0",
        "as_of": search_projection.as_of.isoformat(),
        "source_search_projection_hash": (
            search_projection.projection_hash
        ),
        "chunking_profile": chunking_profile.model_dump(mode="json"),
        "embedding_profile": embedding_profile.model_dump(mode="json"),
        "materialization_state": "inputs_only",
        "chunks": [
            chunk.model_dump(mode="json") for chunk in chunks
        ],
    }
    return KnowledgeVectorProjection(
        **payload,
        projection_hash=content_hash(payload),
    )
