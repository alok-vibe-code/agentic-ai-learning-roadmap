"""Shared data models for Project 06: Agent Pattern Examples."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PatternEvent:
    pattern: str
    step: int
    action: str
    details: dict[str, Any]


@dataclass
class PatternTrace:
    pattern: str
    events: list[PatternEvent] = field(default_factory=list)
    stop_reason: str | None = None

    def add(self, step: int, action: str, **details: Any) -> None:
        self.events.append(
            PatternEvent(
                pattern=self.pattern,
                step=step,
                action=action,
                details=details,
            )
        )


@dataclass(frozen=True)
class PlanStep:
    id: str
    title: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteDecision:
    route: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class ParallelResult:
    index: int
    task: str
    status: str
    value: Any = None
    error: str | None = None


@dataclass(frozen=True)
class ApprovalDecision:
    action: str
    risk: str
    approved: bool
    reason: str
