"""Offline command for embedding reviewed public retrieval chunks."""

from __future__ import annotations

import argparse

from career_agent.db.session import create_database_engine
from career_agent.retrieval.embeddings import (
    EmbeddingConfig,
    OpenAICompatibleEmbeddingProvider,
)
from career_agent.retrieval.vector_store import refresh_public_embeddings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh vectors for changed approved public retrieval chunks."
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    config = EmbeddingConfig.from_environment()
    provider = OpenAICompatibleEmbeddingProvider(config)
    engine = create_database_engine(args.database_url)
    with engine.begin() as connection:
        pending, written = refresh_public_embeddings(
            connection,
            embedding_model=config.model,
            provider=provider,
            batch_size=args.batch_size,
        )
    print(f"embedded {written} of {pending} changed public chunks using {config.model}")


if __name__ == "__main__":
    main()
