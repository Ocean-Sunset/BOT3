"""
Ediscord database module.
Writes bot stats and guild data directly to the database.
Uses Turso's HTTP API via aiohttp (already in requirements).
No external DB driver needed.
"""

import os
import time
import json
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

from Ediscord.cache import settings_cache

_url = None
_token = None
_ensure_done = False


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


def _to_http_url(url: str) -> str:
    """Convert libsql:// or ws:// URLs to https:// for the HTTP API, appending /v2/pipeline."""
    if url.startswith("libsql://"):
        base = "https://" + url[len("libsql://"):]
    elif url.startswith("ws://"):
        base = "http://" + url[len("ws://"):]
    elif url.startswith("wss://"):
        base = "https://" + url[len("wss://"):]
    else:
        base = url
    base = base.rstrip("/")
    if not base.endswith("/v2/pipeline"):
        base += "/v2/pipeline"
    return base


def _wrap_arg(value) -> dict:
    """Wrap a Python value as a Turso pipeline arg."""
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def _unwrap_cell(cell) -> str:
    """Extract a plain Python value from a Turso pipeline cell {type, value}."""
    if isinstance(cell, dict):
        return cell.get("value", "")
    return cell


def _rows_to_records(result: dict) -> List[Record]:
    """Convert a Turso pipeline result object to a list of Record objects."""
    cols = [c["name"] for c in result.get("cols", [])]
    rows = []
    for row in result.get("rows", []):
        rows.append(Record(cols, tuple(_unwrap_cell(c) for c in row)))
    return rows


