"""Deterministic rank fusion for lexical and vector evidence retrieval."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class HybridRank:
    claim_id: str
    score: float
    lexical_rank: int | None
    vector_rank: int | None


def reciprocal_rank_fusion(
    *,
    lexical_claim_ids: list[str],
    vector_claim_ids: list[str],
    limit: int = 10,
    rank_constant: int = 60,
) -> list[HybridRank]:
    """Fuse two retrieval rankings without comparing incompatible score scales.

    Lexical scores and vector distances have different meanings. Reciprocal Rank
    Fusion (RRF) uses only their rank positions, which keeps the merge stable
    while either retriever is tuned independently.
    """

    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if rank_constant <= 0:
        raise ValueError("rank_constant must be positive")

    lexical_ranks = {
        claim_id: rank
        for rank, claim_id in enumerate(dict.fromkeys(lexical_claim_ids), start=1)
    }
    vector_ranks = {
        claim_id: rank
        for rank, claim_id in enumerate(dict.fromkeys(vector_claim_ids), start=1)
    }
    scores: defaultdict[str, float] = defaultdict(float)
    for ranks in (lexical_ranks, vector_ranks):
        for claim_id, rank in ranks.items():
            scores[claim_id] += 1 / (rank_constant + rank)

    return [
        HybridRank(
            claim_id=claim_id,
            score=score,
            lexical_rank=lexical_ranks.get(claim_id),
            vector_rank=vector_ranks.get(claim_id),
        )
        for claim_id, score in sorted(
            scores.items(),
            key=lambda item: (
                -item[1],
                lexical_ranks.get(item[0], float("inf")),
                vector_ranks.get(item[0], float("inf")),
                item[0],
            ),
        )[:limit]
    ]
