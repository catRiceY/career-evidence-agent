from pathlib import Path

from fastapi.testclient import TestClient

from career_agent.api.main import create_app
def test_hybrid_endpoint_reports_unconfigured_in_a_non_vector_test_database(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'evidence.sqlite'}"
    client = TestClient(create_app(database_url))

    response = client.get("/v1/public/evidence/search/hybrid", params={"q": "studio"})

    assert response.status_code == 503
    assert response.json()["detail"] == "hybrid retrieval is not configured"
