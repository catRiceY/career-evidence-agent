"""Load and evaluate public Answer Gateway status regression cases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class PublicAnswerEvalCase:
    id: str
    question: str
    expected_status: str
    purpose: str


@dataclass(frozen=True)
class PublicAnswerEvalResult:
    case_id: str
    expected_status: str
    actual_status: str
    passed: bool


def load_public_answer_eval_cases(path: Path) -> list[PublicAnswerEvalCase]:
    return [PublicAnswerEvalCase(**item) for item in json.loads(path.read_text("utf-8"))]


def evaluate_public_answer_statuses(
    cases: list[PublicAnswerEvalCase], *, ask: Callable[[str], str]
) -> list[PublicAnswerEvalResult]:
    return [
        PublicAnswerEvalResult(
            case_id=case.id,
            expected_status=case.expected_status,
            actual_status=(actual_status := ask(case.question)),
            passed=actual_status == case.expected_status,
        )
        for case in cases
    ]
