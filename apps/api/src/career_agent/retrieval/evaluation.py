"""Small deterministic retrieval evaluation for public evidence search."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from career_agent.retrieval.public_search import search_public_evidence
from career_agent.retrieval.bm25 import search_public_bm25_evidence


@dataclass(frozen=True)
class RetrievalEvalCase:
    id: str
    query: str
    expected_claim_ids: list[str]
    k: int


@dataclass(frozen=True)
class RetrievalEvalResult:
    case_id: str
    expected_claim_ids: list[str]
    retrieved_claim_ids: list[str]
    recall_at_k: float


def load_retrieval_eval_cases(path: Path) -> list[RetrievalEvalCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return [
        RetrievalEvalCase(
            id=item["id"],
            query=item["query"],
            expected_claim_ids=item["expected_claim_ids"],
            k=item.get("k", 5),
        )
        for item in raw_cases
    ]


def evaluate_public_retrieval(
    session: Session, cases: list[RetrievalEvalCase]
) -> list[RetrievalEvalResult]:
    return evaluate_retrieval_cases(
        cases,
        retrieve=lambda query, limit: [
            item.claim_id for item in search_public_evidence(session, query, limit=limit)
        ],
    )


def evaluate_public_bm25(
    session: Session, cases: list[RetrievalEvalCase]
) -> list[RetrievalEvalResult]:
    """Use the same reviewed gold set as the overlap baseline and hybrid run."""
    return evaluate_retrieval_cases(
        cases,
        retrieve=lambda query, limit: [
            item.claim_id for item in search_public_bm25_evidence(session, query, limit=limit)
        ],
    )


def evaluate_retrieval_cases(
    cases: list[RetrievalEvalCase],
    *,
    retrieve: Callable[[str, int], list[str]],
) -> list[RetrievalEvalResult]:
    """Measure recall against approved gold claim IDs for any retriever.

    The same reviewed eval set can therefore compare lexical, vector, hybrid,
    or later reranked retrieval without ever binding runtime answers to chunks.
    """

    results: list[RetrievalEvalResult] = []
    for case in cases:
        retrieved_ids = retrieve(case.query, case.k)
        expected_ids = set(case.expected_claim_ids)
        recall = (
            len(expected_ids & set(retrieved_ids)) / len(expected_ids)
            if expected_ids
            else 1.0
        )
        results.append(
            RetrievalEvalResult(
                case_id=case.id,
                expected_claim_ids=case.expected_claim_ids,
                retrieved_claim_ids=retrieved_ids,
                recall_at_k=recall,
            )
        )
    return results
