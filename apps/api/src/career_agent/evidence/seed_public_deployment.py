"""Idempotently seed a deployment database from reviewed public evidence only."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from career_agent.db.models import EvidenceCardRecord
from career_agent.db.session import create_database_engine
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.registry_import import import_new_evidence_card


def seed_public_deployment(session: Session, cards_dir: Path) -> tuple[int, int]:
    """Add missing approved/public cards and reject a divergent existing card."""

    paths = sorted(cards_dir.glob("*.json"))
    if not paths:
        raise ValueError(f"no public evidence cards found in {cards_dir}")

    imported = skipped = 0
    for path in paths:
        card = load_canonical_evidence_card(path)
        if card.review_status != "approved" or card.answer_visibility != "public":
            raise ValueError(f"public deployment card {card.id!r} is not approved/public")
        if any(source.source_visibility != "public" for source in card.sources):
            raise ValueError(f"public deployment card {card.id!r} has a non-public source")

        existing = session.get(EvidenceCardRecord, card.id)
        if existing is None:
            import_new_evidence_card(session, card)
            imported += 1
        elif existing.version == card.version:
            skipped += 1
        else:
            raise ValueError(
                f"deployment database has {card.id!r} at version {existing.version}; "
                "manual reviewed migration required"
            )
    return imported, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a deployment database with reviewed public evidence only."
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--cards-dir", type=Path, required=True)
    args = parser.parse_args()

    engine = create_database_engine(args.database_url)
    with Session(engine) as session:
        imported, skipped = seed_public_deployment(session, args.cards_dir)
        session.commit()
    print(f"public deployment seed: imported={imported} skipped={skipped}")


if __name__ == "__main__":
    main()
