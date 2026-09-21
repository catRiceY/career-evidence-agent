from pathlib import Path

from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.session import create_database_engine
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.registry_import import import_new_evidence_card
from career_agent.retrieval.evaluation import (
    RetrievalEvalCase,
    evaluate_retrieval_cases,
    evaluate_public_retrieval,
    evaluate_public_bm25,
    load_retrieval_eval_cases,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
APPROVED_CARDS_DIR = REPO_ROOT / "evidence" / "registry" / "approved"
EVAL_CASES_PATH = REPO_ROOT / "evals" / "retrieval" / "public-baseline.json"


def test_public_retrieval_baseline_recalls_expected_reviewed_claims(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'eval.sqlite'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for path in sorted(APPROVED_CARDS_DIR.glob("*.json")):
            import_new_evidence_card(session, load_canonical_evidence_card(path))
        session.commit()

        results = evaluate_public_retrieval(
            session, load_retrieval_eval_cases(EVAL_CASES_PATH)
        )

    assert len(results) == 4
    assert all(result.recall_at_k == 1.0 for result in results)


def test_retrieval_eval_can_compare_a_different_retriever_against_same_gold_set() -> None:
    results = evaluate_retrieval_cases(
        [
            RetrievalEvalCase(
                id="EVAL-001",
                query="irrelevant to the stub",
                expected_claim_ids=["claim_a", "claim_b"],
                k=2,
            )
        ],
        retrieve=lambda _query, _limit: ["claim_b", "claim_c"],
    )

    assert results[0].retrieved_claim_ids == ["claim_b", "claim_c"]
    assert results[0].recall_at_k == 0.5


def test_bm25_uses_the_same_gold_set_as_the_older_lexical_baseline(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'bm25-eval.sqlite'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for path in sorted(APPROVED_CARDS_DIR.glob("*.json")):
            import_new_evidence_card(session, load_canonical_evidence_card(path))
        session.commit()
        results = evaluate_public_bm25(session, load_retrieval_eval_cases(EVAL_CASES_PATH))
    assert len(results) == 4
    assert all(0.0 <= result.recall_at_k <= 1.0 for result in results)
