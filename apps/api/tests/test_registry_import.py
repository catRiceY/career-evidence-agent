import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.models import ClaimRecord, EvidenceCardRecord
from career_agent.evidence.legacy_import import normalize_legacy_project_card
from career_agent.evidence.registry_import import import_new_evidence_card


def make_card():
    return normalize_legacy_project_card(
        {
            "id": "legacy_project",
            "title": "Legacy Project",
            "summary": "A legacy card used for import testing.",
            "claims": [
                {
                    "id": "legacy_claim",
                    "text": "A candidate project feature.",
                    "source_ids": ["legacy_readme"],
                }
            ],
            "sources": [
                {
                    "id": "legacy_readme",
                    "type": "github_readme",
                    "title": "README",
                    "url": "https://example.com/readme",
                }
            ],
        }
    )


def test_import_persists_draft_card_and_source_links() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        import_new_evidence_card(session, make_card())
        session.commit()

        card = session.get(EvidenceCardRecord, "legacy_project")
        claim = session.get(ClaimRecord, "legacy_claim")
        assert card is not None
        assert card.review_status == "draft"
        assert card.answer_visibility == "private"
        assert claim is not None
        assert claim.source_links[0].source_id == "legacy_readme"


def test_import_refuses_to_overwrite_existing_reviewable_card() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        import_new_evidence_card(session, make_card())
        with pytest.raises(ValueError, match="will not overwrite"):
            import_new_evidence_card(session, make_card())
