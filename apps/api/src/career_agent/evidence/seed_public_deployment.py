"""Idempotently seed a deployment database from reviewed public evidence only."""

from __future__ import annotations

import argparse
from pathlib import Path
from datetime import date, datetime

from sqlalchemy.orm import Session

from career_agent.db.models import EvidenceCardRecord
from career_agent.db.session import create_database_engine
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.registry_import import import_new_evidence_card
from career_agent.evidence.schemas import EvidenceCard


def _date_key(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()


def _claim_locators(source_ids: list[str], locators: dict[str, str | None]) -> dict[str, str | None]:
    return {source_id: locators.get(source_id) for source_id in sorted(source_ids)}


def _record_matches_card(record: EvidenceCardRecord, card: EvidenceCard) -> bool:
    """Return whether the deployed record already mirrors the reviewed card."""

    if (
        record.version != card.version
        or record.type != card.type
        or record.title != card.title
        or record.period != card.period
        or record.summary != card.summary
        or record.review_status != card.review_status
        or record.answer_visibility != card.answer_visibility
        or record.source_visibility_default != card.source_visibility_default
        or record.personal_contribution_status != card.personal_contribution_status
        or record.role != card.role
        or record.tech_stack != card.tech_stack
        or record.target_tracks != card.target_tracks
        or record.priority_by_track != card.priority_by_track
        or record.status_notes != card.status_notes
        or record.risks != card.risks
        or record.next_evidence_to_add != card.next_evidence_to_add
        or record.paper_metadata != (card.paper.model_dump(mode="json") if card.paper else None)
    ):
        return False

    source_payload = {
        source.id: {
            "type": source.type,
            "title": source.title,
            "url_or_path": source.url_or_path,
            "source_visibility": source.source_visibility,
            "allowed_quote_scope": source.allowed_quote_scope,
            "locator": source.locator,
            "version_ref": source.version_ref,
            "captured_at": _date_key(source.captured_at),
            "notes": source.notes,
        }
        for source in card.sources
    }
    record_sources = {
        source.id: {
            "type": source.type,
            "title": source.title,
            "url_or_path": source.url_or_path,
            "source_visibility": source.source_visibility,
            "allowed_quote_scope": source.allowed_quote_scope,
            "locator": source.locator,
            "version_ref": source.version_ref,
            "captured_at": _date_key(source.captured_at),
            "notes": source.notes,
        }
        for source in record.sources
    }
    if record_sources != source_payload:
        return False

    claim_payload = {
        claim.id: {
            "text": claim.text,
            "claim_type": claim.claim_type,
            "review_status": claim.review_status,
            "answer_visibility": claim.answer_visibility,
            "personal_contribution_status": claim.personal_contribution_status,
            "evidence_strength": claim.evidence_strength,
            "hr_value": claim.hr_value,
            "risk_or_limit": claim.risk_or_limit,
            "target_tracks": claim.target_tracks,
            "created_from": claim.created_from,
            "source_ids": sorted(claim.source_ids),
            "locators": _claim_locators(
                claim.source_ids, {item.source_id: item.locator for item in claim.locators}
            ),
        }
        for claim in card.claims
    }
    record_claims = {
        claim.id: {
            "text": claim.text,
            "claim_type": claim.claim_type,
            "review_status": claim.review_status,
            "answer_visibility": claim.answer_visibility,
            "personal_contribution_status": claim.personal_contribution_status,
            "evidence_strength": claim.evidence_strength,
            "hr_value": claim.hr_value,
            "risk_or_limit": claim.risk_or_limit,
            "target_tracks": claim.target_tracks,
            "created_from": claim.created_from,
            "source_ids": sorted(link.source_id for link in claim.source_links),
            "locators": _claim_locators(
                [link.source_id for link in claim.source_links],
                {link.source_id: link.locator for link in claim.source_links},
            ),
        }
        for claim in record.claims
    }
    return record_claims == claim_payload


def seed_public_deployment(session: Session, cards_dir: Path) -> tuple[int, int]:
    """Synchronize the deployment database with reviewed public evidence cards."""

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
        elif _record_matches_card(existing, card):
            skipped += 1
        else:
            session.delete(existing)
            session.flush()
            import_new_evidence_card(session, card)
            imported += 1
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
