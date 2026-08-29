"""Data models used by Project 04: Agentic RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    source_url: str
    tags: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    title: str
    source_url: str
    tags: tuple[str, ...]
    text: str
    position: int


@dataclass(frozen=True)
class RetrievalHit:
    chunk: Chunk
    score: float
    matched_terms: tuple[str, ...]


@dataclass
class RAGState:
    question: str
    retrieval_needed: bool
    max_rounds: int
    round: int = 0
    queries: list[str] = field(default_factory=list)
    hits: list[RetrievalHit] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str | None = None
    sufficient: bool = False

    @property
    def unique_chunk_ids(self) -> set[str]:
        return {hit.chunk.id for hit in self.hits}

    @property
    def unique_document_ids(self) -> set[str]:
        return {hit.chunk.document_id for hit in self.hits}
