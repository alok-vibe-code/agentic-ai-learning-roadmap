"""Human- and machine-readable report rendering."""

from __future__ import annotations
import json
from dataclasses import asdict
from models import EvaluationReport


def to_json(report: EvaluationReport) -> str:
    return json.dumps(asdict(report), indent=2, ensure_ascii=False)


def to_markdown(report: EvaluationReport) -> str:
    lines = [
        "# Agent Evaluation Report",
        "",
        f"- **Suite version:** {report.suite_version}",
        f"- **Candidate:** {report.candidate}",
        f"- **Cases:** {len(report.case_results)}",
        f"- **Pass rate:** {report.metrics['case_pass_rate']:.1%}",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]

    for name, value in report.metrics.items():
        lines.append(f"| {name} | {value} |")

    lines.extend([
        "",
        "## Cases",
        "",
        "| Case | Passed | Score | Status | Tools | Citations |",
        "|---|---|---:|---|---|---|",
    ])

    for result in report.case_results:
        tools = ", ".join(call.name for call in result.run.tool_calls) or "none"
        citations = ", ".join(result.run.citations) or "none"
        lines.append(
            f"| {result.case_id} | {'✅' if result.passed else '❌'} | "
            f"{result.score:.2f} | {result.run.status} | {tools} | {citations} |"
        )

    lines.extend(["", "## Regression", ""])
    if report.regression_passed is None:
        lines.append("Not checked.")
    elif report.regression_passed:
        lines.append("✅ All configured baseline thresholds passed.")
    else:
        lines.append("❌ Regression detected:")
        for failure in report.regression_failures:
            lines.append(f"- {failure}")

    return "\n".join(lines) + "\n"
