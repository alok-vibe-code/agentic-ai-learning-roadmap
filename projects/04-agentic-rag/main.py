"""CLI for Project 04: Agentic RAG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentic_rag import AgenticRAG
from chunking import build_chunks, load_documents
from vector_store import LocalVectorStore


DEFAULT_QUESTION = "What makes Agentic RAG different from a fixed RAG pipeline?"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a zero-cost Agentic RAG demo against a bundled knowledge base."
        )
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=DEFAULT_QUESTION,
        help="Question to answer from the bundled knowledge base.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Maximum retrieval rounds. Default: 3.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Chunks retrieved per round. Default: 4.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print routing, rewriting, retrieval, and evidence checks.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()

        knowledge_path = Path(__file__).parent / "data" / "knowledge_base.json"
        documents = load_documents(knowledge_path)
        chunks = build_chunks(documents, chunk_size=70, overlap=15)
        store = LocalVectorStore(chunks)

        agent = AgenticRAG(
            store=store,
            max_rounds=args.max_rounds,
            top_k=args.top_k,
        )
        state, answer = agent.run(args.question)

        if args.trace:
            for event in state.events:
                print(
                    "[rag]",
                    json.dumps(event, ensure_ascii=False),
                    file=sys.stderr,
                )

        print(answer)
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
