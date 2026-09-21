from career_agent.db.session import _normalize_postgres_driver, database_url


def test_database_url_prefers_explicit_value(monkeypatch):
    monkeypatch.setenv("CAREER_AGENT_DATABASE_URL", "postgresql+psycopg://explicit")
    monkeypatch.setenv("POSTGRES_USER", "ignored")
    assert database_url() == "postgresql+psycopg://explicit"


def test_database_url_normalizes_railway_postgres_url(monkeypatch):
    monkeypatch.setenv("CAREER_AGENT_DATABASE_URL", "postgresql://user:pass@host:5432/db")
    assert database_url() == "postgresql+psycopg://user:pass@host:5432/db"


def test_explicit_railway_url_uses_psycopg_driver():
    assert (
        _normalize_postgres_driver("postgresql://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )


def test_database_url_builds_only_from_complete_local_postgres_config(monkeypatch):
    monkeypatch.delenv("CAREER_AGENT_DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "career_agent")
    monkeypatch.setenv("POSTGRES_PASSWORD", "local-pass")
    monkeypatch.setenv("POSTGRES_DB", "career_evidence")
    monkeypatch.setenv("POSTGRES_PORT", "54329")
    url = database_url()
    assert url.startswith("postgresql+psycopg://career_agent:")
    assert url.endswith("@127.0.0.1:54329/career_evidence")
