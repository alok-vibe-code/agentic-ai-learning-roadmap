"""CLI for Project 10: Agent Evaluation Harness."""

from __future__ import annotations
import argparse

from cases import load_cases
from demo_agent import DemoAgent
from evaluator import evaluate_case
from metrics import aggregate_metrics
from models import EvaluationReport
from regression import check_regression, load_baseline
from reporters import to_json, to_markdown


SUITE_VERSION = "1.0"


def run_suite(candidate: str, *, regression: bool) -> EvaluationReport:
    agent = DemoAgent(candidate)
    cases = load_cases()

    results = [
        evaluate_case(case, agent.run(case.query))
        for case in cases
    ]
    metrics = aggregate_metrics(results)

    regression_passed = None
    failures = ()
    if regression:
        regression_passed, failures = check_regression(
            metrics,
            load_baseline(),
        )

    return EvaluationReport(
        suite_version=SUITE_VERSION,
        candidate=candidate,
        case_results=tuple(results),
        metrics=metrics,
        regression_passed=regression_passed,
        regression_failures=failures,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic agent behavior and inspect traces."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument(
        "--candidate",
        choices=["good", "broken"],
        default="good",
    )
    evaluate.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
    )
    evaluate.add_argument(
        "--regression",
        action="store_true",
        help="Apply the versioned baseline thresholds.",
    )

    case = sub.add_parser("case")
    case.add_argument("case_id")
    case.add_argument(
        "--candidate",
        choices=["good", "broken"],
        default="good",
    )

    trace = sub.add_parser("trace")
    trace.add_argument("case_id")
    trace.add_argument(
        "--candidate",
        choices=["good", "broken"],
        default="good",
    )

    sub.add_parser("cases")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "cases":
        for case in load_cases():
            print(
                f"{case.id} | status={case.expected_status} | "
                f"tool={case.expected_tool}"
            )
        return 0

    if args.command in {"case", "trace"}:
        cases = {case.id: case for case in load_cases()}
        if args.case_id not in cases:
            print(f"Unknown case: {args.case_id}")
            return 2

        case = cases[args.case_id]
        run = DemoAgent(args.candidate).run(case.query)

        if args.command == "case":
            result = evaluate_case(case, run)
            print(f"case={result.case_id}")
            print(f"passed={result.passed}")
            print(f"score={result.score}")
            for check in result.checks:
                print(
                    f"{'PASS' if check.passed else 'FAIL'} "
                    f"{check.name}: {check.detail}"
                )
            return 0 if result.passed else 1

        for event in run.trace:
            print(
                f"{event.sequence:02d} "
                f"{event.trace_id} "
                f"{event.span_id} "
                f"parent={event.parent_span_id} "
                f"{event.kind}:{event.name} "
                f"{event.attributes}"
            )
        return 0

    report = run_suite(
        args.candidate,
        regression=args.regression,
    )

    if args.format == "json":
        print(to_json(report))
    else:
        print(to_markdown(report))

    if args.regression and report.regression_passed is False:
        return 1

    return 0 if report.metrics["case_pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
