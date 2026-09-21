import pytest

from career_agent.retrieval.hybrid import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_promotes_agreement_between_retrievers() -> None:
    results = reciprocal_rank_fusion(
        lexical_claim_ids=["studio_01", "studio_04", "ios_05"],
        vector_claim_ids=["ios_05", "studio_01", "ripple_02"],
    )

    assert results[0].claim_id == "studio_01"
    assert results[0].lexical_rank == 1
    assert results[0].vector_rank == 2
    assert {item.claim_id for item in results} == {
        "studio_04",
        "studio_01",
        "ios_05",
        "ripple_02",
    }


def test_reciprocal_rank_fusion_deduplicates_and_validates_configuration() -> None:
    results = reciprocal_rank_fusion(
        lexical_claim_ids=["cora_03", "cora_03"],
        vector_claim_ids=[],
        limit=1,
    )
    assert len(results) == 1
    assert results[0].claim_id == "cora_03"
    assert results[0].lexical_rank == 1
    with pytest.raises(ValueError):
        reciprocal_rank_fusion(lexical_claim_ids=[], vector_claim_ids=[], limit=0)
