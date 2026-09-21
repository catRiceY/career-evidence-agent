from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.models import (
    ClaimRecord,
    ClaimSourceRecord,
    EvidenceCardRecord,
    RunManifestRecord,
    SourceRecord,
)
from career_agent.harness.run_manifest import record_private_jd_match_run
from career_agent.workflows.jd_match import (
    DatabasePrivateEvidenceFinder,
    JDEvidenceHit,
    JDMatchWorkflow,
    JDRequirement,
    StructuredJDRequirementExtractor,
    StructuredJDMatrixAssessor,
    JDMatchRow,
)
import pytest


class StubAssessor:
    def assess(self, requirements, candidates):
        return [JDMatchRow(
            requirement=req, status="strong_match" if candidates[req.id] else "gap",
            claim_ids=[hit.claim_id for hit in candidates[req.id]],
            matched_evidence=candidates[req.id], note="Explicitly assessed test fixture.",
        ) for req in requirements]


class StubExtractor:
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


class StubFinder:
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


class StubChatProvider:
    def complete_json(self, *, system: str, user: str) -> dict[str, object]:
        assert "at most 16" in system
        assert "Do not paraphrase away a conjunct" in system
        assert user == "Need RAG and FastAPI experience"
        return {
            "requirements": [
                {
                    "id": "req_1",
                    "text": "RAG and FastAPI experience",
                    "category": "skill",
                    "importance": "must",
                }
            ]
        }


def test_structured_jd_extractor_validates_model_json() -> None:
    extractor = StructuredJDRequirementExtractor(StubChatProvider())

    result = extractor.extract("Need RAG and FastAPI experience")

    assert result[0].id == "req_1"
    assert result[0].importance == "must"


def test_database_private_finder_returns_only_approved_nonrestricted_evidence() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        card = EvidenceCardRecord(
            id="studio",
            type="project",
            title="ConnectOnion Studio",
            summary="A visual workspace for isolated AI agent sessions.",
            review_status="approved",
            answer_visibility="private",
            tech_stack=["RAG", "FastAPI"],
        )
        safe_source = SourceRecord(
            id="studio_readme",
            evidence_id="studio",
            type="repository",
            title="Studio README",
            url_or_path="https://example.test/studio",
            source_visibility="private",
        )
        safe_claim = ClaimRecord(
            id="studio_rag",
            evidence_id="studio",
            text="Built FastAPI services for an agent workspace and RAG-ready workflows.",
            claim_type="implementation",
            review_status="approved",
            answer_visibility="private",
            evidence_strength="strong",
        )
        restricted_source = SourceRecord(
            id="restricted_source",
            evidence_id="studio",
            type="note",
            title="Restricted note",
            url_or_path="/private/note",
            source_visibility="restricted",
        )
        excluded_claim = ClaimRecord(
            id="restricted_claim",
            evidence_id="studio",
            text="Private FastAPI experiment details.",
            claim_type="implementation",
            review_status="approved",
            answer_visibility="exclude",
            evidence_strength="strong",
        )
        session.add_all(
            [
                card,
                safe_source,
                safe_claim,
                restricted_source,
                excluded_claim,
                ClaimSourceRecord(claim_id="studio_rag", source_id="studio_readme"),
                ClaimSourceRecord(claim_id="restricted_claim", source_id="restricted_source"),
            ]
        )
        session.commit()

        result = DatabasePrivateEvidenceFinder(session).search(
            JDRequirement(
                id="req_1",
                text="RAG FastAPI",
                category="skill",
                importance="must",
            )
        )

    assert [hit.claim_id for hit in result] == ["studio_rag"]
    assert result[0].source_visibility == "private"


def test_jd_match_langgraph_builds_evidence_matrix_and_gap_list() -> None:
    workflow = JDMatchWorkflow(extractor=StubExtractor(), evidence_finder=StubFinder(), matrix_assessor=StubAssessor())

    result = workflow.run(
        jd_text="Example JD", user_id="evan", thread_id="jd-run-001"
    )

    assert result.status == "completed"
    assert result.rows[0].status == "strong_match"
    assert result.rows[0].claim_ids == ["studio_01"]
    assert result.rows[1].status == "gap"
    assert result.gaps == ["Operate Kubernetes at scale"]
    assert result.tool_calls == [
        "extract_jd_requirements",
        "search_private_evidence",
        "build_evidence_matrix",
        "check_visibility",
    ]


