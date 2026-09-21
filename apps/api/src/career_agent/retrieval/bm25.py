"""A deterministic BM25 retriever for reviewed public portfolio evidence."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log
import re

from sqlalchemy.orm import Session

from career_agent.db.models import ClaimRecord, EvidenceCardRecord
from career_agent.retrieval.public_search import (
    PublicSearchResult,
    _is_public_claim,
    _load_public_records,
    _result_from_claim,
)


_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#-]*", flags=re.IGNORECASE)
_HAN_RE = re.compile(r"[\u4e00-\u9fff]+")


def bm25_tokens(text: str) -> list[str]:
    """Keep technical English tokens and transparent Chinese bigrams."""

    folded = text.casefold()
    tokens = _WORD_RE.findall(folded)
    for span in _HAN_RE.findall(folded):
        tokens.extend(span[index:index + 2] for index in range(max(len(span) - 1, 0)))
        if len(span) == 1:
            tokens.append(span)
    return tokens


@dataclass(frozen=True)
class _Document:
    record: EvidenceCardRecord
    claim: ClaimRecord
    tokens: list[str]


def _document_text(record: EvidenceCardRecord, claim: ClaimRecord) -> str:
    return "\n".join((claim.text, record.title, " ".join(record.tech_stack), record.summary, claim.hr_value))


def search_public_bm25_evidence(
    session: Session, query: str, *, limit: int = 10, k1: float = 1.5, b: float = 0.75
) -> list[PublicSearchResult]:
    """Rank approved public Claims with Okapi BM25; policy remains unchanged."""

    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    query_tokens = bm25_tokens(query)
    if not query_tokens:
        return []
    documents = [
        _Document(record, claim, bm25_tokens(_document_text(record, claim)))
        for record in _load_public_records(session)
        for claim in record.claims
        if _is_public_claim(claim)
    ]
    if not documents:
        return []
    frequency_by_document = Counter(token for document in documents for token in set(document.tokens))
    average_length = sum(len(document.tokens) for document in documents) / len(documents)
    results: list[PublicSearchResult] = []
    for document in documents:
        term_frequency = Counter(document.tokens)
        score = 0.0
        for token in set(query_tokens):
            frequency = term_frequency[token]
            if not frequency:
                continue
            inverse_frequency = log(1 + (len(documents) - frequency_by_document[token] + 0.5) / (frequency_by_document[token] + 0.5))
            normaliser = frequency + k1 * (1 - b + b * len(document.tokens) / average_length)
            score += inverse_frequency * frequency * (k1 + 1) / normaliser
        if score > 0:
            results.append(_result_from_claim(document.record, document.claim, score=score))
    return sorted(results, key=lambda item: (-item.score, item.claim_id))[:limit]
