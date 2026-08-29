"""Small deterministic lexical search engine for the bundled source corpus."""

from __future__ import annotations

import json
import re
from pathlib import Path

from models import SearchHit, Source


_STOPWORDS = {
    "a", "ai", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "into", "is", "it", "of", "on", "or", "the", "their", "to", "used",
    "uses", "using", "what", "which", "with"
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]*", text.casefold())
    return [token for token in tokens if token not in _STOPWORDS and len(token) > 1]


class LocalCorpus:
    def __init__(self, sources: list[Source]):
        if not sources:
            raise ValueError("Corpus must contain at least one source.")
        self.sources = sources

    @classmethod
    def from_json(cls, path: str | Path) -> "LocalCorpus":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        sources: list[Source] = []

        for item in raw:
            required = {
                "id", "title", "url", "source_type", "year",
                "tags", "summary", "key_points"
            }
            missing = required.difference(item)
            if missing:
                raise ValueError(
                    f"Source {item.get('id', '<unknown>')} is missing: {sorted(missing)}"
                )

            sources.append(
                Source(
                    id=str(item["id"]),
                    title=str(item["title"]),
                    url=str(item["url"]),
                    source_type=str(item["source_type"]),
                    year=int(item["year"]),
                    tags=tuple(str(tag).casefold() for tag in item["tags"]),
                    summary=str(item["summary"]),
                    key_points=tuple(str(point) for point in item["key_points"]),
                )
            )

        ids = [source.id for source in sources]
        if len(ids) != len(set(ids)):
            raise ValueError("Source IDs must be unique.")

        return cls(sources)

    def search(self, query: str, top_k: int = 4) -> list[SearchHit]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1.")

        query_terms = set(tokenize(query))
        if not query_terms:
            return []

        hits: list[SearchHit] = []

        for source in self.sources:
            title_terms = set(tokenize(source.title))
            tag_terms = set(tokenize(" ".join(source.tags)))
            summary_terms = set(tokenize(source.summary))
            point_terms = set(tokenize(" ".join(source.key_points)))

            matched = (
                (query_terms & title_terms)
                | (query_terms & tag_terms)
                | (query_terms & summary_terms)
                | (query_terms & point_terms)
            )
            if not matched:
                continue

            score = 0.0
            score += 4.0 * len(query_terms & title_terms)
            score += 3.0 * len(query_terms & tag_terms)
            score += 1.5 * len(query_terms & summary_terms)
            score += 1.0 * len(query_terms & point_terms)

            # Small bonus for breadth of matching rather than repeated terms.
            score += 0.25 * len(matched)

            hits.append(
                SearchHit(
                    source=source,
                    score=score,
                    matched_terms=tuple(sorted(matched)),
                )
            )

        hits.sort(key=lambda item: (-item.score, item.source.title.casefold()))
        return hits[:top_k]
