from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.models import (
    ClaimRecord,
    ClaimSourceRecord,
    EvidenceCardRecord,
    SourceRecord,
)


def test_registry_schema_creates_core_tables() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    assert {
        "evidence_cards",
        "claims",
        "sources",
        "claim_sources",
        "review_decisions",
        "evidence_chunks",
        "chunk_embeddings",
    } <= set(inspect(engine).get_table_names())


def test_registry_persists_claim_to_source_traceability() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        card = EvidenceCardRecord(
            id="project_1",
            type="project",
            title="Project",
            summary="A traceable project record.",
        )
        source = SourceRecord(
            id="source_1",
            evidence_id="project_1",
            type="github_readme",
            title="README",
            url_or_path="https://example.com/readme",
            source_visibility="public",
            allowed_quote_scope="short_summary",
        )
        claim = ClaimRecord(
            id="claim_1",
            evidence_id="project_1",
            text="A reviewed project fact.",
            claim_type="project_feature",
        )
        session.add_all([card, source, claim])
        session.flush()
        session.add(ClaimSourceRecord(claim_id="claim_1", source_id="source_1"))
        session.commit()

        stored_claim = session.get(ClaimRecord, "claim_1")
        assert stored_claim is not None
        assert stored_claim.source_links[0].source_id == "source_1"
