"""Read-only public Evidence Registry views.

This module intentionally does not expose a generic database query API.  It
applies the same approval, answer-visibility, and source-visibility gates that
the public Agent tool will use later.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from career_agent.db.models import ClaimRecord, ClaimSourceRecord, EvidenceCardRecord
from career_agent.evidence.schemas import TargetTrack
from career_agent.harness.public_answer import PublicAnswerGateway, PublicAnswerResponse
from career_agent.retrieval.hybrid_search import (
    PublicHybridSearchResult,
    search_public_hybrid_evidence,
)
from career_agent.retrieval.public_search import search_public_evidence
from career_agent.retrieval.vector_store import EmbeddingProvider


class PublicSourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    url_or_path: str
    locator: str | None
    version_ref: str | None


class PublicClaimResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    claim_type: str
    hr_value: str
    risk_or_limit: str
    target_tracks: list[str]
    sources: list[PublicSourceResponse]


class PublicEvidenceCardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    type: str
    summary: str
    role: str | None
    tech_stack: list[str]
    target_tracks: list[str]
    status_notes: list[str]
    claims: list[PublicClaimResponse]


class PublicSearchResultResponse(BaseModel):
    """A cited result from the lexical retrieval baseline, not a generated answer."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    evidence_id: str
    evidence_title: str
    claim_text: str
    score: float
    sources: list[PublicSourceResponse]


class PublicHybridSearchResultResponse(BaseModel):
    """A public, source-cited hybrid retrieval result, not a generated answer."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    evidence_id: str
    evidence_title: str
    claim_text: str
    fused_score: float
    lexical_rank: int | None
    vector_rank: int | None
    vector_distance: float | None
    sources: list[PublicSourceResponse]


class PublicAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2_000)


def _approved_public_claim(claim: ClaimRecord) -> bool:
    if claim.review_status != "approved" or claim.answer_visibility != "public":
        return False
    return bool(claim.source_links) and all(
        link.source.source_visibility == "public" for link in claim.source_links
    )


def _serialize_card(record: EvidenceCardRecord) -> PublicEvidenceCardResponse:
    claims: list[PublicClaimResponse] = []
    for claim in record.claims:
        if not _approved_public_claim(claim):
            continue
        claims.append(
            PublicClaimResponse(
                id=claim.id,
                text=claim.text,
                claim_type=claim.claim_type,
                hr_value=claim.hr_value,
                risk_or_limit=claim.risk_or_limit,
                target_tracks=claim.target_tracks,
                sources=[
                    PublicSourceResponse(
                        id=link.source.id,
                        title=link.source.title,
                        url_or_path=link.source.url_or_path,
                        locator=link.locator or link.source.locator,
                        version_ref=link.source.version_ref,
                    )
                    for link in claim.source_links
                ],
            )
        )
    return PublicEvidenceCardResponse(
        id=record.id,
        title=record.title,
        type=record.type,
        summary=record.summary,
        role=record.role,
        tech_stack=record.tech_stack,
        target_tracks=record.target_tracks,
        status_notes=record.status_notes,
        claims=claims,
    )


def build_public_evidence_router(
    session_factory: sessionmaker[Session],
    *,
    embedding_provider: EmbeddingProvider | None = None,
    embedding_model: str | None = None,
    answer_gateway: PublicAnswerGateway | None = None,
) -> APIRouter:
    if (embedding_provider is None) != (embedding_model is None):
        raise ValueError("embedding_provider and embedding_model must be configured together")
    router = APIRouter(prefix="/v1/public/evidence", tags=["public-evidence"])

    def get_session():
        with session_factory() as session:
            yield session

    def base_query():
        return (
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
            .order_by(EvidenceCardRecord.id)
        )

    @router.get("", response_model=list[PublicEvidenceCardResponse])
    def list_public_evidence(
        track: TargetTrack | None = None,
        limit: int = Query(default=20, ge=1, le=50),
        session: Session = Depends(get_session),
    ) -> list[PublicEvidenceCardResponse]:
        records = session.scalars(base_query()).unique().all()
        if track is not None:
            records = [record for record in records if track.value in record.target_tracks]
        return [_serialize_card(record) for record in records[:limit]]

    @router.get("/search", response_model=list[PublicSearchResultResponse])
    def search_public_evidence_endpoint(
        q: str = Query(min_length=1, max_length=500),
        limit: int = Query(default=10, ge=1, le=30),
        session: Session = Depends(get_session),
    ) -> list[PublicSearchResultResponse]:
        return [
            PublicSearchResultResponse(
                claim_id=result.claim_id,
                evidence_id=result.evidence_id,
                evidence_title=result.evidence_title,
                claim_text=result.claim_text,
                score=result.score,
                sources=[
                    PublicSourceResponse(
                        id=source.id,
                        title=source.title,
                        url_or_path=source.url_or_path,
                        locator=source.locator,
                        version_ref=source.version_ref,
                    )
                    for source in result.sources
                ],
            )
            for result in search_public_evidence(session, q, limit=limit)
        ]

    @router.get("/search/hybrid", response_model=list[PublicHybridSearchResultResponse])
    def search_public_hybrid_evidence_endpoint(
        q: str = Query(min_length=1, max_length=500),
        limit: int = Query(default=10, ge=1, le=30),
        session: Session = Depends(get_session),
    ) -> list[PublicHybridSearchResultResponse]:
        if embedding_provider is None or embedding_model is None:
            raise HTTPException(
                status_code=503,
                detail="hybrid retrieval is not configured",
            )
        results = search_public_hybrid_evidence(
            session,
            q,
            provider=embedding_provider,
            embedding_model=embedding_model,
            limit=limit,
        )
        return [_serialize_hybrid_result(result) for result in results]

    @router.post("/answer", response_model=PublicAnswerResponse)
    def answer_public_hr_question(
        request: PublicAnswerRequest,
        session: Session = Depends(get_session),
    ) -> PublicAnswerResponse:
        if answer_gateway is None:
            raise HTTPException(status_code=503, detail="public answer gateway is not configured")
        return answer_gateway.answer(session, request.question)

    @router.get("/{evidence_id}", response_model=PublicEvidenceCardResponse)
    def get_public_evidence(
        evidence_id: str,
        session: Session = Depends(get_session),
    ) -> PublicEvidenceCardResponse:
        record = session.scalar(base_query().where(EvidenceCardRecord.id == evidence_id))
        if record is None:
            raise HTTPException(status_code=404, detail="public evidence not found")
        return _serialize_card(record)

    return router


def _serialize_hybrid_result(
    result: PublicHybridSearchResult,
) -> PublicHybridSearchResultResponse:
    return PublicHybridSearchResultResponse(
        claim_id=result.claim_id,
        evidence_id=result.evidence_id,
        evidence_title=result.evidence_title,
        claim_text=result.claim_text,
        fused_score=result.fused_score,
        lexical_rank=result.lexical_rank,
        vector_rank=result.vector_rank,
        vector_distance=result.vector_distance,
        sources=[
            PublicSourceResponse(
                id=source.id,
                title=source.title,
                url_or_path=source.url_or_path,
                locator=source.locator,
                version_ref=source.version_ref,
            )
            for source in result.sources
        ],
    )
