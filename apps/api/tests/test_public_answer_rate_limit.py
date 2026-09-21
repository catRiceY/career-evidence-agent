from fastapi.testclient import TestClient

from career_agent.api.rate_limit import PublicAnswerRateLimiter, public_client_id


def test_rate_limiter_rejects_the_next_request_until_its_window_expires():
    now = [0.0]
    limiter = PublicAnswerRateLimiter(max_requests=2, window_seconds=60, clock=lambda: now[0])

    assert limiter.allow("client") == (True, 0)
    assert limiter.allow("client") == (True, 0)
    assert limiter.allow("client") == (False, 61)
    now[0] = 60.0
    assert limiter.allow("client") == (True, 0)


def test_client_id_uses_the_final_forwarded_hop_or_socket_fallback():
    assert public_client_id("untrusted, railway-client", "socket") == "railway-client"
    assert public_client_id(None, "socket") == "socket"


def test_public_answer_path_returns_429_after_configured_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("CAREER_AGENT_PUBLIC_ANSWER_MAX_PER_MINUTE", "1")
    from career_agent.api.main import create_app

    app = create_app(f"sqlite+pysqlite:///{tmp_path / 'limit.sqlite'}")
    client = TestClient(app)
    first = client.post("/v1/public/evidence/answer", json={"question": "one"})
    second = client.post("/v1/public/evidence/answer", json={"question": "two"})

    # The first response is allowed through to its not-configured answer
    # gateway; only the second is rejected by the rate limiter.
    assert first.status_code == 503
    assert second.status_code == 429
    assert second.headers["retry-after"]
