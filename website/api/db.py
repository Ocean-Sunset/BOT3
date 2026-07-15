import os
import logging
import asyncpg

logger = logging.getLogger(__name__)
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool | None:
    global _pool
    if _pool is not None:
        return _pool
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.warning("DATABASE_URL not set")
        return None
    try:
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return _pool
    except Exception as e:
        logger.error(f"Failed to create pool: {e}")
        return None


async def query(sql: str, *args):
    pool = await get_pool()
    if pool is None:
        return []
    return await pool.fetch(sql, *args)


async def fetchrow(sql: str, *args):
    pool = await get_pool()
    if pool is None:
        return None
    return await pool.fetchrow(sql, *args)


async def fetchval(sql: str, *args):
    pool = await get_pool()
    if pool is None:
        return None
    return await pool.fetchval(sql, *args)


async def execute(sql: str, *args):
    pool = await get_pool()
    if pool is None:
        return None
    return await pool.execute(sql, *args)
