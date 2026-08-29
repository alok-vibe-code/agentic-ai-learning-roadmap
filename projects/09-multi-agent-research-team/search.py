"""Deterministic local corpus search used by both architectures."""

from __future__ import annotations
import json
import re
from pathlib import Path
from models import Source

DATA_PATH = Path(__file__).resolve().parent / "data" / "sources.json"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "their",
    "this", "to", "use", "what", "when", "which", "with",
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9-]+", text.casefold())
        if token not in STOPWORDS and len(token) > 1
    }


def load_sources(path: str | Path | None = None) -> list[Source]:
    source_path = Path(path) if path else DATA_PATH
    payload = json.loads(source_path.read_text(encoding="utf-8"))

    if not isinstance(payload, list) or not payload:
        raise ValueError("Source corpus must be a non-empty JSON list.")

    sources: list[Source] = []
    seen_ids: set[str] = set()

    for item in payload:
        source_id = str(item["id"]).strip()
        if not source_id or source_id in seen_ids:
            raise ValueError("Source IDs must be non-empty and unique.")
        seen_ids.add(source_id)

        content = " ".join(str(item["content"]).split())
        if not content:
            raise ValueError(f"Source {source_id} has empty content.")

        sources.append(
            Source(
                id=source_id,
                title=" ".join(str(item["title"]).split()),
                url=str(item["url"]).strip(),
                tags=tuple(str(tag).casefold() for tag in item["tags"]),
                content=content,
            )
        )

    return sources


def sentence_split(text: str) -> list[str]:
    sentences = [
        " ".join(part.split())
        for part in re.split(r"(?<=[.!?])\s+", text.strip())
        if part.strip()
    ]
    return sentences or [text.strip()]


def score_source(query: str, source: Source) -> float:
    query_terms = tokenize(query)
    if not query_terms:
        return 0.0

    title_terms = tokenize(source.title)
    tag_terms = set(source.tags)
    content_terms = tokenize(source.content)

    return (
        len(query_terms & title_terms) * 3.0
        + len(query_terms & tag_terms) * 2.0
        + len(query_terms & content_terms) * 1.0
    )


def best_snippet(query: str, source: Source) -> str:
    query_terms = tokenize(query)
    sentences = sentence_split(source.content)
    scored = [
        (len(query_terms & tokenize(sentence)), -index, sentence)
        for index, sentence in enumerate(sentences)
    ]
    scored.sort(reverse=True)
    return scored[0][2]


def search_sources(
    query: str,
    *,
    top_k: int = 3,
    sources: list[Source] | None = None,
) -> list[tuple[Source, float, str]]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    corpus = sources or load_sources()
    scored: list[tuple[float, str, Source, str]] = []

    for source in corpus:
        score = score_source(query, source)
        if score <= 0:
            continue
        scored.append(
            (score, source.id, source, best_snippet(query, source))
        )

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        (source, score, snippet)
        for score, _, source, snippet in scored[:top_k]
    ]
