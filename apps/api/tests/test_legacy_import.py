from career_agent.evidence.legacy_import import normalize_legacy_project_card
from career_agent.evidence.schemas import AnswerVisibility, ReviewStatus, SourceVisibility


def test_legacy_visibility_never_grants_public_access() -> None:
    card = normalize_legacy_project_card(
        {
            "id": "legacy_project",
            "title": "Legacy Project",
            "visibility": "public_summary_private_source",
            "summary": "A legacy card used for migration testing.",
            "tech_stack": ["Python"],
            "claims": [
                {
                    "id": "legacy_claim",
                    "text": "A candidate project feature.",
                    "visibility": "public",
                    "source_ids": ["legacy_readme"],
                    "evidence_strength": "strong",
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

    assert card.review_status == ReviewStatus.DRAFT
    assert card.answer_visibility == AnswerVisibility.PRIVATE
    assert card.claims[0].answer_visibility == AnswerVisibility.PRIVATE
    assert card.claims[0].review_status == ReviewStatus.DRAFT
    assert card.sources[0].source_visibility == SourceVisibility.PUBLIC


def test_legacy_private_readme_stays_private() -> None:
    card = normalize_legacy_project_card(
        {
            "id": "legacy_project",
            "title": "Legacy Project",
            "summary": "A legacy card used for migration testing.",
            "claims": [],
            "sources": [
                {
                    "id": "legacy_private_readme",
                    "type": "github_readme_private",
                    "title": "Private README",
                    "url": "private://readme",
                }
            ],
        }
    )

    assert card.sources[0].source_visibility == SourceVisibility.PRIVATE
