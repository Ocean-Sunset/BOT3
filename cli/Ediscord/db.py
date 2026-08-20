"""
Ediscord database module.
Writes bot stats and guild data directly to the database.
Uses pyturso with embedded replica for fast local reads + cloud-synced writes.
"""

import os
import time
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_conn = None
_sync_task = None
_SETTINGS_CACHE = {}
_SETTINGS_CACHE_TTL = 30.0


class Record:
    """Dict-like wrapper for DB rows, mimicking asyncpg Record access."""
    __slots__ = ("_columns", "_values")

    def __init__(self, columns: list, values: tuple):
        self._columns = columns
        self._values = values

    def __getitem__(self, key):
        try:
            idx = self._columns.index(key)
            return self._values[idx]
        except (ValueError, IndexError):
            raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        return key in self._columns

    def __iter__(self):
        return zip(self._columns, self._values)

    def keys(self):
        return self._columns

    def values(self):
        return self._values

    def items(self):
        return zip(self._columns, self._values)

    def __len__(self):
        return len(self._columns)

    def __repr__(self):
        return f"Record({dict(self)})"

    def __eq__(self, other):
        if isinstance(other, dict):
            return dict(self) == other
        return NotImplemented


def _wrap_rows(cursor) -> List[Record]:
    """Convert a libsql cursor to a list of Record objects."""
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return [Record(columns, row) for row in cursor.fetchall()]


def _wrap_row(cursor) -> Optional[Record]:
    """Convert a libsql cursor to a single Record or None."""
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return Record(columns, row)


class _ConnWrapper:
    """Async-compatible wrapper around a sync libsql connection."""

    def __init__(self, conn):
        self._conn = conn

    async def fetchrow(self, sql: str, *args) -> Optional[Record]:
        def _do():
            return _wrap_row(self._conn.execute(sql, args))
        return await asyncio.to_thread(_do)

    async def fetch(self, sql: str, *args) -> List[Record]:
        def _do():
            return _wrap_rows(self._conn.execute(sql, args))
        return await asyncio.to_thread(_do)

    async def execute(self, sql: str, *args) -> str:
        def _do():
            self._conn.execute(sql, args)
            self._conn.commit()
        await asyncio.to_thread(_do)
        return "OK"


class _PoolWrapper:
    """Async-compatible pool that mimics asyncpg's pool interface."""

    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return self

    async def __aenter__(self):
        return _ConnWrapper(self._conn)

    async def __aexit__(self, *args):
        pass

    async def fetchrow(self, sql: str, *args) -> Optional[Record]:
        def _do():
            return _wrap_row(self._conn.execute(sql, args))
        return await asyncio.to_thread(_do)

    async def fetch(self, sql: str, *args) -> List[Record]:
        def _do():
            return _wrap_rows(self._conn.execute(sql, args))
        return await asyncio.to_thread(_do)

    async def execute(self, sql: str, *args) -> str:
        def _do():
            self._conn.execute(sql, args)
            self._conn.commit()
        await asyncio.to_thread(_do)
        return "OK"


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
    """Get the database connection pool (actually a single embedded replica connection)."""
    global _conn, _sync_task
    if _conn is not None:
        return _PoolWrapper(_conn)
    url = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url:
        logger.warning("TURSO_DATABASE_URL not set - database sync disabled.")
        return None
    try:
        if token:
            import libsql_experimental as libsql
            _conn = libsql.connect(
                "prowl.db",
                sync_url=url,
                auth_token=token,
            )
            _conn.sync()
            logger.info("Connected to database (embedded replica).")
        else:
            logger.warning("TURSO_AUTH_TOKEN not set - database sync disabled.")
            return None
        await _ensure_tables()
        # Start background sync task
        if _sync_task is None:
            _sync_task = asyncio.create_task(_background_sync())
        return _PoolWrapper(_conn)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        _conn = None
        return None


async def _background_sync():
    """Periodically sync the embedded replica with the cloud primary."""
    while True:
        try:
            await asyncio.sleep(60)
            if _conn is not None:
                await asyncio.to_thread(_conn.sync)
        except Exception as e:
            logger.debug(f"Background sync failed: {e}")


