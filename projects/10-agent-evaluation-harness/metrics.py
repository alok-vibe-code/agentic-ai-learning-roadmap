"""Aggregate evaluation metrics."""

from __future__ import annotations
from statistics import mean
from models import CaseResult


def _check_rate(results: list[CaseResult], check_name: str) -> float:
    values = [
        check.passed
        for result in results
        for check in result.checks
        if check.name == check_name
    ]
    return round(sum(values) / len(values), 4) if values else 0.0


def aggregate_metrics(results: list[CaseResult]) -> dict[str, float]:
    if not results:
        raise ValueError("Cannot aggregate an empty result set.")

    return {
        "case_pass_rate": round(
            sum(result.passed for result in results) / len(results), 4
        ),
        "task_completion_accuracy": _check_rate(
            results, "task_completion"
        ),
        "tool_selection_accuracy": _check_rate(
            results, "tool_selection"
        ),
        "content_check_pass_rate": _check_rate(
            results, "content_requirements"
        ),
        "citation_pass_rate": _check_rate(
            results, "citation_requirement"
        ),
        "groundedness_pass_rate": _check_rate(
            results, "groundedness"
        ),
        "trace_integrity_pass_rate": _check_rate(
            results, "trace_integrity"
        ),
        "failure_rate": round(
            sum(result.run.status == "failed" for result in results)
            / len(results),
            4,
        ),
        "average_latency_ms": round(
            mean(result.run.latency_ms for result in results), 4
        ),
        "estimated_tokens": float(
            sum(result.run.estimated_tokens for result in results)
        ),
        "reported_cost_usd": round(
            sum(result.run.cost_usd for result in results), 6
        ),
    }
