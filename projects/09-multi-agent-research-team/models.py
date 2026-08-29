"""Shared data models for Project 09."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    tags: tuple[str, ...]
    content: str


@dataclass(frozen=True)
class ResearchTask:
    id: str
    facet: str
    query: str


@dataclass(frozen=True)
class ResearchPlan:
    question: str
    tasks: tuple[ResearchTask, ...]
    complexity_score: int
    rationale: str


@dataclass(frozen=True)
class Evidence:
    source_id: str
    source_title: str
    source_url: str
    task_id: str
    facet: str
    researcher: str
    snippet: str
    score: float


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    source_id: str
    source_url: str
    task_id: str
    facet: str
    verified: bool
    reason: str


@dataclass(frozen=True)
class TeamMessage:
    sender: str
    recipient: str
    kind: str
    content: str


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    checks: dict[str, bool]
    issues: tuple[str, ...]


@dataclass
class TeamState:
    question: str
    plan: ResearchPlan | None = None
    evidence: list[Evidence] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    draft: str = ""
    report: str = ""
    review: ReviewResult | None = None
    messages: list[TeamMessage] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    status: str = "created"
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    mode: str
    question: str
    report: str
    status: str
    metrics: dict[str, Any]
    trace: tuple[TeamMessage, ...] = ()
    failures: tuple[str, ...] = ()
