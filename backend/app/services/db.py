"""Async database connection pool for direct Postgres queries (text-to-SQL)."""

from __future__ import annotations

import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return (and lazily create) a shared asyncpg connection pool."""
    global _pool
    if _pool is None:
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not configured — text-to-SQL requires a "
                "direct Postgres connection string"
            )
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=1,
            max_size=5,
        )
    return _pool


async def close_pool() -> None:
    """Gracefully close the pool (call on app shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
