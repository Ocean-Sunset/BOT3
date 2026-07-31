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


def parse_settings(raw, defaults: dict) -> dict:
    """Safely merge a stored settings value (dict or JSON string) with defaults."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return dict(defaults)
    if isinstance(raw, dict):
        return {**defaults, **raw}
    return dict(defaults)


async def get_pool():
    global _pool
    if _pool is not None:
        return _pool
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.warning("DATABASE_URL not set - Neon sync disabled.")
        return None
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3)
        logger.info("Connected to Neon PostgreSQL.")
        await _ensure_tables()
        return _pool
    except Exception as e:
        logger.error(f"Failed to connect to Neon: {e}")
        _pool = None
        return None


async def _ensure_tables():
    """Create required tables if they don't exist (self-healing)."""
    pool = _pool
    if pool is None:
        return
    statements = [
        "CREATE TABLE IF NOT EXISTS bot_stats (key TEXT PRIMARY KEY, value TEXT, updated_at DOUBLE PRECISION)",
        "CREATE TABLE IF NOT EXISTS guild_data (guild_id TEXT PRIMARY KEY, data JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION)",
        "CREATE TABLE IF NOT EXISTS mod_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS mod_log (id SERIAL PRIMARY KEY, guild_id TEXT, user_id TEXT, user_name TEXT, action TEXT, reason TEXT DEFAULT '', moderator TEXT DEFAULT '', created_at DOUBLE PRECISION)",
        "CREATE TABLE IF NOT EXISTS mod_actions (id SERIAL PRIMARY KEY, guild_id TEXT, action TEXT, target_id TEXT, target_name TEXT DEFAULT '', reason TEXT DEFAULT '', moderator TEXT DEFAULT '', duration INTEGER, status TEXT DEFAULT 'pending', created_at DOUBLE PRECISION)",
    ]
    try:
        async with pool.acquire() as conn:
            for stmt in statements:
                await conn.execute(stmt)
            # Add columns to existing tables (safe no-op if already present)
            await conn.execute("ALTER TABLE mod_log ADD COLUMN IF NOT EXISTS moderator TEXT DEFAULT ''")
            await conn.execute("ALTER TABLE mod_actions ADD COLUMN IF NOT EXISTS moderator TEXT DEFAULT ''")
        logger.info("Ensured database tables exist.")
    except Exception as e:
        logger.error(f"ensure_tables failed: {e}")


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


async def push_mod_event(guild_id: str, user_id: str, user_name: str, action: str, reason: str = "", moderator: str = ""):
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO mod_log (guild_id, user_id, user_name, action, reason, moderator, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                str(guild_id), str(user_id), user_name, action, reason, moderator, time.time(),
            )
    except Exception as e:
        logger.error(f"push_mod_event failed: {e}")


async def fetch_mod_settings(guild_id: str) -> dict:
    pool = await get_pool()
    if pool is None:
        return {}
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT settings FROM mod_settings WHERE guild_id = $1", str(guild_id))
            if row:
                d = row["settings"]
                if isinstance(d, str):
                    return json.loads(d)
                return d if isinstance(d, dict) else {}
    except Exception as e:
        logger.error(f"fetch_mod_settings failed: {e}")
    return {}


async def fetch_pending_actions() -> list:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, guild_id, action, target_id, target_name, reason, duration "
                "FROM mod_actions WHERE status = 'pending' ORDER BY created_at ASC LIMIT 50"
            )
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"fetch_pending_actions failed: {e}")
    return []


async def complete_action(action_id: int, status: str = "completed"):
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE mod_actions SET status = $1 WHERE id = $2", status, action_id)
    except Exception as e:
        logger.error(f"complete_action failed: {e}")
