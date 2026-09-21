import pytest
from pydantic import ValidationError

from career_agent.harness.contracts import (
    AccessScope,
    TaskRequest,
    TaskType,
    ToolName,
)
from career_agent.harness.policy import derive_policy


def test_public_policy_only_exposes_public_evidence_tools() -> None:
    decision = derive_policy(
        TaskRequest(
            task_type=TaskType.PUBLIC_HR_QA,
            access_scope=AccessScope.PUBLIC,
            prompt="What projects best demonstrate this candidate's engineering work?",
        )
    )

    assert ToolName.SEARCH_PUBLIC_EVIDENCE in decision.allowed_tools
    assert ToolName.SEARCH_PRIVATE_EVIDENCE not in decision.allowed_tools
    assert decision.evidence_filter.required_review_status == "approved"
    assert decision.evidence_filter.allowed_source_visibilities == ["public"]


def test_public_scope_cannot_request_private_workflow() -> None:
    with pytest.raises(ValidationError):
        TaskRequest(
            task_type=TaskType.JD_MATCH,
            access_scope=AccessScope.PUBLIC,
            prompt="Match this candidate to a JD.",
        )


def test_private_scope_requires_authenticated_identity() -> None:
    with pytest.raises(ValidationError):
        TaskRequest(
            task_type=TaskType.JD_MATCH,
            access_scope=AccessScope.PRIVATE,
            prompt="Match this candidate to a JD.",
        )
