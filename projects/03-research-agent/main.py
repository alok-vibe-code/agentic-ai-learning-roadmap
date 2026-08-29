"""CLI for Project 03: zero-cost bounded Research Agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research_agent import ResearchAgent
from search import LocalCorpus


DEFAULT_QUESTION = (
    "Compare approaches used by major Agentic AI frameworks and SDKs."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a bounded research agent against the bundled educational source corpus."
        )
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=DEFAULT_QUESTION,
        help="Research question. A framework-comparison example is used if omitted.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=6,
        help="Maximum number of research/search steps. Default: 6.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print the agent's step-by-step state transitions to stderr.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        corpus_path = Path(__file__).parent / "data" / "sources.json"
        corpus = LocalCorpus.from_json(corpus_path)

        agent = ResearchAgent(
            corpus=corpus,
            max_steps=args.max_steps,
            top_k=4,
        )
        state, report = agent.run(args.question)

        if args.trace:
            for event in state.events:
                print(
                    "[agent]",
                    json.dumps(event, ensure_ascii=False),
                    file=sys.stderr,
                )

        print(report)
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
