"""Retry, backoff, deadline, budget, and circuit-breaker orchestration."""

from __future__ import annotations

import random
import time

from budget import RequestBudget
from circuit_breaker import CircuitBreaker
from config import RetryConfig
from errors import (
    BudgetExceeded,
    CircuitOpenError,
    PermanentProviderError,
    ProviderTimeout,
    RequestDeadlineExceeded,
    TransientProviderError,
)
from models import AttemptRecord, ProviderResponse
from telemetry import MetricsRegistry, StructuredLogger


RETRYABLE = (TransientProviderError, ProviderTimeout)


def compute_backoff_ms(
    attempt: int,
    config: RetryConfig,
    *,
    random_value: float = 0.5,
) -> int:
    if attempt < 1:
        raise ValueError("attempt must be >= 1")

    base = min(
        config.max_backoff_ms,
        config.base_backoff_ms * (2 ** (attempt - 1)),
    )
    jitter_span = base * config.jitter_ratio
    multiplier = (random_value * 2.0) - 1.0
    value = base + (jitter_span * multiplier)
    return max(0, int(round(value)))


def call_with_resilience(
    provider,
    query: str,
    *,
    retry: RetryConfig,
    attempt_timeout_ms: int,
    request_started_ms: float,
    deadline_ms: int,
    breaker: CircuitBreaker,
    budget: RequestBudget,
    metrics: MetricsRegistry,
    logger: StructuredLogger,
    trace_id: str,
    clock_ms,
    sleeper_ms,
    random_fn=random.random,
) -> tuple[ProviderResponse, tuple[AttemptRecord, ...]]:
    records: list[AttemptRecord] = []

    for attempt in range(1, retry.max_attempts + 1):
        now = float(clock_ms())
        if now - request_started_ms >= deadline_ms:
            metrics.inc("deadline_exceeded")
            raise RequestDeadlineExceeded("Request deadline exceeded.")

        budget.reserve_attempt()

        try:
            breaker.before_call(now)
        except CircuitOpenError:
            metrics.inc(f"circuit_open_block.{provider.name}")
            logger.emit(
                "provider_skipped",
                trace_id=trace_id,
                provider=provider.name,
                reason="circuit_open",
            )
            raise

        metrics.inc("provider_attempts")
        metrics.inc(f"provider_attempts.{provider.name}")
        logger.emit(
            "provider_attempt",
            trace_id=trace_id,
            provider=provider.name,
            attempt=attempt,
        )

        try:
            response = provider.generate(query, timeout_ms=attempt_timeout_ms)
            budget.consume_response(response)
            breaker.record_success()
            metrics.inc("provider_success")
            metrics.inc(f"provider_success.{provider.name}")
            records.append(
                AttemptRecord(provider.name, attempt, "success")
            )
            logger.emit(
                "provider_success",
                trace_id=trace_id,
                provider=provider.name,
                attempt=attempt,
                estimated_tokens=response.estimated_tokens,
                simulated_cost_usd=response.simulated_cost_usd,
            )
            return response, tuple(records)

        except BudgetExceeded:
            metrics.inc("budget_exceeded")
            breaker.record_failure(float(clock_ms()))
            logger.emit(
                "budget_exceeded",
                trace_id=trace_id,
                provider=provider.name,
                attempt=attempt,
            )
            raise

        except PermanentProviderError as exc:
            opened = breaker.record_failure(float(clock_ms()))
            metrics.inc("provider_permanent_failure")
            if opened:
                metrics.inc("circuit_opened")
            records.append(
                AttemptRecord(
                    provider.name,
                    attempt,
                    "failure",
                    error_type=type(exc).__name__,
                )
            )
            logger.emit(
                "provider_failure",
                trace_id=trace_id,
                provider=provider.name,
                attempt=attempt,
                retryable=False,
                error_type=type(exc).__name__,
            )
            raise

        except RETRYABLE as exc:
            opened = breaker.record_failure(float(clock_ms()))
            metrics.inc("provider_retryable_failure")
            if isinstance(exc, ProviderTimeout):
                metrics.inc("provider_timeout")
            if opened:
                metrics.inc("circuit_opened")

            if attempt >= retry.max_attempts:
                records.append(
                    AttemptRecord(
                        provider.name,
                        attempt,
                        "failure",
                        error_type=type(exc).__name__,
                    )
                )
                logger.emit(
                    "provider_failure",
                    trace_id=trace_id,
                    provider=provider.name,
                    attempt=attempt,
                    retryable=True,
                    retry_scheduled=False,
                    error_type=type(exc).__name__,
                )
                raise

            backoff_ms = compute_backoff_ms(
                attempt,
                retry,
                random_value=float(random_fn()),
            )

            if float(clock_ms()) - request_started_ms + backoff_ms >= deadline_ms:
                metrics.inc("deadline_exceeded")
                raise RequestDeadlineExceeded(
                    "Request deadline would be exceeded by retry backoff."
                )

            metrics.inc("retries")
            records.append(
                AttemptRecord(
                    provider.name,
                    attempt,
                    "retry",
                    error_type=type(exc).__name__,
                    backoff_ms=backoff_ms,
                )
            )
            logger.emit(
                "retry_scheduled",
                trace_id=trace_id,
                provider=provider.name,
                attempt=attempt,
                backoff_ms=backoff_ms,
                error_type=type(exc).__name__,
            )
            sleeper_ms(backoff_ms)

    raise RuntimeError("Unreachable retry loop state.")
