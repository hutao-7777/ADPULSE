"""In-memory sliding-window rate limiter for auth endpoints."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Simple sliding-window rate limiter per client IP."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, request: Request) -> bool:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window_seconds
        timestamps = self._clients[client_ip]
        # Prune expired entries
        self._clients[client_ip] = [t for t in timestamps if t > cutoff]
        if len(self._clients[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {self.window_seconds}s.",
            )
        self._clients[client_ip].append(now)
        return True


login_rate_limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)
register_rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=3600)
