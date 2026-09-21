"""Load human-reviewed evidence assets without silently changing their scope."""

from __future__ import annotations

from pathlib import Path

from career_agent.evidence.schemas import EvidenceCard


def load_canonical_evidence_card(path: Path) -> EvidenceCard:
    """Validate one reviewed JSON asset before it can reach the registry."""

    return EvidenceCard.model_validate_json(path.read_text(encoding="utf-8"))
