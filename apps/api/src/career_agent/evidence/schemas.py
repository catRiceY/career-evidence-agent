from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class SourceVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    RESTRICTED = "restricted"


class AnswerVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    EXCLUDE = "exclude"


class PersonalContributionStatus(StrEnum):
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFIRMED = "confirmed"
    NOT_APPLICABLE = "not_applicable"
    TEAM_ONLY = "team_only"


class EvidenceStrength(StrEnum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class PublicationStatus(StrEnum):
    UNKNOWN = "unknown"
    DRAFT = "draft"
    MANUSCRIPT = "manuscript"
    UNDER_SUBMISSION = "under_submission"
    IN_REVIEW = "in_review"
    PREPRINT = "preprint"
    ACCEPTED = "accepted"
    PUBLISHED = "published"


class TargetTrack(StrEnum):
    AGENT_RAG_AI_APP = "agent_rag_ai_app"
    VISION_AI_SAFETY = "vision_ai_safety"
    ML_ALGORITHM_RESEARCH = "ml_algorithm_research"
    BACKEND_FULLSTACK = "backend_fullstack"
    DEVOPS_AUTOMATION = "devops_automation"


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EXCLUDE = "exclude"


class SourceType(StrEnum):
    GITHUB_README = "github_readme"
    GITHUB_README_PRIVATE = "github_readme_private"
    GITHUB_API = "github_api"
    GITHUB_REPO_METADATA = "github_repo_metadata"
    GITHUB_REPO_PUBLIC = "github_repo_public"
    PUBLIC_SITE = "public_site"
    LOCAL_PDF = "local_pdf"
    REPORT = "report"
    SCREENSHOT = "screenshot"
    DEMO_VIDEO = "demo_video"
    COMMIT = "commit"
    PUBLICATION_PREPRINT = "publication_preprint"
    MANUAL_NOTE = "manual_note"


class AllowedQuoteScope(StrEnum):
    NONE = "none"
    SHORT_SUMMARY = "short_summary"
    PARAGRAPH = "paragraph"
    FULL_PUBLIC = "full_public"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Source(StrictModel):
    id: str
    evidence_id: str
    type: SourceType
    title: str
    url_or_path: str
    source_visibility: SourceVisibility
    allowed_quote_scope: AllowedQuoteScope = AllowedQuoteScope.NONE
    locator: str | None = None
    version_ref: str | None = None
    captured_at: date | None = None
    notes: str = ""


class ClaimLocator(StrictModel):
    source_id: str
    locator: str


class Claim(StrictModel):
    id: str
    evidence_id: str
    text: str
    claim_type: Literal[
        "project_feature",
        "personal_contribution",
        "technical_stack",
        "result_metric",
        "research_summary",
        "limitation",
        "policy_boundary",
    ]
    review_status: ReviewStatus = ReviewStatus.DRAFT
    answer_visibility: AnswerVisibility = AnswerVisibility.PRIVATE
    personal_contribution_status: PersonalContributionStatus = (
        PersonalContributionStatus.NEEDS_CONFIRMATION
    )
    evidence_strength: EvidenceStrength = EvidenceStrength.WEAK
    source_ids: list[str] = Field(default_factory=list)
    locators: list[ClaimLocator] = Field(default_factory=list)
    hr_value: str = ""
    risk_or_limit: str = ""
    target_tracks: list[TargetTrack] = Field(default_factory=list)
    created_from: Literal["manual", "github", "pdf", "eval_failure"] = "manual"
    updated_at: date | None = None

    @model_validator(mode="after")
    def public_claims_must_be_approved(self) -> Claim:
        if (
            self.answer_visibility == AnswerVisibility.PUBLIC
            and self.review_status != ReviewStatus.APPROVED
        ):
            raise ValueError("public claims must be approved")
        return self

    @model_validator(mode="after")
    def personal_claims_need_confirmed_contribution(self) -> Claim:
        if (
            self.claim_type == "personal_contribution"
            and self.answer_visibility == AnswerVisibility.PUBLIC
            and self.personal_contribution_status
            != PersonalContributionStatus.CONFIRMED
        ):
            raise ValueError("public personal contribution claims must be confirmed")
        return self


class PaperMetadata(StrictModel):
    authors: list[str] = Field(default_factory=list)
    author_position: str | None = None
    publication_status: PublicationStatus = PublicationStatus.UNKNOWN
    venue_or_target: str | None = None
    status_checked_at: date | None = None
    public_link: str | None = None
    local_file_ref: str | None = None
    abstract_public_approved: bool = False


class EvidenceCard(StrictModel):
    id: str
    version: str = "0.1"
    type: Literal["project", "paper", "system_module", "experience"]
    title: str
    period: str | None = None
    summary: str
    review_status: ReviewStatus = ReviewStatus.DRAFT
    answer_visibility: AnswerVisibility = AnswerVisibility.PRIVATE
    source_visibility_default: SourceVisibility = SourceVisibility.PRIVATE
    personal_contribution_status: PersonalContributionStatus = (
        PersonalContributionStatus.NEEDS_CONFIRMATION
    )
    role: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    target_tracks: list[TargetTrack] = Field(default_factory=list)
    priority_by_track: dict[TargetTrack, Priority] = Field(default_factory=dict)
    status_notes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_evidence_to_add: list[str] = Field(default_factory=list)
    paper: PaperMetadata | None = None
    claims: list[Claim] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    updated_at: date | None = None

    @model_validator(mode="after")
    def paper_cards_need_paper_metadata(self) -> EvidenceCard:
        if self.type == "paper" and self.paper is None:
            raise ValueError("paper evidence cards require paper metadata")
        return self

    @model_validator(mode="after")
    def claim_sources_must_exist(self) -> EvidenceCard:
        source_ids = {source.id for source in self.sources}
        for claim in self.claims:
            missing = set(claim.source_ids) - source_ids
            if missing:
                raise ValueError(
                    f"claim {claim.id} references missing sources: {sorted(missing)}"
                )
        return self

    @model_validator(mode="after")
    def public_claims_need_public_sources(self) -> EvidenceCard:
        source_by_id = {source.id: source for source in self.sources}
        for claim in self.claims:
            if claim.answer_visibility != AnswerVisibility.PUBLIC:
                continue
            private_sources = [
                source_id
                for source_id in claim.source_ids
                if source_by_id[source_id].source_visibility != SourceVisibility.PUBLIC
            ]
            if private_sources:
                raise ValueError(
                    f"public claim {claim.id} references non-public sources: "
                    f"{sorted(private_sources)}"
                )
        return self


class EvalCategory(StrEnum):
    PUBLIC_HR_QA = "public_hr_qa"
    PRIVATE_JD_MATRIX = "private_jd_matrix"
    ADVERSARIAL_BOUNDARY = "adversarial_boundary"
    REGRESSION = "regression"


class EvalScope(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class EvalStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class EvalCase(StrictModel):
    id: str
    category: EvalCategory
    question: str
    scope: EvalScope
    expected_behavior: str
    expected_claim_ids: list[str] = Field(default_factory=list)
    expected_source_ids: list[str] = Field(default_factory=list)
    forbidden_claim_ids: list[str] = Field(default_factory=list)
    forbidden_source_ids: list[str] = Field(default_factory=list)
    grading_focus: list[str] = Field(default_factory=list)
    status: EvalStatus = EvalStatus.DRAFT

    @field_validator("question", "expected_behavior")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class Chunk(StrictModel):
    id: str
    source_id: str
    claim_ids: list[str] = Field(default_factory=list)
    text: str
    chunk_strategy: str
    token_count: int = Field(ge=1)
    embedding_model: str
    index_visibility: EvalScope
    created_at: date | None = None


class ToolCall(StrictModel):
    tool_name: str
    args_hash: str
    result_status: Literal["success", "error", "denied"]
    used_claim_ids: list[str] = Field(default_factory=list)
    used_source_ids: list[str] = Field(default_factory=list)


class RunValidation(StrictModel):
    citation_pass: bool
    privacy_pass: bool
    structure_pass: bool


class RunCost(StrictModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)


class RunManifest(StrictModel):
    id: str
    task_type: Literal["public_hr_qa", "jd_match", "mock_interview", "eval_run"]
    scope: EvalScope
    input_hash: str
    model: str
    prompt_version: str
    policy_version: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    output_claim_ids: list[str] = Field(default_factory=list)
    validation: RunValidation
    cost: RunCost
    created_at: date | None = None

    @model_validator(mode="after")
    def public_runs_must_pass_privacy(self) -> RunManifest:
        if self.scope == EvalScope.PUBLIC and not self.validation.privacy_pass:
            raise ValueError("public run manifests must pass privacy validation")
        return self
