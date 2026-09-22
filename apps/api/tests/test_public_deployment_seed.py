from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.models import EvidenceCardRecord
from career_agent.evidence.seed_public_deployment import seed_public_deployment


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_public_deployment_seed_is_idempotent_and_public_only(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'deployment.sqlite'}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        imported, skipped = seed_public_deployment(
            session, REPO_ROOT / "evidence" / "registry" / "approved"
        )
        session.commit()
        assert (imported, skipped) == (5, 0)

        imported, skipped = seed_public_deployment(
            session, REPO_ROOT / "evidence" / "registry" / "approved"
        )
        assert (imported, skipped) == (0, 5)
        cards = session.scalars(select(EvidenceCardRecord)).all()

    assert cards
    assert all(card.review_status == "approved" for card in cards)
    assert all(card.answer_visibility == "public" for card in cards)