async def _execute_http(sql: str, args=()) -> dict:
    """Execute a single SQL statement via Turso pipeline API, return result dict."""
    import aiohttp
    global _url, _token
    if not _url:
        raise RuntimeError("TURSO_DATABASE_URL not set")
    headers = {"Content-Type": "application/json"}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    body = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": [_wrap_arg(a) for a in (args or [])]}},
            {"type": "close"},
        ]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(_url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise RuntimeError(f"Turso HTTP {resp.status}: {data}")
            results = data.get("results", [])
            if not results:
                return {}
            first = results[0]
            if first.get("type") == "error":
                raise RuntimeError(f"Turso pipeline error: {first.get('error', {})}")
            return first.get("response", {}).get("result", {})


async def _execute_batch_http(statements: list) -> list:
    """Execute multiple SQL statements in one Turso pipeline request."""
    import aiohttp
    global _url, _token
    if not _url:
        raise RuntimeError("TURSO_DATABASE_URL not set")
    headers = {"Content-Type": "application/json"}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    requests = []
    for sql, args in statements:
        requests.append({"type": "execute", "stmt": {"sql": sql, "args": [_wrap_arg(a) for a in (args or [])]}})
    requests.append({"type": "close"})
    body = {"requests": requests}
    async with aiohttp.ClientSession() as session:
        async with session.post(_url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise RuntimeError(f"Turso HTTP {resp.status}: {data}")
            results = data.get("results", [])
            out = []
            for r in results:
                if r.get("type") == "error":
                    raise RuntimeError(f"Turso pipeline error: {r.get('error', {})}")
                out.append(r.get("response", {}).get("result", {}))
            return out


class _ConnWrapper:
    """Async-compatible wrapper matching the interface callers expect."""

    async def fetchrow(self, sql: str, *args) -> Optional[Record]:
        result = await _execute_http(sql, args)
        records = _rows_to_records(result)
        return records[0] if records else None

    async def fetch(self, sql: str, *args) -> List[Record]:
        result = await _execute_http(sql, args)
        return _rows_to_records(result)

    async def execute(self, sql: str, *args) -> str:
        await _execute_http(sql, args)
        return "OK"


class _PoolWrapper:
    """Mimics asyncpg pool interface — all callers use pool.acquire() as conn."""

    def acquire(self):
        return self

    async def __aenter__(self):
        return _ConnWrapper()

    async def __aexit__(self, *args):
        pass

    async def fetchrow(self, sql: str, *args) -> Optional[Record]:
        return await _ConnWrapper().fetchrow(sql, *args)

    async def fetch(self, sql: str, *args) -> List[Record]:
        return await _ConnWrapper().fetch(sql, *args)

    async def execute(self, sql: str, *args) -> str:
        return await _ConnWrapper().execute(sql, *args)


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
    """Get the database connection wrapper (HTTP to Turso)."""
    global _url, _token, _ensure_done
    if _url is None:
        raw = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("DATABASE_URL")
        _url = _to_http_url(raw) if raw else None
        _token = os.environ.get("TURSO_AUTH_TOKEN")
    if not _url:
        logger.warning("TURSO_DATABASE_URL not set - database disabled.")
        return None
    try:
        if not _ensure_done:
            await _ensure_tables()
            _ensure_done = True
        return _PoolWrapper()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return None


def get_settings_cache_key(table: str, guild_id) -> tuple:
    return (table, str(guild_id))


async def load_cached_settings(table: str, guild_id, defaults: dict) -> dict:
    """Load settings from the cache, falling back to Turso on a miss.

    Turso is the source of truth. A failed Turso read is NOT cached (the loader
    returns ``None``), so a Turso outage cannot poison the cache; the next call
    simply retries Turso. A missing row caches the effective defaults, which is
    correct because defaults are the real value in that case.
    """
    key = get_settings_cache_key(table, guild_id)

    async def _load():
        pool = await get_pool()
        if not pool:
            return None
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT settings FROM {table} WHERE guild_id = ?", str(guild_id)
                )
            if row is None:
                return dict(defaults)
            return parse_settings(row["settings"], defaults)
        except Exception as e:
            logger.debug(f"load_cached_settings failed for {table}/{guild_id}: {e}")
            return None

    value = await settings_cache.get_or_load(key, _load)
    return dict(value) if value is not None else dict(defaults)


async def save_cached_settings(table: str, guild_id, settings: dict):
    """Persist settings to Turso and update the cache immediately.

    The cache is updated before the DB write so the writer sees its own change
    without a Turso round-trip. A failed Turso write is logged but does not
    roll back the cache; the bot is the authoritative writer here and will
    reconcile on retry.
    """
    pool = await get_pool()
    if pool is None:
        return
    key = get_settings_cache_key(table, guild_id)
    await settings_cache.set(key, dict(settings))
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
    statements = [
        ("CREATE TABLE IF NOT EXISTS bot_stats (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS guild_data (guild_id TEXT PRIMARY KEY, data TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS mod_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS mod_log (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, user_id TEXT, user_name TEXT, action TEXT, reason TEXT DEFAULT '', moderator TEXT DEFAULT '', created_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS mod_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, action TEXT, target_id TEXT, target_name TEXT DEFAULT '', reason TEXT DEFAULT '', moderator TEXT DEFAULT '', duration INTEGER, status TEXT DEFAULT 'pending', created_at REAL, request_id TEXT UNIQUE)", ()),
        ("CREATE TABLE IF NOT EXISTS muted_users (guild_id TEXT, user_id TEXT, user_name TEXT DEFAULT '', reason TEXT DEFAULT '', end_ts REAL, PRIMARY KEY (guild_id, user_id))", ()),
        ("CREATE TABLE IF NOT EXISTS ai_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS welcome_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS verify_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS leveling_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS leveling_data (guild_id TEXT NOT NULL, user_id TEXT NOT NULL, xp INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, user_id))", ()),
        ("CREATE TABLE IF NOT EXISTS automation_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS autoresponder (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, trigger TEXT NOT NULL, response TEXT NOT NULL, match_type TEXT NOT NULL DEFAULT 'contains', channel_id TEXT, cooldown INTEGER DEFAULT 0, created_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS social_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS invite_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS invite_stats (guild_id TEXT NOT NULL, inviter_id TEXT NOT NULL, code TEXT NOT NULL, uses INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, inviter_id, code))", ()),
        ("CREATE TABLE IF NOT EXISTS ticket_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE TABLE IF NOT EXISTS ticket_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, channel_id TEXT NOT NULL, user_id TEXT NOT NULL, transcript TEXT NOT NULL, closed_at TEXT NOT NULL)", ()),
        ("CREATE TABLE IF NOT EXISTS member_history (guild_id TEXT NOT NULL, timestamp REAL NOT NULL, member_count INTEGER NOT NULL, PRIMARY KEY (guild_id, timestamp))", ()),
        ("CREATE TABLE IF NOT EXISTS message_history (guild_id TEXT NOT NULL, timestamp REAL NOT NULL, message_count INTEGER NOT NULL, PRIMARY KEY (guild_id, timestamp))", ()),
        ("CREATE TABLE IF NOT EXISTS captcha_codes (code TEXT PRIMARY KEY, provider TEXT NOT NULL, guild_id TEXT DEFAULT '', user_id TEXT DEFAULT '', created_at REAL NOT NULL, expires_at REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0)", ()),
        ("CREATE TABLE IF NOT EXISTS automation_graph (guild_id TEXT PRIMARY KEY, nodes TEXT NOT NULL DEFAULT '[]', connections TEXT NOT NULL DEFAULT '[]', updated_at REAL NOT NULL DEFAULT 0)", ()),
        ("CREATE TABLE IF NOT EXISTS automation_runs (guild_id TEXT NOT NULL, bucket_ts REAL NOT NULL, count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, bucket_ts))", ()),
        ("CREATE TABLE IF NOT EXISTS automation_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL DEFAULT 0)", ()),
        ("CREATE TABLE IF NOT EXISTS alias_settings (guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL)", ()),
        ("CREATE INDEX IF NOT EXISTS idx_automation_logs_guild ON automation_logs (guild_id, id DESC)", ()),
        ("CREATE INDEX IF NOT EXISTS idx_autoresponder_guild ON autoresponder (guild_id)", ()),
    ]
    # Migration: ALTER TABLE ADD COLUMN (no IF NOT EXISTS — run individually, ignore "duplicate column")
    migrations = [
        "ALTER TABLE autoresponder ADD COLUMN channel_id TEXT",
        "ALTER TABLE autoresponder ADD COLUMN cooldown INTEGER DEFAULT 0",
        "ALTER TABLE captcha_codes ADD COLUMN guild_id TEXT DEFAULT ''",
        "ALTER TABLE captcha_codes ADD COLUMN user_id TEXT DEFAULT ''",
        "ALTER TABLE mod_log ADD COLUMN moderator TEXT DEFAULT ''",
        "ALTER TABLE mod_actions ADD COLUMN moderator TEXT DEFAULT ''",
        "ALTER TABLE mod_actions ADD COLUMN error TEXT DEFAULT ''",
        "ALTER TABLE mod_actions ADD COLUMN processed_at REAL",
        "ALTER TABLE mod_actions ADD COLUMN request_id TEXT UNIQUE",
    ]
    try:
        await _execute_batch_http(statements)
        logger.info("Ensured database tables exist.")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("Schema was already created concurrently.")
        else:
            logger.error(f"ensure_tables failed: {e}")
    for m_sql in migrations:
        try:
            await _execute_http(m_sql)
        except Exception:
            pass  # column already exists


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
                "SELECT id, guild_id, action, target_id, target_name, reason, duration, request_id "
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


async def update_action_status(request_id: str, status: str, error: str = ""):
    """Update action status by request_id (used by the direct bridge)."""
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE mod_actions SET status = ?, error = ?, processed_at = unixepoch() WHERE request_id = ?",
                status, error, request_id,
            )
    except Exception as e:
        logger.error(f"update_action_status failed: {e}")


async def get_action_by_request_id(request_id: str):
    """Fetch a single action row by request_id."""
    pool = await get_pool()
    if pool is None:
        return None
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, guild_id, action, target_id, target_name, reason, moderator, duration, status, error, created_at, processed_at, request_id "
                "FROM mod_actions WHERE request_id = ?",
                request_id,
            )
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_action_by_request_id failed: {e}")
    return None


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
