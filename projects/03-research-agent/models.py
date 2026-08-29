"""Data models for the zero-cost Research Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    source_type: str
    year: int
    tags: tuple[str, ...]
    summary: str
    key_points: tuple[str, ...]


@dataclass(frozen=True)
class SearchHit:
    source: Source
    score: float
    matched_terms: tuple[str, ...]


@dataclass
class Evidence:
    source: Source
    score: float
    query: str
    matched_terms: tuple[str, ...]


@dataclass
class ResearchState:
    question: str
    plan: list[str]
    required_facets: list[str]
    pending_queries: list[str]
    max_steps: int
    step: int = 0
    searched_queries: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str | None = None

    @property
    def source_ids(self) -> set[str]:
        return {item.source.id for item in self.evidence}

    @property
    def covered_tags(self) -> set[str]:
        tags: set[str] = set()
        for item in self.evidence:
            tags.update(item.source.tags)
        return tags
