"""In-process rate limiting for CPU-expensive endpoints.

Provides lightweight, in-memory sliding-window request throttling
to prevent CPU/worker starvation on solver and planning endpoints.
Production deployments should front this with an API Gateway or Redis.
"""

import time
import threading
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    """Thread-safe, sliding-window rate limiter per client IP or authenticated identity."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._history: Dict[str, List[float]] = {}

    def _cleanup_old_requests(self, now: float) -> None:
        """Remove timestamps older than window."""
        cutoff = now - self.window_seconds
        for key in list(self._history.keys()):
            self._history[key] = [t for t in self._history[key] if t > cutoff]
            if not self._history[key]:
                del self._history[key]

    def check_rate_limit(self, client_key: str) -> Tuple[bool, int, float]:
        """Check if request is permitted.

        Returns:
            (allowed: bool, remaining: int, retry_after: float)
        """
        now = time.monotonic()
        with self._lock:
            self._cleanup_old_requests(now)
            timestamps = self._history.setdefault(client_key, [])
            if len(timestamps) >= self.max_requests:
                oldest = timestamps[0]
                retry_after = max(1.0, (oldest + self.window_seconds) - now)
                return False, 0, retry_after

            timestamps.append(now)
            remaining = self.max_requests - len(timestamps)
            return True, remaining, 0.0


# Shared default limiter for CPU-intensive planning and optimization endpoints:
# 60 solver runs per 60 seconds per client IP/identity
planning_rate_limiter = InMemoryRateLimiter(max_requests=60, window_seconds=60.0)


async def enforce_planning_rate_limit(request: Request) -> None:
    """FastAPI dependency to throttle heavy solver initiation endpoints."""
    # Key by authenticated user or client IP
    client_ip = request.client.host if request.client else "unknown"
    auth_header = request.headers.get("Authorization", "")
    key = f"{client_ip}:{auth_header[:30]}"

    allowed, remaining, retry_after = planning_rate_limiter.check_rate_limit(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Optimization rate limit exceeded. Please wait before submitting another solve.",
                    "details": {"retry_after_seconds": round(retry_after, 1)},
                }
            },
            headers={"Retry-After": str(int(retry_after))},
        )
