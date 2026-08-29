"""CLI for Project 07: Framework Comparison Demo."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from common_task import triage_request
from comparison import capability_matrix, recommend
from models import CAPABILITY_KEYS
from profiles import get_profile, load_profiles


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [
        max(len(str(row[index])) for row in [headers] + rows)
        for index in range(len(headers))
    ]

    def render(row: list[str]) -> str:
        return " | ".join(
            str(value).ljust(widths[index])
            for index, value in enumerate(row)
        )

    print(render(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(render(row))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare agent framework capabilities against the same normalized task."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("matrix", help="Print the framework capability matrix.")

    profile = subparsers.add_parser("profile", help="Show one framework profile.")
    profile.add_argument(
        "framework_id",
        choices=["openai-agents-sdk", "langgraph", "pydantic-ai"],
    )

    recommendation = subparsers.add_parser(
        "recommend",
        help="Filter by hard requirements and rank by preferences.",
    )
    recommendation.add_argument(
        "--require",
        nargs="*",
        default=[],
        help="Hard capability requirements.",
    )
    recommendation.add_argument(
        "--prefer",
        nargs="*",
        default=[],
        help="Soft capability preferences.",
    )

    task = subparsers.add_parser(
        "task",
        help="Run the framework-neutral support-triage task.",
    )
    task.add_argument("request")

    compare_task = subparsers.add_parser(
        "compare-task",
        help="Show how the same task maps into each framework.",
    )
    compare_task.add_argument("request")

    subparsers.add_parser(
        "capabilities",
        help="List accepted capability names for recommendation queries.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    profiles = load_profiles()

    if args.command == "matrix":
        headers = ["capability"] + [profile.name for profile in profiles]
        print_table(headers, capability_matrix(profiles))
        return 0

    if args.command == "profile":
        profile = get_profile(args.framework_id, profiles)
        print(json.dumps({
            "id": profile.id,
            "name": profile.name,
            "kind": profile.kind,
            "verified_date": profile.verified_date,
            "docs_url": profile.docs_url,
            "install": profile.install,
            "runtime_note": profile.runtime_note,
            "capabilities": profile.capabilities,
            "task_mapping": profile.task_mapping,
            "strengths": profile.strengths,
            "watch_items": profile.watch_items,
        }, indent=2, ensure_ascii=False))
        return 0

    if args.command == "recommend":
        results = recommend(
            profiles,
            required=args.require,
            preferred=args.prefer,
        )
        rows = []
        for result in results:
            rows.append([
                result.framework_name,
                "yes" if result.eligible else "no",
                str(result.preference_score),
                ", ".join(result.missing_requirements) or "-",
                ", ".join(result.matched_preferences) or "-",
            ])
        print_table(
            [
                "framework",
                "eligible",
                "preference_score",
                "missing_required",
                "matched_preferences",
            ],
            rows,
        )
        print(
            "\nNote: this is a transparent rule-based filter, "
            "not a claim that one framework is universally best."
        )
        return 0

    if args.command == "task":
        result = triage_request(args.request)
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
        return 0

    if args.command == "compare-task":
        result = triage_request(args.request)
        print("Normalized task result:")
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
        print("\nFramework mappings:")
        for profile in profiles:
            print(f"\n{profile.name}")
            print("-" * len(profile.name))
            for key, value in profile.task_mapping.items():
                print(f"{key}: {value}")
        return 0

    if args.command == "capabilities":
        for capability in CAPABILITY_KEYS:
            print(capability)
        return 0

    parser.error("Unknown command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