def get_settings_cache_key(table: str, guild_id) -> tuple:
    return (table, str(guild_id))


def get_cached_settings(table: str, guild_id, defaults: dict) -> dict:
    key = get_settings_cache_key(table, guild_id)
    entry = _SETTINGS_CACHE.get(key)
    if entry and time.time() - entry["ts"] < _SETTINGS_CACHE_TTL:
        return dict(entry["value"])
    return dict(defaults)


async def load_cached_settings(table: str, guild_id, defaults: dict) -> dict:
    key = get_settings_cache_key(table, guild_id)
    cached = get_cached_settings(table, guild_id, defaults)
    if cached != defaults:
        return cached
    pool = await get_pool()
    if not pool:
        return dict(defaults)
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(f"SELECT settings FROM {table} WHERE guild_id = ?", str(guild_id))
            value = parse_settings(row["settings"], defaults) if row else dict(defaults)
        _SETTINGS_CACHE[key] = {"value": value, "ts": time.time()}
        return value
    except Exception as e:
        logger.debug(f"load_cached_settings failed for {table}/{guild_id}: {e}")
        return dict(defaults)


async def save_cached_settings(table: str, guild_id, settings: dict):
    pool = await get_pool()
    if pool is None:
        return
    key = get_settings_cache_key(table, guild_id)
    _SETTINGS_CACHE[key] = {"value": dict(settings), "ts": time.time()}
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                f"INSERT INTO {table} (guild_id, settings) VALUES (?, ?) ON CONFLICT (guild_id) DO UPDATE SET settings = ?",
                str(guild_id), json.dumps(settings), json.dumps(settings),
            )
    except Exception as e:
        logger.debug(f"save_cached_settings failed for {table}/{guild_id}: {e}")


