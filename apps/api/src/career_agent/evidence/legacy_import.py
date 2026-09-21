from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from career_agent.evidence.schemas import (
    AllowedQuoteScope,
    AnswerVisibility,
    Claim,
    EvidenceCard,
    EvidenceStrength,
    PersonalContributionStatus,
    ReviewStatus,
    Source,
    SourceType,
    SourceVisibility,
)

_YAML_BLOCK = re.compile(r"```yaml\s*\n(?P<content>.*?)\n```", re.DOTALL)

_PUBLIC_SOURCE_TYPES = {
    SourceType.GITHUB_API,
    SourceType.GITHUB_README,
    SourceType.GITHUB_REPO_METADATA,
    SourceType.GITHUB_REPO_PUBLIC,
    SourceType.PUBLIC_SITE,
}


def load_legacy_project_card(path: Path) -> EvidenceCard:
    """Read a Phase 1 Markdown card and normalize it without granting access.

    Legacy card visibility values are deliberately never promoted to public
    answer visibility. The human review step creates approved canonical claims.
    """

    match = _YAML_BLOCK.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"no YAML code block found in {path}")

    raw = yaml.safe_load(match.group("content"))
    if not isinstance(raw, dict):
        raise ValueError(f"YAML block in {path} must be a mapping")
    return normalize_legacy_project_card(raw)


def normalize_legacy_project_card(raw: dict[str, Any]) -> EvidenceCard:
    """Adapt a legacy project card to the strict runtime contract.

    This function is intentionally a one-way safety boundary: candidate
    visibility is retained in notes, while runtime visibility stays private.
    """

    evidence_id = _required_text(raw, "id")
    sources = [_normalize_source(evidence_id, item) for item in raw.get("sources", [])]
    claims = [
        _normalize_claim(evidence_id, item)
        for item in raw.get("claims", [])
    ]
    legacy_visibility = str(raw.get("visibility", "unspecified"))

    return EvidenceCard(
        id=evidence_id,
        type="project",
        title=_required_text(raw, "title"),
        period=_optional_text(raw.get("period")),
        summary=_required_text(raw, "summary"),
        review_status=ReviewStatus.DRAFT,
        answer_visibility=AnswerVisibility.PRIVATE,
        source_visibility_default=SourceVisibility.PRIVATE,
        personal_contribution_status=PersonalContributionStatus.NEEDS_CONFIRMATION,
        role=_optional_text(raw.get("role")),
        tech_stack=_string_list(raw.get("tech_stack")),
        status_notes=[
            "Imported from legacy Markdown card; no public authorization implied.",
            f"Legacy visibility candidate: {legacy_visibility}",
        ],
        risks=_string_list(raw.get("risks")),
        next_evidence_to_add=_string_list(raw.get("next_evidence_to_add")),
        claims=claims,
        sources=sources,
    )


def _normalize_source(evidence_id: str, raw: Any) -> Source:
    if not isinstance(raw, dict):
        raise ValueError("legacy source must be a mapping")
    source_type = SourceType(_required_text(raw, "type"))
    visibility = (
        SourceVisibility.PUBLIC
        if source_type in _PUBLIC_SOURCE_TYPES
        else SourceVisibility.PRIVATE
    )
    return Source(
        id=_required_text(raw, "id"),
        evidence_id=evidence_id,
        type=source_type,
        title=_required_text(raw, "title"),
        url_or_path=_required_text(raw, "url"),
        source_visibility=visibility,
        allowed_quote_scope=(
            AllowedQuoteScope.SHORT_SUMMARY
            if visibility == SourceVisibility.PUBLIC
            else AllowedQuoteScope.NONE
        ),
        locator=_optional_text(raw.get("locator")),
        notes=_optional_text(raw.get("note")) or "Imported from legacy source.",
    )


def _normalize_claim(evidence_id: str, raw: Any) -> Claim:
    if not isinstance(raw, dict):
        raise ValueError("legacy claim must be a mapping")
    strength = str(raw.get("evidence_strength", EvidenceStrength.WEAK))
    if strength not in {item.value for item in EvidenceStrength}:
        strength = EvidenceStrength.WEAK
    legacy_visibility = str(raw.get("visibility", "unspecified"))
    risk = _optional_text(raw.get("risk_or_limit")) or ""
    return Claim(
        id=_required_text(raw, "id"),
        evidence_id=evidence_id,
        text=_required_text(raw, "text"),
        claim_type="project_feature",
        review_status=ReviewStatus.DRAFT,
        answer_visibility=AnswerVisibility.PRIVATE,
        personal_contribution_status=PersonalContributionStatus.NEEDS_CONFIRMATION,
        evidence_strength=EvidenceStrength(strength),
        source_ids=_string_list(raw.get("source_ids")),
        hr_value=_optional_text(raw.get("hr_value")) or "",
        risk_or_limit=(
            f"{risk} Legacy visibility candidate: {legacy_visibility}.".strip()
        ),
        created_from="manual",
    )


def _required_text(raw: dict[str, Any], key: str) -> str:
    value = _optional_text(raw.get(key))
    if value is None:
        raise ValueError(f"legacy card requires non-empty '{key}'")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("expected text value")
    value = value.strip()
    return value or None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected a list of text values")
    return [item.strip() for item in value if item.strip()]
