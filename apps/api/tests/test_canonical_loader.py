from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.models import ClaimRecord, EvidenceCardRecord, SourceRecord
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.registry_import import import_new_evidence_card
from career_agent.evidence.schemas import AnswerVisibility, ReviewStatus


REPO_ROOT = Path(__file__).resolve().parents[3]
APPROVED_CARDS_DIR = REPO_ROOT / "evidence" / "registry" / "approved"


def test_approved_nas_cards_are_public_and_schema_valid() -> None:
    cards = [
        load_canonical_evidence_card(path)
        for path in sorted(APPROVED_CARDS_DIR.glob("*.json"))
    ]

    assert [card.id for card in cards] == [
        "paper_cora_nas",
        "paper_ripple",
        "project_career_evidence_agent",
        "project_connectonion_ios",
        "project_connectonion_studio",
    ]
    assert all(card.review_status == ReviewStatus.APPROVED for card in cards)
    assert all(card.answer_visibility == AnswerVisibility.PUBLIC for card in cards)
    assert all(source.source_visibility == "public" for card in cards for source in card.sources)
    assert all(
        claim.review_status == ReviewStatus.APPROVED
        for card in cards
        for claim in card.claims
    )


def test_approved_nas_cards_import_as_linked_registry_records() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        for path in sorted(APPROVED_CARDS_DIR.glob("*.json")):
            import_new_evidence_card(session, load_canonical_evidence_card(path))
        session.commit()

        assert session.query(EvidenceCardRecord).count() == 5
        assert session.query(SourceRecord).count() == 8
        assert session.query(ClaimRecord).count() == 26
        assert {
            card.id for card in session.query(EvidenceCardRecord).all()
        } == {
            "paper_cora_nas",
            "paper_ripple",
            "project_career_evidence_agent",
            "project_connectonion_ios",
            "project_connectonion_studio",
        }
