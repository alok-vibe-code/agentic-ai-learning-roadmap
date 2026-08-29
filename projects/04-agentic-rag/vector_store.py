"""Small in-memory TF-IDF vector store implemented with the Python standard library."""

from __future__ import annotations

import math
import re
from collections import Counter

from models import Chunk, RetrievalHit


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "does", "for",
    "from", "how", "in", "into", "is", "it", "of", "on", "or", "that", "the",
    "their", "this", "to", "what", "when", "which", "with"
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]*", text.casefold())
    return [
        token
        for token in tokens
        if token not in _STOPWORDS and len(token) > 1
    ]


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0

    dot = sum(value * right.get(term, 0.0) for term, value in left.items())
    if dot == 0:
        return 0.0

    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class LocalVectorStore:
    """Index Chunk objects as sparse TF-IDF vectors."""

    def __init__(self, chunks: list[Chunk]):
        if not chunks:
            raise ValueError("Vector store requires at least one chunk.")
        self.chunks = chunks
        self.document_frequency = self._build_document_frequency(chunks)
        self.total_chunks = len(chunks)
        self.chunk_vectors = {
            chunk.id: self._vectorize_tokens(tokenize(self._searchable_text(chunk)))
            for chunk in chunks
        }

    @staticmethod
    def _searchable_text(chunk: Chunk) -> str:
        return f"{chunk.title} {' '.join(chunk.tags)} {chunk.text}"

    @staticmethod
    def _build_document_frequency(chunks: list[Chunk]) -> Counter:
        frequency: Counter = Counter()
        for chunk in chunks:
            frequency.update(set(tokenize(LocalVectorStore._searchable_text(chunk))))
        return frequency

    def _idf(self, term: str) -> float:
        # Smoothed IDF.
        return math.log(
            (1 + self.total_chunks) /
            (1 + self.document_frequency.get(term, 0))
        ) + 1.0

    def _vectorize_tokens(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = len(tokens)
        return {
            term: (count / total) * self._idf(term)
            for term, count in counts.items()
        }

    def search(self, query: str, top_k: int = 4) -> list[RetrievalHit]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1.")

        query_tokens = tokenize(query)
        query_vector = self._vectorize_tokens(query_tokens)
        query_terms = set(query_tokens)
        hits: list[RetrievalHit] = []

        for chunk in self.chunks:
            vector = self.chunk_vectors[chunk.id]
            score = _cosine_similarity(query_vector, vector)
            if score <= 0:
                continue

            searchable_terms = set(tokenize(self._searchable_text(chunk)))
            matched = tuple(sorted(query_terms & searchable_terms))
            hits.append(
                RetrievalHit(
                    chunk=chunk,
                    score=score,
                    matched_terms=matched,
                )
            )

        hits.sort(
            key=lambda hit: (
                -hit.score,
                hit.chunk.title.casefold(),
                hit.chunk.position,
            )
        )
        return hits[:top_k]
