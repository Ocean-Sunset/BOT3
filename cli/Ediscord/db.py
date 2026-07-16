"""
Ediscord database module.
Writes bot stats and guild data directly to Neon PostgreSQL.
"""

import os
import time
import json
import logging

logger = logging.getLogger(__name__)

_pool = None


async def get_pool():
    global _pool
    if _pool is not None:
        return _pool
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.warning("DATABASE_URL not set — Neon sync disabled.")
        return None
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3)
        logger.info("Connected to Neon PostgreSQL.")
        return _pool
    except Exception as e:
        logger.error(f"Failed to connect to Neon: {e}")
        _pool = None
        return None


async def push_bot_stats(data: dict):
    pool = await get_pool()
    if pool is None:
        return
    now = time.time()
    try:
        async with pool.acquire() as conn:
            for k, v in data.items():
                await conn.execute(
                    "INSERT INTO bot_stats (key, value, updated_at) VALUES ($1, $2, $3) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at",
                    k, str(v), now,
                )
    except Exception as e:
        logger.error(f"push_bot_stats failed: {e}")


async def push_guild_data(guilds: list):
    pool = await get_pool()
    if pool is None:
        return
    now = time.time()
    try:
        async with pool.acquire() as conn:
            for g in guilds:
                gid = str(g.get("id", ""))
                await conn.execute(
                    "INSERT INTO guild_data (guild_id, data, updated_at) VALUES ($1, $2::jsonb, $3) "
                    "ON CONFLICT (guild_id) DO UPDATE SET data = EXCLUDED.data, updated_at = EXCLUDED.updated_at",
                    gid, json.dumps(g), now,
                )
    except Exception as e:
        logger.error(f"push_guild_data failed: {e}")


async def push_mod_event(guild_id: str, user_id: str, user_name: str, action: str, reason: str = ""):
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO mod_log (guild_id, user_id, user_name, action, reason, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                str(guild_id), str(user_id), user_name, action, reason, time.time(),
            )
    except Exception as e:
        logger.error(f"push_mod_event failed: {e}")
