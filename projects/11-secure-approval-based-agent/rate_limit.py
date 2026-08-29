from __future__ import annotations
from collections import defaultdict, deque

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        if max_requests < 1 or window_seconds < 1:
            raise ValueError("Rate-limit values must be positive.")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, principal_id: str, now: float) -> tuple[bool, int]:
        queue = self._events[principal_id]
        cutoff = now - self.window_seconds
        while queue and queue[0] <= cutoff:
            queue.popleft()
        if len(queue) >= self.max_requests:
            return False, len(queue)
        queue.append(now)
        return True, len(queue)

    def count(self, principal_id: str, now: float) -> int:
        queue = self._events[principal_id]
        cutoff = now - self.window_seconds
        while queue and queue[0] <= cutoff:
            queue.popleft()
        return len(queue)
