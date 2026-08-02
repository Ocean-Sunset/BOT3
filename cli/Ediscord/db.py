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


async def setup_action_listener(callback):
    """Open a dedicated connection LISTENing on 'prowl_actions' for instant wakeups."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    try:
        import asyncpg
        conn = await asyncpg.connect(dsn)
        await conn.add_listener("prowl_actions", callback)
        return conn
    except Exception as e:
        logger.error(f"setup_action_listener failed: {e}")
        try:
            await conn.close()
        except Exception:
            pass
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
        "CREATE TABLE IF NOT EXISTS muted_users (guild_id TEXT, user_id TEXT, user_name TEXT DEFAULT '', reason TEXT DEFAULT '', end_ts DOUBLE PRECISION, PRIMARY KEY (guild_id, user_id))",
        "CREATE TABLE IF NOT EXISTS ai_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS welcome_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS verify_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS leveling_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS leveling_data (guild_id TEXT NOT NULL, user_id TEXT NOT NULL, xp INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, user_id))",
        "CREATE TABLE IF NOT EXISTS automation_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS autoresponder (id SERIAL PRIMARY KEY, guild_id TEXT NOT NULL, trigger TEXT NOT NULL, response TEXT NOT NULL, match_type TEXT NOT NULL DEFAULT 'contains', created_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "ALTER TABLE autoresponder ADD COLUMN IF NOT EXISTS channel_id TEXT",
        "ALTER TABLE autoresponder ADD COLUMN IF NOT EXISTS cooldown INTEGER DEFAULT 0",
        "CREATE TABLE IF NOT EXISTS social_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS invite_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS invite_stats (guild_id TEXT NOT NULL, inviter_id TEXT NOT NULL, code TEXT NOT NULL, uses INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, inviter_id, code))",
        "CREATE TABLE IF NOT EXISTS ticket_settings (guild_id TEXT PRIMARY KEY, settings JSONB NOT NULL DEFAULT '{}', updated_at DOUBLE PRECISION DEFAULT (extract(epoch from now())))",
        "CREATE TABLE IF NOT EXISTS ticket_logs (id SERIAL PRIMARY KEY, guild_id TEXT NOT NULL, channel_id TEXT NOT NULL, user_id TEXT NOT NULL, transcript TEXT NOT NULL, closed_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS member_history (guild_id TEXT NOT NULL, timestamp DOUBLE PRECISION NOT NULL, member_count INTEGER NOT NULL, PRIMARY KEY (guild_id, timestamp))",
        "CREATE TABLE IF NOT EXISTS message_history (guild_id TEXT NOT NULL, timestamp DOUBLE PRECISION NOT NULL, message_count INTEGER NOT NULL, PRIMARY KEY (guild_id, timestamp))",
        "CREATE TABLE IF NOT EXISTS captcha_codes (code TEXT PRIMARY KEY, provider TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL, used BOOLEAN NOT NULL DEFAULT FALSE)",
    ]
    try:
        async with pool.acquire() as conn:
            for stmt in statements:
                await conn.execute(stmt)
            # Add columns to existing tables (safe no-op if already present)
            await conn.execute("ALTER TABLE mod_log ADD COLUMN IF NOT EXISTS moderator TEXT DEFAULT ''")
            await conn.execute("ALTER TABLE mod_actions ADD COLUMN IF NOT EXISTS moderator TEXT DEFAULT ''")
            await conn.execute("ALTER TABLE mod_actions ADD COLUMN IF NOT EXISTS error TEXT DEFAULT ''")
            await conn.execute("ALTER TABLE mod_actions ADD COLUMN IF NOT EXISTS processed_at DOUBLE PRECISION")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_autoresponder_guild ON autoresponder (guild_id)")
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


async def create_captcha_code(provider: str, ttl_hours: int = 1) -> str:
    """Generate a short-lived single-use code that unlocks the captcha solve page."""
    pool = await get_pool()
    if pool is None:
        return ""
    import secrets
    code = secrets.token_urlsafe(12)
    now = time.time()
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM captcha_codes WHERE expires_at < $1", now)
            await conn.execute(
                "INSERT INTO captcha_codes (code, provider, created_at, expires_at) VALUES ($1, $2, $3, $4)",
                code, provider, now, now + ttl_hours * 3600,
            )
        return code
    except Exception as e:
        logger.error(f"create_captcha_code failed: {e}")
        return ""


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


async def complete_action(action_id: int, status: str = "completed", error: str = ""):
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE mod_actions SET status = $1, error = $2, processed_at = extract(epoch from now()) WHERE id = $3",
                status, error, action_id,
            )
    except Exception as e:
        logger.error(f"complete_action failed: {e}")


async def set_muted_user(guild_id, user_id, user_name="", reason="", end_ts=0):
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO muted_users (guild_id, user_id, user_name, reason, end_ts) "
                "VALUES ($1, $2, $3, $4, $5) "
                "ON CONFLICT (guild_id, user_id) DO UPDATE SET user_name = $3, reason = $4, end_ts = $5",
                str(guild_id), str(user_id), user_name, reason, end_ts,
            )
    except Exception as e:
        logger.error(f"set_muted_user failed: {e}")


async def remove_muted_user(guild_id, user_id):
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM muted_users WHERE guild_id = $1 AND user_id = $2",
                str(guild_id), str(user_id),
            )
    except Exception as e:
        logger.error(f"remove_muted_user failed: {e}")


async def fetch_muted_users(guild_id) -> list:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT guild_id, user_id, user_name, reason, end_ts FROM muted_users "
                "WHERE guild_id = $1 ORDER BY end_ts ASC",
                str(guild_id),
            )
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"fetch_muted_users failed: {e}")
        return []


GUILD_TABLES = [
    "guild_data", "mod_settings", "mod_log", "mod_actions", "muted_users",
    "ai_settings", "welcome_settings", "verify_settings", "leveling_settings", "leveling_data",
    "automation_settings", "autoresponder", "social_settings", "invite_settings", "invite_stats",
    "ticket_settings", "ticket_logs", "member_history", "message_history", "verify_logs",
]


async def delete_guild_data(guild_id):
    """Delete all rows for a guild across guild-scoped tables (called when the bot leaves/kicked)."""
    pool = await get_pool()
    if pool is None:
        return
    gid = str(guild_id)
    try:
        async with pool.acquire() as conn:
            for table in GUILD_TABLES:
                try:
                    await conn.execute(f"DELETE FROM {table} WHERE guild_id = $1", gid)
                except Exception:
                    pass  # table may not exist yet
        logger.info(f"Deleted all data for guild {gid}.")
    except Exception as e:
        logger.error(f"delete_guild_data failed for {gid}: {e}")
