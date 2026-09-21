from __future__ import annotations

from career_agent.harness.contracts import (
    AccessScope,
    Budget,
    EvidenceFilter,
    PolicyDecision,
    TaskRequest,
    ToolName,
)


def derive_policy(request: TaskRequest) -> PolicyDecision:
    """Return the only tool and evidence permissions a workflow may receive.

    This is deliberately deterministic. A model can select among allowed tools,
    but cannot relax scope, approval, source visibility, or run budgets.
    """

    if request.access_scope == AccessScope.PUBLIC:
        return PolicyDecision(
            access_scope=AccessScope.PUBLIC,
            allowed_tools=[
                ToolName.SEARCH_PUBLIC_EVIDENCE,
                ToolName.READ_EVIDENCE_CARD,
                ToolName.VALIDATE_CITATIONS,
                ToolName.CHECK_VISIBILITY,
            ],
            evidence_filter=EvidenceFilter(
                access_scope=AccessScope.PUBLIC,
                required_review_status="approved",
                required_answer_visibility="public",
                allowed_source_visibilities=["public"],
            ),
            budget=Budget(max_tool_calls=4, max_replans=1, max_output_tokens=700),
        )

    return PolicyDecision(
        access_scope=AccessScope.PRIVATE,
        allowed_tools=[
            ToolName.SEARCH_PRIVATE_EVIDENCE,
            ToolName.READ_EVIDENCE_CARD,
            ToolName.VALIDATE_CITATIONS,
            ToolName.CHECK_VISIBILITY,
            ToolName.EXTRACT_JD_REQUIREMENTS,
            ToolName.BUILD_EVIDENCE_MATRIX,
            ToolName.GENERATE_INTERVIEW_QUESTIONS,
            ToolName.REVIEW_INTERVIEW_ANSWER,
            ToolName.RECORD_HUMAN_CORRECTION,
        ],
        evidence_filter=EvidenceFilter(
            access_scope=AccessScope.PRIVATE,
            required_review_status="approved",
            required_answer_visibility="private",
            allowed_source_visibilities=["public", "private"],
        ),
        budget=Budget(max_tool_calls=10, max_replans=2, max_output_tokens=1600),
        allow_human_correction=True,
    )
