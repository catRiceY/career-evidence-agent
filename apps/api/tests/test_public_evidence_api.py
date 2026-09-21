from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from career_agent.api.main import create_app
from career_agent.db.base import Base
from career_agent.db.session import create_database_engine
from career_agent.evidence.canonical_loader import load_canonical_evidence_card
from career_agent.evidence.legacy_import import normalize_legacy_project_card
from career_agent.evidence.registry_import import import_new_evidence_card


REPO_ROOT = Path(__file__).resolve().parents[3]
APPROVED_CARDS_DIR = REPO_ROOT / "evidence" / "registry" / "approved"


def seed_database(database_url: str) -> None:
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for path in sorted(APPROVED_CARDS_DIR.glob("*.json")):
            import_new_evidence_card(session, load_canonical_evidence_card(path))
        import_new_evidence_card(
            session,
            normalize_legacy_project_card(
                {
                    "id": "private_legacy",
                    "title": "Must not leak",
                    "summary": "Private draft summary.",
                    "claims": [
                        {
                            "id": "private_legacy_claim",
                            "text": "Private claim.",
                            "source_ids": ["private_legacy_source"],
                        }
                    ],
                    "sources": [
                        {
                            "id": "private_legacy_source",
                            "type": "github_readme_private",
                            "title": "Private README",
                            "url": "https://example.invalid/private",
                        }
                    ],
                }
            ),
        )
        session.commit()


def test_public_api_filters_by_approval_visibility_and_track(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'evidence.sqlite'}"
    seed_database(database_url)
    client = TestClient(create_app(database_url))

    assert client.get("/health").json() == {"status": "ok"}

    response = client.get(
        "/v1/public/evidence",
        params={"track": "agent_rag_ai_app"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert {item["id"] for item in payload} == {
        "project_connectonion_ios",
        "project_connectonion_studio",
    }
    assert all(
        source["url_or_path"] != "https://example.invalid/private"
        for item in payload
        for claim in item["claims"]
        for source in claim["sources"]
    )

    assert client.get("/v1/public/evidence/private_legacy").status_code == 404


def test_public_api_cors_allows_only_configured_portfolio_origin(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'cors.sqlite'}"
    seed_database(database_url)
    monkeypatch.setenv("CAREER_AGENT_PUBLIC_CORS_ORIGINS", "https://portfolio.example")
    client = TestClient(create_app(database_url))

    allowed = client.options(
        "/v1/public/evidence",
        headers={
            "Origin": "https://portfolio.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/v1/public/evidence",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "https://portfolio.example"
    assert "access-control-allow-origin" not in denied.headers


def test_public_search_returns_only_cited_approved_public_claims(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'evidence.sqlite'}"
    seed_database(database_url)
    client = TestClient(create_app(database_url))

    studio_response = client.get("/v1/public/evidence/search", params={"q": "WebSocket QR"})
    assert studio_response.status_code == 200
    studio_results = studio_response.json()
    assert studio_results
    assert studio_results[0]["evidence_id"] == "project_connectonion_studio"

    paper_response = client.get("/v1/public/evidence/search", params={"q": "NAS"})
    assert paper_response.status_code == 200
    assert "paper_cora_nas" in {item["evidence_id"] for item in paper_response.json()}

    for item in studio_results + paper_response.json():
        assert item["evidence_id"] != "private_legacy"
        assert all(source["url_or_path"] != "https://example.invalid/private" for source in item["sources"])

    assert client.get("/v1/public/evidence/search", params={"q": ""}).status_code == 422
