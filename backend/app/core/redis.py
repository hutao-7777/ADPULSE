"""Async Redis client configuration and helpers.

Redis is used for caching, distributed locks, rate limiting, and RTB hot data.
The client gracefully falls back to no-op behavior when REDIS_URL is unavailable
or when running in SQLite demo mode.
"""

from typing import Any, Optional

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

_pool: Optional[ConnectionPool] = None
_redis: Optional[Redis] = None


def get_redis_pool() -> Optional[ConnectionPool]:
    """Return the shared Redis connection pool, or None if not configured."""
    global _pool
    if _pool is None and settings.REDIS_URL:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_MAX_CONNECTIONS,
            decode_responses=True,
        )
    return _pool


def get_redis() -> Optional[Redis]:
    """Return the shared async Redis client, or None if not configured."""
    global _redis
    if _redis is None:
        pool = get_redis_pool()
        if pool is not None:
            _redis = Redis(connection_pool=pool)
    return _redis


async def close_redis() -> None:
    """Close the shared Redis client and reset the pool."""
    global _redis, _pool
    if _redis is not None:
        await _redis.close()
        _redis = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


class NoOpRedis:
    """Fallback Redis-like client that does nothing, for demo/SQLite mode."""

    async def get(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    async def set(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    async def setex(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    async def delete(self, *_args: Any, **_kwargs: Any) -> int:
        return 0

    async def exists(self, *_args: Any, **_kwargs: Any) -> int:
        return 0

    async def hgetall(self, *_args: Any, **_kwargs: Any) -> dict:
        return {}

    async def hset(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    async def expire(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    async def lock(self, *_args: Any, **_kwargs: Any):
        class _NoOpLock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        return _NoOpLock()


async def get_redis_or_noop() -> Redis | NoOpRedis:
    """Return the real Redis client if available, otherwise a no-op fallback."""
    client = get_redis()
    if client is None:
        return NoOpRedis()
    try:
        await client.ping()
    except Exception:
        return NoOpRedis()
    return client
