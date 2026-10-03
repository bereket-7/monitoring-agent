"""Request rate limiting with Redis primary and in-memory fallback."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from redis.asyncio import Redis

from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)


class InMemoryRateLimiter:
    """Process-local sliding window limiter for tests and Redis outages."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


_memory_limiter = InMemoryRateLimiter()


async def allow_request(
    *,
    key: str,
    settings: Settings,
    redis_client: Redis[str] | None = None,
) -> bool:
    """Return True when the caller remains under the configured rate limit."""
    limit = settings.rate_limit_requests_per_minute
    window = 60
    if limit <= 0:
        return True

    if redis_client is not None:
        try:
            redis_key = f"rate:{key}:{int(time.time() // window)}"
            count = await redis_client.incr(redis_key)
            if count == 1:
                await redis_client.expire(redis_key, window + 1)
            return int(count) <= limit
        except Exception as exc:
            logger.warning("rate_limit_redis_failed", error=str(exc))

    return _memory_limiter.allow(key, limit=limit, window_seconds=window)


def reset_memory_limiter() -> None:
    """Test helper to clear in-memory buckets."""
    global _memory_limiter
    _memory_limiter = InMemoryRateLimiter()