async def _ensure_tables():
    """Create required tables if they don't exist (self-healing)."""
    pool = await get_pool()
    if pool is None:
        return
    statements = [
        "CREATE TABLE IF NOT EXISTS bot_stats (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS guild_data (guild_id TEXT PRIMARY KEY, data TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS mod_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS mod_log (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, user_id TEXT, user_name TEXT, action TEXT, reason TEXT DEFAULT '', moderator TEXT DEFAULT '', created_at REAL)",
        "CREATE TABLE IF NOT EXISTS mod_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, action TEXT, target_id TEXT, target_name TEXT DEFAULT '', reason TEXT DEFAULT '', moderator TEXT DEFAULT '', duration INTEGER, status TEXT DEFAULT 'pending', created_at REAL)",
        "CREATE TABLE IF NOT EXISTS muted_users (guild_id TEXT, user_id TEXT, user_name TEXT DEFAULT '', reason TEXT DEFAULT '', end_ts REAL, PRIMARY KEY (guild_id, user_id))",
        "CREATE TABLE IF NOT EXISTS ai_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS welcome_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS verify_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS leveling_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS leveling_data (guild_id TEXT NOT NULL, user_id TEXT NOT NULL, xp INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, user_id))",
        "CREATE TABLE IF NOT EXISTS automation_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS autoresponder (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, trigger TEXT NOT NULL, response TEXT NOT NULL, match_type TEXT NOT NULL DEFAULT 'contains', created_at REAL)",
        "ALTER TABLE autoresponder ADD COLUMN IF NOT EXISTS channel_id TEXT",
        "ALTER TABLE autoresponder ADD COLUMN IF NOT EXISTS cooldown INTEGER DEFAULT 0",
        "CREATE TABLE IF NOT EXISTS social_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS invite_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS invite_stats (guild_id TEXT NOT NULL, inviter_id TEXT NOT NULL, code TEXT NOT NULL, uses INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, inviter_id, code))",
        "CREATE TABLE IF NOT EXISTS ticket_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS ticket_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, channel_id TEXT NOT NULL, user_id TEXT NOT NULL, transcript TEXT NOT NULL, closed_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS member_history (guild_id TEXT NOT NULL, timestamp REAL NOT NULL, member_count INTEGER NOT NULL, PRIMARY KEY (guild_id, timestamp))",
        "CREATE TABLE IF NOT EXISTS message_history (guild_id TEXT NOT NULL, timestamp REAL NOT NULL, message_count INTEGER NOT NULL, PRIMARY KEY (guild_id, timestamp))",
        "CREATE TABLE IF NOT EXISTS captcha_codes (code TEXT PRIMARY KEY, provider TEXT NOT NULL, guild_id TEXT DEFAULT '', user_id TEXT DEFAULT '', created_at REAL NOT NULL, expires_at REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS automation_graph (guild_id TEXT PRIMARY KEY, nodes TEXT NOT NULL DEFAULT '[]', connections TEXT NOT NULL DEFAULT '[]', updated_at REAL NOT NULL DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS automation_runs (guild_id TEXT NOT NULL, bucket_ts REAL NOT NULL, count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, bucket_ts))",
        "CREATE TABLE IF NOT EXISTS automation_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL DEFAULT 0)",
        "CREATE INDEX IF NOT EXISTS idx_automation_logs_guild ON automation_logs (guild_id, id DESC)",
        "ALTER TABLE captcha_codes ADD COLUMN IF NOT EXISTS guild_id TEXT DEFAULT ''",
        "ALTER TABLE captcha_codes ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT ''",
    ]
    try:
        async with pool.acquire() as conn:
            for stmt in statements:
                await conn.execute(stmt)
            await conn.execute("ALTER TABLE mod_log ADD COLUMN IF NOT EXISTS moderator TEXT DEFAULT ''")
            await conn.execute("ALTER TABLE mod_actions ADD COLUMN IF NOT EXISTS moderator TEXT DEFAULT ''")
            await conn.execute("ALTER TABLE mod_actions ADD COLUMN IF NOT EXISTS error TEXT DEFAULT ''")
            await conn.execute("ALTER TABLE mod_actions ADD COLUMN IF NOT EXISTS processed_at REAL")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_autoresponder_guild ON autoresponder (guild_id)")
        logger.info("Ensured database tables exist.")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("Schema was already created concurrently.")
        else:
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
                    "INSERT INTO bot_stats (key, value, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                    k, str(v), now,
                )
    except Exception as e:
        logger.error(f"push_bot_stats failed: {e}")


async def create_captcha_code(provider: str, guild_id: str = "", user_id: str = "", ttl_hours: int = 1) -> str:
    """Generate a short-lived single-use code that unlocks the captcha solve page."""
    pool = await get_pool()
    if pool is None:
        return ""
    import secrets
    code = secrets.token_urlsafe(12)
    now = time.time()
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM captcha_codes WHERE expires_at < ?", now)
            await conn.execute(
                "INSERT INTO captcha_codes (code, provider, guild_id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                code, provider, str(guild_id or ""), str(user_id or ""), now, now + ttl_hours * 3600,
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
                    "INSERT INTO guild_data (guild_id, data, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT (guild_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
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
                "INSERT INTO mod_log (guild_id, user_id, user_name, action, reason, moderator, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
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
            row = await conn.fetchrow("SELECT settings FROM mod_settings WHERE guild_id = ?", str(guild_id))
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
                "UPDATE mod_actions SET status = ?, error = ?, processed_at = unixepoch() WHERE id = ?",
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
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (guild_id, user_id) DO UPDATE SET user_name = ?, reason = ?, end_ts = ?",
                str(guild_id), str(user_id), user_name, reason, end_ts, user_name, reason, end_ts,
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
                "DELETE FROM muted_users WHERE guild_id = ? AND user_id = ?",
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
                "WHERE guild_id = ? ORDER BY end_ts ASC",
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
                    await conn.execute(f"DELETE FROM {table} WHERE guild_id = ?", gid)
                except Exception:
                    pass  # table may not exist yet
        logger.info(f"Deleted all data for guild {gid}.")
    except Exception as e:
        logger.error(f"delete_guild_data failed for {gid}: {e}")
