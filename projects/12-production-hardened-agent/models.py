"""Core models for Project 12."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    provider: str
    estimated_tokens: int
    simulated_cost_usd: float
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttemptRecord:
    provider: str
    attempt: int
    outcome: str
    error_type: str | None = None
    backoff_ms: int = 0


@dataclass(frozen=True)
class AgentResult:
    status: str
    text: str
    trace_id: str
    provider: str | None
    degraded: bool
    cache_status: str
    attempts: tuple[AttemptRecord, ...] = ()
    sources: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthSnapshot:
    status: str
    primary_circuit: str
    fallback_circuit: str
    cache_entries: int
    metrics: dict[str, int | float]
