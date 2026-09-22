from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.models import EvidenceChunkRecord
from career_agent.db.session import create_database_engine
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.legacy_import import normalize_legacy_project_card
from career_agent.evidence.registry_import import import_new_evidence_card
from career_agent.retrieval.chunks import CHUNK_STRATEGY, rebuild_public_claim_chunks


REPO_ROOT = Path(__file__).resolve().parents[3]
APPROVED_CARDS_DIR = REPO_ROOT / "evidence" / "registry" / "approved"


def test_chunk_builder_uses_only_approved_public_claim_source_pairs(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'chunks.sqlite'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for path in sorted(APPROVED_CARDS_DIR.glob("*.json")):
            import_new_evidence_card(session, load_canonical_evidence_card(path))
        import_new_evidence_card(
            session,
            normalize_legacy_project_card(
                {
                    "id": "private_legacy",
                    "title": "Must not leak",
                    "summary": "Private draft summary.",
                    "claims": [{"id": "private_legacy_claim", "text": "Private claim.", "source_ids": ["private_source"]}],
                    "sources": [{"id": "private_source", "type": "github_readme_private", "title": "Private README", "url": "https://example.invalid/private"}],
                }
            ),
        )
        session.commit()

        built = rebuild_public_claim_chunks(session)
        session.commit()
        chunks = session.scalars(select(EvidenceChunkRecord)).all()

        assert built == len(chunks) == 30
        assert {chunk.chunk_strategy for chunk in chunks} == {CHUNK_STRATEGY}
        assert {chunk.index_visibility for chunk in chunks} == {"public"}
        assert all("private" not in chunk.id for chunk in chunks)
        assert all(len(chunk.content_hash) == 64 for chunk in chunks)

        assert rebuild_public_claim_chunks(session) == 30
        session.commit()
        assert session.scalars(select(EvidenceChunkRecord)).all()
