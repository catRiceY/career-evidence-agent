"""A vendor-neutral OpenAI-compatible embedding client.

The provider is intentionally separated from chunk construction and pgvector
storage. A future model swap changes a local environment setting and triggers
a rebuild; it cannot alter reviewed claims or public/private boundaries.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class EmbeddingConfig:
    base_url: str
    api_key: str
    model: str
    dimensions: int | None = None
    timeout_seconds: float = 30.0

    @classmethod
    def from_environment(cls) -> "EmbeddingConfig":
        required = {
            "CAREER_AGENT_EMBEDDING_BASE_URL": os.environ.get(
                "CAREER_AGENT_EMBEDDING_BASE_URL"
            ),
            "CAREER_AGENT_EMBEDDING_API_KEY": os.environ.get(
                "CAREER_AGENT_EMBEDDING_API_KEY"
            ),
            "CAREER_AGENT_EMBEDDING_MODEL": os.environ.get(
                "CAREER_AGENT_EMBEDDING_MODEL"
            ),
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise RuntimeError(f"missing embedding configuration: {', '.join(missing)}")
        dimensions = os.environ.get("CAREER_AGENT_EMBEDDING_DIMENSIONS")
        return cls(
            base_url=required["CAREER_AGENT_EMBEDDING_BASE_URL"].rstrip("/"),
            api_key=required["CAREER_AGENT_EMBEDDING_API_KEY"],
            model=required["CAREER_AGENT_EMBEDDING_MODEL"],
            dimensions=int(dimensions) if dimensions else None,
        )


@dataclass(frozen=True)
class EmbeddingBatch:
    model: str
    vectors: list[list[float]]

    @property
    def dimensions(self) -> int:
        return len(self.vectors[0]) if self.vectors else 0


class OpenAICompatibleEmbeddingProvider:
    def __init__(self, config: EmbeddingConfig, *, client: httpx.Client | None = None):
        self._config = config
        self._client = client or httpx.Client(timeout=config.timeout_seconds)

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch(model=self._config.model, vectors=[])
        payload: dict[str, object] = {"model": self._config.model, "input": texts}
        if self._config.dimensions is not None:
            payload["dimensions"] = self._config.dimensions
        response = self._client.post(
            f"{self._config.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self._config.api_key}"},
            json=payload,
        )
        response.raise_for_status()
        items = sorted(response.json()["data"], key=lambda item: item["index"])
        vectors = [[float(value) for value in item["embedding"]] for item in items]
        if len(vectors) != len(texts):
            raise ValueError("embedding response count does not match input count")
        if any(not vector for vector in vectors):
            raise ValueError("embedding response contains an empty vector")
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) != 1 or any(
            not math.isfinite(value) for vector in vectors for value in vector
        ):
            raise ValueError("embedding response contains invalid vector values")
        if self._config.dimensions is not None and dimensions != {self._config.dimensions}:
            raise ValueError("embedding response dimensions do not match configuration")
        return EmbeddingBatch(model=self._config.model, vectors=vectors)
