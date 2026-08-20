from __future__ import annotations

import os
import logging
import time
import json
import asyncio
from typing import Optional, List

logger = logging.getLogger(__name__)

_conn = None
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


async def get_conn():
    """Get the libsql connection (creates lazily, one per process)."""
    global _conn
    if _conn is not None:
        return _conn
    url = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url:
        logger.warning("TURSO_DATABASE_URL not set")
        return None
    try:
        import libsql
        kwargs = {"database": url}
        if token:
            kwargs["auth_token"] = token
        _conn = libsql.connect(**kwargs)
        return _conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None


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


async def get_pool():
    """Get a connection wrapper (mimics asyncpg pool interface for callers)."""
    conn = await get_conn()
    if conn is None:
        return None
    return _ConnWrapper(conn)


def _parse_settings(raw, defaults: dict) -> dict:
    """Parse JSON or TEXT settings field."""
    if not raw:
        return dict(defaults)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return dict(defaults)
    return dict(defaults)


def _get_cache_key(table: str, guild_id) -> tuple:
    return (table, str(guild_id))


def _get_cached_settings(table: str, guild_id, defaults: dict) -> Optional[dict]:
    key = _get_cache_key(table, guild_id)
    entry = _SETTINGS_CACHE.get(key)
    if entry and time.time() - entry["ts"] < _SETTINGS_CACHE_TTL:
        return dict(entry["value"])
    return None


async def fetchrow_cached(table: str, sql: str, guild_id, defaults: dict):
    """Fetch a settings row with built-in cache (only for settings queries)."""
    cached = _get_cached_settings(table, guild_id, defaults)
    if cached is not None:
        return cached

    conn = await get_conn()
    if conn is None:
        return dict(defaults)

    try:
        def _do():
            return _wrap_row(conn.execute(sql, (str(guild_id),)))
        row = await asyncio.to_thread(_do)
        if row and row.get("settings"):
            value = _parse_settings(row["settings"], defaults)
            key = _get_cache_key(table, guild_id)
            _SETTINGS_CACHE[key] = {"value": value, "ts": time.time()}
            return value
        return dict(defaults)
    except Exception as e:
        logger.debug(f"fetchrow_cached failed for {table}/{guild_id}: {e}")
        return dict(defaults)


def _update_cache(table: str, guild_id, value: dict):
    """Update the cache after a settings save."""
    key = _get_cache_key(table, guild_id)
    _SETTINGS_CACHE[key] = {"value": dict(value), "ts": time.time()}


async def query(sql: str, *args):
    conn = await get_conn()
    if conn is None:
        return []
    def _do():
        return _wrap_rows(conn.execute(sql, args))
    return await asyncio.to_thread(_do)


async def fetchrow(sql: str, *args):
    conn = await get_conn()
    if conn is None:
        return None
    def _do():
        return _wrap_row(conn.execute(sql, args))
    return await asyncio.to_thread(_do)


async def fetchval(sql: str, *args):
    conn = await get_conn()
    if conn is None:
        return None
    def _do():
        row = conn.execute(sql, args).fetchone()
        return row[0] if row else None
    return await asyncio.to_thread(_do)


async def execute(sql: str, *args):
    conn = await get_conn()
    if conn is None:
        return None
    def _do():
        conn.execute(sql, args)
        conn.commit()
    await asyncio.to_thread(_do)
    return "OK"
