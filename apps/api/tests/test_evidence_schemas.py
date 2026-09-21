import pytest
from pydantic import ValidationError

from career_agent.evidence.schemas import (
    AnswerVisibility,
    Claim,
    EvidenceCard,
    ReviewStatus,
    Source,
    SourceType,
    SourceVisibility,
)


def make_source() -> Source:
    return Source(
        id="source_1",
        evidence_id="project_1",
        type=SourceType.GITHUB_README,
        title="README",
        url_or_path="https://example.com/repo",
        source_visibility=SourceVisibility.PUBLIC,
    )


def test_public_claim_must_be_approved() -> None:
    with pytest.raises(ValidationError):
        Claim(
            id="claim_1",
            evidence_id="project_1",
            text="Unapproved public claim.",
            claim_type="project_feature",
            answer_visibility=AnswerVisibility.PUBLIC,
            source_ids=["source_1"],
        )


def test_claim_sources_must_exist_on_card() -> None:
    source = make_source()
    claim = Claim(
        id="claim_1",
        evidence_id="project_1",
        text="Approved public claim.",
        claim_type="project_feature",
        review_status=ReviewStatus.APPROVED,
        answer_visibility=AnswerVisibility.PUBLIC,
        source_ids=["missing_source"],
    )

    with pytest.raises(ValidationError):
        EvidenceCard(
            id="project_1",
            type="project",
            title="Project",
            summary="Summary",
            claims=[claim],
            sources=[source],
        )


def test_valid_card_accepts_existing_source_ids() -> None:
    source = make_source()
    claim = Claim(
        id="claim_1",
        evidence_id="project_1",
        text="Approved public claim.",
        claim_type="project_feature",
        review_status=ReviewStatus.APPROVED,
        answer_visibility=AnswerVisibility.PUBLIC,
        source_ids=["source_1"],
    )

    card = EvidenceCard(
        id="project_1",
        type="project",
        title="Project",
        summary="Summary",
        claims=[claim],
        sources=[source],
    )

    assert card.claims[0].id == "claim_1"


def test_public_claim_cannot_use_private_source() -> None:
    source = make_source().model_copy(
        update={"source_visibility": SourceVisibility.PRIVATE}
    )
    claim = Claim(
        id="claim_1",
        evidence_id="project_1",
        text="Approved public claim.",
        claim_type="project_feature",
        review_status=ReviewStatus.APPROVED,
        answer_visibility=AnswerVisibility.PUBLIC,
        source_ids=["source_1"],
    )

    with pytest.raises(ValidationError):
        EvidenceCard(
            id="project_1",
            type="project",
            title="Project",
            summary="Summary",
            claims=[claim],
            sources=[source],
        )