class RestrictedFinder(StubFinder):
    def search(self, requirement: JDRequirement) -> list[JDEvidenceHit]:
        if requirement.id != "req_rag":
            return []
        return [
            JDEvidenceHit(
                claim_id="private_paper_01",
                evidence_id="private_paper",
                evidence_title="Unpublished work",
                claim_text="Private experimental finding.",
                review_status="in_review",
                answer_visibility="exclude",
                source_visibility="restricted",
                strength="strong",
            )
        ]


def test_jd_match_stops_for_human_review_when_evidence_boundary_is_unclear() -> None:
    workflow = JDMatchWorkflow(extractor=StubExtractor(), evidence_finder=RestrictedFinder())

    result = workflow.run(
        jd_text="Example JD", user_id="evan", thread_id="jd-run-002"
    )

    assert result.status == "needs_human_review"
    assert result.rows[0].status == "needs_review"
    assert result.rows[0].claim_ids == []
    assert result.questions_for_user


def test_jd_match_manifest_hashes_input_and_keeps_only_used_claim_ids() -> None:
    workflow = JDMatchWorkflow(extractor=StubExtractor(), evidence_finder=StubFinder(), matrix_assessor=StubAssessor())
    result = workflow.run(
        jd_text="Example JD", user_id="evan", thread_id="jd-run-003"
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run_id = record_private_jd_match_run(
            session,
            jd_text="Example JD",
            model_name="test-model",
            result=result,
            latency_ms=12,
        )
        record = session.get(RunManifestRecord, run_id)

    assert record is not None
    assert record.task_type == "jd_match"
    assert record.access_scope == "private"
    assert record.retrieved_claim_ids == ["studio_01"]
    assert record.cited_claim_ids == []
    assert "Example JD" not in record.input_hash
    assert [tool["tool_name"] for tool in record.tool_trace] == result.tool_calls


def test_reliable_retrieval_alone_is_never_a_strong_job_match():
    result = JDMatchWorkflow(StubExtractor(), StubFinder()).run(
        jd_text="Example", user_id="evan", thread_id="no-semantic-assessment"
    )
    assert result.status == "needs_human_review"
    assert result.rows[0].status == "needs_review"
    assert result.rows[0].claim_ids == []


class AssessmentProvider:
    def __init__(self, rows):
        self.rows = rows

    def complete_json(self, *, system, user):
        return {"rows": self.rows}


@pytest.mark.parametrize("rows", [
    [{"requirement_id": "edu", "status": "strong_match", "claim_ids": ["invented"], "note": "bad"}],
    [{"requirement_id": "edu", "status": "strong_match", "claim_ids": [], "note": "bad"}],
    [{"requirement_id": "edu", "status": "gap", "claim_ids": ["studio_01"], "note": "bad"}],
    [],
])
def test_semantic_assessment_rejects_invalid_links_and_coverage(rows):
    requirement = JDRequirement(id="edu", text="2027届硕士", category="experience", importance="must")
    candidates = {"edu": StubFinder().search(StubExtractor().extract("")[0])}
    with pytest.raises(ValueError):
        StructuredJDMatrixAssessor(AssessmentProvider(rows)).assess([requirement], candidates)


def test_semantic_gap_overrides_strong_but_irrelevant_evidence():
    requirement = JDRequirement(id="edu", text="2027届硕士", category="experience", importance="must")
    candidates = {"edu": StubFinder().search(StubExtractor().extract("")[0])}
    rows = StructuredJDMatrixAssessor(AssessmentProvider([
        {"requirement_id": "edu", "status": "gap", "claim_ids": [], "note": "未提供教育信息。"}
    ])).assess([requirement], candidates)
    assert rows[0].status == "gap"
    assert rows[0].matched_evidence == []


def test_restricted_claim_text_never_reaches_semantic_provider():
    class CheckedAssessor:
        def assess(self, requirements, candidates):
            assert all(not hits for hits in candidates.values())
            return [JDMatchRow(requirement=req, status="gap", claim_ids=[], note="No eligible evidence")
                    for req in requirements]

    result = JDMatchWorkflow(StubExtractor(), RestrictedFinder(), CheckedAssessor()).run(
        jd_text="Example", user_id="evan", thread_id="restricted-before-provider"
    )
    assert result.status == "needs_human_review"
    assert result.rows[0].matched_evidence == []


def test_assessment_repairs_once_then_stops_if_still_invalid():
    requirement = JDRequirement(id="edu", text="2027届硕士", category="experience", importance="must")

    class Provider:
        calls = 0
        def complete_json(self, *, system, user):
            self.calls += 1
            if self.calls == 2:
                assert "上次输出未通过" in user
            return {"rows": [{"requirement_id": "edu", "status": "strong_match",
                              "claim_ids": ["invented"], "note": "invalid"}]}

    provider = Provider()
    with pytest.raises(ValueError, match="unavailable"):
        StructuredJDMatrixAssessor(provider).assess([requirement], {"edu": []})
    assert provider.calls == 2


def test_assessment_context_keeps_each_requirements_evidence_together():
    import json

    requirements = StubExtractor().extract("")
    candidates = {req.id: StubFinder().search(req) for req in requirements}

    class Provider:
        def complete_json(self, *, system, user):
            payload = json.loads(user)
            assert "evidence" not in payload
            for row in payload["requirements"]:
                expected = [hit.claim_id for hit in candidates[row["id"]]]
                assert row["candidate_claim_ids"] == expected
                assert [hit["claim_id"] for hit in row["evidence"]] == expected
            return {"rows": [{"requirement_id": req.id, "status": "gap", "claim_ids": [],
                              "note": "结构测试，不代表模型语义评估。"} for req in requirements]}

    assert len(StructuredJDMatrixAssessor(Provider()).assess(requirements, candidates)) == len(requirements)


def test_assessment_rejects_rationale_that_mentions_an_unlinked_claim():
    requirement = JDRequirement(id="edu", text="2027届硕士", category="experience", importance="must")
    unrelated = StubFinder().search(StubExtractor().extract("")[0])[0]
    candidates = {"edu": [], "other_requirement": [unrelated]}
    with pytest.raises(ValueError, match="rationale references"):
        StructuredJDMatrixAssessor(AssessmentProvider([
            {"requirement_id": "edu", "status": "gap", "claim_ids": [],
             "note": "studio_01并不能证明毕业届别。"}
        ])).assess([requirement], candidates)


def test_assessment_rejects_accepted_as_published_when_publication_is_required():
    requirement = JDRequirement(id="paper", text="发表论文", category="experience", importance="preferred")
    accepted = JDEvidenceHit(
        claim_id="SLICE-06", evidence_id="paper_slice", evidence_title="SLICE",
        claim_text="SLICE已被BMVC接收为Oral。", review_status="approved",
        answer_visibility="private", source_visibility="private", strength="strong",
        risk_or_limit="accepted不等同于已正式出版。",
    )
    with pytest.raises(ValueError, match="accepted work as published"):
        StructuredJDMatrixAssessor(AssessmentProvider([
            {"requirement_id": "paper", "status": "partial_match", "claim_ids": ["SLICE-06"],
             "note": "SLICE-06符合顶会发表要求。"}
        ])).assess([requirement], {"paper": [accepted]})


def test_workflow_returns_reviewable_matrix_when_bounded_assessor_still_fails():
    class AlwaysInvalidAssessor:
        def assess(self, *_args):
            raise ValueError("unavailable claim")

    result = JDMatchWorkflow(StubExtractor(), StubFinder(), AlwaysInvalidAssessor()).run(
        jd_text="Example", user_id="evan", thread_id="invalid-matrix-output"
    )
    assert result.status == "needs_human_review"
    assert "build_evidence_matrix_rejected" in result.tool_calls
    assert all(row.status in {"needs_review", "gap"} for row in result.rows)
