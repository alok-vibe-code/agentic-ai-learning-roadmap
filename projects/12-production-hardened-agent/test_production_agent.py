"""Offline test suite for Project 12."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from agent import ProductionHardenedAgent, cache_key, normalize_query
from budget import RequestBudget
from cache import TTLCache
from circuit_breaker import CircuitBreaker
from config import AppConfig, load_config
from errors import (
    BudgetExceeded,
    CircuitOpenError,
    PermanentProviderError,
    ProviderTimeout,
    RequestDeadlineExceeded,
    TransientProviderError,
)
from health import build_health_snapshot
from models import CircuitState, ProviderResponse
from rate_limit import SlidingWindowRateLimiter
from resilience import compute_backoff_ms, call_with_resilience
from service import ScriptedProvider
from telemetry import MetricsRegistry, StructuredLogger


class FakeClock:
    def __init__(self, value=1000.0):
        self.value = float(value)

    def __call__(self):
        return self.value

    def sleep(self, ms):
        self.value += ms

    def advance(self, ms):
        self.value += ms


def config_dict():
    path = Path(__file__).resolve().parent / "config" / "default.json"
    return json.loads(path.read_text(encoding="utf-8"))


def config_from(modifier=None):
    data = config_dict()
    if modifier:
        modifier(data)
    return AppConfig.from_dict(data)


def make_agent(
    primary_script=None,
    fallback_script=None,
    *,
    config=None,
    clock=None,
    primary_tokens=120,
    primary_cost=0.001,
    fallback_tokens=90,
    fallback_cost=0.0002,
):
    config = config or load_config()
    clock = clock or FakeClock()
    primary = ScriptedProvider(
        config.primary_provider,
        script=primary_script or ["success"],
        estimated_tokens=primary_tokens,
        simulated_cost_usd=primary_cost,
    )
    fallback = ScriptedProvider(
        config.fallback_provider,
        script=fallback_script or ["success"],
        estimated_tokens=fallback_tokens,
        simulated_cost_usd=fallback_cost,
    )
    logger = StructuredLogger()
    agent = ProductionHardenedAgent(
        config=config,
        primary=primary,
        fallback=fallback,
        clock_ms=clock,
        sleeper_ms=clock.sleep,
        random_fn=lambda: 0.5,
        logger=logger,
    )
    return agent, clock, primary, fallback, logger


class ConfigTests(unittest.TestCase):
    def test_default_loads(self):
        config = load_config()
        self.assertEqual(config.primary_provider, "mock-primary")

    def test_jitter_range(self):
        data = config_dict()
        data["retry"]["jitter_ratio"] = 1.1
        with self.assertRaises(ValueError):
            AppConfig.from_dict(data)

    def test_primary_fallback_must_differ(self):
        data = config_dict()
        data["providers"]["fallback"] = data["providers"]["primary"]
        with self.assertRaises(ValueError):
            AppConfig.from_dict(data)

    def test_backoff_relationship(self):
        data = config_dict()
        data["retry"]["base_backoff_ms"] = 200
        data["retry"]["max_backoff_ms"] = 100
        with self.assertRaises(ValueError):
            AppConfig.from_dict(data)

    def test_stale_window_relationship(self):
        data = config_dict()
        data["cache"]["ttl_ms"] = 100
        data["cache"]["stale_ttl_ms"] = 50
        with self.assertRaises(ValueError):
            AppConfig.from_dict(data)

    def test_missing_section(self):
        data = config_dict()
        del data["budget"]
        with self.assertRaises(ValueError):
            AppConfig.from_dict(data)

    def test_config_root_must_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)


# Generate field validation tests for all positive-integer configuration fields.
POSITIVE_PATHS = [
    ("request", "max_query_chars"),
    ("request", "deadline_ms"),
    ("retry", "max_attempts"),
    ("retry", "base_backoff_ms"),
    ("retry", "max_backoff_ms"),
    ("timeout", "attempt_timeout_ms"),
    ("circuit_breaker", "failure_threshold"),
    ("circuit_breaker", "recovery_timeout_ms"),
    ("circuit_breaker", "half_open_max_calls"),
    ("cache", "ttl_ms"),
    ("cache", "stale_ttl_ms"),
    ("cache", "max_entries"),
    ("rate_limit", "max_requests"),
    ("rate_limit", "window_ms"),
    ("budget", "max_provider_attempts"),
    ("budget", "max_estimated_tokens"),
]


def _make_invalid_positive_test(section, field):
    def test(self):
        data = config_dict()
        data[section][field] = 0
        with self.assertRaises(ValueError):
            AppConfig.from_dict(data)
    return test


for _section, _field in POSITIVE_PATHS:
    setattr(
        ConfigTests,
        f"test_positive_{_section}_{_field}",
        _make_invalid_positive_test(_section, _field),
    )


class BackoffTests(unittest.TestCase):
    def setUp(self):
        self.retry = load_config().retry

    def test_attempt_one(self):
        self.assertEqual(compute_backoff_ms(1, self.retry, random_value=0.5), 20)

    def test_attempt_two(self):
        self.assertEqual(compute_backoff_ms(2, self.retry, random_value=0.5), 40)

    def test_cap(self):
        self.assertEqual(compute_backoff_ms(10, self.retry, random_value=0.5), 100)

    def test_low_jitter(self):
        value = compute_backoff_ms(1, self.retry, random_value=0.0)
        self.assertEqual(value, 16)

    def test_high_jitter(self):
        value = compute_backoff_ms(1, self.retry, random_value=1.0)
        self.assertEqual(value, 24)

    def test_invalid_attempt(self):
        with self.assertRaises(ValueError):
            compute_backoff_ms(0, self.retry)


class CircuitBreakerTests(unittest.TestCase):
    def setUp(self):
        self.breaker = CircuitBreaker(3, 1000, 1)

    def test_initial_closed(self):
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)

    def test_failure_count(self):
        self.breaker.record_failure(0)
        self.assertEqual(self.breaker.failure_count, 1)

    def test_opens_at_threshold(self):
        self.breaker.record_failure(0)
        self.breaker.record_failure(1)
        opened = self.breaker.record_failure(2)
        self.assertTrue(opened)
        self.assertEqual(self.breaker.state, CircuitState.OPEN)

    def test_open_blocks_before_recovery(self):
        for t in (0, 1, 2):
            self.breaker.record_failure(t)
        with self.assertRaises(CircuitOpenError):
            self.breaker.before_call(500)

    def test_open_transitions_half_open(self):
        for t in (0, 1, 2):
            self.breaker.record_failure(t)
        self.breaker.before_call(1002)
        self.assertEqual(self.breaker.state, CircuitState.HALF_OPEN)

    def test_half_open_success_closes(self):
        for t in (0, 1, 2):
            self.breaker.record_failure(t)
        self.breaker.before_call(1002)
        self.breaker.record_success()
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)

    def test_half_open_failure_reopens(self):
        for t in (0, 1, 2):
            self.breaker.record_failure(t)
        self.breaker.before_call(1002)
        self.breaker.record_failure(1003)
        self.assertEqual(self.breaker.state, CircuitState.OPEN)

    def test_success_resets_failure_count(self):
        self.breaker.record_failure(0)
        self.breaker.record_success()
        self.assertEqual(self.breaker.failure_count, 0)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            CircuitBreaker(0, 1000)

    def test_half_open_probe_limit(self):
        breaker = CircuitBreaker(1, 10, 1)
        breaker.record_failure(0)
        breaker.before_call(10)
        with self.assertRaises(CircuitOpenError):
            breaker.before_call(10)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = TTLCache(100, 300, 2)
        self.value = ProviderResponse("x", "p", 1, 0.0)

    def test_set_and_fresh_get(self):
        self.cache.set("a", self.value, 0)
        self.assertIsNotNone(self.cache.get_fresh("a", 50))

    def test_fresh_boundary(self):
        self.cache.set("a", self.value, 0)
        self.assertIsNotNone(self.cache.get_fresh("a", 100))

    def test_stale_after_ttl(self):
        self.cache.set("a", self.value, 0)
        self.assertIsNotNone(self.cache.get_stale("a", 101))

    def test_stale_boundary(self):
        self.cache.set("a", self.value, 0)
        self.assertIsNotNone(self.cache.get_stale("a", 300))

    def test_expired_not_stale(self):
        self.cache.set("a", self.value, 0)
        self.assertIsNone(self.cache.get_stale("a", 301))

    def test_lru_eviction(self):
        self.cache.set("a", self.value, 0)
        self.cache.set("b", self.value, 0)
        self.cache.get_fresh("a", 1)
        self.cache.set("c", self.value, 2)
        self.assertIsNone(self.cache.get_fresh("b", 3))

    def test_replace_existing(self):
        other = ProviderResponse("y", "p", 1, 0.0)
        self.cache.set("a", self.value, 0)
        self.cache.set("a", other, 1)
        self.assertEqual(self.cache.get_fresh("a", 2).text, "y")

    def test_purge(self):
        self.cache.set("a", self.value, 0)
        self.assertEqual(self.cache.purge_expired(301), 1)
        self.assertEqual(len(self.cache), 0)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            TTLCache(100, 50, 1)


class RateLimitTests(unittest.TestCase):
    def test_under_limit(self):
        limiter = SlidingWindowRateLimiter(2, 100)
        self.assertTrue(limiter.allow("u", 0)[0])
        self.assertTrue(limiter.allow("u", 1)[0])

    def test_at_limit(self):
        limiter = SlidingWindowRateLimiter(2, 100)
        limiter.allow("u", 0)
        limiter.allow("u", 1)
        self.assertFalse(limiter.allow("u", 2)[0])

    def test_window_releases(self):
        limiter = SlidingWindowRateLimiter(1, 100)
        limiter.allow("u", 0)
        self.assertTrue(limiter.allow("u", 101)[0])

    def test_principals_separate(self):
        limiter = SlidingWindowRateLimiter(1, 100)
        limiter.allow("a", 0)
        self.assertTrue(limiter.allow("b", 0)[0])

    def test_current(self):
        limiter = SlidingWindowRateLimiter(2, 100)
        limiter.allow("u", 0)
        self.assertEqual(limiter.current("u", 1), 1)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(0, 100)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config().budget

    def test_reserve_attempt(self):
        budget = RequestBudget(self.config)
        budget.reserve_attempt()
        self.assertEqual(budget.usage.attempts, 1)

    def test_attempt_limit(self):
        budget = RequestBudget(self.config)
        for _ in range(self.config.max_provider_attempts):
            budget.reserve_attempt()
        with self.assertRaises(BudgetExceeded):
            budget.reserve_attempt()

    def test_consume_response(self):
        budget = RequestBudget(self.config)
        response = ProviderResponse("x", "p", 100, 0.001)
        budget.consume_response(response)
        self.assertEqual(budget.usage.estimated_tokens, 100)

    def test_token_limit(self):
        config = config_from(
            lambda d: d["budget"].update({"max_estimated_tokens": 50})
        ).budget
        budget = RequestBudget(config)
        with self.assertRaises(BudgetExceeded):
            budget.consume_response(ProviderResponse("x", "p", 51, 0.0))

    def test_cost_limit(self):
        config = config_from(
            lambda d: d["budget"].update({"max_simulated_cost_usd": 0.0001})
        ).budget
        budget = RequestBudget(config)
        with self.assertRaises(BudgetExceeded):
            budget.consume_response(ProviderResponse("x", "p", 1, 0.001))

    def test_snapshot(self):
        budget = RequestBudget(self.config)
        budget.reserve_attempt()
        self.assertEqual(budget.snapshot()["attempts"], 1)


class ServiceTests(unittest.TestCase):
    def test_success(self):
        provider = ScriptedProvider("p", script=["success"])
        response = provider.generate("Explain retries", timeout_ms=100)
        self.assertEqual(response.provider, "p")

    def test_transient(self):
        provider = ScriptedProvider("p", script=["transient"])
        with self.assertRaises(TransientProviderError):
            provider.generate("x", timeout_ms=100)

    def test_permanent(self):
        provider = ScriptedProvider("p", script=["permanent"])
        with self.assertRaises(PermanentProviderError):
            provider.generate("x", timeout_ms=100)

    def test_timeout_script(self):
        provider = ScriptedProvider("p", script=["timeout"])
        with self.assertRaises(ProviderTimeout):
            provider.generate("x", timeout_ms=100)

    def test_latency_timeout(self):
        provider = ScriptedProvider("p", simulated_latency_ms=200)
        with self.assertRaises(ProviderTimeout):
            provider.generate("x", timeout_ms=100)

    def test_script_repeats_last(self):
        provider = ScriptedProvider("p", script=["transient", "success"])
        with self.assertRaises(TransientProviderError):
            provider.generate("x", timeout_ms=100)
        self.assertEqual(provider.generate("x", timeout_ms=100).provider, "p")
        self.assertEqual(provider.generate("x", timeout_ms=100).provider, "p")

    def test_unknown_script_is_permanent(self):
        provider = ScriptedProvider("p", script=["weird"])
        with self.assertRaises(PermanentProviderError):
            provider.generate("x", timeout_ms=100)

    def test_no_match_is_explicit(self):
        provider = ScriptedProvider("p")
        response = provider.generate("xyzzy plugh", timeout_ms=100)
        self.assertIn("does not contain enough", response.text)


class TelemetryTests(unittest.TestCase):
    def test_metric_inc(self):
        metrics = MetricsRegistry()
        metrics.inc("x")
        self.assertEqual(metrics.snapshot()["x"], 1)

    def test_metric_add(self):
        metrics = MetricsRegistry()
        metrics.inc("x", 2.5)
        self.assertEqual(metrics.snapshot()["x"], 2.5)

    def test_metric_set(self):
        metrics = MetricsRegistry()
        metrics.set("x", 4)
        self.assertEqual(metrics.snapshot()["x"], 4)

    def test_logger_record(self):
        logger = StructuredLogger()
        record = logger.emit("event", trace_id="abc", value=1)
        self.assertEqual(record["trace_id"], "abc")
        self.assertEqual(len(logger.records), 1)


class ResilienceTests(unittest.TestCase):
    def call(self, script, *, config=None, clock=None):
        config = config or load_config()
        clock = clock or FakeClock()
        provider = ScriptedProvider(config.primary_provider, script=script)
        breaker = CircuitBreaker(
            config.circuit.failure_threshold,
            config.circuit.recovery_timeout_ms,
            config.circuit.half_open_max_calls,
        )
        budget = RequestBudget(config.budget)
        metrics = MetricsRegistry()
        logger = StructuredLogger()
        response = call_with_resilience(
            provider,
            "Explain retries",
            retry=config.retry,
            attempt_timeout_ms=config.attempt_timeout_ms,
            request_started_ms=clock(),
            deadline_ms=config.deadline_ms,
            breaker=breaker,
            budget=budget,
            metrics=metrics,
            logger=logger,
            trace_id="trace",
            clock_ms=clock,
            sleeper_ms=clock.sleep,
            random_fn=lambda: 0.5,
        )
        return response, provider, breaker, budget, metrics, logger, clock

    def test_success_first_try(self):
        (response, attempts), provider, *_ = self.call(["success"])
        self.assertEqual(response.provider, provider.name)
        self.assertEqual(len(attempts), 1)

    def test_transient_then_success(self):
        (response, attempts), provider, *_ = self.call(["transient", "success"])
        self.assertEqual(response.provider, provider.name)
        self.assertEqual(len(attempts), 2)

    def test_timeout_then_success(self):
        (response, attempts), *_ = self.call(["timeout", "success"])
        self.assertEqual(len(attempts), 2)

    def test_permanent_not_retried(self):
        config = load_config()
        clock = FakeClock()
        provider = ScriptedProvider(config.primary_provider, script=["permanent"])
        breaker = CircuitBreaker(3, 1000)
        with self.assertRaises(PermanentProviderError):
            call_with_resilience(
                provider, "x",
                retry=config.retry,
                attempt_timeout_ms=config.attempt_timeout_ms,
                request_started_ms=clock(),
                deadline_ms=config.deadline_ms,
                breaker=breaker,
                budget=RequestBudget(config.budget),
                metrics=MetricsRegistry(),
                logger=StructuredLogger(),
                trace_id="t",
                clock_ms=clock,
                sleeper_ms=clock.sleep,
                random_fn=lambda: 0.5,
            )
        self.assertEqual(provider.calls, 1)

    def test_retry_exhaustion(self):
        config = load_config()
        clock = FakeClock()
        provider = ScriptedProvider(config.primary_provider, script=["transient"])
        with self.assertRaises(TransientProviderError):
            call_with_resilience(
                provider, "x",
                retry=config.retry,
                attempt_timeout_ms=config.attempt_timeout_ms,
                request_started_ms=clock(),
                deadline_ms=config.deadline_ms,
                breaker=CircuitBreaker(99, 1000),
                budget=RequestBudget(config.budget),
                metrics=MetricsRegistry(),
                logger=StructuredLogger(),
                trace_id="t",
                clock_ms=clock,
                sleeper_ms=clock.sleep,
                random_fn=lambda: 0.5,
            )
        self.assertEqual(provider.calls, config.retry.max_attempts)

    def test_deadline_before_attempt(self):
        config = load_config()
        clock = FakeClock(5000)
        with self.assertRaises(RequestDeadlineExceeded):
            call_with_resilience(
                ScriptedProvider("p"), "x",
                retry=config.retry,
                attempt_timeout_ms=config.attempt_timeout_ms,
                request_started_ms=0,
                deadline_ms=100,
                breaker=CircuitBreaker(3, 1000),
                budget=RequestBudget(config.budget),
                metrics=MetricsRegistry(),
                logger=StructuredLogger(),
                trace_id="t",
                clock_ms=clock,
                sleeper_ms=clock.sleep,
                random_fn=lambda: 0.5,
            )

    def test_circuit_open_blocks(self):
        config = load_config()
        clock = FakeClock()
        breaker = CircuitBreaker(1, 1000)
        breaker.record_failure(clock())
        with self.assertRaises(CircuitOpenError):
            call_with_resilience(
                ScriptedProvider("p"), "x",
                retry=config.retry,
                attempt_timeout_ms=config.attempt_timeout_ms,
                request_started_ms=clock(),
                deadline_ms=config.deadline_ms,
                breaker=breaker,
                budget=RequestBudget(config.budget),
                metrics=MetricsRegistry(),
                logger=StructuredLogger(),
                trace_id="t",
                clock_ms=clock,
                sleeper_ms=clock.sleep,
                random_fn=lambda: 0.5,
            )

    def test_retry_metric(self):
        (_, _), _, _, _, metrics, _, _ = self.call(["transient", "success"])
        self.assertEqual(metrics.snapshot()["retries"], 1)

    def test_trace_propagates_to_logs(self):
        (_, _), _, _, _, _, logger, _ = self.call(["transient", "success"])
        self.assertTrue(logger.records)
        self.assertTrue(all(r["trace_id"] == "trace" for r in logger.records))


class AgentUtilityTests(unittest.TestCase):
    def test_normalize_query(self):
        self.assertEqual(normalize_query("  Hello   World "), "Hello World")

    def test_cache_key_normalized(self):
        self.assertEqual(cache_key("Hello   World"), cache_key(" hello world "))

    def test_cache_key_differs(self):
        self.assertNotEqual(cache_key("a"), cache_key("b"))


class AgentWorkflowTests(unittest.TestCase):
    def test_primary_success(self):
        agent, _, primary, fallback, _ = make_agent()
        result = agent.answer("u", "Explain retries")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.provider, primary.name)
        self.assertFalse(result.degraded)
        self.assertEqual(fallback.calls, 0)

    def test_primary_retry_success(self):
        agent, _, primary, fallback, _ = make_agent(
            ["transient", "success"], ["success"]
        )
        result = agent.answer("u", "Explain retries")
        self.assertEqual(result.provider, primary.name)
        self.assertEqual(primary.calls, 2)
        self.assertEqual(fallback.calls, 0)

    def test_primary_timeout_retry_success(self):
        agent, _, primary, _, _ = make_agent(
            ["timeout", "success"], ["success"]
        )
        result = agent.answer("u", "Explain timeout")
        self.assertEqual(result.provider, primary.name)
        self.assertEqual(primary.calls, 2)

    def test_permanent_primary_uses_fallback(self):
        agent, _, _, fallback, _ = make_agent(["permanent"], ["success"])
        result = agent.answer("u", "Explain fallback")
        self.assertEqual(result.provider, fallback.name)
        self.assertTrue(result.degraded)

    def test_exhausted_primary_uses_fallback(self):
        agent, _, _, fallback, _ = make_agent(["transient"], ["success"])
        result = agent.answer("u", "Explain fallback")
        self.assertEqual(result.provider, fallback.name)
        self.assertTrue(result.degraded)

    def test_both_permanent_unavailable(self):
        agent, _, _, _, _ = make_agent(["permanent"], ["permanent"])
        result = agent.answer("u", "Explain logging")
        self.assertEqual(result.status, "unavailable")
        self.assertIn("No unsupported answer", result.text)

    def test_fresh_cache_avoids_second_call(self):
        agent, _, primary, _, _ = make_agent()
        first = agent.answer("u", "Explain caching")
        second = agent.answer("u", "Explain caching")
        self.assertEqual(first.status, "ok")
        self.assertEqual(second.cache_status, "fresh")
        self.assertEqual(primary.calls, 1)

    def test_fresh_cache_budget_zero(self):
        agent, _, _, _, _ = make_agent()
        agent.answer("u", "Explain caching")
        second = agent.answer("u", "Explain caching")
        self.assertEqual(second.metadata["budget"]["attempts"], 0)

    def test_stale_if_error(self):
        agent, clock, primary, fallback, _ = make_agent()
        first = agent.answer("u", "Explain graceful degradation")
        self.assertEqual(first.status, "ok")
        clock.advance(agent.config.cache.ttl_ms + 1)
        primary.script = ["permanent"]
        primary.calls = 0
        fallback.script = ["permanent"]
        fallback.calls = 0
        second = agent.answer("u", "Explain graceful degradation")
        self.assertEqual(second.status, "degraded")
        self.assertEqual(second.cache_status, "stale")

    def test_stale_expired_unavailable(self):
        agent, clock, primary, fallback, _ = make_agent()
        agent.answer("u", "Explain graceful degradation")
        clock.advance(agent.config.cache.stale_ttl_ms + 1)
        primary.script = ["permanent"]
        primary.calls = 0
        fallback.script = ["permanent"]
        fallback.calls = 0
        result = agent.answer("u", "Explain graceful degradation")
        self.assertEqual(result.status, "unavailable")

    def test_rate_limit(self):
        config = config_from(
            lambda d: d["rate_limit"].update({"max_requests": 2})
        )
        agent, _, _, _, _ = make_agent(config=config)
        self.assertEqual(agent.answer("u", "Explain retry").status, "ok")
        self.assertEqual(agent.answer("u", "Explain cache").status, "ok")
        self.assertEqual(agent.answer("u", "Explain timeout").status, "rate_limited")

    def test_rate_limit_separate_principals(self):
        config = config_from(
            lambda d: d["rate_limit"].update({"max_requests": 1})
        )
        agent, _, _, _, _ = make_agent(config=config)
        self.assertEqual(agent.answer("a", "Explain retry").status, "ok")
        self.assertEqual(agent.answer("b", "Explain retry").status, "ok")

    def test_empty_query(self):
        agent, *_ = make_agent()
        self.assertEqual(agent.answer("u", " ").status, "invalid_request")

    def test_non_string_query(self):
        agent, *_ = make_agent()
        self.assertEqual(agent.answer("u", None).status, "invalid_request")  # type: ignore[arg-type]

    def test_empty_principal(self):
        agent, *_ = make_agent()
        self.assertEqual(agent.answer("", "Explain retry").status, "invalid_request")

    def test_long_query(self):
        config = config_from(
            lambda d: d["request"].update({"max_query_chars": 10})
        )
        agent, *_ = make_agent(config=config)
        self.assertEqual(agent.answer("u", "x" * 11).status, "invalid_request")

    def test_custom_trace_id(self):
        agent, *_ = make_agent()
        result = agent.answer("u", "Explain retry", trace_id="trace-123")
        self.assertEqual(result.trace_id, "trace-123")

    def test_trace_in_log_records(self):
        agent, *_, logger = make_agent()
        result = agent.answer("u", "Explain retry", trace_id="trace-abc")
        self.assertEqual(result.trace_id, "trace-abc")
        self.assertTrue(all(r["trace_id"] == "trace-abc" for r in logger.records))

    def test_fallback_metric(self):
        agent, *_ = make_agent(["permanent"], ["success"])
        agent.answer("u", "Explain fallback")
        metrics = agent.metrics.snapshot()
        self.assertEqual(metrics["fallback_attempted"], 1)
        self.assertEqual(metrics["fallback_success"], 1)

    def test_cache_metric(self):
        agent, *_ = make_agent()
        agent.answer("u", "Explain cache")
        agent.answer("u", "Explain cache")
        self.assertEqual(agent.metrics.snapshot()["cache_hit_fresh"], 1)

    def test_unavailable_metric(self):
        agent, *_ = make_agent(["permanent"], ["permanent"])
        agent.answer("u", "Explain cache")
        self.assertEqual(agent.metrics.snapshot()["requests_unavailable"], 1)

    def test_budget_attempt_limit_stops_fallback(self):
        config = config_from(
            lambda d: d["budget"].update({"max_provider_attempts": 1})
        )
        agent, _, _, fallback, _ = make_agent(
            ["permanent"], ["success"], config=config
        )
        result = agent.answer("u", "Explain fallback")
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(fallback.calls, 0)

    def test_token_budget_can_fail_successful_provider(self):
        config = config_from(
            lambda d: d["budget"].update({"max_estimated_tokens": 50})
        )
        agent, *_ = make_agent(config=config, primary_tokens=120)
        result = agent.answer("u", "Explain retry")
        self.assertEqual(result.status, "unavailable")

    def test_cost_budget_can_fail_successful_provider(self):
        config = config_from(
            lambda d: d["budget"].update({"max_simulated_cost_usd": 0.0001})
        )
        agent, *_ = make_agent(config=config, primary_cost=0.001)
        result = agent.answer("u", "Explain retry")
        self.assertEqual(result.status, "unavailable")

    def test_primary_and_fallback_circuits_independent(self):
        config = config_from(
            lambda d: d["circuit_breaker"].update({"failure_threshold": 1})
        )
        agent, _, _, _, _ = make_agent(
            ["permanent"], ["success"], config=config
        )
        result = agent.answer("u", "Explain fallback")
        self.assertEqual(result.status, "ok")
        self.assertEqual(agent.primary_breaker.state, CircuitState.OPEN)
        self.assertEqual(agent.fallback_breaker.state, CircuitState.CLOSED)

    def test_open_primary_skips_to_fallback(self):
        config = config_from(
            lambda d: d["circuit_breaker"].update({"failure_threshold": 1})
        )
        agent, _, primary, fallback, _ = make_agent(
            ["permanent"], ["success"], config=config
        )
        agent.answer("u1", "Explain retry")
        calls = primary.calls
        result = agent.answer("u2", "Explain different fallback")
        self.assertEqual(primary.calls, calls)
        self.assertEqual(result.provider, fallback.name)

    def test_health_healthy(self):
        agent, *_ = make_agent()
        self.assertEqual(agent.health().status, "healthy")

    def test_health_degraded(self):
        config = config_from(
            lambda d: d["circuit_breaker"].update({"failure_threshold": 1})
        )
        agent, *_ = make_agent(["permanent"], ["success"], config=config)
        agent.answer("u", "Explain fallback")
        self.assertEqual(agent.health().status, "degraded")

    def test_health_unhealthy(self):
        config = config_from(
            lambda d: d["circuit_breaker"].update({"failure_threshold": 1})
        )
        agent, *_ = make_agent(["permanent"], ["permanent"], config=config)
        agent.answer("u", "Explain fallback")
        self.assertEqual(agent.health().status, "unhealthy")

    def test_health_cache_entries(self):
        agent, *_ = make_agent()
        agent.answer("u", "Explain caching")
        self.assertEqual(agent.health().cache_entries, 1)


class ScenarioMatrixTests(unittest.TestCase):
    """A compact matrix verifies many primary/fallback combinations."""

    CASES = [
        (["success"], ["success"], "ok", "mock-primary", False),
        (["transient", "success"], ["success"], "ok", "mock-primary", False),
        (["timeout", "success"], ["success"], "ok", "mock-primary", False),
        (["permanent"], ["success"], "ok", "local-fallback", True),
        (["transient"], ["success"], "ok", "local-fallback", True),
        (["timeout"], ["success"], "ok", "local-fallback", True),
        (["permanent"], ["permanent"], "unavailable", None, True),
        (["permanent"], ["transient"], "unavailable", None, True),
        (["transient"], ["permanent"], "unavailable", None, True),
    ]


def _make_scenario_test(index, primary_script, fallback_script, status, provider, degraded):
    def test(self):
        agent, *_ = make_agent(primary_script, fallback_script)
        result = agent.answer(f"case-{index}", "Explain observability and retries")
        self.assertEqual(result.status, status)
        self.assertEqual(result.provider, provider)
        self.assertEqual(result.degraded, degraded)
    return test


for _i, _case in enumerate(ScenarioMatrixTests.CASES, start=1):
    setattr(
        ScenarioMatrixTests,
        f"test_scenario_{_i:02d}",
        _make_scenario_test(_i, *_case),
    )


if __name__ == "__main__":
    unittest.main()
