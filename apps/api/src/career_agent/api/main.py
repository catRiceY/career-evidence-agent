from __future__ import annotations

import os
from dataclasses import replace

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from career_agent.api.private_studio import build_private_studio_router
from career_agent.api.public_evidence import build_public_evidence_router
from career_agent.api.rate_limit import PublicAnswerRateLimiter, public_client_id
from career_agent.db.session import create_session_factory
from career_agent.generation.chat import (
    ChatConfig,
    OpenAICompatibleStructuredChatProvider,
    StructuredChatProvider,
)
from career_agent.harness.public_answer import build_hybrid_public_answer_gateway
from career_agent.harness.run_manifest import record_public_answer_run
from career_agent.observability import configure_observability
from career_agent.retrieval.embeddings import (
    EmbeddingConfig,
    OpenAICompatibleEmbeddingProvider,
)
from career_agent.retrieval.vector_store import EmbeddingProvider


def create_app(
    database_url: str | None = None,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    embedding_model: str | None = None,
    private_owner_token: str | None = None,
    private_chat_provider: StructuredChatProvider | None = None,
    private_model_name: str | None = None,
) -> FastAPI:
    """Build the API without ever selecting a database implicitly in production."""

    app = FastAPI(
        title="Career Evidence Agent API",
        version="0.1.0",
        description="Evidence-first API for the public Career Evidence Agent.",
    )
    default_allowed_origins = {
        "https://catricey.github.io",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    }
    configured_allowed_origins = {
        item.strip()
        for item in os.getenv("CAREER_AGENT_PUBLIC_CORS_ORIGINS", "").split(",")
        if item.strip()
    }
    allowed_origins = sorted(default_allowed_origins | configured_allowed_origins)
    if allowed_origins:
        # Browsers may call only explicitly configured portfolio origins. This
        # is not authentication, but prevents accidentally granting every web
        # page permission to use a paid public-answer endpoint.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )
    configure_observability()
    session_factory = create_session_factory(database_url)
    answer_rate_limiter = PublicAnswerRateLimiter(
        max_requests=int(os.getenv("CAREER_AGENT_PUBLIC_ANSWER_MAX_PER_MINUTE", "12")),
        window_seconds=60.0,
    )

    @app.middleware("http")
    async def rate_limit_public_answers(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/v1/public/evidence/answer":
            allowed, retry_after = answer_rate_limiter.allow(
                public_client_id(
                    request.headers.get("x-forwarded-for"),
                    request.client.host if request.client else None,
                )
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "public answer request limit reached; retry shortly"},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # An explicit database URL is principally used by tests and one-off tools.
    # Do not silently couple those callers to a real provider configured in the
    # process environment (and accidentally incur an API request against a
    # SQLite test database). The default production app still loads both from
    # the environment as one coherent configuration.
    answer_gateway = None
    configured_chat_provider: StructuredChatProvider | None = None
    configured_chat_model: str | None = None
    configured_chat_config: ChatConfig | None = None
    if database_url is None and embedding_provider is None and embedding_model is None:
        try:
            embedding_config = EmbeddingConfig.from_environment()
            chat_config = ChatConfig.from_environment()
        except RuntimeError:
            pass
        else:
            embedding_provider = OpenAICompatibleEmbeddingProvider(embedding_config)
            embedding_model = embedding_config.model
            configured_chat_provider = OpenAICompatibleStructuredChatProvider(chat_config)
            configured_chat_model = chat_config.model
            configured_chat_config = chat_config
            answer_gateway = build_hybrid_public_answer_gateway(
                chat_provider=configured_chat_provider,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                model_name=chat_config.model,
                record_run=record_public_answer_run,
            )
    app.include_router(
        build_public_evidence_router(
            session_factory,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            answer_gateway=answer_gateway,
        )
    )
    owner_token = private_owner_token if private_owner_token is not None else os.getenv("CAREER_AGENT_OWNER_TOKEN")
    private_provider = private_chat_provider
    private_model = private_model_name or configured_chat_model
    if owner_token and private_provider is None and configured_chat_config is not None:
        # JD extraction and the full evidence matrix need the same larger
        # response budget as the local CLI. Keep public HR answers concise.
        private_provider = OpenAICompatibleStructuredChatProvider(
            replace(
                configured_chat_config,
                max_output_tokens=max(configured_chat_config.max_output_tokens, 3000),
                timeout_seconds=max(configured_chat_config.timeout_seconds, 120.0),
            )
        )
    # Fail closed: a configured token without a configured structured model
    # does not create a half-working private route.
    if owner_token and private_provider is not None and private_model is not None:
        app.include_router(
            build_private_studio_router(
                session_factory,
                owner_token=owner_token,
                chat_provider=private_provider,
                model_name=private_model,
            )
        )
    return app
