from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from career_agent.evidence.schemas import StrictModel


class AccessScope(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class TaskType(StrEnum):
    PUBLIC_HR_QA = "public_hr_qa"
    JD_MATCH = "jd_match"
    MOCK_INTERVIEW = "mock_interview"
    INTERVIEW_ANSWER_FEEDBACK = "interview_answer_feedback"
    EVAL_RUN = "eval_run"


class ToolName(StrEnum):
    SEARCH_PUBLIC_EVIDENCE = "search_public_evidence"
    SEARCH_PRIVATE_EVIDENCE = "search_private_evidence"
    READ_EVIDENCE_CARD = "read_evidence_card"
    VALIDATE_CITATIONS = "validate_citations"
    CHECK_VISIBILITY = "check_visibility"
    EXTRACT_JD_REQUIREMENTS = "extract_jd_requirements"
    BUILD_EVIDENCE_MATRIX = "build_evidence_matrix"
    GENERATE_INTERVIEW_QUESTIONS = "generate_interview_questions"
    REVIEW_INTERVIEW_ANSWER = "review_interview_answer"
    RECORD_HUMAN_CORRECTION = "record_human_correction"


class TaskRequest(StrictModel):
    """A normalized request before it is allowed to enter an agent workflow."""

    task_type: TaskType
    access_scope: AccessScope
    prompt: str = Field(min_length=1)
    user_id: str | None = None
    requested_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def public_requests_are_limited_to_hr_qa(self) -> TaskRequest:
        if (
            self.access_scope == AccessScope.PUBLIC
            and self.task_type != TaskType.PUBLIC_HR_QA
        ):
            raise ValueError("public scope only permits public_hr_qa")
        return self

    @model_validator(mode="after")
    def private_requests_need_an_identity(self) -> TaskRequest:
        if self.access_scope == AccessScope.PRIVATE and not self.user_id:
            raise ValueError("private scope requires an authenticated user_id")
        return self


class EvidenceFilter(StrictModel):
    """Mandatory filter passed to every evidence retrieval tool."""

    access_scope: AccessScope
    required_review_status: str
    required_answer_visibility: str
    allowed_source_visibilities: list[str]


class Budget(StrictModel):
    max_tool_calls: int = Field(default=4, ge=1, le=20)
    max_replans: int = Field(default=1, ge=0, le=5)
    max_output_tokens: int = Field(default=800, ge=100, le=4000)


class PolicyDecision(StrictModel):
    access_scope: AccessScope
    allowed_tools: list[ToolName]
    evidence_filter: EvidenceFilter
    budget: Budget
    require_citation_validation: bool = True
    require_visibility_validation: bool = True
    allow_human_correction: bool = False
