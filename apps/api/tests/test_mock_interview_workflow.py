import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.models import RunManifestRecord
from career_agent.harness.run_manifest import record_private_mock_interview_run
from career_agent.workflows.jd_match import (
    JDEvidenceHit,
    JDMatchWorkflow,
    JDRequirement,
    JDMatchRow,
)
from career_agent.workflows.mock_interview import (
    InterviewFocus,
    InterviewQuestion,
    MockInterviewPlanWorkflow,
)


class JDExtractor:
    def extract(self, _jd_text: str) -> list[JDRequirement]:
        return [
            JDRequirement(
                id="req_rag",
                text="Build a production RAG system",
                category="skill",
                importance="must",
            ),
            JDRequirement(
                id="req_k8s",
                text="Operate Kubernetes at scale",
                category="experience",
                importance="preferred",
            ),
        ]


class EvidenceFinder:
    def search(self, requirement: JDRequirement) -> list[JDEvidenceHit]:
        if requirement.id == "req_rag":
            return [
                JDEvidenceHit(
                    claim_id="studio_01",
                    evidence_id="project_connectonion_studio",
                    evidence_title="ConnectOnion Studio",
                    claim_text="Built an Agent management surface.",
                    review_status="approved",
                    answer_visibility="private",
                    source_visibility="private",
                    strength="strong",
                )
            ]
        return []


class QuestionGenerator:
    def generate(self, focus: list[InterviewFocus]) -> list[InterviewQuestion]:
        assert {item.requirement.id for item in focus} == {"req_rag", "req_k8s"}
        return [
            InterviewQuestion(
                id="q_1",
                question="How did you design the RAG workflow?",
                focus_requirement_id="req_rag",
                linked_claim_ids=["studio_01"],
                purpose="Verify the candidate can explain an evidenced system design.",
            ),
            InterviewQuestion(
                id="q_2",
                question="What reliability trade-offs did you consider?",
                focus_requirement_id="req_rag",
                linked_claim_ids=["studio_01"],
                purpose="Probe engineering judgment without inventing metrics.",
            ),
            InterviewQuestion(
                id="q_3",
                question="What is your current experience gap around Kubernetes?",
                focus_requirement_id="req_k8s",
                linked_claim_ids=[],
                purpose="Practice an honest answer to a known gap.",
            ),
        ]


class Assessor:
    def assess(self, requirements, candidates):
        return [JDMatchRow(requirement=req,
                           status="partial_match" if candidates[req.id] else "gap",
                           claim_ids=[hit.claim_id for hit in candidates[req.id]],
                           matched_evidence=candidates[req.id], note="Test assessment")
                for req in requirements]


def _completed_jd_result():
    return JDMatchWorkflow(extractor=JDExtractor(), evidence_finder=EvidenceFinder(), matrix_assessor=Assessor()).run(
        jd_text="Example JD", user_id="evan", thread_id="jd-source-001"
    )


def test_mock_interview_plan_is_grounded_in_matrix_rows() -> None:
    plan = MockInterviewPlanWorkflow(QuestionGenerator()).run(
        jd_result=_completed_jd_result(), user_id="evan", thread_id="interview-001"
    )

    assert plan.status == "ready"
    assert plan.questions[0].linked_claim_ids == ["studio_01"]
    assert plan.focus[0].evidence[0].claim_text == "Built an Agent management surface."
    assert plan.questions[-1].linked_claim_ids == []
    assert plan.tool_calls == [
        "select_interview_focus",
        "generate_interview_questions",
        "validate_question_evidence_links",
    ]


class NeedsReviewFinder(EvidenceFinder):
    def search(self, requirement: JDRequirement) -> list[JDEvidenceHit]:
        if requirement.id != "req_rag":
            return []
        return [
            JDEvidenceHit(
                claim_id="restricted_01",
                evidence_id="private_paper",
                evidence_title="Unpublished work",
                claim_text="Restricted detail.",
                review_status="in_review",
                answer_visibility="exclude",
                source_visibility="restricted",
                strength="strong",
            )
        ]


def test_mock_interview_stops_if_input_jd_matrix_needs_human_review() -> None:
    jd_result = JDMatchWorkflow(
        extractor=JDExtractor(), evidence_finder=NeedsReviewFinder()
    ).run(jd_text="Example JD", user_id="evan", thread_id="jd-source-002")

    plan = MockInterviewPlanWorkflow(QuestionGenerator()).run(
        jd_result=jd_result, user_id="evan", thread_id="interview-002"
    )

    assert plan.status == "needs_human_review"
    assert plan.questions == []
    assert plan.tool_calls == ["select_interview_focus"]


def test_mock_interview_manifest_omits_questions_but_keeps_evidence_links() -> None:
    plan = MockInterviewPlanWorkflow(QuestionGenerator()).run(
        jd_result=_completed_jd_result(), user_id="evan", thread_id="interview-003"
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run_id = record_private_mock_interview_run(
            session,
            session_label="practice-003",
            model_name="test-model",
            plan=plan,
            latency_ms=9,
        )
        record = session.get(RunManifestRecord, run_id)

    assert record is not None
    assert record.task_type == "mock_interview"
    assert record.retrieved_claim_ids == ["studio_01"]
    assert record.cited_claim_ids == []
    assert "RAG workflow" not in str(record.tool_trace)


def test_interview_invalid_links_retry_once_and_fail_closed():
    class InvalidGenerator(QuestionGenerator):
        calls = 0
        def generate(self, focus):
            self.calls += 1
            questions = super().generate(focus)
            questions[0] = questions[0].model_copy(update={"linked_claim_ids": ["unavailable"]})
            return questions

    generator = InvalidGenerator()
    with pytest.raises(ValueError, match="unselected claim"):
        MockInterviewPlanWorkflow(generator).run(
            jd_result=_completed_jd_result(), user_id="evan", thread_id="invalid-interview"
        )
    assert generator.calls == 2
