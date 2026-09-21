import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.models import RunManifestRecord
from career_agent.harness.run_manifest import record_private_interview_feedback_run
from career_agent.workflows.interview_feedback import (
    GroundedAnswerPoint,
    InterviewAnswerFeedback,
    InterviewAnswerFeedbackWorkflow,
    StructuredInterviewAnswerReviewer,
)
from career_agent.workflows.jd_match import JDEvidenceHit, JDRequirement
from career_agent.workflows.mock_interview import (
    InterviewFocus,
    InterviewQuestion,
    MockInterviewPlan,
)


def _plan(*, linked_claim_ids=None) -> MockInterviewPlan:
    evidence = JDEvidenceHit(
        claim_id="studio_01", evidence_id="studio", evidence_title="ConnectOnion Studio",
        claim_text="Built a visual workspace for isolated Agent sessions.",
        review_status="approved", answer_visibility="private", source_visibility="private", strength="strong",
    )
    requirement = JDRequirement(id="agent", text="Agent system experience", category="experience", importance="must")
    return MockInterviewPlan(
        status="ready", thread_id="practice-feedback",
        focus=[InterviewFocus(requirement=requirement, status="strong_match", claim_ids=["studio_01"],
                             evidence=[evidence], note="Approved test fact")],
        questions=[InterviewQuestion(id="q_1", question="Explain the workspace design.",
                                     focus_requirement_id="agent",
                                     linked_claim_ids=linked_claim_ids if linked_claim_ids is not None else ["studio_01"],
                                     purpose="Check evidence-backed explanation.")],
    )


class Reviewer:
    def review(self, *, question, evidence, candidate_answer):
        assert question.id == "q_1"
        assert [item.claim_id for item in evidence] == ["studio_01"]
        assert candidate_answer == "I built isolated workspaces, and then I deployed it to a million users."
        return InterviewAnswerFeedback(
            status="ready", question_id="q_1",
            grounded_points=[GroundedAnswerPoint(text="Explains isolated workspaces.", claim_ids=["studio_01"])],
            points_to_verify=["The claimed million-user deployment is not in approved evidence."],
            coaching_notes=["Keep the workspace explanation; add a reviewed source before claiming scale."],
            follow_up_question="How did the isolation affect an Agent session?",
        )


def test_answer_feedback_separates_grounded_and_unverified_details():
    result = InterviewAnswerFeedbackWorkflow(Reviewer()).run(
        plan=_plan(), question_id="q_1",
        candidate_answer="I built isolated workspaces, and then I deployed it to a million users.", user_id="evan",
    )
    assert result.status == "ready"
    assert result.grounded_points[0].claim_ids == ["studio_01"]
    assert "million-user" in result.points_to_verify[0]
    assert result.tool_calls == [
        "select_question_evidence", "review_interview_answer", "validate_interview_feedback_links",
    ]


def test_answer_feedback_stops_for_gap_question_without_calling_reviewer():
    class NeverReviewer:
        def review(self, **_kwargs):
            raise AssertionError("gap question must not call a model")

    result = InterviewAnswerFeedbackWorkflow(NeverReviewer()).run(
        plan=_plan(linked_claim_ids=[]), question_id="q_1", candidate_answer="Some Linux answer", user_id="evan"
    )
    assert result.status == "needs_human_review"
    assert result.grounded_points == []
    assert result.tool_calls == ["select_question_evidence"]


def test_answer_feedback_rejects_claim_not_linked_to_question():
    class InvalidReviewer(Reviewer):
        def review(self, **kwargs):
            response = super().review(**kwargs)
            return response.model_copy(update={"grounded_points": [
                GroundedAnswerPoint(text="Bad reference", claim_ids=["another_claim"])
            ]})

    with pytest.raises(ValueError, match="not linked"):
        InterviewAnswerFeedbackWorkflow(InvalidReviewer()).run(
            plan=_plan(), question_id="q_1",
            candidate_answer="I built isolated workspaces, and then I deployed it to a million users.", user_id="evan",
        )


def test_feedback_manifest_hashes_answer_and_keeps_only_claim_ids():
    feedback = InterviewAnswerFeedbackWorkflow(Reviewer()).run(
        plan=_plan(), question_id="q_1",
        candidate_answer="I built isolated workspaces, and then I deployed it to a million users.", user_id="evan",
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run_id = record_private_interview_feedback_run(
            session, question_id="q_1", candidate_answer="secret interview answer",
            model_name="test-model", feedback=feedback, latency_ms=5,
        )
        record = session.get(RunManifestRecord, run_id)
    assert record is not None
    assert record.task_type == "interview_answer_feedback"
    assert record.cited_claim_ids == ["studio_01"]
    assert "secret interview answer" not in record.input_hash
    assert "million" not in str(record.tool_trace)


def test_structured_reviewer_accepts_the_prompt_schema_without_runtime_status():
    class PromptSchemaProvider:
        def complete_json(self, *, system, user):
            assert "points_to_verify" in system
            assert "studio_01" in user
            return {
                "question_id": "q_1",
                "grounded_points": [{"text": "Explains isolation.", "claim_ids": ["studio_01"]}],
                "points_to_verify": ["The deployment scale needs a source."],
                "coaching_notes": ["Explain the workspace design first."],
                "follow_up_question": None,
            }

    result = InterviewAnswerFeedbackWorkflow(StructuredInterviewAnswerReviewer(PromptSchemaProvider())).run(
        plan=_plan(), question_id="q_1", candidate_answer="I built isolated workspaces.", user_id="evan",
    )
    assert result.status == "ready"
    assert result.run_id is None
    assert result.grounded_points[0].claim_ids == ["studio_01"]
    assert result.points_to_verify == ["The deployment scale needs a source."]
    assert result.tool_calls[-1] == "validate_interview_feedback_links"


def test_structured_reviewer_cannot_supply_runtime_metadata():
    class RuntimeMetadataProvider:
        def complete_json(self, **_kwargs):
            return {"question_id": "q_1", "status": "ready", "run_id": "fake_run"}

    plan = _plan()
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        StructuredInterviewAnswerReviewer(RuntimeMetadataProvider()).review(
            question=plan.questions[0], evidence=plan.focus[0].evidence,
            candidate_answer="An answer.",
        )
