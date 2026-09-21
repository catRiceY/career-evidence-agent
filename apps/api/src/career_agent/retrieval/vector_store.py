"""PostgreSQL pgvector persistence and search for public derived chunks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Connection, text


def vector_literal(vector: list[float]) -> str:
    """Render a checked vector literal for PostgreSQL's `vector` type."""

    if not vector or any(not math.isfinite(value) for value in vector):
        raise ValueError("vector must contain at least one finite value")
    return "[" + ",".join(format(value, ".17g") for value in vector) + "]"


@dataclass(frozen=True)
class ChunkEmbedding:
    chunk_id: str
    embedding_model: str
    vector: list[float]
    content_hash: str


@dataclass(frozen=True)
class VectorSearchHit:
    chunk_id: str
    claim_id: str
    source_id: str
    text: str
    distance: float


@dataclass(frozen=True)
class ChunkPendingEmbedding:
    id: str
    text: str
    content_hash: str


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]): ...


def public_chunks_needing_embeddings(
    connection: Connection, *, embedding_model: str
) -> list[ChunkPendingEmbedding]:
    """Find public chunks with no current vector for this model/content hash."""

    rows = connection.execute(
        text(
            """
            SELECT c.id, c.text, c.content_hash
            FROM evidence_chunks AS c
            LEFT JOIN chunk_embeddings AS ce
              ON ce.chunk_id = c.id AND ce.embedding_model = :embedding_model
            WHERE c.index_visibility = 'public'
              AND (ce.chunk_id IS NULL OR ce.content_hash <> c.content_hash)
            ORDER BY c.id
            """
        ),
        {"embedding_model": embedding_model},
    ).mappings()
    return [
        ChunkPendingEmbedding(
            id=row["id"], text=row["text"], content_hash=row["content_hash"]
        )
        for row in rows
    ]


def refresh_public_embeddings(
    connection: Connection,
    *,
    embedding_model: str,
    provider: EmbeddingProvider,
    batch_size: int = 32,
) -> tuple[int, int]:
    """Embed only changed public chunks and persist them behind the scope gate.

    Returns `(pending, written)`. The caller owns the transaction so a failed
    provider request cannot commit a partial batch accidentally.
    """

    if not 1 <= batch_size <= 256:
        raise ValueError("batch_size must be between 1 and 256")
    pending = public_chunks_needing_embeddings(
        connection, embedding_model=embedding_model
    )
    written = 0
    for start in range(0, len(pending), batch_size):
        group = pending[start : start + batch_size]
        batch = provider.embed([chunk.text for chunk in group])
        if batch.model != embedding_model:
            raise ValueError("embedding provider returned a different model")
        if len(batch.vectors) != len(group):
            raise ValueError("embedding provider returned an unexpected vector count")
        written += upsert_public_chunk_embeddings(
            connection,
            [
                ChunkEmbedding(
                    chunk_id=chunk.id,
                    embedding_model=embedding_model,
                    vector=vector,
                    content_hash=chunk.content_hash,
                )
                for chunk, vector in zip(group, batch.vectors, strict=True)
            ],
        )
    return len(pending), written


def upsert_public_chunk_embeddings(
    connection: Connection, embeddings: list[ChunkEmbedding]
) -> int:
    """Persist embeddings only for current public derived chunks.

    The INSERT is deliberately joined to `evidence_chunks`: caller-supplied
    chunk IDs cannot create vectors for private chunks or stale arbitrary IDs.
    """

    written = 0
    statement = text(
        """
        INSERT INTO chunk_embeddings (
            chunk_id, embedding_model, embedding_dimensions, embedding, content_hash
        )
        SELECT c.id, :embedding_model, :embedding_dimensions,
               CAST(:embedding AS vector), :content_hash
        FROM evidence_chunks AS c
        WHERE c.id = :chunk_id AND c.index_visibility = 'public'
        ON CONFLICT (chunk_id, embedding_model) DO UPDATE SET
            embedding_dimensions = EXCLUDED.embedding_dimensions,
            embedding = EXCLUDED.embedding,
            content_hash = EXCLUDED.content_hash,
            created_at = CURRENT_TIMESTAMP
        """
    )
    for item in embeddings:
        result = connection.execute(
            statement,
            {
                "chunk_id": item.chunk_id,
                "embedding_model": item.embedding_model,
                "embedding_dimensions": len(item.vector),
                "embedding": vector_literal(item.vector),
                "content_hash": item.content_hash,
            },
        )
        written += result.rowcount
    return written


def search_public_vectors(
    connection: Connection,
    *,
    embedding_model: str,
    query_vector: list[float],
    limit: int = 10,
) -> list[VectorSearchHit]:
    """Exact cosine search over public chunks for one embedding-model version."""

    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    rows = connection.execute(
        text(
            """
            SELECT c.id AS chunk_id, c.claim_id, c.source_id, c.text,
                   ce.embedding <=> CAST(:query_embedding AS vector) AS distance
            FROM chunk_embeddings AS ce
            JOIN evidence_chunks AS c ON c.id = ce.chunk_id
            WHERE ce.embedding_model = :embedding_model
              AND ce.embedding_dimensions = :embedding_dimensions
              AND c.index_visibility = 'public'
            ORDER BY ce.embedding <=> CAST(:query_embedding AS vector), c.id
            LIMIT :limit
            """
        ),
        {
            "embedding_model": embedding_model,
            "embedding_dimensions": len(query_vector),
            "query_embedding": vector_literal(query_vector),
            "limit": limit,
        },
    ).mappings()
    return [
        VectorSearchHit(
            chunk_id=row["chunk_id"],
            claim_id=row["claim_id"],
            source_id=row["source_id"],
            text=row["text"],
            distance=float(row["distance"]),
        )
        for row in rows
    ]
