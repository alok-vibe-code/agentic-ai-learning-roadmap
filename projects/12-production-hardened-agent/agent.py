"""Production-hardened agent orchestration."""

from __future__ import annotations

import hashlib
import time

from budget import RequestBudget
from cache import TTLCache
from circuit_breaker import CircuitBreaker
from config import AppConfig, load_config
from errors import AgentOperationalError, BudgetExceeded
from health import build_health_snapshot
from models import AgentResult
from rate_limit import SlidingWindowRateLimiter
from resilience import call_with_resilience
from service import ScriptedProvider
from telemetry import MetricsRegistry, StructuredLogger, new_trace_id


def _system_clock_ms() -> float:
    return time.monotonic() * 1000.0


def _system_sleep_ms(ms: int) -> None:
    time.sleep(ms / 1000.0)


def normalize_query(query: str) -> str:
    return " ".join(query.split())


def cache_key(query: str) -> str:
    normalized = normalize_query(query).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ProductionHardenedAgent:
    def __init__(
        self,
        *,
        config: AppConfig | None = None,
        primary=None,
        fallback=None,
        clock_ms=_system_clock_ms,
        sleeper_ms=_system_sleep_ms,
        random_fn=lambda: 0.5,
        logger: StructuredLogger | None = None,
    ) -> None:
        self.config = config or load_config()
        self.clock_ms = clock_ms
        self.sleeper_ms = sleeper_ms
        self.random_fn = random_fn
        self.logger = logger or StructuredLogger(echo=False)
        self.metrics = MetricsRegistry()

        self.primary = primary or ScriptedProvider(self.config.primary_provider)
        self.fallback = fallback or ScriptedProvider(
            self.config.fallback_provider,
            estimated_tokens=90,
            simulated_cost_usd=0.0002,
        )

        circuit = self.config.circuit
        self.primary_breaker = CircuitBreaker(
            circuit.failure_threshold,
            circuit.recovery_timeout_ms,
            circuit.half_open_max_calls,
        )
        self.fallback_breaker = CircuitBreaker(
            circuit.failure_threshold,
            circuit.recovery_timeout_ms,
            circuit.half_open_max_calls,
        )

        cache = self.config.cache
        self.cache = TTLCache(
            cache.ttl_ms,
            cache.stale_ttl_ms,
            cache.max_entries,
        )

        rate = self.config.rate_limit
        self.rate_limiter = SlidingWindowRateLimiter(
            rate.max_requests,
            rate.window_ms,
        )

    def answer(
        self,
        principal: str,
        query: str,
        *,
        trace_id: str | None = None,
    ) -> AgentResult:
        trace_id = trace_id or new_trace_id()
        start_ms = float(self.clock_ms())

        if not isinstance(principal, str) or not principal.strip():
            return AgentResult(
                "invalid_request",
                "Principal must be a non-empty string.",
                trace_id,
                None,
                False,
                "miss",
            )

        if not isinstance(query, str):
            return AgentResult(
                "invalid_request",
                "Query must be a string.",
                trace_id,
                None,
                False,
                "miss",
            )

        query = normalize_query(query)
        if not query:
            return AgentResult(
                "invalid_request",
                "Query cannot be empty.",
                trace_id,
                None,
                False,
                "miss",
            )

        if len(query) > self.config.max_query_chars:
            return AgentResult(
                "invalid_request",
                f"Query exceeds {self.config.max_query_chars} characters.",
                trace_id,
                None,
                False,
                "miss",
            )

        allowed, current = self.rate_limiter.allow(principal, start_ms)
        if not allowed:
            self.metrics.inc("rate_limited")
            self.logger.emit(
                "request_rate_limited",
                trace_id=trace_id,
                principal=principal,
                current=current,
            )
            return AgentResult(
                "rate_limited",
                "Rate limit exceeded.",
                trace_id,
                None,
                True,
                "miss",
            )

        self.metrics.inc("requests")
        key = cache_key(query)
        fresh = self.cache.get_fresh(key, start_ms)
        if fresh is not None:
            self.metrics.inc("cache_hit_fresh")
            self.logger.emit(
                "cache_hit",
                trace_id=trace_id,
                cache_status="fresh",
                provider=fresh.provider,
            )
            return AgentResult(
                "ok",
                fresh.text,
                trace_id,
                fresh.provider,
                False,
                "fresh",
                sources=fresh.sources,
                metadata={
                    "budget": {
                        "attempts": 0,
                        "estimated_tokens": 0,
                        "simulated_cost_usd": 0.0,
                    }
                },
            )

        self.metrics.inc("cache_miss")
        budget = RequestBudget(self.config.budget)
        all_attempts = []

        provider_plan = (
            (self.primary, self.primary_breaker, False),
            (self.fallback, self.fallback_breaker, True),
        )

        last_error: Exception | None = None

        for provider, breaker, degraded in provider_plan:
            if degraded:
                self.metrics.inc("fallback_attempted")
                self.logger.emit(
                    "fallback_selected",
                    trace_id=trace_id,
                    provider=provider.name,
                )

            try:
                response, attempts = call_with_resilience(
                    provider,
                    query,
                    retry=self.config.retry,
                    attempt_timeout_ms=self.config.attempt_timeout_ms,
                    request_started_ms=start_ms,
                    deadline_ms=self.config.deadline_ms,
                    breaker=breaker,
                    budget=budget,
                    metrics=self.metrics,
                    logger=self.logger,
                    trace_id=trace_id,
                    clock_ms=self.clock_ms,
                    sleeper_ms=self.sleeper_ms,
                    random_fn=self.random_fn,
                )
                all_attempts.extend(attempts)
                now_ms = float(self.clock_ms())
                self.cache.set(key, response, now_ms)
                self.metrics.inc("requests_succeeded")
                if degraded:
                    self.metrics.inc("fallback_success")
                self.logger.emit(
                    "request_complete",
                    trace_id=trace_id,
                    status="ok",
                    provider=response.provider,
                    degraded=degraded,
                )
                return AgentResult(
                    "ok",
                    response.text,
                    trace_id,
                    response.provider,
                    degraded,
                    "miss",
                    attempts=tuple(all_attempts),
                    sources=response.sources,
                    metadata={
                        "budget": budget.snapshot(),
                        "latency_ms": round(now_ms - start_ms, 3),
                    },
                )

            except (AgentOperationalError, BudgetExceeded) as exc:
                last_error = exc
                self.metrics.inc("provider_plan_failure")
                self.logger.emit(
                    "provider_plan_failure",
                    trace_id=trace_id,
                    provider=provider.name,
                    error_type=type(exc).__name__,
                )
                # If budget itself is exhausted, another provider cannot run.
                if isinstance(exc, BudgetExceeded):
                    break

        now_ms = float(self.clock_ms())
        stale = self.cache.get_stale(key, now_ms)
        if stale is not None:
            self.metrics.inc("cache_hit_stale")
            self.metrics.inc("graceful_degradation")
            self.logger.emit(
                "stale_cache_used",
                trace_id=trace_id,
                provider=stale.provider,
                error_type=type(last_error).__name__ if last_error else None,
            )
            return AgentResult(
                "degraded",
                stale.text,
                trace_id,
                stale.provider,
                True,
                "stale",
                attempts=tuple(all_attempts),
                sources=stale.sources,
                metadata={
                    "budget": budget.snapshot(),
                    "reason": type(last_error).__name__ if last_error else "provider_failure",
                },
            )

        self.metrics.inc("requests_unavailable")
        self.metrics.inc("graceful_degradation")
        self.logger.emit(
            "request_unavailable",
            trace_id=trace_id,
            error_type=type(last_error).__name__ if last_error else None,
        )
        return AgentResult(
            "unavailable",
            "The agent is temporarily unavailable. No unsupported answer was generated.",
            trace_id,
            None,
            True,
            "miss",
            attempts=tuple(all_attempts),
            metadata={
                "budget": budget.snapshot(),
                "reason": type(last_error).__name__ if last_error else "provider_failure",
            },
        )

    def health(self):
        return build_health_snapshot(self)
