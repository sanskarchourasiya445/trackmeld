"""In-process rate limiting for CPU-expensive endpoints.

Provides lightweight, in-memory sliding-window request throttling
to prevent CPU/worker starvation on solver and planning endpoints.
Production deployments should front this with an API Gateway or Redis.

Trusted-proxy support
---------------------
Set TRUSTED_PROXY_IPS in the environment (comma-separated CIDR or exact IPs).
Only when the immediate TCP peer (request.client.host) is in that list will
X-Forwarded-For be honoured to extract the real client IP.
If TRUSTED_PROXY_IPS is empty or not set, the raw TCP peer IP is always used.
"""

import ipaddress
import os
import time
import threading
from typing import Dict, List, Optional, Tuple

from fastapi import Request, HTTPException, status


# ---------------------------------------------------------------------------
# Trusted proxy resolution
# ---------------------------------------------------------------------------

def _parse_trusted_proxies(raw: str) -> List[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse comma-separated IP/CIDR strings into network objects."""
    networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            networks.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            # Ignore malformed entries rather than crashing at startup
            pass
    return networks


def _resolve_client_ip(request: Request) -> str:
    """Return the real client IP, honoring X-Forwarded-For only when the
    immediate TCP peer is a configured trusted proxy."""
    raw_trusted = os.environ.get("TRUSTED_PROXY_IPS", "")
    trusted_networks = _parse_trusted_proxies(raw_trusted)

    peer_host = request.client.host if request.client else "unknown"

    if trusted_networks and peer_host != "unknown":
        try:
            peer_addr = ipaddress.ip_address(peer_host)
            peer_is_trusted = any(peer_addr in net for net in trusted_networks)
        except ValueError:
            peer_is_trusted = False

        if peer_is_trusted:
            forwarded = request.headers.get("X-Forwarded-For", "")
            # X-Forwarded-For: client, proxy1, proxy2 — leftmost is real client
            first = forwarded.split(",")[0].strip()
            if first:
                return first

    return peer_host


# ---------------------------------------------------------------------------
# Core rate limiter
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Shared limiters
# ---------------------------------------------------------------------------

# Planning-run submission: 60 per 60 s per client
planning_rate_limiter = InMemoryRateLimiter(max_requests=60, window_seconds=60.0)

# Expensive compute (solve, validate, diagnostics, copilot): 30 per 60 s per client
compute_rate_limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60.0)


# ---------------------------------------------------------------------------
# FastAPI dependency factories
# ---------------------------------------------------------------------------

def _make_rate_limit_dependency(limiter: InMemoryRateLimiter, description: str):
    """Return a FastAPI dependency that enforces the given limiter."""
    async def _enforce(request: Request) -> None:
        client_ip = _resolve_client_ip(request)
        auth_header = request.headers.get("Authorization", "")
        key = f"{client_ip}:{auth_header[:30]}"

        allowed, remaining, retry_after = limiter.check_rate_limit(key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"{description} rate limit exceeded. Please wait before retrying.",
                        "details": {"retry_after_seconds": round(retry_after, 1)},
                    }
                },
                headers={"Retry-After": str(int(retry_after))},
            )

    return _enforce


# Planning-run submission throttle (POST /api/v1/planning-runs)
enforce_planning_rate_limit = _make_rate_limit_dependency(
    planning_rate_limiter,
    "Planning job submission",
)

# Heavy compute throttle (solve, validate, diagnostics, copilot/explain)
enforce_compute_rate_limit = _make_rate_limit_dependency(
    compute_rate_limiter,
    "Computation",
)
