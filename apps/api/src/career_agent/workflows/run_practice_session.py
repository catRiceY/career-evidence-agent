"""Run a local JD matrix followed by an evidence-aware interview plan."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from career_agent.db.session import create_database_engine, database_url
from career_agent.generation.chat import ChatConfig, OpenAICompatibleStructuredChatProvider
from career_agent.harness.run_manifest import (
    record_private_jd_match_run,
    record_private_mock_interview_run,
)
from career_agent.workflows.jd_match import (
    DatabasePrivateEvidenceFinder,
    JDMatchWorkflow,
    StructuredJDRequirementExtractor,
    StructuredJDMatrixAssessor,
)
from career_agent.workflows.mock_interview import (
    MockInterviewPlanWorkflow,
    StructuredInterviewQuestionGenerator,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local JD evidence matrix followed by a mock-interview plan."
    )
    parser.add_argument("--jd-file", type=Path, required=True)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--user-id", required=True)
    parser.add_argument(
        "--thread-id",
        required=True,
        help="Stable prefix; the command derives separate JD and interview IDs.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    jd_text = args.jd_file.read_text(encoding="utf-8").strip()
    if not jd_text:
        raise ValueError("JD file is empty")

    configured = ChatConfig.from_environment()
    chat_config = replace(configured, max_output_tokens=max(configured.max_output_tokens, 3000), timeout_seconds=120.0)
    chat_provider = OpenAICompatibleStructuredChatProvider(chat_config)
    engine = create_database_engine(args.database_url or database_url())
    with Session(engine) as session:
        jd_started_at = perf_counter()
        jd_result = JDMatchWorkflow(
            extractor=StructuredJDRequirementExtractor(chat_provider),
            evidence_finder=DatabasePrivateEvidenceFinder(session),
            matrix_assessor=StructuredJDMatrixAssessor(chat_provider),
        ).run(
            jd_text=jd_text,
            user_id=args.user_id,
            thread_id=f"{args.thread_id}:jd",
        )
        jd_run_id = record_private_jd_match_run(
            session,
            jd_text=jd_text,
            model_name=chat_config.model,
            result=jd_result,
            latency_ms=round((perf_counter() - jd_started_at) * 1000),
        )
        jd_result = jd_result.model_copy(update={"run_id": jd_run_id})

        plan_started_at = perf_counter()
        plan = MockInterviewPlanWorkflow(
            StructuredInterviewQuestionGenerator(chat_provider)
        ).run(
            jd_result=jd_result,
            user_id=args.user_id,
            thread_id=f"{args.thread_id}:interview",
        )
        interview_run_id = record_private_mock_interview_run(
            session,
            session_label=args.thread_id,
            model_name=chat_config.model,
            plan=plan,
            latency_ms=round((perf_counter() - plan_started_at) * 1000),
        )
        plan = plan.model_copy(update={"run_id": interview_run_id})

    print(
        json.dumps(
            {
                "jd_matrix": jd_result.model_dump(mode="json"),
                "mock_interview_plan": plan.model_dump(mode="json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
