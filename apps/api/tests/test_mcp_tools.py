from pathlib import Path

from sqlalchemy.orm import Session

from career_agent.db.base import Base
from career_agent.db.session import create_database_engine
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.registry_import import import_new_evidence_card
from career_agent.mcp.tools import (
    get_public_project_summary_tool,
    list_suggested_hr_questions_tool,
    search_public_evidence_tool,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _session(tmp_path: Path) -> Session:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'mcp.sqlite'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    for path in sorted((REPO_ROOT / "evidence/registry/approved").glob("*.json")):
        import_new_evidence_card(session, load_canonical_evidence_card(path))
    session.commit()
    return session


def test_mcp_public_tools_preserve_review_and_visibility_boundary(tmp_path: Path):
    with _session(tmp_path) as session:
        results = search_public_evidence_tool(session, "Agent 工作区")
        card = get_public_project_summary_tool(session, "project_connectonion_studio")
        unknown = get_public_project_summary_tool(session, "project_galaxy_morphology")
    assert results and results[0]["sources"]
    assert card is not None and card["id"] == "project_connectonion_studio"
    assert unknown is None


def test_mcp_suggested_questions_are_static_public_prompts():
    assert len(list_suggested_hr_questions_tool()) >= 3
