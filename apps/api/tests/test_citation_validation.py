from career_agent.harness.citations import AnswerDraft, validate_citations


def test_citation_validator_accepts_retrieved_policy_allowed_claims() -> None:
    result = validate_citations(
        AnswerDraft(
            answer="Studio supports Agent management with observable runtime state.",
            statements=[
                {
                    "text": "Studio supports Agent management and diagnostics.",
                    "cited_claim_ids": ["studio_01", "studio_04"],
                }
            ],
        ),
        allowed_claim_ids={"studio_01", "studio_04"},
        retrieved_claim_ids={"studio_01", "studio_04"},
    )

    assert result.passed is True
    assert result.errors == []


def test_citation_validator_rejects_missing_out_of_scope_and_unretrieved_claims() -> None:
    result = validate_citations(
        AnswerDraft(
            answer="This draft contains unsupported statements.",
            statements=[
                {"text": "No citation.", "cited_claim_ids": []},
                {"text": "Private evidence.", "cited_claim_ids": ["private_legacy_claim"]},
                {"text": "Allowed but not retrieved.", "cited_claim_ids": ["cora_03"]},
            ],
        ),
        allowed_claim_ids={"studio_01", "cora_03"},
        retrieved_claim_ids={"studio_01"},
    )

    assert result.passed is False
    assert "statement 1 has no claim citation" in result.errors
    assert any("outside policy scope" in error for error in result.errors)
    assert any("was not retrieved" in error for error in result.errors)
