"""Run live public-answer safety regression cases against local infrastructure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from career_agent.db.session import create_database_engine
from career_agent.evals.public_answer import (
    evaluate_public_answer_statuses,
    load_public_answer_eval_cases,
)
from career_agent.generation.chat import ChatConfig, OpenAICompatibleStructuredChatProvider
from career_agent.harness.public_answer import build_hybrid_public_answer_gateway
from career_agent.harness.run_manifest import record_public_answer_run
from career_agent.retrieval.embeddings import (
    EmbeddingConfig,
    OpenAICompatibleEmbeddingProvider,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run live public Answer Gateway safety regression cases."
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).resolve().parents[5]
        / "evals"
        / "answers"
        / "public-answer-safety.json",
    )
    args = parser.parse_args()

    embedding_config = EmbeddingConfig.from_environment()
    chat_config = ChatConfig.from_environment()
    gateway = build_hybrid_public_answer_gateway(
        chat_provider=OpenAICompatibleStructuredChatProvider(chat_config),
        embedding_provider=OpenAICompatibleEmbeddingProvider(embedding_config),
        embedding_model=embedding_config.model,
        model_name=chat_config.model,
        record_run=record_public_answer_run,
    )
    engine = create_database_engine(args.database_url)
    with Session(engine) as session:
        results = evaluate_public_answer_statuses(
            load_public_answer_eval_cases(args.cases),
            ask=lambda question: gateway.answer(session, question).status,
        )
    payload = {
        "suite": "public_answer_safety",
        "passed": all(result.passed for result in results),
        "cases": [
            {
                "id": result.case_id,
                "expected_status": result.expected_status,
                "actual_status": result.actual_status,
                "passed": result.passed,
            }
            for result in results
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
