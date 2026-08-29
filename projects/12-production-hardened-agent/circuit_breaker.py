"""CLOSED / OPEN / HALF_OPEN circuit breaker."""

from __future__ import annotations

from models import CircuitState
from errors import CircuitOpenError


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int,
        recovery_timeout_ms: int,
        half_open_max_calls: int = 1,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be positive.")
        if recovery_timeout_ms < 1:
            raise ValueError("recovery_timeout_ms must be positive.")
        if half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be positive.")

        self.failure_threshold = failure_threshold
        self.recovery_timeout_ms = recovery_timeout_ms
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at_ms: float | None = None
        self.half_open_calls = 0

    def before_call(self, now_ms: float) -> None:
        if self.state == CircuitState.OPEN:
            assert self.opened_at_ms is not None
            if now_ms - self.opened_at_ms >= self.recovery_timeout_ms:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise CircuitOpenError("Circuit breaker is open.")

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitOpenError("Circuit breaker half-open probe limit reached.")
            self.half_open_calls += 1

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at_ms = None
        self.half_open_calls = 0

    def record_failure(self, now_ms: float) -> bool:
        opened = False

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at_ms = now_ms
            self.failure_count = self.failure_threshold
            self.half_open_calls = 0
            return True

        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at_ms = now_ms
            self.half_open_calls = 0
            opened = True

        return opened
