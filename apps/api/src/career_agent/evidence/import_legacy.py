from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.session import create_database_engine
from career_agent.evidence.legacy_import import load_legacy_project_card
from career_agent.evidence.registry_import import import_new_evidence_card


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely import legacy project cards as draft/private evidence."
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--projects-dir", type=Path, required=True)
    args = parser.parse_args()

    engine = create_database_engine(args.database_url)
    Base.metadata.create_all(engine)
    card_paths = sorted(
        path for path in args.projects_dir.glob("*.md") if path.name != "README.md"
    )

    with Session(engine) as session:
        for path in card_paths:
            card = load_legacy_project_card(path)
            import_new_evidence_card(session, card)
            print(f"imported {card.id} as {card.review_status}/{card.answer_visibility}")
        session.commit()


if __name__ == "__main__":
    main()
