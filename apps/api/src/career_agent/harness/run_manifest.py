"""Persistence for compact, privacy-preserving Harness audit records."""

from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm import Session

from career_agent.db.models import RunManifestRecord
from career_agent.harness.public_answer import PublicAnswerResponse

if TYPE_CHECKING:
    from career_agent.workflows.jd_match import JDMatchResult
    from career_agent.workflows.mock_interview import MockInterviewPlan
    from career_agent.workflows.interview_feedback import InterviewAnswerFeedback


PROMPT_VERSION = "public_answer_v1"
POLICY_VERSION = "public_policy_v1"


def record_public_answer_run(
    session: Session,
    *,
    prompt: str,
    model_name: str,
    response: PublicAnswerResponse,
    latency_ms: int,
) -> str:
    """Store audit metadata, never the original question or model answer."""

    run_id = f"run_{uuid4().hex}"
    retrieved_claim_ids = response.retrieved_claim_ids
    retrieval_status = "success" if retrieved_claim_ids else "empty"
    session.add(
        RunManifestRecord(
            id=run_id,
            task_type="public_hr_qa",
            access_scope="public",
            input_hash=sha256(prompt.encode("utf-8")).hexdigest(),
            model=model_name,
            prompt_version=PROMPT_VERSION,
            policy_version=POLICY_VERSION,
            status=response.status,
            retrieved_claim_ids=retrieved_claim_ids,
            cited_claim_ids=response.cited_claim_ids,
            tool_trace=[
                {
                    "tool_name": "search_public_hybrid_evidence",
                    "result_status": retrieval_status,
                    "used_claim_ids": retrieved_claim_ids,
                    "used_source_ids": [
                        source.id
                        for citation in response.citations
                        for source in citation.sources
                    ],
                },
                {
                    "tool_name": "validate_citations",
                    "result_status": "success"
                    if response.status == "grounded"
                    else "denied",
                    "used_claim_ids": response.cited_claim_ids,
                    "used_source_ids": [],
                },
            ],
            citation_pass=response.status != "rejected_by_citation_gate",
            privacy_pass=True,
            structure_pass=True,
            latency_ms=latency_ms,
        )
    )
    session.commit()
    return run_id


def record_private_jd_match_run(
    session: Session,
    *,
    jd_text: str,
    model_name: str,
    result: "JDMatchResult",
    latency_ms: int,
) -> str:
    """Record a JD run without persisting its sensitive input or output.

    A JD and the resulting gap analysis are both personal preparation data. The
    manifest therefore keeps only a hash, workflow steps, status, and the
    approved claim IDs that were used. It stores no JD text, generated matrix,
    source path, or private evidence text.
    """

    run_id = f"run_{uuid4().hex}"
    retrieved_claim_ids = sorted(
        {claim_id for row in result.rows for claim_id in row.claim_ids}
    )
    session.add(
        RunManifestRecord(
            id=run_id,
            task_type="jd_match",
            access_scope="private",
            input_hash=sha256(jd_text.encode("utf-8")).hexdigest(),
            model=model_name,
            prompt_version="jd_semantic_matrix_v2",
            policy_version="private_policy_v1",
            status=result.status,
            retrieved_claim_ids=retrieved_claim_ids,
            cited_claim_ids=[],
            tool_trace=[
                {
                    "tool_name": tool_name,
                    "result_status": "denied" if tool_name == "check_visibility" and result.status == "needs_human_review" else "success",
                    "used_claim_ids": retrieved_claim_ids
                    if tool_name == "search_private_evidence"
                    else [],
                    "used_source_ids": [],
                }
                for tool_name in result.tool_calls
            ],
            citation_pass=True,
            privacy_pass=True,
            structure_pass=True,
            latency_ms=latency_ms,
        )
    )
    session.commit()
    return run_id


def record_private_mock_interview_run(
    session: Session,
    *,
    session_label: str,
    model_name: str,
    plan: "MockInterviewPlan",
    latency_ms: int,
) -> str:
    """Persist minimal telemetry for a private interview-plan run.

    The generated questions can reveal a candidate's preparation gaps, so they
    are deliberately excluded from the audit table. Only their evidence links
    and the bounded workflow trace are retained.
    """

    run_id = f"run_{uuid4().hex}"
    linked_claim_ids = sorted(
        {claim_id for question in plan.questions for claim_id in question.linked_claim_ids}
    )
    session.add(
        RunManifestRecord(
            id=run_id,
            task_type="mock_interview",
            access_scope="private",
            input_hash=sha256(session_label.encode("utf-8")).hexdigest(),
            model=model_name,
            prompt_version="mock_interview_plan_v2",
            policy_version="private_policy_v1",
            status=plan.status,
            retrieved_claim_ids=linked_claim_ids,
            cited_claim_ids=[],
            tool_trace=[
                {
                    "tool_name": tool_name,
                    "result_status": "success",
                    "used_claim_ids": linked_claim_ids
                    if tool_name == "generate_interview_questions"
                    else [],
                    "used_source_ids": [],
                }
                for tool_name in plan.tool_calls
            ],
            citation_pass=True,
            privacy_pass=True,
            structure_pass=True,
            latency_ms=latency_ms,
        )
    )
    session.commit()
    return run_id


def record_private_interview_feedback_run(
    session: Session,
    *,
    question_id: str,
    candidate_answer: str,
    model_name: str,
    feedback: "InterviewAnswerFeedback",
    latency_ms: int,
) -> str:
    """Audit an answer-review run without retaining the user's answer or feedback text."""

    run_id = f"run_{uuid4().hex}"
    cited_claim_ids = sorted({
        claim_id for point in feedback.grounded_points for claim_id in point.claim_ids
    })
    session.add(
        RunManifestRecord(
            id=run_id,
            task_type="interview_answer_feedback",
            access_scope="private",
            input_hash=sha256(f"{question_id}\n{candidate_answer}".encode("utf-8")).hexdigest(),
            model=model_name,
            prompt_version="interview_answer_feedback_v1",
            policy_version="private_policy_v1",
            status=feedback.status,
            retrieved_claim_ids=cited_claim_ids,
            cited_claim_ids=cited_claim_ids,
            tool_trace=[
                {
                    "tool_name": tool_name,
                    "result_status": "success",
                    "used_claim_ids": cited_claim_ids if tool_name == "review_interview_answer" else [],
                    "used_source_ids": [],
                }
                for tool_name in feedback.tool_calls
            ],
            citation_pass=True,
            privacy_pass=True,
            structure_pass=True,
            latency_ms=latency_ms,
        )
    )
    session.commit()
    return run_id
