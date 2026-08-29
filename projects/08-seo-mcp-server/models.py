"""Shared models for Project 08: SEO MCP Server."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Heading:
    level: int
    text: str


@dataclass(frozen=True)
class LinkRecord:
    original: str
    resolved: str
    kind: str


@dataclass
class PageSnapshot:
    title: str | None = None
    meta_descriptions: list[str] = field(default_factory=list)
    canonicals: list[str] = field(default_factory=list)
    robots_values: list[str] = field(default_factory=list)
    googlebot_values: list[str] = field(default_factory=list)
    headings: list[Heading] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditIssue:
    code: str
    severity: str
    message: str


def dataclass_to_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
