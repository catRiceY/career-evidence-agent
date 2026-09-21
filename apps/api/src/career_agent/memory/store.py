from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_agent.db.models import CareerMemoryRecord


MEMORY_KINDS = {"career_preference", "interview_reflection", "jd_note"}


def save_private_memory(session: Session, *, owner_id: str, kind: str, content: str) -> CareerMemoryRecord:
    if kind not in MEMORY_KINDS:
        raise ValueError("unsupported memory kind")
    if not content.strip() or len(content) > 2_000:
        raise ValueError("memory content must be between 1 and 2000 characters")
    record = CareerMemoryRecord(id=f"mem_{uuid4().hex}", owner_id=owner_id, kind=kind, content=content.strip())
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_private_memories(session: Session, *, owner_id: str, limit: int = 20) -> list[CareerMemoryRecord]:
    if not 1 <= limit <= 50:
        raise ValueError("memory limit must be between 1 and 50")
    return list(session.scalars(
        select(CareerMemoryRecord).where(CareerMemoryRecord.owner_id == owner_id).order_by(CareerMemoryRecord.updated_at.desc()).limit(limit)
    ))
