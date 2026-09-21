"""Small in-process protection for the paid public-answer endpoint.

This is intentionally a deployment baseline, not a distributed quota system:
one Railway replica owns one set of counters.  A future multi-replica service
should move this responsibility to an edge or shared Redis-backed limiter.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Callable


@dataclass
class PublicAnswerRateLimiter:
    max_requests: int
    window_seconds: float
    clock: Callable[[], float] = monotonic
    _requests: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: Lock = field(default_factory=Lock)

    def allow(self, client_id: str) -> tuple[bool, int]:
        """Return whether a request may proceed and a conservative retry delay."""

        now = self.clock()
        with self._lock:
            timestamps = self._requests[client_id]
            while timestamps and now - timestamps[0] >= self.window_seconds:
                timestamps.popleft()
            if len(timestamps) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - timestamps[0])) + 1)
                return False, retry_after
            timestamps.append(now)
            return True, 0


def public_client_id(forwarded_for: str | None, fallback: str | None) -> str:
    """Use the final proxy-provided hop, falling back to the socket address."""

    if forwarded_for:
        candidate = forwarded_for.rsplit(",", maxsplit=1)[-1].strip()
        if candidate:
            return candidate
    return fallback or "unknown"
