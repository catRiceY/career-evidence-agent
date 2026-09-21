"""Policy-gated business tools shared by the MCP server and unit tests."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from career_agent.api.public_evidence import _serialize_card
from career_agent.db.models import ClaimRecord, ClaimSourceRecord, EvidenceCardRecord
from career_agent.harness.contracts import AccessScope, TaskRequest, TaskType
from career_agent.harness.policy import derive_policy
from career_agent.retrieval.bm25 import search_public_bm25_evidence


SUGGESTED_HR_QUESTIONS = [
    "ConnectOnion Studio 解决了什么问题？",
    "你在 Agent/RAG 工程方面做过哪些可验证的工作？",
    "请介绍一个与你申请岗位最相关的项目，并说明你的个人贡献。",
]


def search_public_evidence_tool(session: Session, query: str, limit: int = 5) -> list[dict]:
    """Return only cited, reviewed public evidence; never a generated answer."""
    policy = derive_policy(TaskRequest(
        task_type=TaskType.PUBLIC_HR_QA, access_scope=AccessScope.PUBLIC, prompt=query,
    ))
    if limit > policy.budget.max_tool_calls + 1:
        raise ValueError("MCP public search limit exceeds its bounded tool policy")
    return [
        {
            "claim_id": result.claim_id,
            "evidence_id": result.evidence_id,
            "evidence_title": result.evidence_title,
            "claim_text": result.claim_text,
            "bm25_score": result.score,
            "sources": [source.__dict__ for source in result.sources],
        }
        for result in search_public_bm25_evidence(session, query, limit=limit)
    ]


def get_public_project_summary_tool(session: Session, evidence_id: str) -> dict | None:
    derive_policy(TaskRequest(
        task_type=TaskType.PUBLIC_HR_QA, access_scope=AccessScope.PUBLIC, prompt=evidence_id,
        requested_evidence_ids=[evidence_id],
    ))
    record = session.scalar(
        select(EvidenceCardRecord).where(
            EvidenceCardRecord.id == evidence_id,
            EvidenceCardRecord.review_status == "approved",
            EvidenceCardRecord.answer_visibility == "public",
        ).options(
            selectinload(EvidenceCardRecord.claims).selectinload(ClaimRecord.source_links).selectinload(ClaimSourceRecord.source)
        )
    )
    if record is None:
        return None
    return _serialize_card(record).model_dump(mode="json")


def list_suggested_hr_questions_tool() -> list[str]:
    return SUGGESTED_HR_QUESTIONS
