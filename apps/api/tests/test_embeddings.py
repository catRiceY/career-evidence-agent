import json

import httpx
import pytest

from career_agent.retrieval.embeddings import (
    EmbeddingConfig,
    OpenAICompatibleEmbeddingProvider,
)
from career_agent.retrieval.vector_store import vector_literal


def test_openai_compatible_embedding_provider_preserves_input_order_and_dimensions() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        assert request.headers["authorization"] == "Bearer test-key"
        assert json.loads(request.content) == {
            "model": "test-embedding",
            "input": ["first", "second"],
            "dimensions": 3,
        }
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                ]
            },
        )

    provider = OpenAICompatibleEmbeddingProvider(
        EmbeddingConfig(
            base_url="https://embedding.example/v1",
            api_key="test-key",
            model="test-embedding",
            dimensions=3,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    batch = provider.embed(["first", "second"])
    assert batch.vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert batch.dimensions == 3


def test_vector_literal_rejects_invalid_values() -> None:
    assert vector_literal([0.1, 2.0]) == "[0.10000000000000001,2]"
    with pytest.raises(ValueError):
        vector_literal([])
    with pytest.raises(ValueError):
        vector_literal([float("nan")])


def test_embedding_config_requires_all_secret_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CAREER_AGENT_EMBEDDING_BASE_URL", raising=False)
    monkeypatch.delenv("CAREER_AGENT_EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("CAREER_AGENT_EMBEDDING_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="CAREER_AGENT_EMBEDDING_API_KEY"):
        EmbeddingConfig.from_environment()
