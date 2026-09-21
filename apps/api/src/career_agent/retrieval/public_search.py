"""A deterministic, explainable public-evidence retrieval baseline.

This is deliberately *not* vector RAG yet. It gives the project a safe,
testable retrieval contract before embeddings and a vector index are added:
only claims that can be shown on the public surface may enter the candidate
set, and each result keeps its evidence sources attached.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from career_agent.db.models import ClaimRecord, ClaimSourceRecord, EvidenceCardRecord


_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#-]*", flags=re.IGNORECASE)
_HAN_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass(frozen=True)
class PublicSearchSource:
    id: str
    title: str
    url_or_path: str
    locator: str | None
    version_ref: str | None


@dataclass(frozen=True)
class PublicSearchResult:
    claim_id: str
    evidence_id: str
    evidence_title: str
    claim_text: str
    score: float
    sources: list[PublicSearchSource]


def _normalise(text: str) -> str:
    return " ".join(text.casefold().split())


def _query_terms(query: str) -> set[str]:
    """Return English/technical terms plus CJK characters for a small baseline.

    CJK word segmentation is intentionally deferred to the embedding/retrieval
    phase. Character overlap keeps this baseline useful for Chinese queries
    without adding a tokenizer dependency or hiding matching behaviour.
    """

    folded = query.casefold()
    return set(_WORD_RE.findall(folded)) | set(_HAN_RE.findall(folded))


def _is_public_claim(claim: ClaimRecord) -> bool:
    return (
        claim.review_status == "approved"
        and claim.answer_visibility == "public"
        and bool(claim.source_links)
        and all(link.source.source_visibility == "public" for link in claim.source_links)
    )


def _score(query: str, terms: set[str], fields: list[tuple[str, float]]) -> float:
    """Score a claim using transparent field-weighted lexical matching."""

    normalised_query = _normalise(query)
    score = 0.0
    for value, weight in fields:
        folded = _normalise(value)
        if normalised_query and normalised_query in folded:
            score += weight * 4
        score += weight * sum(term in folded for term in terms)
    return score


def _load_public_records(session: Session) -> list[EvidenceCardRecord]:
    """Load the small, reviewed public corpus with its citation graph."""

    return session.scalars(
        select(EvidenceCardRecord)
        .where(
            EvidenceCardRecord.review_status == "approved",
            EvidenceCardRecord.answer_visibility == "public",
        )
        .options(
            selectinload(EvidenceCardRecord.claims)
            .selectinload(ClaimRecord.source_links)
            .selectinload(ClaimSourceRecord.source)
        )
    ).unique().all()


def _result_from_claim(
    record: EvidenceCardRecord, claim: ClaimRecord, *, score: float
) -> PublicSearchResult:
    return PublicSearchResult(
        claim_id=claim.id,
        evidence_id=record.id,
        evidence_title=record.title,
        claim_text=claim.text,
        score=score,
        sources=[
            PublicSearchSource(
                id=link.source.id,
                title=link.source.title,
                url_or_path=link.source.url_or_path,
                locator=link.locator or link.source.locator,
                version_ref=link.source.version_ref,
            )
            for link in claim.source_links
        ],
    )


def public_results_by_claim_id(
    session: Session, claim_ids: list[str]
) -> dict[str, PublicSearchResult]:
    """Resolve public claim IDs into cited presentation records.

    Vector search returns derived chunk IDs/claim IDs rather than presentation
    data.  This second, policy-gated lookup keeps citations from the evidence
    registry authoritative even when a vector result did not appear in lexical
    candidate retrieval.
    """

    requested = set(claim_ids)
    if not requested:
        return {}
    results: dict[str, PublicSearchResult] = {}
    for record in _load_public_records(session):
        for claim in record.claims:
            if claim.id in requested and _is_public_claim(claim):
                results[claim.id] = _result_from_claim(record, claim, score=0.0)
    return results


def search_public_evidence(
    session: Session, query: str, *, limit: int = 10
) -> list[PublicSearchResult]:
    """Rank approved public claims while preserving their source citations."""

    terms = _query_terms(query)
    if not terms:
        return []

    records = _load_public_records(session)

    results: list[PublicSearchResult] = []
    for record in records:
        for claim in record.claims:
            if not _is_public_claim(claim):
                continue
            score = _score(
                query,
                terms,
                [
                    (claim.text, 5.0),
                    (record.title, 4.0),
                    (" ".join(record.tech_stack), 3.0),
                    (record.summary, 2.0),
                    (claim.hr_value, 1.0),
                ],
            )
            if score <= 0:
                continue
            results.append(_result_from_claim(record, claim, score=score))

    return sorted(results, key=lambda result: (-result.score, result.claim_id))[:limit]
