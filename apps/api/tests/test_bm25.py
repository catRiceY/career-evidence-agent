from pathlib import Path

from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.session import create_database_engine
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.registry_import import import_new_evidence_card
from career_agent.retrieval.bm25 import bm25_tokens, search_public_bm25_evidence


REPO_ROOT = Path(__file__).resolve().parents[3]


def _session(tmp_path: Path) -> Session:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'bm25.sqlite'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    for path in sorted((REPO_ROOT / "evidence/registry/approved").glob("*.json")):
        import_new_evidence_card(session, load_canonical_evidence_card(path))
    session.commit()
    return session


def test_bm25_tokens_keep_technical_terms_and_chinese_bigrams():
    tokens = bm25_tokens("用 pgvector 做 Agent 检索")
    assert "pgvector" in tokens
    assert "agent" in tokens
    assert "检索" in tokens


def test_bm25_returns_only_reviewed_public_claims_with_sources(tmp_path: Path):
    with _session(tmp_path) as session:
        results = search_public_bm25_evidence(session, "隔离 Agent 工作区", limit=5)
    assert results
    assert all(result.sources for result in results)
    assert results[0].claim_id.startswith("studio_")


def test_bm25_rejects_an_invalid_result_limit(tmp_path: Path):
    with _session(tmp_path) as session:
        try:
            search_public_bm25_evidence(session, "Agent", limit=0)
        except ValueError as error:
            assert "limit" in str(error)
        else:
            raise AssertionError("invalid limit must be rejected")
