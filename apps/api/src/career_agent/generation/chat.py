"""Vendor-neutral, OpenAI-compatible structured text generation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class ChatConfig:
    """Configuration for answer drafting, separate from retrieval embeddings.

    The development default reuses the existing DashScope endpoint and key.
    Production may set the `CAREER_AGENT_CHAT_*` values independently when
    model routing or key rotation becomes necessary.
    """

    base_url: str
    api_key: str
    model: str = "qwen3.6-flash"
    max_output_tokens: int = 700
    timeout_seconds: float = 45.0

    @classmethod
    def from_environment(cls) -> "ChatConfig":
        base_url = os.getenv("CAREER_AGENT_CHAT_BASE_URL") or os.getenv(
            "CAREER_AGENT_EMBEDDING_BASE_URL"
        )
        api_key = os.getenv("CAREER_AGENT_CHAT_API_KEY") or os.getenv(
            "CAREER_AGENT_EMBEDDING_API_KEY"
        )
        if not base_url or not api_key:
            raise RuntimeError("missing chat configuration")
        return cls(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=os.getenv("CAREER_AGENT_CHAT_MODEL", "qwen3.6-flash"),
            max_output_tokens=int(os.getenv("CAREER_AGENT_CHAT_MAX_OUTPUT_TOKENS", "700")),
        )


class StructuredChatProvider(Protocol):
    def complete_json(self, *, system: str, user: str) -> dict[str, object]: ...


class OpenAICompatibleStructuredChatProvider:
    def __init__(self, config: ChatConfig, *, client: httpx.Client | None = None):
        self._config = config
        self._client = client or httpx.Client(timeout=config.timeout_seconds)

    def complete_json(self, *, system: str, user: str) -> dict[str, object]:
        response = self._client.post(
            f"{self._config.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._config.api_key}"},
            json={
                "model": self._config.model,
                "temperature": 0.1,
                "max_tokens": self._config.max_output_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("chat provider did not return a JSON object")
        return parsed
