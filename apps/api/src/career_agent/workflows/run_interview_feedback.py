"""Review one locally saved mock-interview answer against its linked evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from career_agent.db.session import create_database_engine, database_url
from career_agent.generation.chat import ChatConfig, OpenAICompatibleStructuredChatProvider
from career_agent.harness.run_manifest import record_private_interview_feedback_run
from career_agent.workflows.interview_feedback import (
    InterviewAnswerFeedbackWorkflow,
    StructuredInterviewAnswerReviewer,
)
from career_agent.workflows.mock_interview import MockInterviewPlan


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check one mock-interview answer against the plan's approved evidence."
    )
    parser.add_argument("--plan-file", type=Path, required=True,
                        help="JSON output from run_practice_session, kept locally.")
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--answer-file", type=Path, required=True,
                        help="Plain-text candidate answer; it is hashed, not saved in the audit record.")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--database-url", default=None)
    return parser.parse_args()


def _load_plan(path: Path) -> MockInterviewPlan:
    raw = json.loads(path.read_text(encoding="utf-8"))
    # Accept either the full practice-session JSON or only its plan object.
    if isinstance(raw, dict) and "mock_interview_plan" in raw:
        raw = raw["mock_interview_plan"]
    return MockInterviewPlan.model_validate(raw)


def main() -> None:
    args = _parse_args()
    answer = args.answer_file.read_text(encoding="utf-8").strip()
    if not answer:
        raise ValueError("answer file is empty")
    configured = ChatConfig.from_environment()
    config = replace(configured, max_output_tokens=max(configured.max_output_tokens, 1200), timeout_seconds=90.0)
    workflow = InterviewAnswerFeedbackWorkflow(StructuredInterviewAnswerReviewer(
        OpenAICompatibleStructuredChatProvider(config)
    ))
    started = perf_counter()
    feedback = workflow.run(plan=_load_plan(args.plan_file), question_id=args.question_id,
                            candidate_answer=answer, user_id=args.user_id)
    engine = create_database_engine(args.database_url or database_url())
    with Session(engine) as session:
        run_id = record_private_interview_feedback_run(
            session, question_id=args.question_id, candidate_answer=answer,
            model_name=config.model, feedback=feedback,
            latency_ms=round((perf_counter() - started) * 1000),
        )
    print(json.dumps(feedback.model_copy(update={"run_id": run_id}).model_dump(mode="json"),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
