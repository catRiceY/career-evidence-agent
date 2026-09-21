from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from career_agent.api.main import create_app
from career_agent.api import main as api_main
from career_agent.db.base import Base
from career_agent.db.models import RunManifestRecord
from career_agent.generation.chat import ChatConfig


class MatrixProvider:
    def __init__(self):
        self.calls = 0

    def complete_json(self, *, system, user):
        self.calls += 1
        if self.calls == 1:
            assert "Extract at most 16" in system
            return {"requirements": [{
                "id": "req_1", "text": "Agent system experience",
                "category": "experience", "importance": "must",
            }]}
        assert "candidate_claim_ids" in user
        return {"rows": [{
            "requirement_id": "req_1", "status": "gap", "claim_ids": [],
            "note": "当前空测试库没有可用证据。",
        }]}


def _database_url(tmp_path: Path) -> str:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'private-api.db'}"
    Base.metadata.create_all(create_engine(database_url))
    return database_url


def test_private_studio_requires_owner_bearer_token(tmp_path: Path):
    client = TestClient(create_app(
        _database_url(tmp_path), private_owner_token="owner-test-token",
        private_chat_provider=MatrixProvider(), private_model_name="test-model",
    ))
    assert client.get("/v1/private/studio/status").status_code == 401
    assert client.get("/v1/private/studio/status", headers={"Authorization": "Bearer wrong"}).status_code == 403
    response = client.get("/v1/private/studio/status", headers={"Authorization": "Bearer owner-test-token"})
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "authentication": "owner_bearer_token"}


def test_private_jd_endpoint_records_only_a_hash(tmp_path: Path):
    database_url = _database_url(tmp_path)
    provider = MatrixProvider()
    client = TestClient(create_app(
        database_url, private_owner_token="owner-test-token",
        private_chat_provider=provider, private_model_name="test-model",
    ))
    jd = "Sensitive job text must never be stored verbatim in a run manifest."
    response = client.post(
        "/v1/private/studio/jd-match",
        headers={"Authorization": "Bearer owner-test-token"},
        json={"jd_text": jd, "session_label": "private-test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["rows"][0]["status"] == "gap"
    assert body["run_id"].startswith("run_")
    assert provider.calls == 2
    with Session(create_engine(database_url)) as session:
        record = session.get(RunManifestRecord, body["run_id"])
    assert record is not None
    assert record.access_scope == "private"
    assert jd not in record.input_hash


def test_private_routes_are_absent_without_explicit_token(tmp_path: Path):
    client = TestClient(create_app(_database_url(tmp_path)))
    assert client.get("/v1/private/studio/status").status_code == 404


def test_owner_can_save_private_memory_but_unknown_kinds_are_rejected(tmp_path: Path):
    client = TestClient(create_app(
        _database_url(tmp_path), private_owner_token="owner-test-token",
        private_chat_provider=MatrixProvider(), private_model_name="test-model",
    ))
    headers = {"Authorization": "Bearer owner-test-token"}
    saved = client.post("/v1/private/studio/memories", headers=headers, json={
        "kind": "interview_reflection", "content": "Explain evidence boundaries before discussing architecture.",
    })
    assert saved.status_code == 201
    assert saved.json()["visibility"] == "private"
    assert client.get("/v1/private/studio/memories", headers=headers).json()[0]["id"] == saved.json()["id"]
    invalid = client.post("/v1/private/studio/memories", headers=headers, json={"kind": "chat_history", "content": "no"})
    assert invalid.status_code == 422


def test_automation_draft_stays_pending_review(tmp_path: Path):
    client = TestClient(create_app(
        _database_url(tmp_path), private_owner_token="owner-test-token",
        private_chat_provider=MatrixProvider(), private_model_name="test-model",
    ))
    response = client.post("/v1/private/studio/ingestion-drafts", headers={"Authorization": "Bearer owner-test-token"}, json={
        "source_url": "https://github.com/catRiceY/example", "title": "Example repository update", "source_type": "github_webhook",
    })
    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"


@pytest.mark.parametrize("tokens,timeout", [(700, 45.0), (4096, 150.0)])
def test_environment_private_jd_budget_is_separate_from_public(
    tmp_path: Path, monkeypatch, tokens: int, timeout: float
):
    monkeypatch.setenv("CAREER_AGENT_DATABASE_URL", _database_url(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_OWNER_TOKEN", "owner-test-token")
    monkeypatch.setenv("CAREER_AGENT_EMBEDDING_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("CAREER_AGENT_EMBEDDING_API_KEY", "unused-test-key")
    monkeypatch.setenv("CAREER_AGENT_EMBEDDING_MODEL", "test-embedding")
    configured = ChatConfig(
        base_url="https://example.invalid/v1", api_key="unused-test-key",
        model="test-chat", max_output_tokens=tokens, timeout_seconds=timeout,
    )
    monkeypatch.setattr(ChatConfig, "from_environment", classmethod(lambda cls: configured))
    monkeypatch.setattr(api_main, "OpenAICompatibleEmbeddingProvider", lambda config: object())
    providers = []

    class ConfiguredMatrixProvider(MatrixProvider):
        def __init__(self, config):
            super().__init__()
            self.config = config
            providers.append(self)

    monkeypatch.setattr(api_main, "OpenAICompatibleStructuredChatProvider", ConfiguredMatrixProvider)
    client = TestClient(create_app())
    response = client.post(
        "/v1/private/studio/jd-match",
        headers={"Authorization": "Bearer owner-test-token"},
        json={"jd_text": "Agent system experience", "session_label": "budget-test"},
    )
    assert response.status_code == 200
    public_provider, private_provider = providers
    assert public_provider.config == configured
    assert public_provider.calls == 0
    assert private_provider.config.max_output_tokens == max(tokens, 3000)
    assert private_provider.config.timeout_seconds == max(timeout, 120.0)
    assert private_provider.calls == 2
