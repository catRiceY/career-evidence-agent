from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

from career_agent.db.base import Base


class PgVectorType(UserDefinedType):
    """Metadata-only representation of PostgreSQL's pgvector column type.

    Vector reads and writes deliberately remain in ``retrieval.vector_store``
    as parameterised SQL.  The ORM mapping exists so Alembic's schema audit
    knows this managed table is intentional rather than proposing its removal.
    """

    cache_ok = True

    def get_col_spec(self, **_kw: object) -> str:
        return "vector"


@compiles(PgVectorType, "sqlite")
def _compile_vector_for_sqlite(_type: PgVectorType, _compiler: object, **_kw: object) -> str:
    """Keep lightweight SQLite contract tests usable without pgvector."""

    return "TEXT"


class EvidenceCardRecord(Base):
    __tablename__ = "evidence_cards"
    __table_args__ = (
        CheckConstraint("type IN ('project', 'paper', 'system_module', 'experience')"),
        CheckConstraint("review_status IN ('draft', 'in_review', 'approved', 'rejected')"),
        CheckConstraint("answer_visibility IN ('public', 'private', 'exclude')"),
        CheckConstraint(
            "personal_contribution_status IN "
            "('needs_confirmation', 'confirmed', 'not_applicable', 'team_only')"
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="0.1")
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    period: Mapped[str | None] = mapped_column(String(128))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    answer_visibility: Mapped[str] = mapped_column(
        String(32), nullable=False, default="private"
    )
    source_visibility_default: Mapped[str] = mapped_column(
        String(32), nullable=False, default="private"
    )
    personal_contribution_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="needs_confirmation"
    )
    role: Mapped[str | None] = mapped_column(String(512))
    tech_stack: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    target_tracks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    priority_by_track: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    status_notes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    next_evidence_to_add: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    paper_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    claims: Mapped[list[ClaimRecord]] = relationship(
        back_populates="evidence_card", cascade="all, delete-orphan"
    )
    sources: Mapped[list[SourceRecord]] = relationship(
        back_populates="evidence_card", cascade="all, delete-orphan"
    )


class SourceRecord(Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("source_visibility IN ('public', 'private', 'restricted')"),
        CheckConstraint(
            "allowed_quote_scope IN ('none', 'short_summary', 'paragraph', 'full_public')"
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url_or_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    allowed_quote_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="none"
    )
    locator: Mapped[str | None] = mapped_column(Text)
    version_ref: Mapped[str | None] = mapped_column(String(256))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    evidence_card: Mapped[EvidenceCardRecord] = relationship(back_populates="sources")
    claim_links: Mapped[list[ClaimSourceRecord]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class ClaimRecord(Base):
    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint("review_status IN ('draft', 'in_review', 'approved', 'rejected')"),
        CheckConstraint("answer_visibility IN ('public', 'private', 'exclude')"),
        CheckConstraint(
            "personal_contribution_status IN "
            "('needs_confirmation', 'confirmed', 'not_applicable', 'team_only')"
        ),
        CheckConstraint("evidence_strength IN ('strong', 'medium', 'weak')"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    answer_visibility: Mapped[str] = mapped_column(
        String(32), nullable=False, default="private"
    )
    personal_contribution_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="needs_confirmation"
    )
    evidence_strength: Mapped[str] = mapped_column(
        String(32), nullable=False, default="weak"
    )
    hr_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_or_limit: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_tracks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_from: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    evidence_card: Mapped[EvidenceCardRecord] = relationship(back_populates="claims")
    source_links: Mapped[list[ClaimSourceRecord]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    review_decisions: Mapped[list[ReviewDecisionRecord]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class ClaimSourceRecord(Base):
    __tablename__ = "claim_sources"

    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True
    )
    locator: Mapped[str | None] = mapped_column(Text)

    claim: Mapped[ClaimRecord] = relationship(back_populates="source_links")
    source: Mapped[SourceRecord] = relationship(back_populates="claim_links")


class EvidenceChunkRecord(Base):
    """A rebuildable retrieval unit; never the source of truth for a claim."""

    __tablename__ = "evidence_chunks"
    __table_args__ = (
        CheckConstraint("index_visibility IN ('public', 'private')"),
        CheckConstraint("chunk_strategy IN ('claim_source_v1')"),
    )

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    index_visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_locator: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChunkEmbeddingRecord(Base):
    """One rebuildable pgvector embedding for a derived evidence chunk.

    This table has no business-domain relationship because it is intentionally
    accessed through the scope-gated SQL in ``retrieval.vector_store``.  Its
    model declaration keeps the migration metadata complete and auditable.
    """

    __tablename__ = "chunk_embeddings"
    __table_args__ = (Index("ix_chunk_embeddings_model_hash", "embedding_model", "content_hash"),)

    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    embedding_model: Mapped[str] = mapped_column(String(256), primary_key=True)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[str] = mapped_column(PgVectorType(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReviewDecisionRecord(Base):
    __tablename__ = "review_decisions"
    __table_args__ = (
        CheckConstraint("decision IN ('approved', 'rejected', 'needs_changes')"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_answer_visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    next_review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    next_answer_visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    claim: Mapped[ClaimRecord] = relationship(back_populates="review_decisions")


class RunManifestRecord(Base):
    """Privacy-preserving audit record for one Harness execution."""

    __tablename__ = "run_manifests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    access_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(256), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    retrieved_claim_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    cited_claim_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tool_trace: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    citation_pass: Mapped[bool] = mapped_column(nullable=False)
    privacy_pass: Mapped[bool] = mapped_column(nullable=False)
    structure_pass: Mapped[bool] = mapped_column(nullable=False)
    latency_ms: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CareerMemoryRecord(Base):
    """Owner-scoped durable preparation notes, never public evidence."""

    __tablename__ = "career_memories"
    __table_args__ = (
        CheckConstraint("kind IN ('career_preference', 'interview_reflection', 'jd_note')"),
        CheckConstraint("visibility = 'private'"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="private")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class IngestionDraftRecord(Base):
    """External changes await review; automation cannot publish them itself."""

    __tablename__ = "ingestion_drafts"
    __table_args__ = (CheckConstraint("status IN ('pending_review', 'accepted', 'rejected')"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
