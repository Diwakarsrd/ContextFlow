"""In-memory rate limiter for failed authentication attempts.

Scope and honesty check: this is a single-process, in-memory sliding
window — it resets on restart and doesn't coordinate across multiple
API server replicas. That's a real limitation for a horizontally-scaled
deployment (tracked in ROADMAP.md — a Redis-backed limiter is the
natural fix once that matters). For a single-instance deployment, which
is what this project supports today, it meaningfully slows naive
brute-force key guessing without adding an external dependency.
"""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_attempts: int = 10, window_seconds: float = 60.0) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def record_failure(self, identity: str) -> None:
        now = time.time()
        self._attempts[identity] = [
            t for t in self._attempts[identity] if now - t < self.window_seconds
        ] + [now]

    def record_success(self, identity: str) -> None:
        """A successful auth clears the failure count for that identity —
        legitimate clients that briefly typo a key aren't punished
        indefinitely."""
        self._attempts.pop(identity, None)

    def is_blocked(self, identity: str) -> bool:
        now = time.time()
        recent = [t for t in self._attempts.get(identity, []) if now - t < self.window_seconds]
        self._attempts[identity] = recent
        return len(recent) >= self.max_attempts
