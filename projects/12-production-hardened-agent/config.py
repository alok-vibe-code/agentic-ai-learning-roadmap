"""Validated JSON configuration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "default.json"


def _positive_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def _nonnegative_number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{name} must be a non-negative number.")
    return float(value)


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int
    base_backoff_ms: int
    max_backoff_ms: int
    jitter_ratio: float


@dataclass(frozen=True)
class CircuitConfig:
    failure_threshold: int
    recovery_timeout_ms: int
    half_open_max_calls: int


@dataclass(frozen=True)
class CacheConfig:
    ttl_ms: int
    stale_ttl_ms: int
    max_entries: int


@dataclass(frozen=True)
class RateLimitConfig:
    max_requests: int
    window_ms: int


@dataclass(frozen=True)
class BudgetConfig:
    max_provider_attempts: int
    max_estimated_tokens: int
    max_simulated_cost_usd: float


@dataclass(frozen=True)
class AppConfig:
    max_query_chars: int
    deadline_ms: int
    attempt_timeout_ms: int
    retry: RetryConfig
    circuit: CircuitConfig
    cache: CacheConfig
    rate_limit: RateLimitConfig
    budget: BudgetConfig
    primary_provider: str
    fallback_provider: str

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        try:
            request = data["request"]
            retry = data["retry"]
            timeout = data["timeout"]
            circuit = data["circuit_breaker"]
            cache = data["cache"]
            rate = data["rate_limit"]
            budget = data["budget"]
            providers = data["providers"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Missing configuration section: {exc}") from exc

        jitter = _nonnegative_number(retry["jitter_ratio"], "retry.jitter_ratio")
        if jitter > 1:
            raise ValueError("retry.jitter_ratio must be between 0 and 1.")

        max_cost = _nonnegative_number(
            budget["max_simulated_cost_usd"],
            "budget.max_simulated_cost_usd",
        )

        primary = providers.get("primary")
        fallback = providers.get("fallback")
        if not isinstance(primary, str) or not primary.strip():
            raise ValueError("providers.primary must be a non-empty string.")
        if not isinstance(fallback, str) or not fallback.strip():
            raise ValueError("providers.fallback must be a non-empty string.")
        if primary == fallback:
            raise ValueError("Primary and fallback provider names must differ.")

        retry_config = RetryConfig(
            max_attempts=_positive_int(retry["max_attempts"], "retry.max_attempts"),
            base_backoff_ms=_positive_int(retry["base_backoff_ms"], "retry.base_backoff_ms"),
            max_backoff_ms=_positive_int(retry["max_backoff_ms"], "retry.max_backoff_ms"),
            jitter_ratio=jitter,
        )
        if retry_config.base_backoff_ms > retry_config.max_backoff_ms:
            raise ValueError("retry.base_backoff_ms cannot exceed retry.max_backoff_ms.")

        cache_config = CacheConfig(
            ttl_ms=_positive_int(cache["ttl_ms"], "cache.ttl_ms"),
            stale_ttl_ms=_positive_int(cache["stale_ttl_ms"], "cache.stale_ttl_ms"),
            max_entries=_positive_int(cache["max_entries"], "cache.max_entries"),
        )
        if cache_config.stale_ttl_ms < cache_config.ttl_ms:
            raise ValueError("cache.stale_ttl_ms must be >= cache.ttl_ms.")

        return cls(
            max_query_chars=_positive_int(
                request["max_query_chars"], "request.max_query_chars"
            ),
            deadline_ms=_positive_int(request["deadline_ms"], "request.deadline_ms"),
            attempt_timeout_ms=_positive_int(
                timeout["attempt_timeout_ms"], "timeout.attempt_timeout_ms"
            ),
            retry=retry_config,
            circuit=CircuitConfig(
                failure_threshold=_positive_int(
                    circuit["failure_threshold"],
                    "circuit_breaker.failure_threshold",
                ),
                recovery_timeout_ms=_positive_int(
                    circuit["recovery_timeout_ms"],
                    "circuit_breaker.recovery_timeout_ms",
                ),
                half_open_max_calls=_positive_int(
                    circuit["half_open_max_calls"],
                    "circuit_breaker.half_open_max_calls",
                ),
            ),
            cache=cache_config,
            rate_limit=RateLimitConfig(
                max_requests=_positive_int(
                    rate["max_requests"], "rate_limit.max_requests"
                ),
                window_ms=_positive_int(rate["window_ms"], "rate_limit.window_ms"),
            ),
            budget=BudgetConfig(
                max_provider_attempts=_positive_int(
                    budget["max_provider_attempts"],
                    "budget.max_provider_attempts",
                ),
                max_estimated_tokens=_positive_int(
                    budget["max_estimated_tokens"],
                    "budget.max_estimated_tokens",
                ),
                max_simulated_cost_usd=max_cost,
            ),
            primary_provider=primary.strip(),
            fallback_provider=fallback.strip(),
        )


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be an object.")
    return AppConfig.from_dict(data)
