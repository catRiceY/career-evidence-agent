import pytest

from career_agent.workflows.evidence_critic import CriticFinding, EvidenceReviewWorkflow
from career_agent.workflows.jd_match import JDEvidenceHit, JDMatchResult, JDMatchRow, JDRequirement


def _result() -> JDMatchResult:
    requirement = JDRequirement(id="req_1", text="Agent system experience", category="experience", importance="must")
    hit = JDEvidenceHit(claim_id="studio_01", evidence_id="studio", evidence_title="Studio", claim_text="Built isolated workspaces.", review_status="approved", answer_visibility="private", source_visibility="private", strength="strong")
    return JDMatchResult(
        status="completed", thread_id="test", requirements=[requirement],
        rows=[JDMatchRow(requirement=requirement, status="partial_match", claim_ids=["studio_01"], note="Directly scoped evidence.", matched_evidence=[hit])],
        gaps=[], questions_for_user=[], tool_calls=[],
    )


class Analyst:
    def analyse(self, jd_text):
        assert jd_text == "JD"
        return _result()


def test_critic_blocker_requires_human_review():
    class Critic:
        def review(self, _result):
            return [CriticFinding(requirement_id="req_1", severity="blocker", issue="The scope is narrower than the JD.", claim_ids=["studio_01"])]
    result = EvidenceReviewWorkflow(Analyst(), Critic()).run("JD")
    assert result.status == "needs_human_review"
    assert result.tool_calls == ["analyst.analyse_jd", "critic.review_evidence", "validate_critic_links"]


def test_critic_cannot_borrow_claims_from_another_requirement():
    class Critic:
        def review(self, _result):
            return [CriticFinding(requirement_id="req_1", severity="warning", issue="bad", claim_ids=["other_01"])]
    with pytest.raises(ValueError, match="outside"):
        EvidenceReviewWorkflow(Analyst(), Critic()).run("JD")
