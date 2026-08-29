"""Typed models for the evaluation harness."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    expected_status: str
    expected_tool: str | None
    must_include: tuple[str, ...]
    must_not_include: tuple[str, ...]
    must_cite_source: bool
    allowed_source_ids: tuple[str, ...]
    max_steps: int


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    returned_source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TraceEvent:
    sequence: int
    trace_id: str
    span_id: str
    parent_span_id: str | None
    kind: str
    name: str
    attributes: dict[str, Any]


@dataclass(frozen=True)
class AgentRun:
    status: str
    answer: str
    tool_calls: tuple[ToolCall, ...]
    citations: tuple[str, ...]
    steps: int
    estimated_tokens: int
    cost_usd: float
    latency_ms: float
    trace: tuple[TraceEvent, ...]
    error: str | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    passed: bool
    score: float
    checks: tuple[CheckResult, ...]
    run: AgentRun


@dataclass(frozen=True)
class EvaluationReport:
    suite_version: str
    candidate: str
    case_results: tuple[CaseResult, ...]
    metrics: dict[str, float]
    regression_passed: bool | None = None
    regression_failures: tuple[str, ...] = ()


@dataclass
class MutableTrace:
    trace_id: str
    events: list[TraceEvent] = field(default_factory=list)
