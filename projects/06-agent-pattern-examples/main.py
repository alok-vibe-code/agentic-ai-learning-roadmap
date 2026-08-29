"""CLI for Project 06: Agent Pattern Examples."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from patterns.evaluator_optimizer import run_evaluator_optimizer
from patterns.human_in_loop import request_action, simulate_execution
from patterns.parallelization import run_parallel
from patterns.planning import build_plan
from patterns.reflection import run_reflection
from patterns.routing import route_request, run_specialist


def _print_trace(trace) -> None:
    print("\nTrace:")
    for event in trace.events:
        print(
            f"- step={event.step} action={event.action} "
            f"{json.dumps(event.details, ensure_ascii=False)}"
        )
    print(f"- stop_reason={trace.stop_reason}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic examples of six agentic design patterns."
    )
    subparsers = parser.add_subparsers(dest="pattern", required=True)

    reflection = subparsers.add_parser("reflection")
    reflection.add_argument("draft")
    reflection.add_argument("--max-rounds", type=int, default=3)

    planning = subparsers.add_parser("planning")
    planning.add_argument("goal")

    routing = subparsers.add_parser("routing")
    routing.add_argument("request")

    parallel = subparsers.add_parser("parallel")
    parallel.add_argument("tasks", nargs="+")
    parallel.add_argument("--max-workers", type=int, default=4)

    evaluator = subparsers.add_parser("evaluator")
    evaluator.add_argument("candidate")
    evaluator.add_argument("--max-rounds", type=int, default=4)

    hitl = subparsers.add_parser("hitl")
    hitl.add_argument("action")
    hitl.add_argument(
        "--approve",
        action="store_true",
        help="Simulate explicit human approval for medium/high-risk actions.",
    )

    subparsers.add_parser(
        "all",
        help="Run one compact demonstration of every pattern.",
    )
    return parser


def run_all() -> None:
    print("=== Reflection ===")
    result, trace = run_reflection("Agents help")
    print(result)
    print("stop:", trace.stop_reason)

    print("\n=== Planning ===")
    steps, trace = build_plan("Build a small agent evaluation tool")
    for step in steps:
        print(step.id, step.title, "depends_on=", list(step.depends_on))
    print("stop:", trace.stop_reason)

    print("\n=== Routing ===")
    decision, trace = route_request("Calculate 12 * 7")
    print(asdict(decision))
    print(run_specialist(decision.route, "12 * 7"))
    print("stop:", trace.stop_reason)

    print("\n=== Parallelization ===")
    results, trace = run_parallel(["alpha", "beta", "fail:demo"])
    for result in results:
        print(asdict(result))
    print("stop:", trace.stop_reason)

    print("\n=== Evaluator-Optimizer ===")
    result, evaluation, trace = run_evaluator_optimizer("Useful automation")
    print(result)
    print("score:", evaluation.score)
    print("stop:", trace.stop_reason)

    print("\n=== Human-in-the-Loop ===")
    decision, trace = request_action("publish the report", approved=False)
    print(asdict(decision))
    print(simulate_execution(decision))
    print("stop:", trace.stop_reason)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.pattern == "reflection":
        result, trace = run_reflection(args.draft, args.max_rounds)
        print(result)
        _print_trace(trace)
        return 0

    if args.pattern == "planning":
        steps, trace = build_plan(args.goal)
        for step in steps:
            dependencies = ", ".join(step.depends_on) or "none"
            print(f"{step.id}. {step.title} [depends on: {dependencies}]")
        _print_trace(trace)
        return 0

    if args.pattern == "routing":
        decision, trace = route_request(args.request)
        print(
            f"route={decision.route} confidence={decision.confidence:.2f} "
            f"reason={decision.reason}"
        )
        print(run_specialist(decision.route, args.request))
        _print_trace(trace)
        return 0

    if args.pattern == "parallel":
        results, trace = run_parallel(
            args.tasks,
            max_workers=args.max_workers,
        )
        for result in results:
            print(json.dumps(asdict(result), ensure_ascii=False))
        _print_trace(trace)
        return 0

    if args.pattern == "evaluator":
        result, evaluation, trace = run_evaluator_optimizer(
            args.candidate,
            args.max_rounds,
        )
        print(result)
        print(
            f"score={evaluation.score} "
            f"issues={list(evaluation.issues)}"
        )
        _print_trace(trace)
        return 0

    if args.pattern == "hitl":
        decision, trace = request_action(
            args.action,
            approved=args.approve,
        )
        print(json.dumps(asdict(decision), ensure_ascii=False))
        print(simulate_execution(decision))
        _print_trace(trace)
        return 0

    if args.pattern == "all":
        run_all()
        return 0

    parser.error("Unknown pattern.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
