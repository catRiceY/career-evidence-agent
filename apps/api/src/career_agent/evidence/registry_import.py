from __future__ import annotations

from sqlalchemy.orm import Session

from career_agent.db.models import (
    ClaimRecord,
    ClaimSourceRecord,
    EvidenceCardRecord,
    SourceRecord,
)
from career_agent.evidence.schemas import EvidenceCard


def import_new_evidence_card(session: Session, card: EvidenceCard) -> EvidenceCardRecord:
    """Persist a normalized card once, without overwriting review decisions.

    Legacy inputs are necessarily stale relative to a human review. Updating an
    existing ID is therefore intentionally rejected; later versions will use a
    reviewed update command that records a ReviewDecisionRecord.
    """

    if session.get(EvidenceCardRecord, card.id) is not None:
        raise ValueError(
            f"evidence card '{card.id}' already exists; import will not overwrite it"
        )

    record = EvidenceCardRecord(
        id=card.id,
        version=card.version,
        type=card.type,
        title=card.title,
        period=card.period,
        summary=card.summary,
        review_status=card.review_status,
        answer_visibility=card.answer_visibility,
        source_visibility_default=card.source_visibility_default,
        personal_contribution_status=card.personal_contribution_status,
        role=card.role,
        tech_stack=card.tech_stack,
        target_tracks=card.target_tracks,
        priority_by_track=card.priority_by_track,
        status_notes=card.status_notes,
        risks=card.risks,
        next_evidence_to_add=card.next_evidence_to_add,
        paper_metadata=(card.paper.model_dump(mode="json") if card.paper else None),
    )
    session.add(record)

    for source in card.sources:
        session.add(
            SourceRecord(
                id=source.id,
                evidence_id=card.id,
                type=source.type,
                title=source.title,
                url_or_path=source.url_or_path,
                source_visibility=source.source_visibility,
                allowed_quote_scope=source.allowed_quote_scope,
                locator=source.locator,
                version_ref=source.version_ref,
                captured_at=source.captured_at,
                notes=source.notes,
            )
        )

    for claim in card.claims:
        session.add(
            ClaimRecord(
                id=claim.id,
                evidence_id=card.id,
                text=claim.text,
                claim_type=claim.claim_type,
                review_status=claim.review_status,
                answer_visibility=claim.answer_visibility,
                personal_contribution_status=claim.personal_contribution_status,
                evidence_strength=claim.evidence_strength,
                hr_value=claim.hr_value,
                risk_or_limit=claim.risk_or_limit,
                target_tracks=claim.target_tracks,
                created_from=claim.created_from,
            )
        )
        locators = {item.source_id: item.locator for item in claim.locators}
        for source_id in claim.source_ids:
            session.add(
                ClaimSourceRecord(
                    claim_id=claim.id,
                    source_id=source_id,
                    locator=locators.get(source_id),
                )
        )

    session.flush()
    return record
