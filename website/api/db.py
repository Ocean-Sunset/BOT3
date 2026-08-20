from __future__ import annotations

import os
import logging
import time
import json
import asyncio
from typing import Optional, List

logger = logging.getLogger(__name__)

_url = None
_token = None
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


def _rows_to_records(result: dict) -> List[Record]:
    """Convert a Turso HTTP result object to a list of Record objects."""
    cols = [c["name"] for c in result.get("cols", [])]
    return [Record(cols, tuple(row)) for row in result.get("rows", [])]


async def _execute_http(sql: str, args=()) -> dict:
    """Execute a single SQL statement via Turso HTTP API."""
    import httpx
    global _url, _token
    if not _url:
        raise RuntimeError("TURSO_DATABASE_URL not set")
    headers = {"Content-Type": "application/json"}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    body = {"statements": [{"q": sql, "params": list(args) if args else []}]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_url, json=body, headers=headers)
        data = resp.json()
        if resp.status_code >= 400:
            raise RuntimeError(f"Turso HTTP {resp.status_code}: {data}")
        results = data.get("results", [])
        return results[0] if results else {}


async def _execute_batch_http(statements: list) -> list:
    """Execute multiple SQL statements in one HTTP request."""
    import httpx
    global _url, _token
    if not _url:
        raise RuntimeError("TURSO_DATABASE_URL not set")
    headers = {"Content-Type": "application/json"}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    stmts = []
    for sql, args in statements:
        stmts.append({"q": sql, "params": list(args) if args else []})
    body = {"statements": stmts}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_url, json=body, headers=headers)
        data = resp.json()
        if resp.status_code >= 400:
            raise RuntimeError(f"Turso HTTP {resp.status_code}: {data}")
        return data.get("results", [])


def _to_http_url(url: str) -> str:
    """Convert libsql:// or ws:// URLs to https:// for the HTTP API."""
    if url.startswith("libsql://"):
        return "https://" + url[len("libsql://"):]
    if url.startswith("ws://"):
        return "http://" + url[len("ws://"):]
    if url.startswith("wss://"):
        return "https://" + url[len("wss://"):]
    return url


async def get_conn():
    """Initialize connection settings (lazy, once per process)."""
    global _url, _token
    if _url is not None:
        return True
    raw = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("DATABASE_URL")
    _url = _to_http_url(raw) if raw else None
    _token = os.environ.get("TURSO_AUTH_TOKEN")
    if not _url:
        logger.warning("TURSO_DATABASE_URL not set")
        return None
    return True


class _ConnWrapper:
    """Async wrapper matching the interface callers expect."""

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


async def get_pool():
    """Get a connection wrapper (mimics asyncpg pool interface for callers)."""
    ok = await get_conn()
    if not ok:
        return None
    return _ConnWrapper()


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

    ok = await get_conn()
    if not ok:
        return dict(defaults)

    try:
        result = await _execute_http(sql, (str(guild_id),))
        records = _rows_to_records(result)
        row = records[0] if records else None
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
    ok = await get_conn()
    if not ok:
        return []
    try:
        result = await _execute_http(sql, args)
        return _rows_to_records(result)
    except Exception as e:
        logger.debug(f"query failed: {e}")
        return []


async def fetchrow(sql: str, *args):
    ok = await get_conn()
    if not ok:
        return None
    try:
        result = await _execute_http(sql, args)
        records = _rows_to_records(result)
        return records[0] if records else None
    except Exception as e:
        logger.debug(f"fetchrow failed: {e}")
        return None


async def fetchval(sql: str, *args):
    ok = await get_conn()
    if not ok:
        return None
    try:
        records = await query(sql, *args)
        if records:
            return records[0][0] if len(records[0]) > 0 else None
        return None
    except Exception as e:
        logger.debug(f"fetchval failed: {e}")
        return None


async def execute(sql: str, *args):
    ok = await get_conn()
    if not ok:
        return None
    try:
        await _execute_http(sql, args)
        return "OK"
    except Exception as e:
        logger.debug(f"execute failed: {e}")
        return None
