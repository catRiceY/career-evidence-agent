"""Run the private JD evidence-matrix workflow from a local terminal.

This is intentionally a local developer entry point, not an HTTP endpoint.
It is useful while the future Career Studio authentication boundary is still
being designed. The JD and selected approved claim text are sent to the
configured model provider; the result is printed locally. Local execution is
not offline execution. Never supply material disallowed for that provider.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from career_agent.db.session import create_database_engine, database_url
from career_agent.generation.chat import ChatConfig, OpenAICompatibleStructuredChatProvider
from career_agent.harness.run_manifest import record_private_jd_match_run
from career_agent.workflows.jd_match import (
    DatabasePrivateEvidenceFinder,
    JDMatchWorkflow,
    StructuredJDRequirementExtractor,
    StructuredJDMatrixAssessor,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a private JD-to-evidence matching matrix locally."
    )
    parser.add_argument(
        "--jd-file",
        type=Path,
        required=True,
        help="UTF-8 plain-text file containing one job description.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional SQLAlchemy URL; otherwise CAREER_AGENT_DATABASE_URL is used.",
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="Owner identity recorded in the workflow request (for example: evan).",
    )
    parser.add_argument(
        "--thread-id",
        required=True,
        help="Stable ID for this resumable local JD analysis run.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    jd_text = args.jd_file.read_text(encoding="utf-8").strip()
    if not jd_text:
        raise ValueError("JD file is empty")

    engine = create_database_engine(args.database_url or database_url())
    with Session(engine) as session:
        configured = ChatConfig.from_environment()
        chat_config = replace(configured, max_output_tokens=max(configured.max_output_tokens, 3000), timeout_seconds=120.0)
        chat_provider = OpenAICompatibleStructuredChatProvider(chat_config)
        extractor = StructuredJDRequirementExtractor(
            chat_provider
        )
        workflow = JDMatchWorkflow(
            extractor=extractor,
            evidence_finder=DatabasePrivateEvidenceFinder(session),
            matrix_assessor=StructuredJDMatrixAssessor(chat_provider),
        )
        started_at = perf_counter()
        result = workflow.run(
            jd_text=jd_text,
            user_id=args.user_id,
            thread_id=args.thread_id,
        )
        run_id = record_private_jd_match_run(
            session,
            jd_text=jd_text,
            model_name=chat_config.model,
            result=result,
            latency_ms=round((perf_counter() - started_at) * 1000),
        )
        result = result.model_copy(update={"run_id": run_id})

    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
