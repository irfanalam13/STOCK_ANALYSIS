"""Per-WebSocket message rate limiter (sliding window).

In-process and lock-free — one instance per connection, so no Redis round-trip
on the hot receive path. Time is injectable for deterministic tests.
"""
import time
from collections import deque


class MessageRateLimiter:
    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._events: deque[float] = deque()

    def allow(self, now: float | None = None) -> bool:
        """Record a message; return False if it exceeds the window budget."""
        now = time.monotonic() if now is None else now
        cutoff = now - self.window
        while self._events and self._events[0] <= cutoff:
            self._events.popleft()
        if len(self._events) >= self.limit:
            return False
        self._events.append(now)
        return True
