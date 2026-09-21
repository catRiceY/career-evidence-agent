"""Deterministic citation gates for model-produced answer drafts.

The validator does not decide whether wording is persuasive. It enforces the
more fundamental invariant: each factual statement must cite claim IDs that
were both permitted by policy and actually retrieved for this request.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from career_agent.evidence.schemas import StrictModel


class AnswerStatement(StrictModel):
    text: str = Field(min_length=1)
    cited_claim_ids: list[str] = Field(default_factory=list)


class AnswerDraft(StrictModel):
    answer: str = Field(min_length=1)
    answerable: bool = True
    statements: list[AnswerStatement] = Field(default_factory=list)

    @model_validator(mode="after")
    def answerable_drafts_need_cited_statements(self) -> "AnswerDraft":
        if self.answerable and not self.statements:
            raise ValueError("answerable drafts need at least one factual statement")
        if not self.answerable and self.statements:
            raise ValueError("insufficient-evidence drafts must not contain factual statements")
        return self


class CitationValidationResult(StrictModel):
    passed: bool
    cited_claim_ids: list[str]
    errors: list[str]


def validate_citations(
    draft: AnswerDraft,
    *,
    allowed_claim_ids: set[str],
    retrieved_claim_ids: set[str],
) -> CitationValidationResult:
    """Check citation completeness and request-local retrieval grounding."""

    errors: list[str] = []
    cited_ids: list[str] = []
    for position, statement in enumerate(draft.statements, start=1):
        if not statement.cited_claim_ids:
            errors.append(f"statement {position} has no claim citation")
            continue
        for claim_id in statement.cited_claim_ids:
            cited_ids.append(claim_id)
            if claim_id not in allowed_claim_ids:
                errors.append(
                    f"statement {position} cites claim '{claim_id}' outside policy scope"
                )
            elif claim_id not in retrieved_claim_ids:
                errors.append(
                    f"statement {position} cites claim '{claim_id}' that was not retrieved"
                )
    return CitationValidationResult(
        passed=not errors,
        cited_claim_ids=list(dict.fromkeys(cited_ids)),
        errors=errors,
    )
