"""Build rebuildable, source-cited retrieval chunks from reviewed claims."""

from __future__ import annotations

import hashlib

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from career_agent.db.models import (
    ClaimRecord,
    ClaimSourceRecord,
    EvidenceCardRecord,
    EvidenceChunkRecord,
)
from career_agent.retrieval.public_search import _is_public_claim


CHUNK_STRATEGY = "claim_source_v1"


def _chunk_id(claim_id: str, source_id: str) -> str:
    return f"chunk__{claim_id}__{source_id}"


def rebuild_public_claim_chunks(session: Session) -> int:
    """Recreate the public derived index from the reviewed registry.

    The chunk text is the approved claim, not an unreviewed extraction of an
    original document. Each claim/source pair remains independently cited.
    This makes re-indexing deterministic and prevents derived retrieval data
    from silently widening public visibility.
    """

    session.execute(
        delete(EvidenceChunkRecord).where(
            EvidenceChunkRecord.index_visibility == "public",
            EvidenceChunkRecord.chunk_strategy == CHUNK_STRATEGY,
        )
    )
    records = session.scalars(
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

    count = 0
    for record in records:
        for claim in record.claims:
            if not _is_public_claim(claim):
                continue
            for link in claim.source_links:
                content = claim.text
                session.add(
                    EvidenceChunkRecord(
                        id=_chunk_id(claim.id, link.source.id),
                        claim_id=claim.id,
                        source_id=link.source.id,
                        text=content,
                        chunk_strategy=CHUNK_STRATEGY,
                        index_visibility="public",
                        source_locator=link.locator or link.source.locator,
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    )
                )
                count += 1
    session.flush()
    return count
