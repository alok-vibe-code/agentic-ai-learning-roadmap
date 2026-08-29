"""Per-principal sliding-window rate limiter."""

from __future__ import annotations

from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_ms: int) -> None:
        if max_requests < 1 or window_ms < 1:
            raise ValueError("Rate-limit configuration must be positive.")
        self.max_requests = max_requests
        self.window_ms = window_ms
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, principal: str, now_ms: float) -> tuple[bool, int]:
        queue = self._events[principal]
        cutoff = now_ms - self.window_ms

        while queue and queue[0] <= cutoff:
            queue.popleft()

        if len(queue) >= self.max_requests:
            return False, len(queue)

        queue.append(now_ms)
        return True, len(queue)

    def current(self, principal: str, now_ms: float) -> int:
        queue = self._events[principal]
        cutoff = now_ms - self.window_ms
        while queue and queue[0] <= cutoff:
            queue.popleft()
        return len(queue)
