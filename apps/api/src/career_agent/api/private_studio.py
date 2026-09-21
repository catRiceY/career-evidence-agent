"""Owner-protected local Studio endpoints.

These endpoints are intentionally absent unless an explicit owner token is
configured. They are not a replacement for production OIDC, but they prevent
private JD text and evidence from sharing the public API surface during local
development.
"""

from __future__ import annotations

import secrets
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from career_agent.db.models import IngestionDraftRecord
from career_agent.memory.store import list_private_memories, save_private_memory

from career_agent.generation.chat import StructuredChatProvider
from career_agent.harness.run_manifest import record_private_jd_match_run
from career_agent.workflows.jd_match import (
    DatabasePrivateEvidenceFinder,
    JDMatchResult,
    JDMatchWorkflow,
    StructuredJDMatrixAssessor,
    StructuredJDRequirementExtractor,
)


class PrivateStudioStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    authentication: str


class PrivateJDMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jd_text: str = Field(min_length=1, max_length=20_000)
    session_label: str = Field(min_length=1, max_length=200)


class PrivateMemoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=2_000)


class PrivateMemoryResponse(BaseModel):
    id: str
    kind: str
    content: str
    visibility: str


class IngestionDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_url: str = Field(min_length=1, max_length=2_000)
    title: str = Field(min_length=1, max_length=512)
    source_type: str = Field(min_length=1, max_length=64)
    summary: str = Field(default="", max_length=4_000)


def build_private_studio_router(
    session_factory: sessionmaker[Session],
    *,
    owner_token: str,
    chat_provider: StructuredChatProvider,
    model_name: str,
) -> APIRouter:
    router = APIRouter(prefix="/v1/private/studio", tags=["private-studio"])
    security = HTTPBearer(auto_error=False)

    def require_owner(
        credentials: HTTPAuthorizationCredentials | None = Security(security),
    ) -> None:
        if credentials is None:
            raise HTTPException(status_code=401, detail="owner authentication required")
        if credentials.scheme.lower() != "bearer" or not secrets.compare_digest(credentials.credentials, owner_token):
            raise HTTPException(status_code=403, detail="invalid owner token")

    def get_session():
        with session_factory() as session:
            yield session

    @router.get("/status", response_model=PrivateStudioStatus)
    def private_status(_: None = Depends(require_owner)) -> PrivateStudioStatus:
        return PrivateStudioStatus(status="ready", authentication="owner_bearer_token")

    @router.get("/memories", response_model=list[PrivateMemoryResponse])
    def list_memories(
        _: None = Depends(require_owner), session: Session = Depends(get_session),
    ) -> list[PrivateMemoryResponse]:
        return [PrivateMemoryResponse(id=item.id, kind=item.kind, content=item.content, visibility=item.visibility)
                for item in list_private_memories(session, owner_id="owner")]

    @router.post("/memories", response_model=PrivateMemoryResponse, status_code=201)
    def save_memory(
        request: PrivateMemoryRequest, _: None = Depends(require_owner), session: Session = Depends(get_session),
    ) -> PrivateMemoryResponse:
        try:
            record = save_private_memory(session, owner_id="owner", kind=request.kind, content=request.content)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return PrivateMemoryResponse(id=record.id, kind=record.kind, content=record.content, visibility=record.visibility)

    @router.post("/ingestion-drafts", status_code=201)
    def create_ingestion_draft(
        request: IngestionDraftRequest, _: None = Depends(require_owner), session: Session = Depends(get_session),
    ) -> dict[str, str]:
        """Automation can queue a source, but can never publish it or re-index it."""
        draft = IngestionDraftRecord(
            id=f"draft_{uuid4().hex}", owner_id="owner", source_url=request.source_url,
            title=request.title, source_type=request.source_type, summary=request.summary,
        )
        session.add(draft)
        session.commit()
        return {"id": draft.id, "status": draft.status}

    @router.post("/jd-match", response_model=JDMatchResult)
    def private_jd_match(
        request: PrivateJDMatchRequest,
        _: None = Depends(require_owner),
        session: Session = Depends(get_session),
    ) -> JDMatchResult:
        started = perf_counter()
        workflow = JDMatchWorkflow(
            extractor=StructuredJDRequirementExtractor(chat_provider),
            evidence_finder=DatabasePrivateEvidenceFinder(session),
            matrix_assessor=StructuredJDMatrixAssessor(chat_provider),
        )
        # The authenticated owner is the only actor this local boundary knows.
        # A client body cannot choose another user identity.
        result = workflow.run(
            jd_text=request.jd_text,
            user_id="owner",
            thread_id=f"studio:{request.session_label}:jd",
        )
        run_id = record_private_jd_match_run(
            session,
            jd_text=request.jd_text,
            model_name=model_name,
            result=result,
            latency_ms=round((perf_counter() - started) * 1000),
        )
        return result.model_copy(update={"run_id": run_id})

    return router
