"""Evaluator-optimizer pattern: measure -> improve -> repeat within bounds."""

from __future__ import annotations

import re
from dataclasses import dataclass

from models import PatternTrace


@dataclass(frozen=True)
class Evaluation:
    score: int
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.score >= 85


def evaluate_summary(text: str) -> Evaluation:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return Evaluation(0, ("empty",))

    issues: list[str] = []
    words = re.findall(r"[A-Za-z0-9'-]+", normalized)

    if len(words) < 12:
        issues.append("insufficient_detail")
    if len(words) > 45:
        issues.append("too_verbose")
    if not re.search(r"\b(agent|agentic|workflow|system|pattern)\b", normalized, re.I):
        issues.append("missing_subject")
    if not re.search(r"\b(because|by|using|through|while)\b", normalized, re.I):
        issues.append("missing_mechanism")
    if normalized[-1:] not in ".!?":
        issues.append("missing_punctuation")

    score = max(0, 100 - 18 * len(issues))
    return Evaluation(score, tuple(issues))


def optimize_summary(text: str, evaluation: Evaluation) -> str:
    result = " ".join(text.strip().split())

    if "missing_subject" in evaluation.issues:
        result = "An agentic workflow " + result[:1].lower() + result[1:]

    if "insufficient_detail" in evaluation.issues:
        if result and result[-1:] in ".!?":
            result = result[:-1]
        result += (
            " by making its control flow, stopping conditions, "
            "and quality checks explicit"
        )

    if "missing_mechanism" in evaluation.issues and not re.search(
        r"\b(because|by|using|through|while)\b", result, re.I
    ):
        if result and result[-1:] in ".!?":
            result = result[:-1]
        result += " by applying a measurable feedback loop"

    if "too_verbose" in evaluation.issues:
        words = result.split()
        result = " ".join(words[:40]).rstrip(",;:")

    result = " ".join(result.split()).strip()
    if result and result[-1:] not in ".!?":
        result += "."
    return result


def run_evaluator_optimizer(
    candidate: str,
    max_rounds: int = 4,
) -> tuple[str, Evaluation, PatternTrace]:
    if max_rounds < 1:
        raise ValueError("max_rounds must be >= 1.")

    current = candidate
    trace = PatternTrace(pattern="evaluator-optimizer")

    for step in range(1, max_rounds + 1):
        evaluation = evaluate_summary(current)
        trace.add(
            step,
            "evaluate",
            score=evaluation.score,
            issues=list(evaluation.issues),
        )

        if evaluation.passed:
            trace.stop_reason = "quality_threshold_met"
            return current, evaluation, trace

        improved = optimize_summary(current, evaluation)
        trace.add(step, "optimize", changed=improved != current)
        current = improved

    final = evaluate_summary(current)
    trace.add(
        max_rounds + 1,
        "final_evaluate",
        score=final.score,
        issues=list(final.issues),
    )
    trace.stop_reason = (
        "quality_threshold_met"
        if final.passed
        else "max_rounds_reached"
    )
    return current, final, trace
