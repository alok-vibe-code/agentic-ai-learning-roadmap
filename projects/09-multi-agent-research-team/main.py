"""CLI for Project 09."""

from __future__ import annotations
import argparse
import json

from comparison import compare_architectures
from coordinator import MultiAgentResearchTeam
from search import load_sources
from single_agent import SingleAgentResearcher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a deterministic multi-agent research team and compare it "
            "with a simpler single-agent baseline."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    team = subparsers.add_parser("team")
    team.add_argument("question")
    team.add_argument("--trace", action="store_true")

    single = subparsers.add_parser("single")
    single.add_argument("question")

    compare = subparsers.add_parser("compare")
    compare.add_argument("question")

    subparsers.add_parser("sources")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "team":
        result = MultiAgentResearchTeam().run(args.question)
        print(result.report or "# No approved report\n")
        print("## Run Metadata")
        print(json.dumps({
            "status": result.status,
            "metrics": result.metrics,
            "failures": result.failures,
        }, indent=2))

        if args.trace:
            print("\n## Coordination Trace")
            for message in result.trace:
                print(
                    f"{message.sender} -> {message.recipient} "
                    f"[{message.kind}]: {message.content}"
                )
        return 0 if result.status == "approved" else 1

    if args.command == "single":
        result = SingleAgentResearcher().run(args.question)
        print(result.report)
        print("## Run Metadata")
        print(json.dumps(result.metrics, indent=2))
        return 0

    if args.command == "compare":
        print(json.dumps(
            compare_architectures(args.question),
            indent=2,
            ensure_ascii=False,
        ))
        return 0

    if args.command == "sources":
        for source in load_sources():
            print(f"{source.id} | {source.title} | {source.url}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
