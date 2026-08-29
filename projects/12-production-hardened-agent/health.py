"""Health snapshot helpers."""

from __future__ import annotations

from models import CircuitState, HealthSnapshot


def build_health_snapshot(agent) -> HealthSnapshot:
    primary_state = agent.primary_breaker.state.value
    fallback_state = agent.fallback_breaker.state.value

    if (
        agent.primary_breaker.state == CircuitState.OPEN
        and agent.fallback_breaker.state == CircuitState.OPEN
    ):
        status = "unhealthy"
    elif (
        agent.primary_breaker.state == CircuitState.OPEN
        or agent.fallback_breaker.state == CircuitState.OPEN
    ):
        status = "degraded"
    else:
        status = "healthy"

    return HealthSnapshot(
        status=status,
        primary_circuit=primary_state,
        fallback_circuit=fallback_state,
        cache_entries=len(agent.cache),
        metrics=agent.metrics.snapshot(),
    )
