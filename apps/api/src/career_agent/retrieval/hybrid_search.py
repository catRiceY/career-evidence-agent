"""Policy-gated hybrid retrieval over lexical claims and pgvector chunks."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from career_agent.retrieval.embeddings import EmbeddingBatch
from career_agent.retrieval.bm25 import search_public_bm25_evidence
from career_agent.retrieval.hybrid import reciprocal_rank_fusion
from career_agent.retrieval.public_search import (
    PublicSearchSource,
    public_results_by_claim_id,
    search_public_evidence,
)
from career_agent.retrieval.vector_store import EmbeddingProvider, search_public_vectors


@dataclass(frozen=True)
class PublicHybridSearchResult:
    claim_id: str
    evidence_id: str
    evidence_title: str
    claim_text: str
    fused_score: float
    lexical_rank: int | None
    vector_rank: int | None
    vector_distance: float | None
    sources: list[PublicSearchSource]


def search_public_hybrid_evidence(
    session: Session,
    query: str,
    *,
    embedding_model: str,
    provider: EmbeddingProvider,
    limit: int = 10,
    candidate_limit: int = 30,
) -> list[PublicHybridSearchResult]:
    """Fuse public lexical and vector candidates without relaxing policy gates.

    The vector table is derived storage, so vector hits are resolved back through
    reviewed claim records before being returned. RRF combines ranks, not lexical
    scores and vector distances, which have incompatible scales.
    """

    if not 1 <= limit <= 30:
        raise ValueError("limit must be between 1 and 30")
    if not limit <= candidate_limit <= 50:
        raise ValueError("candidate_limit must be between limit and 50")

    # BM25 is the sparse leg. The original transparent overlap scorer remains
    # available as a diagnostic baseline, not the hybrid rank list.
    lexical_results = search_public_bm25_evidence(session, query, limit=candidate_limit)
    embedded_query = provider.embed([query])
    if embedded_query.model != embedding_model or len(embedded_query.vectors) != 1:
        raise ValueError("embedding provider returned an unexpected query embedding")
    query_vector = embedded_query.vectors[0]
    if not query_vector:
        raise ValueError("embedding provider returned an empty query embedding")

    vector_hits = search_public_vectors(
        session.connection(),
        embedding_model=embedding_model,
        query_vector=query_vector,
        limit=candidate_limit,
    )
    fused = reciprocal_rank_fusion(
        lexical_claim_ids=[result.claim_id for result in lexical_results],
        vector_claim_ids=[hit.claim_id for hit in vector_hits],
        limit=limit,
    )
    records = public_results_by_claim_id(
        session, [result.claim_id for result in fused]
    )
    distances = {}
    for hit in vector_hits:
        distances.setdefault(hit.claim_id, hit.distance)

    return [
        PublicHybridSearchResult(
            claim_id=result.claim_id,
            evidence_id=record.evidence_id,
            evidence_title=record.evidence_title,
            claim_text=record.claim_text,
            fused_score=result.score,
            lexical_rank=result.lexical_rank,
            vector_rank=result.vector_rank,
            vector_distance=distances.get(result.claim_id),
            sources=record.sources,
        )
        for result in fused
        if (record := records.get(result.claim_id)) is not None
    ]
