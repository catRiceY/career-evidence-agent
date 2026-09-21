"""Run the reviewed public retrieval eval set against live hybrid retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from career_agent.db.session import create_database_engine
from career_agent.retrieval.embeddings import (
    EmbeddingConfig,
    OpenAICompatibleEmbeddingProvider,
)
from career_agent.retrieval.evaluation import (
    evaluate_retrieval_cases,
    load_retrieval_eval_cases,
)
from career_agent.retrieval.hybrid_search import search_public_hybrid_evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate live public hybrid retrieval against approved gold claims."
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).resolve().parents[5]
        / "evals"
        / "retrieval"
        / "public-baseline.json",
    )
    args = parser.parse_args()

    config = EmbeddingConfig.from_environment()
    provider = OpenAICompatibleEmbeddingProvider(config)
    engine = create_database_engine(args.database_url)
    with Session(engine) as session:
        results = evaluate_retrieval_cases(
            load_retrieval_eval_cases(args.cases),
            retrieve=lambda query, limit: [
                item.claim_id
                for item in search_public_hybrid_evidence(
                    session,
                    query,
                    embedding_model=config.model,
                    provider=provider,
                    limit=limit,
                )
            ],
        )
    payload = {
        "retriever": "public_hybrid_rrf",
        "embedding_model": config.model,
        "mean_recall_at_k": sum(result.recall_at_k for result in results) / len(results),
        "cases": [
            {
                "id": result.case_id,
                "expected_claim_ids": result.expected_claim_ids,
                "retrieved_claim_ids": result.retrieved_claim_ids,
                "recall_at_k": result.recall_at_k,
            }
            for result in results
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
