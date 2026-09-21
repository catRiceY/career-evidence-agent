"""Import reviewed canonical evidence cards into a new registry database."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.session import create_database_engine
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.registry_import import import_new_evidence_card


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and import reviewed canonical evidence cards."
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--cards-dir", type=Path, required=True)
    args = parser.parse_args()

    engine = create_database_engine(args.database_url)
    Base.metadata.create_all(engine)
    card_paths = sorted(args.cards_dir.glob("*.json"))
    if not card_paths:
        raise SystemExit(f"no canonical JSON cards found in {args.cards_dir}")

    with Session(engine) as session:
        for path in card_paths:
            card = load_canonical_evidence_card(path)
            import_new_evidence_card(session, card)
            print(
                f"imported {card.id} as "
                f"{card.review_status}/{card.answer_visibility}"
            )
        session.commit()


if __name__ == "__main__":
    main()
