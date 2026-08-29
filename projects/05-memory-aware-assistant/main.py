"""CLI for Project 05: Memory-Aware Assistant."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from assistant import MemoryAwareAssistant
from store import JSONMemoryStore, default_store_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Explicit, privacy-conscious local memory for an educational assistant."
        )
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help=(
            "Optional JSON store path. Default is outside the repository at "
            "~/.agentic-ai-learning-roadmap/project05-memory.json"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    remember = subparsers.add_parser(
        "remember",
        help="Explicitly save or update one non-sensitive memory.",
    )
    remember.add_argument(
        "--category",
        required=True,
        choices=["preference", "project", "workflow", "episode"],
    )
    remember.add_argument("--key", required=True)
    remember.add_argument("--value", required=True)
    remember.add_argument(
        "--ttl-seconds",
        type=int,
        default=None,
        help="Optional expiration time in seconds.",
    )

    recall = subparsers.add_parser(
        "recall",
        help="Search active persistent memories.",
    )
    recall.add_argument("query")
    recall.add_argument("--top-k", type=int, default=5)

    list_command = subparsers.add_parser(
        "list",
        help="List active persistent memories.",
    )
    list_command.add_argument(
        "--category",
        choices=["preference", "project", "workflow", "episode"],
        default=None,
    )

    forget = subparsers.add_parser(
        "forget",
        help="Delete one persistent memory.",
    )
    forget.add_argument(
        "--category",
        required=True,
        choices=["preference", "project", "workflow", "episode"],
    )
    forget.add_argument("--key", required=True)

    clear = subparsers.add_parser(
        "clear",
        help="Clear all persistent memory.",
    )
    clear.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation flag.",
    )

    subparsers.add_parser(
        "purge-expired",
        help="Delete expired memories from the JSON store.",
    )

    subparsers.add_parser(
        "where",
        help="Print the persistent memory file location.",
    )

    subparsers.add_parser(
        "session-demo",
        help="Demonstrate working memory that disappears when the process ends.",
    )

    return parser


def _print_record(record) -> None:
    expiry = record.expires_at or "never"
    print(
        f"[{record.category}] {record.key} = {record.value} "
        f"(expires: {expiry})"
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    store = JSONMemoryStore(args.store)
    assistant = MemoryAwareAssistant(store)

    try:
        if args.command == "remember":
            print(
                assistant.remember(
                    category=args.category,
                    key=args.key,
                    value=args.value,
                    ttl_seconds=args.ttl_seconds,
                )
            )
            return 0

        if args.command == "recall":
            matches = assistant.recall(args.query, top_k=args.top_k)
            if not matches:
                print("No matching active memories.")
                return 0

            for index, match in enumerate(matches, start=1):
                record = match.record
                print(
                    f"{index}. [{record.category}] {record.key} = "
                    f"{record.value} "
                    f"(score: {match.score:.2f}, "
                    f"matched: {', '.join(match.matched_terms)})"
                )
            return 0

        if args.command == "list":
            records = store.list_records(category=args.category)
            if not records:
                print("No active persistent memories.")
                return 0
            for record in records:
                _print_record(record)
            return 0

        if args.command == "forget":
            print(assistant.forget(args.category, args.key))
            return 0

        if args.command == "clear":
            if not args.yes:
                print(
                    "Refusing to clear memory without explicit --yes confirmation.",
                    file=sys.stderr,
                )
                return 2
            print(assistant.clear_persistent_memory())
            return 0

        if args.command == "purge-expired":
            removed = store.purge_expired()
            print(f"Purged {removed} expired memory record(s).")
            return 0

        if args.command == "where":
            print(store.path)
            return 0

        if args.command == "session-demo":
            assistant.working.set("current-task", "Test working memory")
            print(
                "Working memory inside this process:",
                assistant.working.get("current-task"),
            )
            print(
                "Persistent store was not modified. "
                "Run the command again and this working-memory item is recreated "
                "rather than recalled from disk."
            )
            return 0

        parser.error("Unknown command.")
        return 2

    except ValueError as exc:
        print(f"Rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
